from app.domain.exceptions.base import EntityNotFoundError, BusinessRuleViolationError


class SessionNotFoundError(EntityNotFoundError):
    """Raised when a charging session cannot be found."""
    pass


class SessionAlreadyStoppedError(BusinessRuleViolationError):
    """Raised when attempting to stop an already stopped session."""
    pass


class InvalidEnergyValueError(BusinessRuleViolationError):
    """Raised when an invalid energy value is provided."""
    pass