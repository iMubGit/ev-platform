from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List

from app.core.dependencies import get_charger_repo
from app.domain.entities import Charger
from app.domain.exceptions import ChargerNotFoundError
from app.infrastructure.database.repositories import InMemoryChargerRepository
from app.interfaces.api.schemas import ChargerCreateRequest, ChargerResponse

router = APIRouter(prefix="/chargers", tags=["Chargers"])


@router.post("/", response_model=ChargerResponse, status_code=201)
async def create_charger(
    request: ChargerCreateRequest,
    repo: InMemoryChargerRepository = Depends(get_charger_repo),
):
    charger = Charger.create(
        serial_number=request.serial_number,
        location=request.location,
    )
    await repo.save(charger)
    return ChargerResponse(
        id=charger.id,
        serial_number=charger.serial_number,
        location=charger.location,
        status=charger.status,
    )


@router.get("/", response_model=List[ChargerResponse])
async def list_chargers(
    limit: int = 100,
    offset: int = 0,
    repo: InMemoryChargerRepository = Depends(get_charger_repo),
):
    chargers = await repo.list_all(limit=limit, offset=offset)
    return [
        ChargerResponse(
            id=c.id,
            serial_number=c.serial_number,
            location=c.location,
            status=c.status,
        )
        for c in chargers
    ]


@router.get("/{charger_id}", response_model=ChargerResponse)
async def get_charger(
    charger_id: UUID,
    repo: InMemoryChargerRepository = Depends(get_charger_repo),
):
    charger = await repo.get_by_id(charger_id)
    if charger is None:
        raise HTTPException(status_code=404, detail="Charger not found")
    return ChargerResponse(
        id=charger.id,
        serial_number=charger.serial_number,
        location=charger.location,
        status=charger.status,
    )


@router.delete("/{charger_id}", status_code=204)
async def delete_charger(
    charger_id: UUID,
    repo: InMemoryChargerRepository = Depends(get_charger_repo),
):
    charger = await repo.get_by_id(charger_id)
    if charger is None:
        raise HTTPException(status_code=404, detail="Charger not found")
    await repo.delete(charger_id)