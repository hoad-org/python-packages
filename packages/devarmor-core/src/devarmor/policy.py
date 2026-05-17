"""Policy engine and evaluation."""

import logging
import re
from typing import Any, Optional

from .models import (
    PolicyConfig,
    PolicyEvaluation,
    SkillPermission,
)

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluate policies and make authorization decisions."""

    def __init__(self, policy_config: PolicyConfig):
        """Initialize policy engine.

        Args:
            policy_config: PolicyConfig to use for evaluations
        """
        self.config = policy_config

    def evaluate_skill_installation(
        self,
        skill_name: str,
        version: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate if a skill can be installed.

        Args:
            skill_name: Name of skill to install
            version: Version being installed
            actor: Who is installing (e.g., "user", "system")
            details: Additional context for evaluation

        Returns:
            PolicyEvaluation result
        """
        details = details or {}
        violated = []

        # Check skill permissions policy
        if self.config.skill_permissions.enabled:
            perm_result = self._evaluate_skill_permissions(
                skill_name=skill_name, action="install", actor=actor, details=details
            )
            if not perm_result.allowed:
                violated.extend(perm_result.violated_policies)

        # Check security policy
        if self.config.security.enabled and self.config.security.require_approval:
            violated.append("security:require_approval")

        if violated:
            return PolicyEvaluation(
                allowed=False,
                violated_policies=violated,
                reason=f"Installation of {skill_name} violates policies: {', '.join(violated)}",
            )

        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason=f"Installation of {skill_name} allowed",
        )

    def evaluate_skill_upgrade(
        self,
        skill_name: str,
        old_version: str,
        new_version: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate if a skill can be upgraded.

        Args:
            skill_name: Name of skill to upgrade
            old_version: Current version
            new_version: Version being upgraded to
            actor: Who is upgrading
            details: Additional context for evaluation

        Returns:
            PolicyEvaluation result
        """
        details = {**(details or {}), "old_version": old_version, "new_version": new_version}

        # Reuse installation evaluation
        return self.evaluate_skill_installation(
            skill_name=skill_name,
            version=new_version,
            actor=actor,
            details=details,
        )

    def evaluate_skill_removal(
        self,
        skill_name: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate if a skill can be removed.

        Args:
            skill_name: Name of skill to remove
            actor: Who is removing
            details: Additional context for evaluation

        Returns:
            PolicyEvaluation result
        """
        details = details or {}

        # Skill removal is generally allowed if basic security passes
        if self.config.security.enabled and self.config.security.require_approval:
            return PolicyEvaluation(
                allowed=False,
                violated_policies=["security:require_approval"],
                reason=f"Removal of {skill_name} requires approval",
            )

        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason=f"Removal of {skill_name} allowed",
        )

    def evaluate_cost_control(
        self,
        resource_type: str,
        estimated_cost: float,
        actor: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate if operation would violate cost control policy.

        Args:
            resource_type: Type of resource (e.g., "compute", "storage")
            estimated_cost: Estimated cost of operation
            actor: Who is performing the operation
            details: Additional context

        Returns:
            PolicyEvaluation result
        """
        if not self.config.cost_control.enabled:
            return PolicyEvaluation(allowed=True, violated_policies=[], reason="Cost control disabled")

        details = details or {}
        violated = []

        # Check global limit
        if self.config.cost_control.global_limit:
            if estimated_cost > self.config.cost_control.global_limit.amount:
                violated.append("cost_control:exceeds_global_limit")

        # Check service limits
        if resource_type in self.config.cost_control.service_limits:
            service_limit = self.config.cost_control.service_limits[resource_type]
            if estimated_cost > service_limit.amount:
                violated.append(f"cost_control:exceeds_{resource_type}_limit")

        if violated:
            return PolicyEvaluation(
                allowed=False,
                violated_policies=violated,
                reason=f"Operation would exceed cost limits: {', '.join(violated)}",
            )

        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason="Cost control policy satisfied",
        )

    def evaluate_security_policy(
        self,
        action: str,
        actor: str,
        target: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate if action satisfies security policy.

        Args:
            action: Action being performed (e.g., "exec_command", "access_secret")
            actor: Who is performing the action
            target: Target of the action
            details: Additional context

        Returns:
            PolicyEvaluation result
        """
        if not self.config.security.enabled:
            return PolicyEvaluation(allowed=True, violated_policies=[], reason="Security policy disabled")

        details = details or {}
        violated = []

        # Check forbidden patterns
        for pattern in self.config.security.forbidden_patterns:
            try:
                if re.search(pattern, action) or re.search(pattern, target):
                    violated.append(f"security:forbidden_pattern_{pattern}")
            except re.error as e:
                logger.warning(f"Invalid regex pattern in security policy: {pattern}: {str(e)}")

        # Check allowed domains if configured
        if self.config.security.allowed_domains is not None:
            if target not in self.config.security.allowed_domains:
                violated.append("security:not_in_allowed_domains")

        # Check external API calls
        if self.config.security.block_external_api_calls:
            if details.get("is_external_call"):
                violated.append("security:external_api_calls_blocked")

        if violated:
            return PolicyEvaluation(
                allowed=False,
                violated_policies=violated,
                reason=f"Security policy violations: {', '.join(violated)}",
            )

        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason="Security policy satisfied",
        )

    def _evaluate_skill_permissions(
        self,
        skill_name: str,
        action: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate skill permissions.

        Args:
            skill_name: Name of skill
            action: Action being performed
            actor: Who is performing
            details: Additional context

        Returns:
            PolicyEvaluation result
        """
        if not self.config.skill_permissions.enabled:
            return PolicyEvaluation(allowed=True, violated_policies=[], reason="Skill permissions disabled")

        details = details or {}
        violated = []

        # Check blocklist
        if skill_name in self.config.skill_permissions.skill_blocklist:
            violated.append("skill_permissions:blocked")

        # Check allowlist (if non-empty)
        if self.config.skill_permissions.skill_allowlist:
            if skill_name not in self.config.skill_permissions.skill_allowlist:
                violated.append("skill_permissions:not_in_allowlist")

        # Find permission for this skill
        perm = self._find_skill_permission(skill_name)

        # Check allowed commands
        if perm and action not in perm.allowed_commands and perm.allowed_commands:
            violated.append(f"skill_permissions:action_not_allowed_{action}")

        if violated:
            return PolicyEvaluation(
                allowed=False,
                violated_policies=violated,
                reason=f"Skill permission violations: {', '.join(violated)}",
            )

        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason=f"Skill {skill_name} permissions allow action {action}",
        )

    def _find_skill_permission(self, skill_name: str) -> Optional[SkillPermission]:
        """Find permission config for a skill.

        Args:
            skill_name: Name of skill

        Returns:
            SkillPermission or None if not found
        """
        for perm in self.config.skill_permissions.default_permissions:
            if perm.skill_name == skill_name:
                return perm
        return None

    def get_skill_permission(self, skill_name: str) -> Optional[SkillPermission]:
        """Get permission configuration for a skill.

        Args:
            skill_name: Name of skill

        Returns:
            SkillPermission or None
        """
        return self._find_skill_permission(skill_name)

    def is_skill_allowed(self, skill_name: str) -> bool:
        """Check if skill is generally allowed.

        Args:
            skill_name: Name of skill

        Returns:
            True if skill is allowed
        """
        if not self.config.skill_permissions.enabled:
            return True

        if skill_name in self.config.skill_permissions.skill_blocklist:
            return False

        if self.config.skill_permissions.skill_allowlist:
            return skill_name in self.config.skill_permissions.skill_allowlist

        return True
