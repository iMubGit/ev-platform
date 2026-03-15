from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.entities import Charger


class ChargerRepository(ABC):

    @abstractmethod
    async def get_by_id(self, charger_id: UUID) -> Optional[Charger]:
        """Retrieve a charger by its ID."""
        pass

    @abstractmethod
    async def get_by_serial(self, serial_number: str) -> Optional[Charger]:
        """Retrieve a charger by its serial number."""
        pass

    @abstractmethod
    async def list_all(self) -> List[Charger]:
        """List all chargers in the system."""
        pass

    @abstractmethod
    async def save(self, charger: Charger) -> None:
        """Persist a charger entity."""
        pass

    @abstractmethod
    async def delete(self, charger_id: UUID) -> None:
        """Remove a charger."""
        pass