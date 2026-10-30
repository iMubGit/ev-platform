import os

import httpx
import pytest

from app.core import captcha
from app.core.config import settings


DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"


@pytest.mark.asyncio
async def test_cloudflare_siteverify_responds_but_test_token_cannot_pass_login_action(monkeypatch):
    monkeypatch.setattr(
        settings,
        "turnstile_secret_key",
        os.environ["TURNSTILE_TEST_PASS_SECRET"],
    )
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)

    # First inspect Cloudflare's actual response so a failure tells us
    # whether the problem is the remote test fixture or our response handling.
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            captcha.TURNSTILE_VERIFY_URL,
            data={
                "secret": settings.turnstile_secret_key,
                "response": DUMMY_TOKEN,
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("metadata", {}).get("result_with_testing_key") is True

    # A Cloudflare test-key response is not proof of a login-action token.
    assert await captcha.verify_turnstile_token(DUMMY_TOKEN) is False


@pytest.mark.asyncio
async def test_cloudflare_siteverify_rejects_official_failing_test_token(monkeypatch):
    monkeypatch.setattr(
        settings,
        "turnstile_secret_key",
        os.environ["TURNSTILE_TEST_FAIL_SECRET"],
    )
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)

    assert await captcha.verify_turnstile_token(
        DUMMY_TOKEN,
        expected_action="test",
    ) is False


@pytest.mark.asyncio
async def test_cloudflare_siteverify_rejects_already_spent_test_token(monkeypatch):
    monkeypatch.setattr(
        settings,
        "turnstile_secret_key",
        os.environ["TURNSTILE_TEST_DUPLICATE_SECRET"],
    )
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)

    assert await captcha.verify_turnstile_token(
        DUMMY_TOKEN,
        expected_action="test",
    ) is False
