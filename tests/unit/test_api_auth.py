import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import hash_password, create_access_token
from app.main import app


@pytest.fixture
async def client(monkeypatch):
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )

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


class FakeRedis:
    counters = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, key):
        return self.counters.get(key)

    async def eval(self, script, number_of_keys, *args):
        if number_of_keys == 1:
            key, window = args
            count = self.counters.get(key, 0) + 1
            self.counters[key] = count
            return count

        ip_key, identity_key, window = args
        ip_count = self.counters.get(ip_key, 0) + 1
        identity_count = self.counters.get(identity_key, 0) + 1
        self.counters[ip_key] = ip_count
        self.counters[identity_key] = identity_count
        return [ip_count, identity_count]

    async def delete(self, *keys):
        for key in keys:
            self.counters.pop(key, None)


@pytest.mark.asyncio
async def test_login_is_rate_limited_after_five_attempts(client, monkeypatch):
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    for _ in range(5):
        response = await client.post(
            "/auth/token",
            json={"username": settings.admin_username, "password": "wrong"},
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": "wrong"},
    )

    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "900"


@pytest.mark.asyncio
async def test_login_fails_closed_when_redis_is_unavailable(client, monkeypatch):
    from app.core import rate_limit

    class UnavailableRedis:
        async def __aenter__(self):
            raise ConnectionError("Redis is unavailable")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: UnavailableRedis(),
    )
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    response = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": "wrong"},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_global_failed_login_limit_applies_across_usernames(client, monkeypatch):
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )
    monkeypatch.setattr(settings, "login_rate_limit_global_failed", 3)
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    for index, username in enumerate(("first", "second", "third"), start=1):
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(f"192.0.2.{index}", 12345)),
            base_url="http://test",
        ) as ip_client:
            response = await ip_client.post(
                "/auth/token",
                json={"username": username, "password": "wrong"},
            )
        assert response.status_code == 401

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.4", 12345)),
        base_url="http://test",
    ) as new_ip_client:
        blocked = await new_ip_client.post(
            "/auth/token",
            json={"username": "fourth", "password": "wrong"},
        )

    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "900"
    assert FakeRedis.counters[rate_limit._GLOBAL_FAILED_KEY] == 3
