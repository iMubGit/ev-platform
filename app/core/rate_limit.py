import hashlib
import ipaddress
import logging

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


# Count attempts from an IP and an IP/username pair atomically.
_INCREMENT_ATTEMPT_SCRIPT = """
local ip_count = redis.call('INCR', KEYS[1])
if ip_count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local identity_count = redis.call('INCR', KEYS[2])
if identity_count == 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[1])
end

return {ip_count, identity_count}
"""


def get_client_ip(request: Request) -> str:
    """Return a validated client IP from the configured trusted source.

    Cloudflare mode must only be enabled when the application ingress is
    guaranteed to pass through Cloudflare's edge. Never trust X-Forwarded-For.
    """
    if settings.trust_cloudflare_client_ip:
        raw_ip = request.headers.get("cf-connecting-ip")
        if raw_ip is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Client IP cannot be determined securely",
            )
    else:
        raw_ip = request.client.host if request.client else None
        if raw_ip is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Client IP cannot be determined securely",
            )

    try:
        return str(ipaddress.ip_address(raw_ip.strip()))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client IP cannot be determined securely",
        ) from exc


def _ip_digest(request: Request) -> str:
    return hashlib.sha256(get_client_ip(request).encode("utf-8")).hexdigest()


def _login_keys(request: Request, username: str) -> tuple[str, str]:
    normalized_username = username.strip().casefold()
    client_ip = get_client_ip(request)
    ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
    identity_digest = hashlib.sha256(
        f"{client_ip}:{normalized_username}".encode("utf-8")
    ).hexdigest()

    return (
        f"ev-platform:login:ip:{ip_digest}",
        f"ev-platform:login:identity:{identity_digest}",
    )


_GLOBAL_FAILED_KEY = "ev-platform:login:global-failed"


# Record failed credentials for monitoring only. This script never blocks login.
_RECORD_FAILURE_SCRIPT = """
local global_count = redis.call('INCR', KEYS[1])
if global_count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local username_count = redis.call('INCR', KEYS[2])
if username_count == 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[1])
end

return {global_count, username_count}
"""


def _username_failure_key(username: str) -> str:
    normalized_username = username.strip().casefold()
    username_digest = hashlib.sha256(normalized_username.encode("utf-8")).hexdigest()
    return f"ev-platform:login:username-failed:{username_digest}"


async def consume_login_attempt(request: Request, username: str) -> bool:
    ip_key, identity_key = _login_keys(request, username)

    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            counts = await redis.eval(
                _INCREMENT_ATTEMPT_SCRIPT,
                2,
                ip_key,
                identity_key,
                settings.login_rate_limit_window_seconds,
            )
    except (RedisError, OSError, TimeoutError) as exc:
        # Authentication must not continue without the configured limiter.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login protection is temporarily unavailable",
        ) from exc

    ip_count, identity_count = (int(count) for count in counts)
    # Do not hard-lock a shared IP. Require a fresh CAPTCHA after the
    # configured IP threshold; the caller verifies it before checking a password.
    return (
        identity_count > settings.login_captcha_identity_threshold
        or ip_count > settings.login_captcha_ip_threshold
    )


async def consume_captcha_verified_attempt(request: Request) -> None:
    """Limit password checks that have already passed CAPTCHA verification."""
    key = f"ev-platform:login:captcha-verified:{_ip_digest(request)}"
    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            count = await redis.eval(
                """
                local count = redis.call('INCR', KEYS[1])
                if count == 1 then
                    redis.call('EXPIRE', KEYS[1], ARGV[1])
                end
                return count
                """,
                1,
                key,
                settings.login_captcha_verified_window_seconds,
            )
    except (RedisError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login protection is temporarily unavailable",
        ) from exc

    if int(count) > settings.login_captcha_verified_attempts_per_ip:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many CAPTCHA-verified login attempts from this IP. Try again later.",
            headers={
                "Retry-After": str(settings.login_captcha_verified_window_seconds)
            },
        )


async def clear_login_attempts(request: Request, username: str) -> None:
    # Clear only this username/IP pair. Preserve shared-IP and CAPTCHA-verified
    # counters so one person's successful login cannot reset protection for others.
    _, identity_key = _login_keys(request, username)

    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            await redis.delete(identity_key)
    except (RedisError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login protection is temporarily unavailable",
        ) from exc


async def record_failed_login(username: str) -> None:
    """Record failed credentials for monitoring; this does not lock accounts."""
    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            global_count, username_count = await redis.eval(
                _RECORD_FAILURE_SCRIPT,
                2,
                _GLOBAL_FAILED_KEY,
                _username_failure_key(username),
                settings.login_rate_limit_window_seconds,
            )
    except (RedisError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login protection is temporarily unavailable",
        ) from exc

    # Log once when each alert threshold is first reached in the time window.
    if int(username_count) == settings.login_rate_limit_username_alert:
        logger.warning(
            "Repeated failed logins for one username; CAPTCHA/risk review may be needed"
        )
    if int(global_count) == settings.login_rate_limit_global_alert:
        logger.warning(
            "Platform-wide failed-login alert threshold reached; review login activity"
        )
