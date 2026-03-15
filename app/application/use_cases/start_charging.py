from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import ChargingSession
from app.domain.repositories import ChargerRepository, SessionRepository
from app.domain.exceptions import ChargerNotFoundError


@dataclass
class StartChargingInput:
    charger_id: UUID
    user_id: UUID


@dataclass
class StartChargingOutput:
    session_id: UUID
    charger_id: UUID
    user_id: UUID


class StartChargingUseCase:

    def __init__(
        self,
        charger_repo: ChargerRepository,
        session_repo: SessionRepository,
    ):
        self.charger_repo = charger_repo
        self.session_repo = session_repo

    async def execute(self, input: StartChargingInput) -> StartChargingOutput:
        # 1. Fetch the charger
        charger = await self.charger_repo.get_by_id(input.charger_id)
        if charger is None:
            raise ChargerNotFoundError(
                f"Charger {input.charger_id} not found"
            )

        # 2. Apply domain business rule
        charger.start_charging()

        # 3. Create a new session
        session = ChargingSession.start(
            charger_id=charger.id,
            user_id=input.user_id,
        )

        # 4. Persist both
        await self.charger_repo.save(charger)
        await self.session_repo.save(session)

        # 5. Return output
        return StartChargingOutput(
            session_id=session.id,
            charger_id=charger.id,
            user_id=input.user_id,
        )