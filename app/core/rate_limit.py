import hashlib

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


# Count all login attempts, not only failed ones. This makes the limit atomic
# and prevents many simultaneous guesses from bypassing a failed-attempt check.
_INCREMENT_SCRIPT = """
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


async def consume_login_attempt(request: Request, username: str) -> None:
    ip_key, identity_key = _login_keys(request, username)

    try:
        async with Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            counts = await redis.eval(
                _INCREMENT_SCRIPT,
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
    if (
        ip_count > settings.login_rate_limit_per_ip
        or identity_count > settings.login_rate_limit_per_identity
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={
                "Retry-After": str(settings.login_rate_limit_window_seconds)
            },
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
