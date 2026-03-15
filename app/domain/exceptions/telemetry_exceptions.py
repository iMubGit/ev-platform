from app.domain.exceptions.base import EntityNotFoundError


class TelemetryChargerNotFoundError(EntityNotFoundError):
    """Raised when telemetry is submitted for a non-existent charger."""
    pass