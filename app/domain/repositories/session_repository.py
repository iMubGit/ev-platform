from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.entities import ChargingSession


class SessionRepository(ABC):

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Optional[ChargingSession]:
        """Retrieve a session by ID."""
        pass

    @abstractmethod
    async def list_by_charger(self, charger_id: UUID) -> List[ChargingSession]:
        """Retrieve all sessions for a charger."""
        pass

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> List[ChargingSession]:
        """Retrieve all sessions for a user."""
        pass

    @abstractmethod
    async def save(self, session: ChargingSession) -> None:
        """Persist a charging session."""
        pass

    @abstractmethod
    async def delete(self, session_id: UUID) -> None:
        """Delete a charging session."""
        pass