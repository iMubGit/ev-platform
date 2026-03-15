from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories import ChargerRepository, SessionRepository
from app.domain.exceptions import ChargerNotFoundError, SessionNotFoundError


@dataclass
class StopChargingInput:
    session_id: UUID
    energy_kwh: float


@dataclass
class StopChargingOutput:
    session_id: UUID
    charger_id: UUID
    energy_kwh: float
    duration_minutes: float


class StopChargingUseCase:

    def __init__(
        self,
        charger_repo: ChargerRepository,
        session_repo: SessionRepository,
    ):
        self.charger_repo = charger_repo
        self.session_repo = session_repo

    async def execute(self, input: StopChargingInput) -> StopChargingOutput:
        # 1. Fetch the session
        session = await self.session_repo.get_by_id(input.session_id)
        if session is None:
            raise SessionNotFoundError(
                f"Session {input.session_id} not found"
            )

        # 2. Fetch the charger
        charger = await self.charger_repo.get_by_id(session.charger_id)
        if charger is None:
            raise ChargerNotFoundError(
                f"Charger {session.charger_id} not found"
            )

        # 3. Apply domain business rules
        session.stop(energy_kwh=input.energy_kwh)
        charger.stop_charging()

        # 4. Persist both
        await self.session_repo.save(session)
        await self.charger_repo.save(charger)

        # 5. Return output
        return StopChargingOutput(
            session_id=session.id,
            charger_id=charger.id,
            energy_kwh=session.energy_kwh,
            duration_minutes=session.duration_minutes,
        )