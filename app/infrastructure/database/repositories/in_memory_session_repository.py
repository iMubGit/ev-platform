from typing import Optional, List
from uuid import UUID

from app.domain.entities import ChargingSession
from app.domain.repositories import SessionRepository


class InMemorySessionRepository(SessionRepository):

    def __init__(self):
        self._store: dict[UUID, ChargingSession] = {}

    async def get_by_id(self, session_id: UUID) -> Optional[ChargingSession]:
        return self._store.get(session_id)

    async def list_by_charger(
        self, charger_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[ChargingSession]:
        results = [
            s for s in self._store.values()
            if s.charger_id == charger_id
        ]
        return results[offset: offset + limit]

    async def list_by_user(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[ChargingSession]:
        results = [
            s for s in self._store.values()
            if s.user_id == user_id
        ]
        return results[offset: offset + limit]

    async def save(self, session: ChargingSession) -> None:
        self._store[session.id] = session

    async def delete(self, session_id: UUID) -> None:
        self._store.pop(session_id, None)