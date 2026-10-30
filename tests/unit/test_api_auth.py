import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import hash_password, create_access_token
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client


def test_secret_key_must_be_provided():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, _env_prefix="TEST_MISSING_SECRET_")


def test_only_hs256_signing_algorithm_is_allowed():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="unit-test-signing-key-that-is-long-enough",
            algorithm="none",
        )


PROTECTED_REQUESTS = [
    (
        "POST",
        "/chargers/",
        {"serial_number": "AUTH-001", "location": "Osogbo"},
    ),
    ("GET", "/chargers/", None),
    ("GET", f"/chargers/{uuid4()}", None),
    ("DELETE", f"/chargers/{uuid4()}", None),
    (
        "POST",
        "/telemetry/",
        {
            "charger_id": str(uuid4()),
            "voltage": 400.0,
            "current": 32.0,
            "temperature": 45.0,
        },
    ),
]


@pytest.mark.parametrize("method,path,payload", PROTECTED_REQUESTS)
@pytest.mark.asyncio
async def test_protected_routes_reject_missing_token(
    client, method, path, payload
):
    response = await client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_protected_route_rejects_invalid_token(client):
    response = await client.get(
        "/chargers/",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_token_with_non_uuid_subject(client):
    token = create_access_token(subject="not-a-user-uuid")
    response = await client.get(
        "/chargers/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_fails_closed_when_admin_password_is_not_configured(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "admin_password_hash", None)

    response = await client.post(
        "/auth/token",
        json={"username": "admin", "password": "anything"},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_login_token_can_access_protected_route(client, monkeypatch):
    password = "Unit-test-only-strong-password-42!"
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password(password),
    )

    login = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": password},
    )

    assert login.status_code == 200
    token = login.json()["access_token"]

    response = await client.get(
        "/chargers/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client, monkeypatch):
    password_hash = hash_password("Correct-unit-test-password-42!")
    monkeypatch.setattr(settings, "admin_password_hash", password_hash)

    response = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": "wrong-password"},
    )

    assert response.status_code == 401
