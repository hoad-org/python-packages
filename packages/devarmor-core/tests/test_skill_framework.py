"""Tests for DevArmor Skill Framework.

Tests cover:
- Configuration hierarchy (4-level)
- Skill base class lifecycle
- CLI framework
- Exception hierarchy
- Testing utilities
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devarmor import (
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
)


# ============================================================================
# Test Configuration Classes
# ============================================================================


class TestSkillConfig(BaseSkillConfig):
    """Test configuration class."""

    api_key: Optional[str] = None
    timeout: int = 30
    debug: bool = False


class TestSkill(BaseDevArmorSkill):
    """Test skill implementation."""

    name = "test-skill"
    version = "1.0.0"
    description = "Test skill"
    author = "Test Author"

    async def validate_config(self, config: BaseSkillConfig) -> ValidationResult:
        """Validate test skill config."""
        result = ValidationResult(valid=True)
        if isinstance(config, TestSkillConfig):
            if config.timeout < 0:
                result.valid = False
                result.errors.append("timeout must be positive")
        return result


class TestSkillCLI(BaseSkillCLI):
    """Test CLI implementation."""

    skill_name = "test-skill"
    description = "Test skill CLI"

    async def cmd_echo(self, message: str = "hello") -> Dict[str, Any]:
        """Echo a message."""
        return {"message": message}

    async def cmd_fail(self) -> Dict[str, Any]:
        """Fail command."""
        raise ValueError("Command failed")

    async def cmd_config(self) -> Dict[str, Any]:
        """Get config."""
        return {"config": str(self.config)}


# ============================================================================
# Configuration Tests
# ============================================================================


class TestBaseSkillConfig:
    """Tests for BaseSkillConfig."""

    def test_create_with_defaults(self):
        """Test creating config with defaults."""
        config = TestSkillConfig(skill_name="test-skill")
        assert config.skill_name == "test-skill"
        assert config.timeout == 30
        assert config.debug is False

    def test_skill_name_validation(self):
        """Test skill name validation."""
        # Valid names
        config = TestSkillConfig(skill_name="test-skill")
        assert config.skill_name == "test-skill"

        config = TestSkillConfig(skill_name="MySkill")
        assert config.skill_name == "myskill"

        # Invalid names
        with pytest.raises(ValueError):
            TestSkillConfig(skill_name="test@skill")

    def test_load_from_defaults(self):
        """Test loading with code defaults."""
        config = TestSkillConfig.load("test-skill")
        assert config.skill_name == "test-skill"
        assert config.timeout == 30

    def test_load_with_environment_variables(self):
        """Test loading with environment variable overrides."""
        with patch.dict(os.environ, {
            "SKILL_TEST_SKILL_TIMEOUT": "60",
            "SKILL_TEST_SKILL_DEBUG": "true",
            "SKILL_TEST_SKILL_API_KEY": "secret123",
        }):
            config = TestSkillConfig.load("test-skill")
            assert config.timeout == 60
            assert config.debug is True
            assert config.api_key == "secret123"

    def test_load_with_repo_config(self):
        """Test loading with repo config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_file = config_dir / "test-skill.json"

            config_data = {
                "timeout": 90,
                "debug": True,
            }
            config_file.write_text(json.dumps(config_data))

            config = TestSkillConfig.load("test-skill", repo_config_dir=config_dir)
            assert config.timeout == 90
            assert config.debug is True

    def test_load_hierarchy(self):
        """Test full 4-level configuration hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_file = config_dir / "test-skill.json"

            # Write repo config
            config_file.write_text(json.dumps({
                "timeout": 45,
                "api_key": "from_repo",
            }))

            # Test hierarchy: env > repo > defaults
            with patch.dict(os.environ, {
                "SKILL_TEST_SKILL_TIMEOUT": "120",
            }):
                config = TestSkillConfig.load("test-skill", repo_config_dir=config_dir)
                assert config.timeout == 120  # From env (highest priority)
                assert config.api_key == "from_repo"  # From repo
                assert config.debug is False  # From defaults

    def test_save_to_master(self):
        """Test saving config to master location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TestSkillConfig(
                skill_name="test-skill",
                timeout=75,
                api_key="saved",
            )

            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                saved_path = config.save_to_master()

                assert saved_path.exists()
                assert "test-skill" in str(saved_path)

                # Verify contents
                with open(saved_path) as f:
                    data = json.load(f)
                    assert data["timeout"] == 75
                    assert data["api_key"] == "saved"

    def test_save_failure_handling(self):
        """Test handling of save failures."""
        config = TestSkillConfig(skill_name="test-skill")

        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with pytest.raises(SkillConfigError) as exc_info:
                config.save_to_master()
            assert "Failed to save" in str(exc_info.value)


# ============================================================================
# Skill Framework Tests
# ============================================================================


class TestBaseDevArmorSkill:
    """Tests for BaseDevArmorSkill."""

    def test_initialization(self):
        """Test skill initialization."""
        config = TestSkillConfig(skill_name="test-skill")
        skill = TestSkill(config=config)
        assert skill.name == "test-skill"
        assert skill.version == "1.0.0"
        assert skill.config == config

    def test_initialization_without_metadata(self):
        """Test that skill without name/version raises error."""

        class IncompleteSkill(BaseDevArmorSkill):
            async def validate_config(self, config):
                return ValidationResult(valid=True)

        with pytest.raises(SkillException):
            IncompleteSkill()

    @pytest.mark.asyncio
    async def test_on_install_hook(self):
        """Test on_install lifecycle hook."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()

        await skill.on_install(devarmor)

        assert skill.devarmor == devarmor

    @pytest.mark.asyncio
    async def test_on_upgrade_hook(self):
        """Test on_upgrade lifecycle hook."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()

        await skill.on_upgrade("0.9.0", devarmor)

        assert skill.devarmor == devarmor

    @pytest.mark.asyncio
    async def test_on_remove_hook(self):
        """Test on_remove lifecycle hook."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()

        await skill.on_remove(devarmor)  # Should not raise

    @pytest.mark.asyncio
    async def test_validate_config(self):
        """Test config validation."""
        skill = TestSkill()

        config = TestSkillConfig(skill_name="test-skill", timeout=30)
        result = await skill.validate_config(config)
        assert result.valid

        config = TestSkillConfig(skill_name="test-skill", timeout=-1)
        result = await skill.validate_config(config)
        assert not result.valid
        assert "timeout must be positive" in result.errors

    @pytest.mark.asyncio
    async def test_pre_action_check_allowed(self):
        """Test pre-action check when action is allowed."""
        skill = TestSkill()
        skill.devarmor = MockDevArmorAPI()

        decision = await skill.pre_action_check("test-action", {"param": "value"})

        assert decision.allowed
        assert decision.reason == "Action allowed"

    @pytest.mark.asyncio
    async def test_pre_action_check_denied(self):
        """Test pre-action check when action is denied."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()

        # Mock denied evaluation
        devarmor.evaluate_action = AsyncMock(return_value=MagicMock(
            allowed=False,
            violated_policies=["cost-limit"],
            details={"limit": 100},
        ))

        skill.devarmor = devarmor

        decision = await skill.pre_action_check("expensive-action")

        assert not decision.allowed
        assert "Policy violation" in decision.reason
        assert "cost-limit" in decision.violated_policies

    @pytest.mark.asyncio
    async def test_pre_action_check_no_devarmor(self):
        """Test pre-action check without initialized DevArmor."""
        skill = TestSkill()

        decision = await skill.pre_action_check("test-action")

        assert not decision.allowed
        assert "not initialized" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test event publishing."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()
        skill.devarmor = devarmor

        await skill.publish_event("test-event", {"key": "value"})

        assert len(devarmor.events) == 1
        event = devarmor.events[0]
        assert event["skill_name"] == "test-skill"
        assert event["event_type"] == "test-event"
        assert event["payload"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_publish_event_without_devarmor(self):
        """Test event publishing without DevArmor (should not raise)."""
        skill = TestSkill()
        await skill.publish_event("test-event", {})  # Should not raise

    @pytest.mark.asyncio
    async def test_query_shared_state(self):
        """Test querying shared state."""
        skill = TestSkill()
        devarmor = MockDevArmorAPI()
        devarmor.shared_state["issue"] = [{"id": "1", "title": "Test"}]
        skill.devarmor = devarmor

        results = await skill.query_shared_state("issue")

        assert len(results) == 1
        assert results[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_query_shared_state_without_devarmor(self):
        """Test querying shared state without DevArmor."""
        skill = TestSkill()
        results = await skill.query_shared_state("issue")
        assert results == []

    def test_get_info(self):
        """Test getting skill info."""
        skill = TestSkill()
        info = skill.get_info()

        assert info.name == "test-skill"
        assert info.version == "1.0.0"
        assert info.metadata["description"] == "Test skill"
        assert info.metadata["author"] == "Test Author"


# ============================================================================
# CLI Framework Tests
# ============================================================================


class TestBaseSkillCLI:
    """Tests for BaseSkillCLI."""

    @pytest.mark.asyncio
    async def test_execute_command(self):
        """Test executing a command."""
        cli = TestSkillCLI()
        result = await cli.execute(["echo", "world"])

        assert isinstance(result, str)
        assert "world" in result

    @pytest.mark.asyncio
    async def test_execute_without_command(self):
        """Test executing without command."""
        cli = TestSkillCLI()

        with pytest.raises(SkillValidationError):
            await cli.execute([])

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self):
        """Test executing unknown command."""
        cli = TestSkillCLI()

        with pytest.raises(SkillValidationError) as exc_info:
            await cli.execute(["unknown"])

        assert "Unknown command" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_command_failure(self):
        """Test command that raises exception."""
        cli = TestSkillCLI()

        with pytest.raises(SkillException) as exc_info:
            await cli.execute(["fail"])

        assert "Command failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_format_output_json(self):
        """Test JSON output formatting."""
        cli = TestSkillCLI()
        data = {"key": "value", "number": 42}

        output = cli.format_output(data, format="json")

        assert isinstance(output, str)
        parsed = json.loads(output)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    @pytest.mark.asyncio
    async def test_format_output_text(self):
        """Test text output formatting."""
        cli = TestSkillCLI()
        data = {"key": "value"}

        output = cli.format_output(data, format="text")

        assert isinstance(output, str)
        assert "key" in output

    @pytest.mark.asyncio
    async def test_format_output_string(self):
        """Test formatting string output."""
        cli = TestSkillCLI()
        output = cli.format_output("hello", format="text")
        assert output == "hello"

    def test_help(self):
        """Test getting help text."""
        cli = TestSkillCLI()
        help_text = cli.help()

        assert "test-skill" in help_text
        assert "echo" in help_text
        assert "fail" in help_text


# ============================================================================
# Exception Tests
# ============================================================================


class TestSkillExceptions:
    """Tests for skill exception hierarchy."""

    def test_skill_exception(self):
        """Test base SkillException."""
        exc = SkillException("test-skill", "Test error")
        assert exc.skill_name == "test-skill"
        assert exc.message == "Test error"

    def test_skill_config_error(self):
        """Test SkillConfigError."""
        exc = SkillConfigError("test-skill", "Config error")
        assert exc.skill_name == "test-skill"
        assert exc.code == "SKILL_CONFIG_ERROR"

    def test_skill_auth_error(self):
        """Test SkillAuthError."""
        exc = SkillAuthError("test-skill", "Auth failed", auth_type="api_key")
        assert exc.auth_type == "api_key"

    def test_skill_operation_blocked_error(self):
        """Test SkillOperationBlockedError."""
        exc = SkillOperationBlockedError(
            "test-skill",
            "Blocked",
            operation="delete",
            reason="Cost limit",
        )
        assert exc.operation == "delete"
        assert exc.reason == "Cost limit"

    def test_skill_rate_limit_error(self):
        """Test SkillRateLimitError."""
        exc = SkillRateLimitError(
            "test-skill",
            "Rate limited",
            limit_type="api_calls",
            retry_after=60,
        )
        assert exc.limit_type == "api_calls"
        assert exc.retry_after == 60

    def test_skill_validation_error(self):
        """Test SkillValidationError."""
        exc = SkillValidationError("test-skill", "Invalid", field="api_key")
        assert exc.field == "api_key"


# ============================================================================
# Testing Framework Tests
# ============================================================================


class TestSkillTestBase(SkillTestBase):
    """Tests for SkillTestBase."""

    skill_class = TestSkill
    config_class = TestSkillConfig

    def test_mock_devarmor_api(self):
        """Test creating mock DevArmor API."""
        api = self.mock_devarmor_api()
        assert isinstance(api, MockDevArmorAPI)
        assert api.events == []

    def test_mock_config(self):
        """Test creating mock config."""
        config = self.mock_config(timeout=45)
        assert config.skill_name == "test-skill"
        assert config.timeout == 45

    @pytest.mark.asyncio
    async def test_mock_api_event_publishing(self):
        """Test mock API event publishing."""
        api = self.mock_devarmor_api()
        await api.publish_event(
            "test-skill",
            "test-event",
            {"data": "value"},
        )

        assert len(api.events) == 1
        assert api.events[0]["event_type"] == "test-event"

    @pytest.mark.asyncio
    async def test_mock_api_action_evaluation(self):
        """Test mock API action evaluation."""
        api = self.mock_devarmor_api()
        result = await api.evaluate_action("test-skill", "action", {})

        assert result.allowed is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestSkillFrameworkIntegration:
    """Integration tests for full skill framework."""

    @pytest.mark.asyncio
    async def test_full_skill_lifecycle(self):
        """Test complete skill lifecycle."""
        # 1. Create config
        config = TestSkillConfig(skill_name="test-skill", timeout=30)

        # 2. Create skill
        skill = TestSkill(config=config)

        # 3. Validate config
        validation = await skill.validate_config(config)
        assert validation.valid

        # 4. Initialize with DevArmor
        devarmor = MockDevArmorAPI()
        await skill.on_install(devarmor)

        # 5. Perform action with pre-check
        decision = await skill.pre_action_check("create-resource")
        assert decision.allowed

        # 6. Publish event
        await skill.publish_event("resource-created", {"id": "123"})
        assert len(devarmor.events) == 1

        # 7. Cleanup
        await skill.on_remove(devarmor)

    @pytest.mark.asyncio
    async def test_skill_with_cli(self):
        """Test skill integrated with CLI."""
        config = TestSkillConfig(skill_name="test-skill")
        skill = TestSkill(config=config)
        cli = TestSkillCLI(skill=skill, config=config)

        result = await cli.execute(["echo", "test"])

        assert "test" in result

    @pytest.mark.asyncio
    async def test_configuration_hierarchy_in_skill(self):
        """Test full config hierarchy integration with skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Write repo config
            (config_dir / "test-skill.json").write_text(json.dumps({
                "timeout": 60,
            }))

            # Load config through hierarchy
            config = TestSkillConfig.load("test-skill", repo_config_dir=config_dir)

            # Create skill with loaded config
            skill = TestSkill(config=config)

            # Validate
            result = await skill.validate_config(config)
            assert result.valid
            assert config.timeout == 60
