"""DevArmor Core - Skill Governance Platform."""

import logging

from .api import DevArmorAPI
from .audit import AuditLogger, AuditReader
from .config import ConfigLoader, load_config
from .errors import (
    AccessDenied,
    ConfigurationError,
    DevArmorError,
    LifecycleError,
    NotFoundError,
    PolicyError,
    PolicyViolation,
    StateError,
    ValidationError,
)
from .events import EventBus, EventSubscriber
from .lifecycle import SkillLifecycleManager
from .models import (
    AuditLogEntry,
    CostControlPolicy,
    CostLimit,
    Event,
    EventType,
    LifecycleOperation,
    PolicyConfig,
    PolicyEvaluation,
    SecurityPolicy,
    SkillInfo,
    SkillPermission,
    SkillPermissionsPolicy,
    SkillStatus,
)
from .policy import PolicyEngine
from .shared_state import SharedState
from .skill_framework import (
    BaseDevArmorSkill,
    BaseSkillCLI,
    BaseSkillConfig,
    CommandSignature,
    MockDevArmorAPI,
    PolicyDecision,
    SkillAuthError,
    SkillConfigError,
    SkillException,
    SkillOperationBlockedError,
    SkillRateLimitError,
    SkillTestBase,
    SkillValidationError,
    ValidationResult,
    command,
)

__version__ = "0.1.0"
__author__ = "Craig Hoad"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

__all__ = [
    # Main API
    "DevArmorAPI",
    # Configuration
    "ConfigLoader",
    "load_config",
    "BaseSkillConfig",
    # Models
    "PolicyConfig",
    "SkillInfo",
    "SkillStatus",
    "Event",
    "EventType",
    "AuditLogEntry",
    "PolicyEvaluation",
    "LifecycleOperation",
    "CostControlPolicy",
    "CostLimit",
    "SecurityPolicy",
    "SkillPermission",
    "SkillPermissionsPolicy",
    "ValidationResult",
    "PolicyDecision",
    # Core Components
    "PolicyEngine",
    "SkillLifecycleManager",
    "EventBus",
    "EventSubscriber",
    "AuditLogger",
    "AuditReader",
    "SharedState",
    # Skill Framework
    "BaseDevArmorSkill",
    "BaseSkillCLI",
    "SkillTestBase",
    "MockDevArmorAPI",
    "CommandSignature",
    "command",
    # Errors
    "DevArmorError",
    "ConfigurationError",
    "PolicyError",
    "PolicyViolation",
    "AccessDenied",
    "LifecycleError",
    "StateError",
    "ValidationError",
    "NotFoundError",
    "SkillException",
    "SkillConfigError",
    "SkillAuthError",
    "SkillOperationBlockedError",
    "SkillRateLimitError",
    "SkillValidationError",
]
