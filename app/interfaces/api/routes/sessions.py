from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.core.dependencies import (
    get_start_charging_use_case,
    get_stop_charging_use_case,
)
from app.application.use_cases import (
    StartChargingUseCase,
    StartChargingInput,
    StopChargingUseCase,
    StopChargingInput,
)
from app.domain.exceptions import (
    ChargerNotFoundError,
    SessionNotFoundError,
    ChargerNotAvailableError,
    ChargerNotChargingError,
)
from app.interfaces.api.schemas import (
    StartSessionRequest,
    StopSessionRequest,
    SessionResponse,
    StopSessionResponse,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionResponse, status_code=201)
async def start_session(
    request: StartSessionRequest,
    use_case: StartChargingUseCase = Depends(get_start_charging_use_case),
):
    try:
        result = await use_case.execute(
            StartChargingInput(
                charger_id=request.charger_id,
                user_id=request.user_id,
            )
        )
        return SessionResponse(
            session_id=result.session_id,
            charger_id=result.charger_id,
            user_id=result.user_id,
        )
    except ChargerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ChargerNotAvailableError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{session_id}/stop", response_model=StopSessionResponse)
async def stop_session(
    session_id: UUID,
    request: StopSessionRequest,
    use_case: StopChargingUseCase = Depends(get_stop_charging_use_case),
):
    try:
        result = await use_case.execute(
            StopChargingInput(
                session_id=session_id,
                energy_kwh=request.energy_kwh,
            )
        )
        return StopSessionResponse(
            session_id=result.session_id,
            charger_id=result.charger_id,
            energy_kwh=result.energy_kwh,
            duration_minutes=result.duration_minutes,
        )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ChargerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ChargerNotChargingError as e:
        raise HTTPException(status_code=409, detail=str(e))