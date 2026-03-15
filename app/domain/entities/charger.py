from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4


class ChargerStatus(str, Enum):
    AVAILABLE = "available"
    CHARGING = "charging"
    OFFLINE = "offline"
    FAULTED = "faulted"


@dataclass
class Charger:
    id: UUID
    serial_number: str
    location: str
    status: ChargerStatus = ChargerStatus.AVAILABLE

    @staticmethod
    def create(serial_number: str, location: str) -> "Charger":
        return Charger(
            id=uuid4(),
            serial_number=serial_number,
            location=location,
        )

    def start_charging(self):
        if self.status != ChargerStatus.AVAILABLE:
            raise ValueError("Charger not available")
        self.status = ChargerStatus.CHARGING

    def stop_charging(self):
        if self.status != ChargerStatus.CHARGING:
            raise ValueError("Charger is not charging")
        self.status = ChargerStatus.AVAILABLE

    def mark_offline(self):
        self.status = ChargerStatus.OFFLINE

    def mark_faulted(self):
        self.status = ChargerStatus.FAULTED