from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.dependencies import get_charger_repo
from app.core.security import create_access_token
from app.main import app


@pytest.mark.asyncio
async def test_configured_administrator_can_register_charger():
    serial_number = f"ADMIN-{uuid4()}"
    token = create_access_token(subject=str(settings.admin_user_id))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chargers/",
            json={"serial_number": serial_number, "location": "Osogbo"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["serial_number"] == serial_number
    assert body["location"] == "Osogbo"
    assert body["status"] == "available"
    assert body["id"]


@pytest.mark.asyncio
async def test_authenticated_non_admin_cannot_register_charger():
    serial_number = f"NONADMIN-{uuid4()}"
    token = create_access_token(subject=str(uuid4()))
    repo = get_charger_repo()
    before = await repo.list_all()
    before_ids = {charger.id for charger in before}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chargers/",
            json={"serial_number": serial_number, "location": "Osogbo"},
            headers={"Authorization": f"Bearer {token}"},
        )

    after = await repo.list_all()
    after_ids = {charger.id for charger in after}

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator permission required"
    assert after_ids == before_ids
    assert all(charger.serial_number != serial_number for charger in after)
