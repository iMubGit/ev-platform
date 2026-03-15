class DomainException(Exception):
    """Base class for all domain exceptions."""
    pass


class EntityNotFoundError(DomainException):
    """Raised when a requested entity does not exist."""
    pass


class BusinessRuleViolationError(DomainException):
    """Raised when a domain business rule is violated."""
    pass