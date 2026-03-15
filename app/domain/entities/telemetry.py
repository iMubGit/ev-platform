from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class TelemetryEvent:
    charger_id: UUID
    timestamp: datetime
    voltage: float
    current: float
    temperature: float
    id: UUID = field(default_factory=uuid4)

    @property
    def power_kw(self) -> float:
        return (self.voltage * self.current) / 1000