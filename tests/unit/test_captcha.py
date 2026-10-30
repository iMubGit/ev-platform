import httpx
import pytest
from fastapi import HTTPException

from app.core import captcha
from app.core.config import settings


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class MockAsyncClient:
    response_payload = {}
    request_data = None

    def __init__(self, timeout):
        assert timeout == 5.0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, data):
        assert url == captcha.TURNSTILE_VERIFY_URL
        type(self).request_data = data
        return MockResponse(type(self).response_payload)


@pytest.mark.asyncio
async def test_turnstile_verification_accepts_successful_login_token(monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", "test-secret")
    monkeypatch.setattr(settings, "turnstile_expected_hostname", "example.test")
    monkeypatch.setattr(captcha.httpx, "AsyncClient", MockAsyncClient)
    MockAsyncClient.response_payload = {
        "success": True,
        "action": "login",
        "hostname": "example.test",
    }

    result = await captcha.verify_turnstile_token("one-time-token", "192.0.2.10")

    assert result is True
    assert MockAsyncClient.request_data == {
        "secret": "test-secret",
        "response": "one-time-token",
        "remoteip": "192.0.2.10",
    }


@pytest.mark.asyncio
async def test_turnstile_rejects_token_for_another_action(monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", "test-secret")
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)
    monkeypatch.setattr(captcha.httpx, "AsyncClient", MockAsyncClient)
    MockAsyncClient.response_payload = {
        "success": True,
        "action": "password-reset",
        "hostname": "example.test",
    }

    assert await captcha.verify_turnstile_token("wrong-action-token") is False


@pytest.mark.asyncio
async def test_turnstile_fails_closed_when_secret_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", None)

    with pytest.raises(HTTPException) as error:
        await captcha.verify_turnstile_token("one-time-token")

    assert error.value.status_code == 503

@pytest.mark.parametrize("error_code", ["timeout-or-duplicate", "invalid-input-response"])
@pytest.mark.asyncio
async def test_turnstile_rejects_stale_token(monkeypatch, error_code):
    monkeypatch.setattr(settings, "turnstile_secret_key", "test-secret")
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)
    monkeypatch.setattr(captcha.httpx, "AsyncClient", MockAsyncClient)
    MockAsyncClient.response_payload = {
        "success": False,
        "error-codes": [error_code],
    }

    assert await captcha.verify_turnstile_token("stale-token") is False

@pytest.mark.asyncio
async def test_turnstile_fails_closed_when_cloudflare_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", "test-secret")

    class UnavailableClient:
        def __init__(self, timeout):
            assert timeout == 5.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, data):
            request = httpx.Request("POST", url)
            raise httpx.ConnectError("Cloudflare unavailable", request=request)

    monkeypatch.setattr(captcha.httpx, "AsyncClient", UnavailableClient)

    with pytest.raises(HTTPException) as error:
        await captcha.verify_turnstile_token("valid-looking-token")

    assert error.value.status_code == 503
