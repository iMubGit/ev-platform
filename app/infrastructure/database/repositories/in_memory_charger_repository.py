from typing import Optional, List
from uuid import UUID

from app.domain.entities import Charger
from app.domain.repositories import ChargerRepository


class InMemoryChargerRepository(ChargerRepository):

    def __init__(self):
        self._store: dict[UUID, Charger] = {}

    async def get_by_id(self, charger_id: UUID) -> Optional[Charger]:
        return self._store.get(charger_id)

    async def get_by_serial(self, serial_number: str) -> Optional[Charger]:
        for charger in self._store.values():
            if charger.serial_number == serial_number:
                return charger
        return None

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Charger]:
        all_chargers = list(self._store.values())
        return all_chargers[offset: offset + limit]

    async def save(self, charger: Charger) -> None:
        self._store[charger.id] = charger

    async def delete(self, charger_id: UUID) -> None:
        self._store.pop(charger_id, None)