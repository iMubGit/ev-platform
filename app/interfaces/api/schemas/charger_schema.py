from pydantic import BaseModel
from uuid import UUID
from app.domain.entities import ChargerStatus


class ChargerCreateRequest(BaseModel):
    serial_number: str
    location: str


class ChargerResponse(BaseModel):
    id: UUID
    serial_number: str
    location: str
    status: ChargerStatus

    class Config:
        from_attributes = True