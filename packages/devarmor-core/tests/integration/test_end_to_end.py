"""End-to-end integration tests for DevArmor API."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from devarmor import DevArmorAPI
from devarmor.errors import PolicyViolation
from devarmor.models import Event


class TestDevArmorAPIIntegration:
    """Integration tests for full DevArmor workflow."""

    def _create_no_approval_config(self, tmp_path: Path) -> Path:
        """Create a config that doesn't require approval."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("security:\n  require_approval: false\n")
        return config_dir

    @pytest.mark.asyncio
    async def test_full_skill_lifecycle(self) -> None:
        """Test complete skill lifecycle: install -> upgrade -> remove."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Install skill
            result = await api.install_skill(
                skill_name="test-skill",
                version="1.0.0",
                actor="user",
            )
            assert result["name"] == "test-skill"
            assert result["version"] == "1.0.0"

            # Verify skill is installed
            skills = await api.list_installed_skills()
            assert len(skills) == 1

            # Upgrade skill
            result = await api.upgrade_skill(
                skill_name="test-skill",
                new_version="2.0.0",
                actor="user",
            )
            assert result["version"] == "2.0.0"

            # Get skill info
            skill_info = await api.get_skill_info("test-skill")
            assert skill_info["version"] == "2.0.0"

            # Remove skill
            await api.remove_skill(skill_name="test-skill", actor="user")

            # Verify skill is removed
            skills = await api.list_installed_skills()
            assert len(skills) == 0

    @pytest.mark.asyncio
    async def test_event_publishing(self) -> None:
        """Test event publishing and subscription."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            received_events: list[Event] = []

            async def event_callback(event: Event) -> None:
                received_events.append(event)

            # Subscribe to events
            subscriber_id = await api.subscribe_to_events(event_callback)
            assert subscriber_id is not None

            # Install skill (should publish event)
            await api.install_skill(
                skill_name="test-skill",
                version="1.0.0",
                actor="user",
            )

            # Should have received install event
            assert len(received_events) >= 1
            assert any(e.event_type.value == "skill:installed" for e in received_events)

            # Unsubscribe
            result = await api.unsubscribe_from_events(subscriber_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_policy_enforcement(self) -> None:
        """Test that policies are enforced."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create config with blocked skill
            config_dir = tmp_path / "config"
            config_dir.mkdir()
            (config_dir / "config.yaml").write_text(
                """security:
  require_approval: false
skill_permissions:
  enabled: true
  skill_blocklist:
    - dangerous-skill
"""
            )

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Try to install blocked skill (should fail)
            with pytest.raises(PolicyViolation):
                await api.install_skill(
                    skill_name="dangerous-skill",
                    version="1.0.0",
                    actor="user",
                )

    @pytest.mark.asyncio
    async def test_audit_logging(self) -> None:
        """Test that all actions are audited."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Install skill
            await api.install_skill(
                skill_name="test-skill",
                version="1.0.0",
                actor="user",
            )

            # Check audit log
            audit_entries = api.audit_logger.get_entries()

            # Should have at least one entry
            assert len(audit_entries) > 0

            # Should have install operation logged
            assert any(e.action == "install" for e in audit_entries)

    @pytest.mark.asyncio
    async def test_system_status(self) -> None:
        """Test getting system status."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Install a skill
            await api.install_skill(
                skill_name="skill1",
                version="1.0.0",
            )

            # Get status
            status = await api.get_system_status()

            assert status["installed_skills_count"] == 1
            assert status["policy_config_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_multiple_skills(self) -> None:
        """Test managing multiple skills."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Install multiple skills
            for i in range(3):
                await api.install_skill(
                    skill_name=f"skill{i}",
                    version="1.0.0",
                    actor="user",
                )

            # Verify all installed
            skills = await api.list_installed_skills()
            assert len(skills) == 3

            # Upgrade one
            await api.upgrade_skill(
                skill_name="skill0",
                new_version="2.0.0",
            )

            # Remove one
            await api.remove_skill(skill_name="skill1")

            # Check final state
            skills = await api.list_installed_skills()
            assert len(skills) == 2
            assert any(s["name"] == "skill0" and s["version"] == "2.0.0" for s in skills)

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test error handling in lifecycle."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            # Try to upgrade non-existent skill
            from devarmor.errors import StateError

            with pytest.raises(StateError):
                await api.upgrade_skill(
                    skill_name="nonexistent",
                    new_version="2.0.0",
                )

            # Try to remove non-existent skill
            with pytest.raises(StateError):
                await api.remove_skill(skill_name="nonexistent")

    @pytest.mark.asyncio
    async def test_api_lazy_initialization(self) -> None:
        """Test that API initializes lazily on first use."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            # API should not be initialized yet
            assert api._initialized is False

            # First operation should trigger initialization
            await api.list_installed_skills()

            assert api._initialized is True

    @pytest.mark.asyncio
    async def test_event_filtering(self) -> None:
        """Test subscribing to specific event types."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = self._create_no_approval_config(tmp_path)

            api = DevArmorAPI(
                config_dir=config_dir,
                skills_dir=tmp_path / "skills",
                log_dir=tmp_path / "audit",
            )

            await api.initialize()

            from devarmor.models import EventType

            install_events: list[Event] = []
            upgrade_events: list[Event] = []

            async def install_callback(event: Event) -> None:
                install_events.append(event)

            async def upgrade_callback(event: Event) -> None:
                upgrade_events.append(event)

            # Subscribe to specific event types
            await api.subscribe_to_events(
                install_callback,
                event_types=[EventType.SKILL_INSTALLED],
            )
            await api.subscribe_to_events(
                upgrade_callback,
                event_types=[EventType.SKILL_UPGRADED],
            )

            # Install skill
            await api.install_skill(skill_name="skill1", version="1.0.0")

            # Upgrade skill
            await api.upgrade_skill(skill_name="skill1", new_version="2.0.0")

            # Install callback should have received one event
            assert len(install_events) >= 1

            # Upgrade callback should have received one event
            assert len(upgrade_events) >= 1
