from typing import Optional, List
from uuid import UUID

from app.domain.entities import TelemetryEvent
from app.domain.repositories import TelemetryRepository


class InMemoryTelemetryRepository(TelemetryRepository):

    def __init__(self):
        self._store: List[TelemetryEvent] = []

    async def save(self, event: TelemetryEvent) -> None:
        self._store.append(event)

    async def list_by_charger(
        self, charger_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[TelemetryEvent]:
        results = [
            e for e in self._store
            if e.charger_id == charger_id
        ]
        return results[offset: offset + limit]

    async def get_latest_by_charger(self, charger_id: UUID) -> Optional[TelemetryEvent]:
        results = [
            e for e in self._store
            if e.charger_id == charger_id
        ]
        if not results:
            return None
        return max(results, key=lambda e: e.timestamp)