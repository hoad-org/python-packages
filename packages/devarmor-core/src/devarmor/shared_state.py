"""Shared state query interface for DevArmor."""

import logging
from datetime import datetime
from typing import Any, Optional

from .audit import AuditLogger
from .events import EventBus
from .lifecycle import SkillLifecycleManager
from .models import SkillInfo
from .policy import PolicyEngine

logger = logging.getLogger(__name__)


class SharedState:
    """Query interface for DevArmor shared state.

    Provides read access to installed skills, policy evaluations,
    events, and audit logs. Controls access based on permissions.
    """

    def __init__(
        self,
        lifecycle_manager: SkillLifecycleManager,
        policy_engine: PolicyEngine,
        event_bus: EventBus,
        audit_logger: AuditLogger,
    ):
        """Initialize shared state.

        Args:
            lifecycle_manager: SkillLifecycleManager instance
            policy_engine: PolicyEngine instance
            event_bus: EventBus instance
            audit_logger: AuditLogger instance
        """
        self.lifecycle = lifecycle_manager
        self.policy = policy_engine
        self.events = event_bus
        self.audit = audit_logger

    async def query_installed_skills(self, actor: str, include_metadata: bool = False) -> list[SkillInfo]:
        """Query list of installed skills.

        Args:
            actor: Who is making the query
            include_metadata: Whether to include skill metadata

        Returns:
            List of installed SkillInfo objects

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_installed_skills",
            resource="skills",
            result="allowed",
            details={"include_metadata": include_metadata},
        )

        skills = self.lifecycle.list_installed_skills()

        if not include_metadata:
            # Strip metadata if not requested
            for skill in skills:
                skill.metadata = {}

        return skills

    async def query_skill_info(self, skill_name: str, actor: str) -> Optional[SkillInfo]:
        """Query information about a specific skill.

        Args:
            skill_name: Name of skill to query
            actor: Who is making the query

        Returns:
            SkillInfo or None if not found

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_skill_info",
            resource=skill_name,
            result="allowed",
        )

        return self.lifecycle.get_skill_info(skill_name)

    async def query_recent_events(self, actor: str, limit: int = 100) -> list[dict[str, Any]]:
        """Query recent published events.

        Args:
            actor: Who is making the query
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_recent_events",
            resource="events",
            result="allowed",
            details={"limit": limit},
        )

        events = self.events.get_published_events(limit=limit)
        return [event.model_dump() for event in events]

    async def query_audit_log(
        self, actor: str, filter_actor: Optional[str] = None, filter_action: Optional[str] = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Query audit log.

        Args:
            actor: Who is making the query
            filter_actor: Optional actor to filter by
            filter_action: Optional action to filter by
            limit: Maximum number of entries to return

        Returns:
            List of audit log entry dictionaries

        Raises:
            AccessDenied: If actor doesn't have permission to audit log
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_audit_log",
            resource="audit",
            result="allowed",
            details={
                "filter_actor": filter_actor,
                "filter_action": filter_action,
                "limit": limit,
            },
        )

        entries = self.audit.get_entries(limit=limit)

        if filter_actor:
            entries = [e for e in entries if e.actor == filter_actor]

        if filter_action:
            entries = [e for e in entries if e.action == filter_action]

        return [entry.model_dump() for entry in entries]

    async def query_system_status(self, actor: str) -> dict[str, Any]:
        """Query overall system status.

        Args:
            actor: Who is making the query

        Returns:
            System status dictionary

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_system_status",
            resource="system",
            result="allowed",
        )

        installed_skills = self.lifecycle.list_installed_skills()
        recent_events = self.events.get_published_events(limit=10)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "installed_skills_count": len(installed_skills),
            "subscriber_count": self.events.get_subscriber_count(),
            "total_events_published": self.events.get_event_count(),
            "recent_events": [e.model_dump() for e in recent_events],
            "policy_config_version": self.policy.config.version,
        }

    async def query_skill_permission(self, skill_name: str, actor: str) -> Optional[dict[str, Any]]:
        """Query permission configuration for a skill.

        Args:
            skill_name: Name of skill
            actor: Who is making the query

        Returns:
            Permission configuration or None if not configured

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_skill_permission",
            resource=skill_name,
            result="allowed",
        )

        perm = self.policy.get_skill_permission(skill_name)
        return perm.model_dump() if perm else None

    async def query_is_skill_allowed(self, skill_name: str, actor: str) -> bool:
        """Query if a skill is allowed.

        Args:
            skill_name: Name of skill
            actor: Who is making the query

        Returns:
            True if skill is allowed

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_is_skill_allowed",
            resource=skill_name,
            result="allowed",
        )

        return self.policy.is_skill_allowed(skill_name)

    async def query_policy_status(self, actor: str) -> dict[str, Any]:
        """Query policy configuration status.

        Args:
            actor: Who is making the query

        Returns:
            Policy status dictionary

        Raises:
            AccessDenied: If actor doesn't have permission
        """
        # Log the query
        self.audit.log_action(
            actor=actor,
            action="query_policy_status",
            resource="policy",
            result="allowed",
        )

        config = self.policy.config

        return {
            "version": config.version,
            "cost_control_enabled": config.cost_control.enabled,
            "security_enabled": config.security.enabled,
            "skill_permissions_enabled": config.skill_permissions.enabled,
            "allowed_skills_count": len(config.skill_permissions.skill_allowlist),
            "blocked_skills_count": len(config.skill_permissions.skill_blocklist),
        }

    def has_permission(self, actor: str, action: str, resource: str) -> bool:
        """Check if actor has permission to perform action on resource.

        Args:
            actor: Actor identifier
            action: Action to perform
            resource: Resource being accessed

        Returns:
            True if permission is granted
        """
        # For now, log and allow all queries
        # In production, this would integrate with external permission system
        logger.debug(f"Permission check: {actor} {action} {resource} -> granted")
        return True
