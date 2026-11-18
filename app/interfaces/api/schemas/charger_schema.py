from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities import ChargerStatus


class ChargerCreateRequest(BaseModel):
    serial_number: str
    location: str


class ChargerResponse(BaseModel):
    id: UUID
    serial_number: str
    location: str
    status: ChargerStatus

    model_config = ConfigDict(from_attributes=True)
