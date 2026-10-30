import os
import uuid

import pytest
from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core import rate_limit
from app.core.config import settings


def _request_for_ip(ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/auth/token",
            "raw_path": b"/auth/token",
            "query_string": b"",
            "headers": [],
            "client": (ip, 12345),
            "server": ("test", 80),
        }
    )


@pytest.mark.asyncio
async def test_real_redis_enforces_login_rules_and_preserves_shared_ip_history(
    monkeypatch,
):
    redis_url = os.environ["REDIS_URL"]
    monkeypatch.setattr(settings, "redis_url", redis_url)
    monkeypatch.setattr(settings, "login_captcha_ip_threshold", 20)
    monkeypatch.setattr(settings, "login_captcha_identity_threshold", 5)
    monkeypatch.setattr(settings, "login_rate_limit_window_seconds", 900)
    monkeypatch.setattr(settings, "login_captcha_verified_attempts_per_ip", 2)
    monkeypatch.setattr(settings, "login_captcha_verified_window_seconds", 3600)

    # Use a unique client address so parallel CI runs cannot share counters.
    octet = uuid.uuid4().int % 250 + 1
    request = _request_for_ip(f"198.18.0.{octet}")
    username = f"integration-{uuid.uuid4().hex}"
    ip_key, identity_key = rate_limit._login_keys(request, username)
    verified_key = (
        f"ev-platform:login:captcha-verified:{rate_limit._ip_digest(request)}"
    )

    async with Redis.from_url(redis_url, decode_responses=True) as redis:
        await redis.delete(ip_key, identity_key, verified_key)

    try:
        # The real Lua script increments both keys atomically in Redis.
        for attempt in range(20):
            assert await rate_limit.consume_login_attempt(request, username) is False

        assert await rate_limit.consume_login_attempt(request, username) is True

        async with Redis.from_url(redis_url, decode_responses=True) as redis:
            assert int(await redis.get(ip_key)) == 21
            assert int(await redis.get(identity_key)) == 21
            assert 0 < await redis.ttl(ip_key) <= 900
            assert 0 < await redis.ttl(identity_key) <= 900

        # Successful login cleanup must preserve the shared IP counter.
        await rate_limit.clear_login_attempts(request, username)
        async with Redis.from_url(redis_url, decode_responses=True) as redis:
            assert await redis.get(ip_key) == "21"
            assert await redis.get(identity_key) is None

        # CAPTCHA-verified attempts use a distinct real Redis counter.
        await rate_limit.consume_captcha_verified_attempt(request)
        await rate_limit.consume_captcha_verified_attempt(request)
        with pytest.raises(HTTPException) as error:
            await rate_limit.consume_captcha_verified_attempt(request)

        assert error.value.status_code == 429
        assert error.value.headers["Retry-After"] == "3600"
        async with Redis.from_url(redis_url, decode_responses=True) as redis:
            assert int(await redis.get(verified_key)) == 3
            assert 0 < await redis.ttl(verified_key) <= 3600
    finally:
        async with Redis.from_url(redis_url, decode_responses=True) as redis:
            await redis.delete(ip_key, identity_key, verified_key)
