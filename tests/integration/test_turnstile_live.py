import os

import pytest

from app.core import captcha
from app.core.config import settings


DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"


@pytest.mark.asyncio
async def test_cloudflare_siteverify_accepts_official_test_token(monkeypatch):
    monkeypatch.setattr(
        settings,
        "turnstile_secret_key",
        os.environ["TURNSTILE_TEST_PASS_SECRET"],
    )
    monkeypatch.setattr(settings, "turnstile_expected_hostname", None)

    # Cloudflare's official test keys return action="test", not "login".
    # This verifies the real Siteverify request/response without weakening login.
    assert await captcha.verify_turnstile_token(
        DUMMY_TOKEN,
        expected_action="test",
    ) is True


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
