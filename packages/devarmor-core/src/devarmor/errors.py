"""Exception classes for DevArmor Core."""

from typing import Any, Optional


class DevArmorError(Exception):
    """Base exception for all DevArmor errors."""

    def __init__(self, message: str, code: str = "UNKNOWN", details: Optional[dict[str, Any]] = None):
        """Initialize exception with message and error code.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConfigurationError(DevArmorError):
    """Configuration loading or validation error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize configuration error."""
        super().__init__(message, code="CONFIG_ERROR", details=details)


class PolicyError(DevArmorError):
    """Policy parsing or evaluation error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize policy error."""
        super().__init__(message, code="POLICY_ERROR", details=details)


class PolicyViolation(DevArmorError):
    """Policy violation error."""

    def __init__(
        self, message: str, violated_policies: Optional[list[str]] = None, details: Optional[dict[str, Any]] = None
    ):
        """Initialize policy violation."""
        super().__init__(message, code="POLICY_VIOLATION", details=details)
        self.violated_policies = violated_policies or []


class AccessDenied(DevArmorError):
    """Access denied error."""

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize access denied error."""
        super().__init__(message, code="ACCESS_DENIED", details=details)
        self.resource = resource
        self.action = action


class LifecycleError(DevArmorError):
    """Skill lifecycle operation error (install/upgrade/remove)."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        skill_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize lifecycle error."""
        super().__init__(message, code="LIFECYCLE_ERROR", details=details)
        self.operation = operation
        self.skill_name = skill_name


class StateError(DevArmorError):
    """Invalid state transition or operation."""

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        requested_state: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize state error."""
        super().__init__(message, code="STATE_ERROR", details=details)
        self.current_state = current_state
        self.requested_state = requested_state


class ValidationError(DevArmorError):
    """Data validation error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize validation error."""
        super().__init__(message, code="VALIDATION_ERROR", details=details)
        self.field = field
        self.value = value


class NotFoundError(DevArmorError):
    """Resource not found error."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize not found error."""
        super().__init__(message, code="NOT_FOUND", details=details)
        self.resource_type = resource_type
        self.resource_id = resource_id
