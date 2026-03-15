from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


@dataclass
class ChargingSession:
    id: UUID
    charger_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    energy_kwh: float = 0.0

    @staticmethod
    def start(charger_id: UUID, user_id: UUID) -> "ChargingSession":
        return ChargingSession(
            id=uuid4(),
            charger_id=charger_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
        )

    def stop(self, energy_kwh: float):
        if self.ended_at is not None:
            raise ValueError("Session already stopped")
        if energy_kwh < 0:
            raise ValueError("Energy cannot be negative")
        self.ended_at = datetime.utcnow()
        self.energy_kwh = energy_kwh

    @property
    def duration_minutes(self) -> Optional[float]:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() / 60