"""Main DevArmor API class."""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .audit import AuditLogger
from .config import load_config
from .errors import AccessDenied, PolicyViolation
from .events import EventBus
from .lifecycle import SkillLifecycleManager
from .models import EventType as EventTypeEnum
from .models import PolicyConfig
from .policy import PolicyEngine
from .shared_state import SharedState

logger = logging.getLogger(__name__)


class DevArmorAPI:
    """Main DevArmor Core API.

    Async-first API for managing skills, enforcing policies, and
    tracking all decisions through events and audit logs.
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        log_dir: Optional[Path] = None,
    ):
        """Initialize DevArmorAPI.

        Args:
            config_dir: Directory for configuration (default: ~/.devarmor)
            skills_dir: Directory for skill metadata (default: ~/.devarmor/skills)
            log_dir: Directory for audit logs (default: ~/.devarmor/audit)
        """
        self._initialized = False
        self.config_dir = config_dir
        self.skills_dir = skills_dir
        self.log_dir = log_dir

        # Components (lazy initialized)
        self._policy_config: Optional[PolicyConfig] = None
        self._policy_engine: Optional[PolicyEngine] = None
        self._lifecycle_manager: Optional[SkillLifecycleManager] = None
        self._event_bus: Optional[EventBus] = None
        self._audit_logger: Optional[AuditLogger] = None
        self._shared_state: Optional[SharedState] = None

    async def initialize(self) -> None:
        """Initialize all components (call before using API).

        This is an async initialization to support any future async setup.
        """
        if self._initialized:
            return

        logger.info("Initializing DevArmor API")

        # Load configuration
        self._policy_config = load_config(repo_config_dir=self.config_dir)
        logger.debug(f"Loaded policy configuration v{self._policy_config.version}")

        # Initialize components
        self._policy_engine = PolicyEngine(self._policy_config)
        self._lifecycle_manager = SkillLifecycleManager(skills_dir=self.skills_dir)
        self._event_bus = EventBus()
        self._audit_logger = AuditLogger(log_dir=self.log_dir)

        # Initialize shared state
        self._shared_state = SharedState(
            lifecycle_manager=self._lifecycle_manager,
            policy_engine=self._policy_engine,
            event_bus=self._event_bus,
            audit_logger=self._audit_logger,
        )

        self._initialized = True
        logger.info("DevArmor API initialized successfully")

    @property
    def policy_engine(self) -> PolicyEngine:
        """Get policy engine (raises if not initialized)."""
        assert self._policy_engine is not None
        return self._policy_engine

    @property
    def lifecycle_manager(self) -> SkillLifecycleManager:
        """Get lifecycle manager (raises if not initialized)."""
        assert self._lifecycle_manager is not None
        return self._lifecycle_manager

    @property
    def event_bus(self) -> EventBus:
        """Get event bus (raises if not initialized)."""
        assert self._event_bus is not None
        return self._event_bus

    @property
    def audit_logger(self) -> AuditLogger:
        """Get audit logger (raises if not initialized)."""
        assert self._audit_logger is not None
        return self._audit_logger

    @property
    def shared_state(self) -> SharedState:
        """Get shared state (raises if not initialized)."""
        assert self._shared_state is not None
        return self._shared_state

    async def install_skill(
        self,
        skill_name: str,
        version: str,
        actor: str = "system",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Install a skill.

        Args:
            skill_name: Name of skill to install
            version: Version to install
            actor: Who is installing
            metadata: Additional metadata

        Returns:
            Installation result

        Raises:
            PolicyViolation: If installation violates policies
            AccessDenied: If actor lacks permission
        """
        await self._ensure_initialized()

        logger.info(f"Install skill requested: {skill_name} v{version} by {actor}")

        # Evaluate policies
        evaluation = self.policy_engine.evaluate_skill_installation(
            skill_name=skill_name,
            version=version,
            actor=actor,
        )

        # Log policy evaluation
        self.audit_logger.log_policy_evaluation(
            actor=actor,
            action="install",
            resource=skill_name,
            evaluation=evaluation,
        )

        if not evaluation.allowed:
            # Publish denied event
            await self.event_bus.publish_access_denied(
                actor=actor,
                action="install",
                resource=skill_name,
                reason=evaluation.reason,
            )
            raise PolicyViolation(
                evaluation.reason,
                violated_policies=evaluation.violated_policies,
            )

        # Perform installation
        try:
            skill_info = await self.lifecycle_manager.install_skill(
                skill_name=skill_name,
                version=version,
                actor=actor,
                metadata=metadata,
            )

            # Publish success event
            await self.event_bus.publish_skill_installed(
                skill_name=skill_name,
                version=version,
                actor=actor,
            )

            # Log success
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="install",
                version=version,
                result="success",
            )

            return skill_info.model_dump()
        except Exception as e:
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="install",
                version=version,
                result="failure",
                error=str(e),
            )
            raise

    async def upgrade_skill(
        self,
        skill_name: str,
        new_version: str,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Upgrade an installed skill.

        Args:
            skill_name: Name of skill to upgrade
            new_version: Version to upgrade to
            actor: Who is upgrading

        Returns:
            Upgrade result

        Raises:
            PolicyViolation: If upgrade violates policies
            AccessDenied: If actor lacks permission
        """
        await self._ensure_initialized()

        logger.info(f"Upgrade skill requested: {skill_name} to v{new_version} by {actor}")

        # Get current skill info
        skill_info = self.lifecycle_manager.get_skill_info(skill_name)
        if not skill_info:
            raise AccessDenied(f"Skill {skill_name} is not installed")

        # Evaluate policies
        evaluation = self.policy_engine.evaluate_skill_upgrade(
            skill_name=skill_name,
            old_version=skill_info.version,
            new_version=new_version,
            actor=actor,
        )

        # Log policy evaluation
        self.audit_logger.log_policy_evaluation(
            actor=actor,
            action="upgrade",
            resource=skill_name,
            evaluation=evaluation,
        )

        if not evaluation.allowed:
            await self.event_bus.publish_access_denied(
                actor=actor,
                action="upgrade",
                resource=skill_name,
                reason=evaluation.reason,
            )
            raise PolicyViolation(
                evaluation.reason,
                violated_policies=evaluation.violated_policies,
            )

        # Perform upgrade
        try:
            upgraded_skill = await self.lifecycle_manager.upgrade_skill(
                skill_name=skill_name,
                new_version=new_version,
                actor=actor,
            )

            # Publish success event
            await self.event_bus.publish_skill_upgraded(
                skill_name=skill_name,
                old_version=skill_info.version,
                new_version=new_version,
                actor=actor,
            )

            # Log success
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="upgrade",
                version=new_version,
                result="success",
            )

            return upgraded_skill.model_dump()
        except Exception as e:
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="upgrade",
                version=new_version,
                result="failure",
                error=str(e),
            )
            raise

    async def remove_skill(
        self,
        skill_name: str,
        actor: str = "system",
    ) -> None:
        """Remove an installed skill.

        Args:
            skill_name: Name of skill to remove
            actor: Who is removing

        Raises:
            PolicyViolation: If removal violates policies
            AccessDenied: If actor lacks permission
        """
        await self._ensure_initialized()

        logger.info(f"Remove skill requested: {skill_name} by {actor}")

        # Evaluate policies
        evaluation = self.policy_engine.evaluate_skill_removal(
            skill_name=skill_name,
            actor=actor,
        )

        # Log policy evaluation
        self.audit_logger.log_policy_evaluation(
            actor=actor,
            action="remove",
            resource=skill_name,
            evaluation=evaluation,
        )

        if not evaluation.allowed:
            await self.event_bus.publish_access_denied(
                actor=actor,
                action="remove",
                resource=skill_name,
                reason=evaluation.reason,
            )
            raise PolicyViolation(
                evaluation.reason,
                violated_policies=evaluation.violated_policies,
            )

        # Perform removal
        try:
            await self.lifecycle_manager.remove_skill(skill_name=skill_name, actor=actor)

            # Publish success event
            await self.event_bus.publish_skill_removed(
                skill_name=skill_name,
                actor=actor,
            )

            # Log success
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="remove",
                version=None,
                result="success",
            )

            logger.info(f"Skill {skill_name} removed successfully")
        except Exception as e:
            self.audit_logger.log_skill_lifecycle(
                skill_name=skill_name,
                operation="remove",
                version=None,
                result="failure",
                error=str(e),
            )
            raise

    async def subscribe_to_events(
        self,
        callback: Callable[[Any], Any],
        event_types: Optional[list[EventTypeEnum]] = None,
        subscriber_id: Optional[str] = None,
    ) -> str:
        """Subscribe to events.

        Args:
            callback: Async callback function to call on events
            event_types: List of event types to subscribe to (None = all)
            subscriber_id: Optional subscriber identifier

        Returns:
            Subscriber ID for later unsubscription
        """
        await self._ensure_initialized()

        return self.event_bus.subscribe(
            callback=callback,
            event_types=event_types,
            subscriber_id=subscriber_id,
        )

    async def unsubscribe_from_events(self, subscriber_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscriber_id: ID of subscriber to remove

        Returns:
            True if unsubscribed
        """
        await self._ensure_initialized()
        return self.event_bus.unsubscribe(subscriber_id)

    async def get_system_status(self, actor: str = "system") -> dict[str, Any]:
        """Get system status.

        Args:
            actor: Who is requesting status

        Returns:
            System status dictionary
        """
        await self._ensure_initialized()
        return await self.shared_state.query_system_status(actor)

    async def list_installed_skills(self, actor: str = "system") -> list[dict[str, Any]]:
        """List installed skills.

        Args:
            actor: Who is making the request

        Returns:
            List of skill information
        """
        await self._ensure_initialized()

        skills = await self.shared_state.query_installed_skills(actor)
        return [s.model_dump() for s in skills]

    async def get_skill_info(self, skill_name: str, actor: str = "system") -> Optional[dict[str, Any]]:
        """Get information about a skill.

        Args:
            skill_name: Name of skill
            actor: Who is making the request

        Returns:
            Skill information or None
        """
        await self._ensure_initialized()

        skill = await self.shared_state.query_skill_info(skill_name, actor)
        return skill.model_dump() if skill else None

    async def get_recent_events(self, actor: str = "system", limit: int = 100) -> list[dict[str, Any]]:
        """Get recent events.

        Args:
            actor: Who is making the request
            limit: Maximum events to return

        Returns:
            List of events
        """
        await self._ensure_initialized()
        return await self.shared_state.query_recent_events(actor, limit)

    async def _ensure_initialized(self) -> None:
        """Ensure API is initialized."""
        if not self._initialized:
            await self.initialize()
