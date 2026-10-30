import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def diagnostic_settings(monkeypatch):
    monkeypatch.setattr(settings, "staging_diagnostics_enabled", True)
    monkeypatch.setattr(
        settings, "staging_diagnostics_token", "test-diagnostic-token-" + "x" * 32
    )
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)


@pytest.mark.asyncio
async def test_diagnostic_endpoint_is_hidden_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "staging_diagnostics_enabled", False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            json={"expected_public_ip": "203.0.113.10"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_diagnostic_endpoint_hides_itself_for_invalid_token(
    diagnostic_settings,
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            headers={"X-Staging-Diagnostic-Token": "wrong"},
            json={"expected_public_ip": "203.0.113.10"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_diagnostic_compares_expected_ip_and_ignores_forged_xff(
    diagnostic_settings,
):
    async with AsyncClient(
        transport=ASGITransport(
            app=app, client=("192.0.2.20", 12345)
        ),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            headers={
                "X-Staging-Diagnostic-Token": settings.staging_diagnostics_token,
                "CF-Connecting-IP": "203.0.113.10",
                "X-Forwarded-For": "198.51.100.99",
            },
            json={"expected_public_ip": "203.0.113.10"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "cloudflare_header_matches_expected": True,
        "application_ip_matches_expected": True,
    }
    assert "203.0.113.10" not in response.text
    assert "198.51.100.99" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_diagnostic_detects_forged_cloudflare_header(diagnostic_settings):
    async with AsyncClient(
        transport=ASGITransport(
            app=app, client=("192.0.2.20", 12345)
        ),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            headers={
                "X-Staging-Diagnostic-Token": settings.staging_diagnostics_token,
                "CF-Connecting-IP": "198.51.100.99",
                "X-Forwarded-For": "198.51.100.99",
            },
            json={"expected_public_ip": "203.0.113.10"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "cloudflare_header_matches_expected": False,
        "application_ip_matches_expected": False,
    }


@pytest.mark.asyncio
async def test_diagnostic_rejects_invalid_expected_ip(diagnostic_settings):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            headers={"X-Staging-Diagnostic-Token": settings.staging_diagnostics_token},
            json={"expected_public_ip": "not-an-ip"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_diagnostic_requires_long_configured_token(monkeypatch):
    monkeypatch.setattr(settings, "staging_diagnostics_enabled", True)
    monkeypatch.setattr(settings, "staging_diagnostics_token", "too-short")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/__staging__/diagnostics/client-ip",
            headers={"X-Staging-Diagnostic-Token": "too-short"},
            json={"expected_public_ip": "203.0.113.10"},
        )

    assert response.status_code == 503
