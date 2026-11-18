from pydantic import BaseModel, validator
from uuid import UUID
from app.domain.entities import ChargerStatus


class ChargerCreateRequest(BaseModel):
    serial_number: str
    location: str

    @validator("serial_number", "location")
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or contain only whitespace")
        return value


class ChargerResponse(BaseModel):
    id: UUID
    serial_number: str
    location: str
    status: ChargerStatus

    class Config:
        from_attributes = True
