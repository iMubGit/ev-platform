from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.dependencies import get_charger_repo
from app.core.security import create_access_token
from app.infrastructure.database.repositories import InMemoryChargerRepository
from app.main import app


@pytest.fixture
def isolated_charger_repo():
    repo = InMemoryChargerRepository()
    app.dependency_overrides[get_charger_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_charger_repo, None)


def admin_headers():
    token = create_access_token(subject=str(settings.admin_user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_serial_but_accepts_new_serial(
    isolated_charger_repo,
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/chargers/",
            json={"serial_number": "CH-001", "location": "Osogbo"},
            headers=admin_headers(),
        )
        duplicate = await client.post(
            "/chargers/",
            json={"serial_number": "CH-001", "location": "Ile-Ife"},
            headers=admin_headers(),
        )
        second = await client.post(
            "/chargers/",
            json={"serial_number": "CH-002", "location": "Ile-Ife"},
            headers=admin_headers(),
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Charger with this serial number already exists"
    assert second.status_code == 201
    assert first.json()["serial_number"] == "CH-001"
    assert second.json()["serial_number"] == "CH-002"
    assert first.json()["id"] != second.json()["id"]
    assert len(await isolated_charger_repo.list_all()) == 2


@pytest.mark.parametrize("field", ["serial_number", "location"])
@pytest.mark.parametrize("blank_value", ["", "   "])
@pytest.mark.asyncio
async def test_registration_rejects_empty_or_whitespace_only_fields(
    isolated_charger_repo, field, blank_value
):
    payload = {"serial_number": f"CH-{uuid4()}", "location": "Osogbo"}
    payload[field] = blank_value

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chargers/", json=payload, headers=admin_headers()
        )

    assert response.status_code == 422
    assert await isolated_charger_repo.list_all() == []


@pytest.mark.asyncio
async def test_registration_requires_authentication(isolated_charger_repo):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chargers/",
            json={"serial_number": f"CH-{uuid4()}", "location": "Osogbo"},
        )

    assert response.status_code == 401
    assert await isolated_charger_repo.list_all() == []


@pytest.mark.asyncio
async def test_registration_response_contains_id_serial_location_and_available_status(
    isolated_charger_repo,
):
    serial_number = f"CH-{uuid4()}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chargers/",
            json={"serial_number": serial_number, "location": "Osogbo"},
            headers=admin_headers(),
        )

    assert response.status_code == 201
    body = response.json()
    UUID(body["id"])
    assert body["serial_number"] == serial_number
    assert body["location"] == "Osogbo"
    assert body["status"] == "available"
