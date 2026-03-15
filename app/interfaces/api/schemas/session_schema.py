from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class StartSessionRequest(BaseModel):
    charger_id: UUID
    user_id: UUID


class StopSessionRequest(BaseModel):
    energy_kwh: float


class SessionResponse(BaseModel):
    session_id: UUID
    charger_id: UUID
    user_id: UUID


class StopSessionResponse(BaseModel):
    session_id: UUID
    charger_id: UUID
    energy_kwh: float
    duration_minutes: float