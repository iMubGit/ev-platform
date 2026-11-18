import pytest
from fastapi import HTTPException

from app.infrastructure.database.repositories import InMemoryChargerRepository
from app.interfaces.api.routes.chargers import create_charger
from app.interfaces.api.schemas import ChargerCreateRequest


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_serial_but_accepts_new_serial():
    repo = InMemoryChargerRepository()

    first = await create_charger(
        ChargerCreateRequest(serial_number="CH-001", location="Osogbo"),
        repo,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_charger(
            ChargerCreateRequest(serial_number="CH-001", location="Ile-Ife"),
            repo,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Charger with this serial number already exists"

    second = await create_charger(
        ChargerCreateRequest(serial_number="CH-002", location="Ile-Ife"),
        repo,
    )

    assert first.serial_number == "CH-001"
    assert second.serial_number == "CH-002"
    assert first.id != second.id
    assert len(await repo.list_all()) == 2
