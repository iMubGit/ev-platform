from app.domain.exceptions.base import EntityNotFoundError, BusinessRuleViolationError


class ChargerNotFoundError(EntityNotFoundError):
    """Raised when a charger cannot be found."""
    pass


class ChargerNotAvailableError(BusinessRuleViolationError):
    """Raised when a charger is not in AVAILABLE state."""
    pass


class ChargerNotChargingError(BusinessRuleViolationError):
    """Raised when a charger is not in CHARGING state."""
    pass