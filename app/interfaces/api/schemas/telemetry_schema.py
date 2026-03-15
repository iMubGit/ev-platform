from pydantic import BaseModel
from uuid import UUID


class TelemetryIngestRequest(BaseModel):
    charger_id: UUID
    voltage: float
    current: float
    temperature: float


class TelemetryIngestResponse(BaseModel):
    event_id: UUID
    charger_id: UUID
    power_kw: float