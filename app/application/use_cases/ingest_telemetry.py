from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities import TelemetryEvent
from app.domain.repositories import ChargerRepository, TelemetryRepository
from app.domain.exceptions import TelemetryChargerNotFoundError


@dataclass
class IngestTelemetryInput:
    charger_id: UUID
    voltage: float
    current: float
    temperature: float


@dataclass
class IngestTelemetryOutput:
    event_id: UUID
    charger_id: UUID
    power_kw: float


class IngestTelemetryUseCase:

    def __init__(
        self,
        charger_repo: ChargerRepository,
        telemetry_repo: TelemetryRepository,
    ):
        self.charger_repo = charger_repo
        self.telemetry_repo = telemetry_repo

    async def execute(self, input: IngestTelemetryInput) -> IngestTelemetryOutput:
        # 1. Confirm charger exists
        charger = await self.charger_repo.get_by_id(input.charger_id)
        if charger is None:
            raise TelemetryChargerNotFoundError(
                f"Charger {input.charger_id} not found"
            )

        # 2. Create telemetry event
        event = TelemetryEvent(
            charger_id=input.charger_id,
            timestamp=datetime.utcnow(),
            voltage=input.voltage,
            current=input.current,
            temperature=input.temperature,
        )

        # 3. Persist the event
        await self.telemetry_repo.save(event)

        # 4. Return output
        return IngestTelemetryOutput(
            event_id=event.id,
            charger_id=event.charger_id,
            power_kw=event.power_kw,
        )