"""Pydantic models for DevArmor Core."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class SkillStatus(str, Enum):
    """Skill installation status."""

    INSTALLED = "installed"
    PENDING_UPGRADE = "pending_upgrade"
    UPGRADE_IN_PROGRESS = "upgrade_in_progress"
    REMOVE_IN_PROGRESS = "remove_in_progress"
    FAILED = "failed"


class EventType(str, Enum):
    """Types of events that can be published."""

    SKILL_INSTALLED = "skill:installed"
    SKILL_UPGRADED = "skill:upgraded"
    SKILL_REMOVED = "skill:removed"
    POLICY_UPDATED = "policy:updated"
    POLICY_VIOLATED = "policy:violated"
    ACCESS_DENIED = "access:denied"
    AUDIT_LOG = "audit:log"


class CostLimit(BaseModel):
    """Cost limit configuration."""

    amount: float = Field(..., gt=0, description="Cost limit amount")
    currency: str = Field(default="USD", description="Currency code")
    period: str = Field(default="monthly", description="Time period (monthly, yearly)")
    threshold_warning: float = Field(default=0.8, ge=0, le=1, description="Warn at % of limit")


class CostControlPolicy(BaseModel):
    """Cost control policy configuration."""

    enabled: bool = Field(default=True)
    global_limit: Optional[CostLimit] = None
    service_limits: dict[str, CostLimit] = Field(default_factory=dict)
    auto_shutdown_enabled: bool = Field(default=False)
    auto_shutdown_threshold: float = Field(default=1.0, ge=0, le=1)


class SecurityPolicy(BaseModel):
    """Security policy configuration."""

    enabled: bool = Field(default=True)
    require_approval: bool = Field(default=True)
    forbidden_patterns: list[str] = Field(default_factory=list, description="Regex patterns for forbidden operations")
    allowed_domains: Optional[set[str]] = None
    block_external_api_calls: bool = Field(default=False)


class SkillPermission(BaseModel):
    """Permission for a specific skill."""

    skill_name: str
    allowed_commands: list[str] = Field(default_factory=list)
    cost_limit: Optional[CostLimit] = None
    require_approval: bool = Field(default=False)
    max_concurrent_runs: int = Field(default=1, ge=1)
    rate_limit_per_hour: Optional[int] = None


class SkillPermissionsPolicy(BaseModel):
    """Policy for skill permissions and resource limits."""

    enabled: bool = Field(default=True)
    default_permissions: list[SkillPermission] = Field(default_factory=list)
    skill_allowlist: list[str] = Field(default_factory=list, description="Allowed skill names (empty = all)")
    skill_blocklist: list[str] = Field(default_factory=list, description="Blocked skill names")
    require_signature_verification: bool = Field(default=False)
    max_total_concurrent_skills: int = Field(default=5, ge=1)


class PolicyConfig(BaseModel):
    """Complete policy configuration."""

    version: str = Field(default="1.0.0")
    cost_control: CostControlPolicy = Field(default_factory=CostControlPolicy)
    security: SecurityPolicy = Field(default_factory=SecurityPolicy)
    skill_permissions: SkillPermissionsPolicy = Field(default_factory=SkillPermissionsPolicy)
    custom_policies: dict[str, Any] = Field(default_factory=dict)

    @validator("version")
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        if not v:
            return v
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be in format X.Y.Z")
        try:
            [int(p) for p in parts]
        except ValueError:
            raise ValueError("Version parts must be numeric")
        return v


class SkillInfo(BaseModel):
    """Information about an installed skill."""

    name: str
    version: str
    status: SkillStatus
    installed_at: datetime
    last_updated: Optional[datetime] = None
    permissions: Optional[SkillPermission] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    """Published event."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    skill_name: Optional[str] = None
    actor: Optional[str] = None
    action: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    severity: str = Field(default="info", description="info, warning, error, critical")


class AuditLogEntry(BaseModel):
    """Audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: str
    actor: str
    action: str
    resource: str
    result: str = Field(description="success, failure, denied")
    details: dict[str, Any] = Field(default_factory=dict)
    policy_evaluation: Optional[dict[str, Any]] = None


class PolicyEvaluation(BaseModel):
    """Result of evaluating a policy."""

    allowed: bool
    violated_policies: list[str] = Field(default_factory=list)
    reason: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class LifecycleOperation(BaseModel):
    """Lifecycle operation (install/upgrade/remove)."""

    skill_name: str
    operation: str = Field(description="install, upgrade, remove")
    version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(description="pending, in_progress, completed, failed")
    error: Optional[str] = None
    result: dict[str, Any] = Field(default_factory=dict)
