"""Tests for skill lifecycle management."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from devarmor.errors import StateError
from devarmor.lifecycle import SkillLifecycleManager
from devarmor.models import SkillInfo, SkillStatus


class TestSkillLifecycleManager:
    """Test SkillLifecycleManager class."""

    @pytest.fixture
    def manager(self) -> SkillLifecycleManager:
        """Create a lifecycle manager with temp directory."""
        with TemporaryDirectory() as tmpdir:
            manager = SkillLifecycleManager(skills_dir=Path(tmpdir))
            yield manager

    @pytest.mark.asyncio
    async def test_install_skill(self, manager: SkillLifecycleManager) -> None:
        """Test installing a skill."""
        skill_info = await manager.install_skill(
            skill_name="test-skill",
            version="1.0.0",
            actor="user",
        )

        assert skill_info.name == "test-skill"
        assert skill_info.version == "1.0.0"
        assert skill_info.status == SkillStatus.INSTALLED
        assert manager.is_skill_installed("test-skill")

    @pytest.mark.asyncio
    async def test_install_skill_already_installed(self, manager: SkillLifecycleManager) -> None:
        """Test installing skill that's already installed."""
        await manager.install_skill(
            skill_name="test-skill",
            version="1.0.0",
        )

        with pytest.raises(StateError):
            await manager.install_skill(
                skill_name="test-skill",
                version="2.0.0",
            )

    @pytest.mark.asyncio
    async def test_upgrade_skill(self, manager: SkillLifecycleManager) -> None:
        """Test upgrading a skill."""
        # Install first
        await manager.install_skill(skill_name="test-skill", version="1.0.0")

        # Upgrade
        skill_info = await manager.upgrade_skill(
            skill_name="test-skill",
            new_version="2.0.0",
        )

        assert skill_info.version == "2.0.0"
        assert skill_info.status == SkillStatus.INSTALLED
        assert skill_info.last_updated is not None

    @pytest.mark.asyncio
    async def test_upgrade_skill_not_installed(self, manager: SkillLifecycleManager) -> None:
        """Test upgrading skill that's not installed."""
        with pytest.raises(StateError):
            await manager.upgrade_skill(
                skill_name="nonexistent",
                new_version="2.0.0",
            )

    @pytest.mark.asyncio
    async def test_remove_skill(self, manager: SkillLifecycleManager) -> None:
        """Test removing a skill."""
        # Install first
        await manager.install_skill(skill_name="test-skill", version="1.0.0")

        # Remove
        await manager.remove_skill(skill_name="test-skill")

        assert not manager.is_skill_installed("test-skill")

    @pytest.mark.asyncio
    async def test_remove_skill_not_installed(self, manager: SkillLifecycleManager) -> None:
        """Test removing skill that's not installed."""
        with pytest.raises(StateError):
            await manager.remove_skill(skill_name="nonexistent")

    def test_get_skill_info(self, manager: SkillLifecycleManager) -> None:
        """Test getting skill information."""
        # Create mock skill
        manager.skills["test-skill"] = SkillInfo(
            name="test-skill",
            version="1.0.0",
            status=SkillStatus.INSTALLED,
            installed_at=__import__("datetime").datetime.utcnow(),
        )

        skill_info = manager.get_skill_info("test-skill")

        assert skill_info is not None
        assert skill_info.name == "test-skill"

    def test_get_skill_info_not_found(self, manager: SkillLifecycleManager) -> None:
        """Test getting skill info when not found."""
        skill_info = manager.get_skill_info("nonexistent")

        assert skill_info is None

    def test_list_installed_skills(self, manager: SkillLifecycleManager) -> None:
        """Test listing installed skills."""
        # Create mock skills
        from datetime import datetime

        manager.skills["skill1"] = SkillInfo(
            name="skill1",
            version="1.0.0",
            status=SkillStatus.INSTALLED,
            installed_at=datetime.utcnow(),
        )
        manager.skills["skill2"] = SkillInfo(
            name="skill2",
            version="2.0.0",
            status=SkillStatus.INSTALLED,
            installed_at=datetime.utcnow(),
        )

        skills = manager.list_installed_skills()

        assert len(skills) == 2
        assert any(s.name == "skill1" for s in skills)
        assert any(s.name == "skill2" for s in skills)

    def test_is_skill_installed(self, manager: SkillLifecycleManager) -> None:
        """Test checking if skill is installed."""
        from datetime import datetime

        manager.skills["installed"] = SkillInfo(
            name="installed",
            version="1.0.0",
            status=SkillStatus.INSTALLED,
            installed_at=datetime.utcnow(),
        )

        assert manager.is_skill_installed("installed") is True
        assert manager.is_skill_installed("notinstalled") is False

    def test_get_operations(self, manager: SkillLifecycleManager) -> None:
        """Test getting operations."""
        from devarmor.models import LifecycleOperation

        op = LifecycleOperation(
            skill_name="test",
            operation="install",
            version="1.0.0",
            status="completed",
        )
        manager.operations.append(op)

        operations = manager.get_operations()

        assert len(operations) == 1
        assert operations[0].skill_name == "test"

    def test_get_operations_with_limit(self, manager: SkillLifecycleManager) -> None:
        """Test getting operations with limit."""
        from devarmor.models import LifecycleOperation

        for i in range(5):
            op = LifecycleOperation(
                skill_name=f"skill{i}",
                operation="install",
                version="1.0.0",
                status="completed",
            )
            manager.operations.append(op)

        operations = manager.get_operations(limit=2)

        assert len(operations) == 2

    def test_save_skill_metadata(self, manager: SkillLifecycleManager) -> None:
        """Test saving skill metadata to disk."""
        from datetime import datetime

        skill_info = SkillInfo(
            name="test-skill",
            version="1.0.0",
            status=SkillStatus.INSTALLED,
            installed_at=datetime.utcnow(),
        )

        manager._save_skill_metadata(skill_info)

        metadata_file = manager.skills_dir / "test-skill" / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            data = json.load(f)
            assert data["name"] == "test-skill"

    def test_load_skill_metadata(self) -> None:
        """Test loading skill metadata from disk."""
        from datetime import datetime

        with TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create metadata file
            skill_dir = skills_dir / "test-skill"
            skill_dir.mkdir()
            metadata_file = skill_dir / "metadata.json"

            skill_data = {
                "name": "test-skill",
                "version": "1.0.0",
                "status": "installed",
                "installed_at": datetime.utcnow().isoformat(),
                "metadata": {},
            }
            metadata_file.write_text(json.dumps(skill_data))

            # Load manager
            manager = SkillLifecycleManager(skills_dir=skills_dir)

            assert "test-skill" in manager.skills
            assert manager.skills["test-skill"].name == "test-skill"

    @pytest.mark.asyncio
    async def test_install_creates_metadata_file(self, manager: SkillLifecycleManager) -> None:
        """Test that install creates metadata file."""
        await manager.install_skill(
            skill_name="test-skill",
            version="1.0.0",
        )

        metadata_file = manager.skills_dir / "test-skill" / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            data = json.load(f)
            assert data["name"] == "test-skill"
            assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_lifecycle_operations_tracking(self, manager: SkillLifecycleManager) -> None:
        """Test that lifecycle operations are tracked."""
        await manager.install_skill(
            skill_name="test-skill",
            version="1.0.0",
        )

        operations = manager.get_operations()

        assert len(operations) == 1
        assert operations[0].skill_name == "test-skill"
        assert operations[0].operation == "install"
        assert operations[0].status == "completed"

    @pytest.mark.asyncio
    async def test_upgrade_updates_metadata_file(self, manager: SkillLifecycleManager) -> None:
        """Test that upgrade updates metadata file."""
        await manager.install_skill(skill_name="test-skill", version="1.0.0")

        await manager.upgrade_skill(skill_name="test-skill", new_version="2.0.0")

        metadata_file = manager.skills_dir / "test-skill" / "metadata.json"
        with open(metadata_file) as f:
            data = json.load(f)
            assert data["version"] == "2.0.0"
