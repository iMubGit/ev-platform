from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.entities import TelemetryEvent


class TelemetryRepository(ABC):

    @abstractmethod
    async def save(self, event: TelemetryEvent) -> None:
        """Persist a telemetry event."""
        pass

    @abstractmethod
    async def list_by_charger(
        self, charger_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[TelemetryEvent]:
        """Retrieve telemetry history for a charger."""
        pass

    @abstractmethod
    async def get_latest_by_charger(self, charger_id: UUID) -> Optional[TelemetryEvent]:
        """Retrieve the most recent telemetry event for a charger."""
        pass