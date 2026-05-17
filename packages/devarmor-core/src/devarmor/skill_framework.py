"""DevArmor Skill Framework - Base classes for all DevArmor-compliant skills.

This module provides the foundational classes that all skills must inherit from
to integrate with DevArmor's governance, policy, and lifecycle management systems.

Architecture:
- BaseDevArmorSkill: Abstract base for skill implementations
- BaseSkillConfig: Pydantic-based configuration with 4-level hierarchy
- BaseSkillCLI: Async CLI framework with subcommand routing
- SkillTestBase: Testing utilities and fixtures
- SkillException hierarchy: Structured exception types
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field, validator

from .api import DevArmorAPI
from .errors import (
    AccessDenied,
    ConfigurationError,
    DevArmorError,
    LifecycleError,
    PolicyViolation,
    ValidationError,
)
from .models import EventType, PolicyEvaluation, SkillInfo, SkillPermission, SkillStatus

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseSkillConfig")


# ============================================================================
# Exception Hierarchy
# ============================================================================


class SkillException(DevArmorError):
    """Base exception for skill-specific errors."""

    def __init__(self, skill_name: str, message: str, code: str = "SKILL_ERROR", details: Optional[dict[str, Any]] = None):
        """Initialize skill exception.

        Args:
            skill_name: Name of the skill raising the error
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message, code=code, details=details)
        self.skill_name = skill_name


class SkillConfigError(SkillException):
    """Skill configuration error."""

    def __init__(self, skill_name: str, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize config error."""
        super().__init__(skill_name, message, code="SKILL_CONFIG_ERROR", details=details)


class SkillAuthError(SkillException):
    """Skill authentication/authorization error."""

    def __init__(
        self,
        skill_name: str,
        message: str,
        auth_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize auth error."""
        super().__init__(skill_name, message, code="SKILL_AUTH_ERROR", details=details)
        self.auth_type = auth_type


class SkillOperationBlockedError(SkillException):
    """Operation blocked by policy."""

    def __init__(
        self,
        skill_name: str,
        message: str,
        operation: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize operation blocked error."""
        super().__init__(skill_name, message, code="SKILL_OPERATION_BLOCKED", details=details)
        self.operation = operation
        self.reason = reason


class SkillRateLimitError(SkillException):
    """Rate limit exceeded."""

    def __init__(
        self,
        skill_name: str,
        message: str,
        limit_type: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize rate limit error."""
        super().__init__(skill_name, message, code="SKILL_RATE_LIMIT", details=details)
        self.limit_type = limit_type
        self.retry_after = retry_after


class SkillValidationError(SkillException):
    """Skill validation error."""

    def __init__(
        self,
        skill_name: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize validation error."""
        super().__init__(skill_name, message, code="SKILL_VALIDATION_ERROR", details=details)
        self.field = field


# ============================================================================
# Configuration Framework
# ============================================================================


class BaseSkillConfig(BaseModel):
    """Base configuration class for skills with 4-level hierarchy support.

    Configuration hierarchy (priority order):
    1. Environment variables (SKILL_<KEY>=value)
    2. Repo config (.claude/skillname.json)
    3. Master config (~/.devarmor/skillname/config.json)
    4. Code defaults (model defaults)

    Example:
        class MySkillConfig(BaseSkillConfig):
            api_key: str = Field(...)
            timeout: int = Field(default=30)
            debug: bool = Field(default=False)

        config = MySkillConfig.load("my-skill")
    """

    skill_name: str = Field(..., description="Canonical skill name (lowercase, hyphens)")
    version: str = Field(default="0.0.0", description="Skill version (semver)")

    class Config:
        """Pydantic config."""

        # Allow arbitrary types (for complex field types)
        arbitrary_types_allowed = True
        # Extra fields are not allowed
        extra = "forbid"

    @validator("skill_name")
    def validate_skill_name(cls, v: str) -> str:
        """Validate skill name format."""
        if not v or not v.replace("-", "").isalnum():
            raise ValueError("skill_name must be alphanumeric with hyphens only")
        return v.lower()

    @classmethod
    def load(cls: Type[T], skill_name: str, repo_config_dir: Optional[Path] = None) -> T:
        """Load configuration from 4-level hierarchy.

        Args:
            skill_name: Name of skill
            repo_config_dir: Optional repo config directory (overrides default)

        Returns:
            Loaded configuration instance

        Raises:
            SkillConfigError: If configuration is invalid or loading fails

        Implementation notes:
        - Level 1 (lowest priority): Code defaults from model
        - Level 2: Master config (~/.devarmor/skillname/)
        - Level 3: Repo config (.claude/skillname.json)
        - Level 4 (highest priority): Environment variables
        """
        try:
            data: Dict[str, Any] = {"skill_name": skill_name}

            # Level 3: Repo config (if provided)
            if repo_config_dir:
                repo_config_path = repo_config_dir / f"{skill_name}.json"
                if repo_config_path.exists():
                    with open(repo_config_path) as f:
                        repo_data = json.load(f)
                        data.update(repo_data)
                        logger.info(f"Loaded repo config from {repo_config_path}")

            # Level 2: Master config
            master_config_dir = Path.home() / ".devarmor" / skill_name
            if master_config_dir.exists():
                master_config_path = master_config_dir / "config.json"
                if master_config_path.exists():
                    with open(master_config_path) as f:
                        master_data = json.load(f)
                        data.update(master_data)
                        logger.info(f"Loaded master config from {master_config_path}")

            # Level 4: Environment variables (SKILL_<KEY>=value)
            import os

            env_prefix = f"SKILL_{skill_name.upper().replace('-', '_')}_"
            for key, value in os.environ.items():
                if key.startswith(env_prefix):
                    config_key = key[len(env_prefix):].lower()
                    # Try to parse as JSON if it looks like JSON
                    try:
                        data[config_key] = json.loads(value)
                    except json.JSONDecodeError:
                        data[config_key] = value
                    logger.debug(f"Loaded env override: {config_key}")

            return cls(**data)

        except Exception as e:
            raise SkillConfigError(
                skill_name,
                f"Failed to load configuration: {str(e)}",
                details={"error_type": type(e).__name__},
            )

    def save_to_master(self) -> Path:
        """Save configuration to master location (~/.devarmor/skillname/).

        Returns:
            Path where configuration was saved

        Raises:
            SkillConfigError: If save fails
        """
        try:
            config_dir = Path.home() / ".devarmor" / self.skill_name
            config_dir.mkdir(parents=True, exist_ok=True)

            config_path = config_dir / "config.json"
            with open(config_path, "w") as f:
                json.dump(self.dict(exclude={"skill_name"}), f, indent=2, default=str)

            logger.info(f"Saved config to {config_path}")
            return config_path

        except Exception as e:
            raise SkillConfigError(
                self.skill_name,
                f"Failed to save configuration: {str(e)}",
                details={"error_type": type(e).__name__},
            )


# ============================================================================
# Skill Framework
# ============================================================================


class ValidationResult(BaseModel):
    """Result of configuration validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """Decision from policy engine on whether action is allowed."""

    allowed: bool
    reason: str
    violated_policies: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class BaseDevArmorSkill(ABC):
    """Abstract base class for all DevArmor-compliant skills.

    Every skill must inherit from this and implement the required abstract methods.
    This provides hooks into DevArmor's governance and lifecycle management.

    Example:
        class MySkill(BaseDevArmorSkill):
            name = "my-skill"
            version = "1.0.0"
            description = "Does something amazing"
            author = "Craig Hoad"

            async def on_install(self, devarmor: DevArmorAPI) -> None:
                '''Initialize skill on install'''
                await super().on_install(devarmor)
                # Custom install logic

            async def on_upgrade(self, old_version: str, devarmor: DevArmorAPI) -> None:
                '''Migrate state on upgrade'''
                pass

            async def on_remove(self, devarmor: DevArmorAPI) -> None:
                '''Clean up on remove'''
                pass

            async def validate_config(self, config: MySkillConfig) -> ValidationResult:
                '''Validate skill-specific config'''
                result = ValidationResult(valid=True)
                # Validation logic
                return result
    """

    # ========== Metadata (subclasses must override) ==========

    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    author: str = ""

    def __init__(self, config: Optional[BaseSkillConfig] = None, devarmor: Optional[DevArmorAPI] = None):
        """Initialize skill.

        Args:
            config: Skill configuration (optional)
            devarmor: DevArmor API instance (optional)
        """
        if not self.name or not self.version:
            raise SkillException(
                self.name or "unknown",
                "Skill must define name and version class attributes",
                code="SKILL_INIT_ERROR",
            )

        self.config = config
        self.devarmor = devarmor
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    # ========== Lifecycle Hooks (subclasses should override as needed) ==========

    async def on_install(self, devarmor: DevArmorAPI) -> None:
        """Called when skill is first installed.

        Override to initialize skill-specific resources, create databases,
        register endpoints, etc.

        Args:
            devarmor: DevArmor API instance

        Raises:
            LifecycleError: If installation fails
        """
        self.devarmor = devarmor
        self.logger.info(f"Skill {self.name} v{self.version} installed")

    async def on_upgrade(self, old_version: str, devarmor: DevArmorAPI) -> None:
        """Called when skill is upgraded.

        Override to migrate state, run migrations, handle breaking changes, etc.

        Args:
            old_version: Previous version string
            devarmor: DevArmor API instance

        Raises:
            LifecycleError: If upgrade fails
        """
        self.devarmor = devarmor
        self.logger.info(f"Skill {self.name} upgraded from {old_version} to {self.version}")

    async def on_remove(self, devarmor: DevArmorAPI) -> None:
        """Called when skill is being removed.

        Override to clean up resources, delete databases, unregister endpoints, etc.

        Args:
            devarmor: DevArmor API instance

        Raises:
            LifecycleError: If removal fails
        """
        self.logger.info(f"Skill {self.name} removed")

    @abstractmethod
    async def validate_config(self, config: BaseSkillConfig) -> ValidationResult:
        """Validate skill-specific configuration.

        Must be implemented by subclasses to validate skill-specific config options.
        This is called by DevArmor during config updates.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with valid=True if config passes, False otherwise
        """
        pass

    # ========== Policy & Governance ==========

    async def pre_action_check(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """Check if action is allowed by policies before execution.

        This is called before destructive operations. Override to add skill-specific
        policy checks beyond DevArmor's global policies.

        Args:
            action: Action identifier (e.g., "create-issue", "delete-resource")
            params: Action parameters

        Returns:
            PolicyDecision allowing or denying the action

        Raises:
            SkillOperationBlockedError: If action is blocked (caller's responsibility)
        """
        if not self.devarmor:
            return PolicyDecision(
                allowed=False,
                reason="DevArmor not initialized",
            )

        try:
            # Check against DevArmor policy engine
            evaluation = await self.devarmor.evaluate_action(
                skill_name=self.name,
                action=action,
                params=params or {},
            )

            if not evaluation.allowed:
                return PolicyDecision(
                    allowed=False,
                    reason="Policy violation",
                    violated_policies=evaluation.violated_policies,
                    details=evaluation.details,
                )

            return PolicyDecision(
                allowed=True,
                reason="Action allowed",
                details={"evaluation": evaluation.dict()},
            )

        except Exception as e:
            self.logger.error(f"Error evaluating action {action}: {str(e)}")
            return PolicyDecision(
                allowed=False,
                reason=f"Policy evaluation failed: {str(e)}",
            )

    # ========== Event Publishing ==========

    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        severity: str = "info",
        visibility: str = "org",
    ) -> None:
        """Publish an event to DevArmor's event bus.

        Args:
            event_type: Type of event (e.g., "issue-created", "resource-deleted")
            payload: Event payload
            severity: Severity level (info, warning, error, critical)
            visibility: Event visibility (skill, org, global)

        Raises:
            DevArmorError: If publishing fails
        """
        if not self.devarmor:
            self.logger.warning("Cannot publish event: DevArmor not initialized")
            return

        try:
            await self.devarmor.publish_event(
                skill_name=self.name,
                event_type=event_type,
                payload=payload,
                severity=severity,
            )
            self.logger.debug(f"Published event: {event_type}")
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {str(e)}")

    # ========== Shared State Queries ==========

    async def query_shared_state(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query shared state across all skills.

        Allows skills to discover state managed by other skills
        (e.g., find issues created by other skills).

        Args:
            entity_type: Type of entity to query (e.g., "issue", "resource")
            filters: Optional filters (e.g., {"skill_name": "jira-skill"})

        Returns:
            List of matching entities from shared state

        Raises:
            DevArmorError: If query fails
        """
        if not self.devarmor:
            self.logger.warning("Cannot query shared state: DevArmor not initialized")
            return []

        try:
            results = await self.devarmor.query_shared_state(
                entity_type=entity_type,
                filters=filters or {},
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to query shared state {entity_type}: {str(e)}")
            return []

    # ========== Skill Info ==========

    def get_info(self) -> SkillInfo:
        """Get information about this skill.

        Returns:
            SkillInfo model with metadata
        """
        return SkillInfo(
            name=self.name,
            version=self.version,
            status=SkillStatus.INSTALLED,
            installed_at=datetime.utcnow(),
            metadata={
                "description": self.description,
                "author": self.author,
            },
        )


# ============================================================================
# CLI Framework
# ============================================================================


class CommandSignature(BaseModel):
    """Signature of a CLI command."""

    name: str
    handler: str  # Method name on CLI class
    help: str
    params: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class BaseSkillCLI:
    """Base class for skill CLI implementations.

    Provides async command routing, input validation, output formatting,
    and error handling.

    Example:
        class MySkillCLI(BaseSkillCLI):
            skill_name = "my-skill"
            description = "My skill CLI"

            @command(help="Create a resource")
            async def create(self, name: str, **kwargs) -> Dict[str, Any]:
                # Command logic
                return {"status": "created", "name": name}

            @command(help="Delete a resource")
            async def delete(self, id: str, **kwargs) -> Dict[str, Any]:
                # Command logic
                return {"status": "deleted", "id": id}

        async def main():
            cli = MySkillCLI(config=config, devarmor=devarmor)
            result = await cli.execute(["create", "--name=test"])
            print(cli.format_output(result, format="json"))
    """

    skill_name: str = ""
    description: str = ""

    def __init__(
        self,
        config: Optional[BaseSkillConfig] = None,
        skill: Optional[BaseDevArmorSkill] = None,
        devarmor: Optional[DevArmorAPI] = None,
    ):
        """Initialize CLI.

        Args:
            config: Skill configuration
            skill: Skill instance
            devarmor: DevArmor API instance
        """
        self.config = config
        self.skill = skill
        self.devarmor = devarmor
        self.logger = logging.getLogger(f"{__name__}.{self.skill_name}")

    async def execute(
        self,
        args: List[str],
        format: str = "text",
    ) -> Union[Dict[str, Any], str]:
        """Execute a command.

        Args:
            args: Command arguments (first element is command name)
            format: Output format (text, json, yaml)

        Returns:
            Command result

        Raises:
            SkillException: If command fails
        """
        if not args:
            raise SkillValidationError(
                self.skill_name,
                "No command specified",
                field="args",
            )

        command_name = args[0]
        command_args = args[1:]

        # Find command handler
        handler_name = f"cmd_{command_name}"
        if not hasattr(self, handler_name):
            raise SkillValidationError(
                self.skill_name,
                f"Unknown command: {command_name}",
                field="command",
            )

        handler = getattr(self, handler_name)
        if not callable(handler):
            raise SkillValidationError(
                self.skill_name,
                f"Handler for {command_name} is not callable",
                field="handler",
            )

        try:
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*command_args)
            else:
                result = handler(*command_args)

            return self.format_output(result, format=format)

        except Exception as e:
            self.logger.error(f"Command {command_name} failed: {str(e)}")
            raise SkillException(
                self.skill_name,
                f"Command failed: {str(e)}",
                code="SKILL_COMMAND_FAILED",
                details={"command": command_name, "error_type": type(e).__name__},
            )

    def format_output(
        self,
        data: Union[Dict[str, Any], str, List[Any]],
        format: str = "text",
    ) -> str:
        """Format output for display.

        Args:
            data: Data to format
            format: Format type (text, json, yaml)

        Returns:
            Formatted string
        """
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "yaml":
            try:
                import yaml

                return yaml.dump(data, default_flow_style=False)
            except ImportError:
                self.logger.warning("PyYAML not installed, falling back to JSON")
                return json.dumps(data, indent=2, default=str)
        else:  # text
            if isinstance(data, str):
                return data
            return json.dumps(data, indent=2, default=str)

    def help(self) -> str:
        """Get help text for this CLI.

        Returns:
            Help text describing available commands
        """
        help_lines = [f"{self.skill_name} CLI", "=" * 40, self.description, ""]

        # Find all command handlers
        commands = [m for m in dir(self) if m.startswith("cmd_")]
        if commands:
            help_lines.append("Commands:")
            for cmd in sorted(commands):
                handler = getattr(self, cmd)
                doc = handler.__doc__ or "No description"
                cmd_name = cmd[4:]  # Remove 'cmd_' prefix
                help_lines.append(f"  {cmd_name:20} {doc.split(chr(10))[0]}")

        return "\n".join(help_lines)


# ============================================================================
# Testing Framework
# ============================================================================


class SkillTestBase:
    """Base class for skill tests.

    Provides common fixtures, mocking utilities, and test helpers.

    Example:
        class TestMySkill(SkillTestBase):
            skill_class = MySkill
            config_class = MySkillConfig

            async def test_install(self, skill, devarmor_api):
                '''Test installation hook'''
                await skill.on_install(devarmor_api)
                # Assertions

            async def test_validate_config(self, skill):
                '''Test config validation'''
                config = MySkillConfig(skill_name="my-skill")
                result = await skill.validate_config(config)
                assert result.valid
    """

    skill_class: Type[BaseDevArmorSkill] = BaseDevArmorSkill
    config_class: Type[BaseSkillConfig] = BaseSkillConfig

    def setup_method(self) -> None:
        """Set up test fixtures."""
        pass

    def teardown_method(self) -> None:
        """Tear down test fixtures."""
        pass

    def mock_devarmor_api(self) -> "MockDevArmorAPI":
        """Create a mock DevArmor API for testing.

        Returns:
            Mock API instance
        """
        return MockDevArmorAPI()

    def mock_config(self, **overrides: Any) -> BaseSkillConfig:
        """Create a mock config for testing.

        Args:
            **overrides: Config overrides

        Returns:
            Config instance
        """
        defaults = {
            "skill_name": self.skill_class.name or "test-skill",
        }
        defaults.update(overrides)
        return self.config_class(**defaults)


class MockDevArmorAPI:
    """Mock DevArmor API for testing."""

    def __init__(self) -> None:
        """Initialize mock API."""
        self.events: List[Dict[str, Any]] = []
        self.audit_logs: List[Dict[str, Any]] = []
        self.shared_state: Dict[str, List[Dict[str, Any]]] = {}

    async def evaluate_action(
        self,
        skill_name: str,
        action: str,
        params: Dict[str, Any],
    ) -> PolicyEvaluation:
        """Mock action evaluation."""
        return PolicyEvaluation(
            allowed=True,
            violated_policies=[],
            reason="Allowed (mock)",
        )

    async def publish_event(
        self,
        skill_name: str,
        event_type: str,
        payload: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        """Mock event publishing."""
        self.events.append({
            "skill_name": skill_name,
            "event_type": event_type,
            "payload": payload,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def query_shared_state(
        self,
        entity_type: str,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Mock shared state query."""
        return self.shared_state.get(entity_type, [])


# ============================================================================
# Utilities
# ============================================================================


def command(help: str = "") -> Callable:
    """Decorator to mark a method as a CLI command.

    Args:
        help: Help text for the command
    """

    def decorator(func: Callable) -> Callable:
        func._is_command = True  # type: ignore
        func._help = help  # type: ignore
        return func

    return decorator


# Import asyncio for CLI execution
import asyncio

__all__ = [
    # Skill Framework
    "BaseDevArmorSkill",
    "BaseSkillConfig",
    "BaseSkillCLI",
    "SkillTestBase",
    # Models
    "ValidationResult",
    "PolicyDecision",
    # Exceptions
    "SkillException",
    "SkillConfigError",
    "SkillAuthError",
    "SkillOperationBlockedError",
    "SkillRateLimitError",
    "SkillValidationError",
    # Utilities
    "command",
    "MockDevArmorAPI",
    "CommandSignature",
]
