"""Skill lifecycle management (install, upgrade, remove)."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .errors import LifecycleError, StateError
from .models import LifecycleOperation, SkillInfo, SkillStatus

logger = logging.getLogger(__name__)


class SkillLifecycleManager:
    """Manage skill installation, upgrades, and removal."""

    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize lifecycle manager.

        Args:
            skills_dir: Directory to store skill metadata (default: ~/.devarmor/skills)
        """
        self.skills_dir = skills_dir or (Path.home() / ".devarmor" / "skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.operations: list[LifecycleOperation] = []
        self.skills: dict[str, SkillInfo] = {}
        self._load_skill_metadata()

    def _load_skill_metadata(self) -> None:
        """Load skill metadata from disk."""
        try:
            for metadata_file in self.skills_dir.glob("*/metadata.json"):
                try:
                    with open(metadata_file) as f:
                        data = json.load(f)
                        skill = SkillInfo(**data)
                        self.skills[skill.name] = skill
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to load skill metadata from {metadata_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load skill metadata: {str(e)}")

    async def install_skill(
        self,
        skill_name: str,
        version: str,
        actor: str = "system",
        metadata: Optional[dict[str, Any]] = None,
    ) -> SkillInfo:
        """Install a skill.

        Args:
            skill_name: Name of skill to install
            version: Version to install
            actor: Who is performing the installation
            metadata: Additional metadata about the skill

        Returns:
            SkillInfo: Installed skill information

        Raises:
            LifecycleError: If installation fails
            StateError: If skill is already installed
        """
        # Check if already installed
        if skill_name in self.skills:
            raise StateError(
                f"Skill {skill_name} is already installed",
                current_state="installed",
                requested_state="installed",
            )

        operation = LifecycleOperation(
            skill_name=skill_name,
            operation="install",
            version=version,
            status="in_progress",
        )
        self.operations.append(operation)

        try:
            # Simulate installation process
            await self._simulate_package_installation(skill_name, version)

            # Create skill info
            skill_info = SkillInfo(
                name=skill_name,
                version=version,
                status=SkillStatus.INSTALLED,
                installed_at=datetime.utcnow(),
                metadata=metadata or {},
            )

            # Save metadata
            self._save_skill_metadata(skill_info)
            self.skills[skill_name] = skill_info

            # Update operation
            operation.status = "completed"
            operation.result = {"installed_at": skill_info.installed_at.isoformat()}

            logger.info(f"Skill {skill_name} v{version} installed successfully")
            return skill_info
        except Exception as e:
            operation.status = "failed"
            operation.error = str(e)
            raise LifecycleError(
                f"Failed to install {skill_name}: {str(e)}", operation="install", skill_name=skill_name
            )

    async def upgrade_skill(
        self,
        skill_name: str,
        new_version: str,
        actor: str = "system",
    ) -> SkillInfo:
        """Upgrade an installed skill.

        Args:
            skill_name: Name of skill to upgrade
            new_version: Version to upgrade to
            actor: Who is performing the upgrade

        Returns:
            SkillInfo: Upgraded skill information

        Raises:
            LifecycleError: If upgrade fails
            StateError: If skill is not installed
        """
        # Check if installed
        if skill_name not in self.skills:
            raise StateError(
                f"Skill {skill_name} is not installed",
                current_state="not_installed",
                requested_state="installed",
            )

        skill_info = self.skills[skill_name]
        old_version = skill_info.version

        operation = LifecycleOperation(
            skill_name=skill_name,
            operation="upgrade",
            version=new_version,
            status="in_progress",
        )
        self.operations.append(operation)

        try:
            # Update status
            skill_info.status = SkillStatus.UPGRADE_IN_PROGRESS

            # Simulate upgrade process
            await self._simulate_package_installation(skill_name, new_version)

            # Update skill info
            skill_info.version = new_version
            skill_info.status = SkillStatus.INSTALLED
            skill_info.last_updated = datetime.utcnow()

            # Save metadata
            self._save_skill_metadata(skill_info)

            # Update operation
            operation.status = "completed"
            operation.result = {
                "old_version": old_version,
                "new_version": new_version,
                "updated_at": skill_info.last_updated.isoformat(),
            }

            logger.info(f"Skill {skill_name} upgraded from v{old_version} to v{new_version}")
            return skill_info
        except Exception as e:
            operation.status = "failed"
            operation.error = str(e)
            skill_info.status = SkillStatus.INSTALLED
            raise LifecycleError(
                f"Failed to upgrade {skill_name}: {str(e)}", operation="upgrade", skill_name=skill_name
            )

    async def remove_skill(
        self,
        skill_name: str,
        actor: str = "system",
    ) -> None:
        """Remove an installed skill.

        Args:
            skill_name: Name of skill to remove
            actor: Who is performing the removal

        Raises:
            LifecycleError: If removal fails
            StateError: If skill is not installed
        """
        # Check if installed
        if skill_name not in self.skills:
            raise StateError(
                f"Skill {skill_name} is not installed",
                current_state="not_installed",
                requested_state="not_installed",
            )

        skill_info = self.skills[skill_name]

        operation = LifecycleOperation(
            skill_name=skill_name,
            operation="remove",
            status="in_progress",
        )
        self.operations.append(operation)

        try:
            # Update status
            skill_info.status = SkillStatus.REMOVE_IN_PROGRESS

            # Simulate removal process
            await self._simulate_package_removal(skill_name)

            # Remove metadata file
            skill_dir = self.skills_dir / skill_name
            metadata_file = skill_dir / "metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()

            # Remove from tracking
            del self.skills[skill_name]

            # Update operation
            operation.status = "completed"
            operation.result = {"removed_at": datetime.utcnow().isoformat()}

            logger.info(f"Skill {skill_name} removed successfully")
        except Exception as e:
            operation.status = "failed"
            operation.error = str(e)
            if skill_name in self.skills:
                self.skills[skill_name].status = SkillStatus.INSTALLED
            raise LifecycleError(f"Failed to remove {skill_name}: {str(e)}", operation="remove", skill_name=skill_name)

    def get_skill_info(self, skill_name: str) -> Optional[SkillInfo]:
        """Get information about an installed skill.

        Args:
            skill_name: Name of skill

        Returns:
            SkillInfo or None if not installed
        """
        return self.skills.get(skill_name)

    def list_installed_skills(self) -> list[SkillInfo]:
        """List all installed skills.

        Returns:
            List of SkillInfo objects
        """
        return list(self.skills.values())

    def is_skill_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed.

        Args:
            skill_name: Name of skill

        Returns:
            True if skill is installed
        """
        return skill_name in self.skills

    def get_operations(self, limit: Optional[int] = None) -> list[LifecycleOperation]:
        """Get lifecycle operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of LifecycleOperation objects
        """
        if limit:
            return self.operations[-limit:]
        return self.operations.copy()

    async def _simulate_package_installation(self, skill_name: str, version: str) -> None:
        """Simulate package installation.

        Args:
            skill_name: Name of skill
            version: Version being installed
        """
        # Simulate some work
        await asyncio.sleep(0.1)
        logger.debug(f"Simulated installation of {skill_name} v{version}")

    async def _simulate_package_removal(self, skill_name: str) -> None:
        """Simulate package removal.

        Args:
            skill_name: Name of skill
        """
        # Simulate some work
        await asyncio.sleep(0.1)
        logger.debug(f"Simulated removal of {skill_name}")

    def _save_skill_metadata(self, skill_info: SkillInfo) -> None:
        """Save skill metadata to disk.

        Args:
            skill_info: SkillInfo to save
        """
        skill_dir = self.skills_dir / skill_info.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = skill_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(skill_info.model_dump(), f, indent=2, default=str)

        logger.debug(f"Saved metadata for {skill_info.name} to {metadata_file}")
