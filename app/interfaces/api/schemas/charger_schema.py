from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.entities import ChargerStatus


class ChargerCreateRequest(BaseModel):
    serial_number: str
    location: str

    @field_validator("serial_number", "location")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or contain only whitespace")
        return value


class ChargerResponse(BaseModel):
    id: UUID
    serial_number: str
    location: str
    status: ChargerStatus

    model_config = ConfigDict(from_attributes=True)
