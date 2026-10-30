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

    failed_login = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": "wrong-password"},
    )
    assert failed_login.status_code == 401

    login = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": password},
    )

    assert login.status_code == 200
    from app.core import rate_limit
    assert FakeRedis.counters[rate_limit._GLOBAL_FAILED_KEY] == 1
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

        first_key, second_key, window = args
        first_count = self.counters.get(first_key, 0) + 1
        second_count = self.counters.get(second_key, 0) + 1
        self.counters[first_key] = first_count
        self.counters[second_key] = second_count
        return [first_count, second_count]

    async def delete(self, *keys):
        for key in keys:
            self.counters.pop(key, None)


@pytest.mark.asyncio
async def test_login_requires_captcha_instead_of_locking_username_ip_pair(
    client, monkeypatch
):
    from app.interfaces.api.routes import auth

    FakeRedis.counters = {}
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

    challenge = await client.post(
        "/auth/token",
        json={"username": settings.admin_username, "password": "wrong"},
    )
    assert challenge.status_code == 403
    assert challenge.json()["detail"]["code"] == "captcha_required"

    async def accept_test_token(token, remote_ip=None):
        return token == "valid-test-token"

    monkeypatch.setattr(auth, "verify_turnstile_token", accept_test_token)
    login = await client.post(
        "/auth/token",
        json={
            "username": settings.admin_username,
            "password": "Correct-unit-test-password-42!",
            "captcha_token": "valid-test-token",
        },
    )

    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_invalid_captcha_does_not_allow_login(client, monkeypatch):
    from app.interfaces.api.routes import auth

    FakeRedis.counters = {}
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    for _ in range(5):
        await client.post(
            "/auth/token",
            json={"username": settings.admin_username, "password": "wrong"},
        )

    async def reject_test_token(token, remote_ip=None):
        return False

    monkeypatch.setattr(auth, "verify_turnstile_token", reject_test_token)
    response = await client.post(
        "/auth/token",
        json={
            "username": settings.admin_username,
            "password": "Correct-unit-test-password-42!",
            "captcha_token": "invalid-test-token",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "captcha_failed"


@pytest.mark.asyncio
async def test_ip_threshold_requires_captcha_instead_of_blocking_shared_ip(
    client, monkeypatch
):
    from app.interfaces.api.routes import auth

    FakeRedis.counters = {}
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    async def accept_test_token(token, remote_ip=None):
        return token == "fresh-valid-token"

    monkeypatch.setattr(auth, "verify_turnstile_token", accept_test_token)

    # Different usernames model legitimate users sharing one public IP.
    for index in range(20):
        response = await client.post(
            "/auth/token",
            json={"username": f"user-{index}", "password": "wrong"},
        )
        assert response.status_code == 401

    challenge = await client.post(
        "/auth/token",
        json={"username": "user-20", "password": "wrong"},
    )
    assert challenge.status_code == 403
    assert challenge.json()["detail"]["code"] == "captcha_required"

    # A valid challenge permits this one request to reach password checking.
    verified_attempt = await client.post(
        "/auth/token",
        json={
            "username": "user-20",
            "password": "wrong",
            "captcha_token": "fresh-valid-token",
        },
    )
    assert verified_attempt.status_code == 401


@pytest.mark.asyncio
async def test_captcha_verified_attempts_have_a_separate_ip_limit(
    client, monkeypatch
):
    from app.interfaces.api.routes import auth
    FakeRedis.counters = {}
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )
    monkeypatch.setattr(settings, "login_captcha_verified_attempts_per_ip", 2)
    monkeypatch.setattr(settings, "login_captcha_verified_window_seconds", 3600)

    async def accept_test_token(token, remote_ip=None):
        return token == "fresh-valid-token"

    monkeypatch.setattr(auth, "verify_turnstile_token", accept_test_token)

    # Cross the normal IP threshold using distinct usernames on one shared IP.
    for index in range(20):
        response = await client.post(
            "/auth/token",
            json={"username": f"shared-user-{index}", "password": "wrong"},
        )
        assert response.status_code == 401

    # Two valid CAPTCHA responses permit two password checks.
    for index in range(2):
        response = await client.post(
            "/auth/token",
            json={
                "username": f"captcha-user-{index}",
                "password": "wrong",
                "captcha_token": "fresh-valid-token",
            },
        )
        assert response.status_code == 401

    # The third verified attempt is rate-limited before password checking.
    limited = await client.post(
        "/auth/token",
        json={
            "username": "captcha-user-third",
            "password": "wrong",
            "captcha_token": "fresh-valid-token",
        },
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "3600"



@pytest.mark.asyncio
async def test_successful_login_clears_identity_but_preserves_shared_ip_counter(
    monkeypatch,
):
    from starlette.requests import Request
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )
    password = "Correct-unit-test-password-42!"
    monkeypatch.setattr(settings, "admin_password_hash", hash_password(password))
    ip_client = AsyncClient(
        transport=ASGITransport(
            app=app,
            client=("203.0.113.77", 12345),
        ),
        base_url="http://test",
    )

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/token",
        "raw_path": b"/auth/token",
        "query_string": b"",
        "headers": [],
        "client": ("203.0.113.77", 12345),
        "server": ("test", 80),
    }
    request = Request(scope)
    ip_key, identity_key = rate_limit._login_keys(request, settings.admin_username)

    async with ip_client:
        failed = await ip_client.post(
            "/auth/token",
            json={"username": settings.admin_username, "password": "wrong"},
        )
        assert failed.status_code == 401

        successful = await ip_client.post(
            "/auth/token",
            json={"username": settings.admin_username, "password": password},
        )
        assert successful.status_code == 200

    assert FakeRedis.counters[ip_key] == 2
    assert identity_key not in FakeRedis.counters


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
async def test_global_failed_login_threshold_monitors_but_does_not_block(
    client, monkeypatch
):
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )
    monkeypatch.setattr(settings, "login_rate_limit_global_alert", 3)
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    for index, username in enumerate(
        ("first", "second", "third", "fourth"), start=1
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(f"192.0.2.{index}", 12345)),
            base_url="http://test",
        ) as ip_client:
            response = await ip_client.post(
                "/auth/token",
                json={"username": username, "password": "wrong"},
            )
        # Crossing the global alert threshold must not lock out later users.
        assert response.status_code == 401

    assert FakeRedis.counters[rate_limit._GLOBAL_FAILED_KEY] == 4


@pytest.mark.asyncio
async def test_username_failure_monitor_counts_across_different_ips(
    client, monkeypatch
):
    from app.core import rate_limit

    FakeRedis.counters = {}
    monkeypatch.setattr(
        rate_limit.Redis,
        "from_url",
        lambda *args, **kwargs: FakeRedis(),
    )
    monkeypatch.setattr(settings, "login_rate_limit_username_alert", 3)
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )

    for index in range(1, 4):
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(f"198.51.100.{index}", 12345)),
            base_url="http://test",
        ) as ip_client:
            response = await ip_client.post(
                "/auth/token",
                json={"username": "admin", "password": "wrong"},
            )
        assert response.status_code == 401

    assert FakeRedis.counters[rate_limit._username_failure_key("admin")] == 3

@pytest.mark.asyncio
async def test_replayed_turnstile_token_is_rejected_on_second_login(client, monkeypatch):
    from app.interfaces.api.routes import auth

    FakeRedis.counters = {}
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("Correct-unit-test-password-42!"),
    )
    verification_calls = 0

    async def verify_once(token, remote_ip=None):
        nonlocal verification_calls
        verification_calls += 1
        return verification_calls == 1 and token == "one-time-token"

    monkeypatch.setattr(auth, "verify_turnstile_token", verify_once)

    for index in range(20):
        response = await client.post(
            "/auth/token",
            json={"username": f"shared-user-{index}", "password": "wrong"},
        )
        assert response.status_code == 401

    first_use = await client.post(
        "/auth/token",
        json={
            "username": "replay-user",
            "password": "wrong",
            "captcha_token": "one-time-token",
        },
    )
    assert first_use.status_code == 401

    second_use = await client.post(
        "/auth/token",
        json={
            "username": "replay-user",
            "password": "wrong",
            "captcha_token": "one-time-token",
        },
    )
    assert second_use.status_code == 403
    assert second_use.json()["detail"]["code"] == "captcha_failed"
    assert verification_calls == 2

