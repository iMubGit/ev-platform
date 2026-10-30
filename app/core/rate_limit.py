import hashlib
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


def _login_keys(request: Request, username: str) -> tuple[str, str]:
    # Use the direct connection address. Do not trust client-supplied
    # X-Forwarded-For headers unless a trusted-proxy setup is added.
    client_ip = request.client.host if request.client else "unknown"
    normalized_username = username.strip().casefold()

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
    # Do not lock a username/IP pair: require a CAPTCHA after repeated attempts.
    # Only the source IP has a hard temporary limit.
    if ip_count > settings.login_rate_limit_per_ip:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts from this IP. Try again later.",
            headers={
                "Retry-After": str(settings.login_rate_limit_window_seconds)
            },
        )

    return (
        identity_count > settings.login_rate_limit_per_identity
        or ip_count > settings.login_captcha_ip_threshold
    )


async def clear_login_attempts(request: Request, username: str) -> None:
    ip_key, identity_key = _login_keys(request, username)

    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            await redis.delete(ip_key, identity_key)
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
