from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_ingest_telemetry_use_case
from app.application.use_cases import (
    IngestTelemetryUseCase,
    IngestTelemetryInput,
)
from app.domain.exceptions import TelemetryChargerNotFoundError
from app.interfaces.api.dependencies import get_current_user
from app.interfaces.api.schemas import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post("/", response_model=TelemetryIngestResponse, status_code=201)
async def ingest_telemetry(
    request: TelemetryIngestRequest,
    current_user: str = Depends(get_current_user),
    use_case: IngestTelemetryUseCase = Depends(get_ingest_telemetry_use_case),
):
    try:
        result = await use_case.execute(
            IngestTelemetryInput(
                charger_id=request.charger_id,
                voltage=request.voltage,
                current=request.current,
                temperature=request.temperature,
            )
        )
        return TelemetryIngestResponse(
            event_id=result.event_id,
            charger_id=result.charger_id,
            power_kw=result.power_kw,
        )
    except TelemetryChargerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
