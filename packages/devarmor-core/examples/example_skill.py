"""Example skill implementing the DevArmor Skill Framework.

This example demonstrates:
1. Creating a skill configuration class
2. Implementing a skill with lifecycle hooks
3. Building a CLI for the skill
4. Integrating with DevArmor policies
5. Publishing events
6. Writing tests
"""

import json
import logging
from typing import Any, Dict, Optional

from pydantic import Field

from devarmor import (
    BaseDevArmorSkill,
    BaseSkillCLI,
    BaseSkillConfig,
    DevArmorAPI,
    ValidationResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class GitHubSkillConfig(BaseSkillConfig):
    """Configuration for GitHub skill.

    Configuration hierarchy:
    1. Environment variables (SKILL_GITHUB_SKILL_*)
    2. Repo config (.claude/github-skill.json)
    3. Master config (~/.devarmor/github-skill/config.json)
    4. Code defaults
    """

    # API Configuration
    github_token: Optional[str] = Field(default=None, description="GitHub API token")
    github_api_url: str = Field(
        default="https://api.github.com",
        description="GitHub API URL",
    )
    timeout: int = Field(default=30, ge=1, le=300, description="API request timeout")

    # Behavior
    auto_label_issues: bool = Field(default=False, description="Auto-label new issues")
    default_labels: list[str] = Field(default_factory=lambda: ["triage"], description="Default labels")
    rate_limit_safety_margin: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="Stop at X% of rate limit",
    )


# ============================================================================
# Skill Implementation
# ============================================================================


class GitHubSkill(BaseDevArmorSkill):
    """GitHub skill for managing repositories and issues.

    Capabilities:
    - Create, update, close issues
    - Add labels and comments
    - Manage pull requests
    - Query repository data

    Usage:
        skill = GitHubSkill(config=config, devarmor=devarmor)
        await skill.on_install(devarmor)

        # Check if operation is allowed
        decision = await skill.pre_action_check("create-issue", {"repo": "foo"})
        if not decision.allowed:
            raise SkillOperationBlockedError(...)

        # Publish event
        await skill.publish_event("issue-created", {"number": 123})
    """

    name = "github-skill"
    version = "2.1.0"
    description = "GitHub repository and issue management"
    author = "Craig Hoad"

    config: GitHubSkillConfig

    async def on_install(self, devarmor: DevArmorAPI) -> None:
        """Initialize GitHub skill on first install.

        Args:
            devarmor: DevArmor API instance

        Raises:
            LifecycleError: If initialization fails
        """
        await super().on_install(devarmor)

        # Validate API token
        if not self.config.github_token:
            self.logger.warning("GitHub token not configured - API calls will fail")

        # Log installation
        self.logger.info(
            f"GitHub skill v{self.version} installed with API URL: {self.config.github_api_url}"
        )

    async def on_upgrade(self, old_version: str, devarmor: DevArmorAPI) -> None:
        """Migrate state on upgrade.

        Args:
            old_version: Previous version
            devarmor: DevArmor API instance
        """
        await super().on_upgrade(old_version, devarmor)

        # Run migrations
        if old_version < "2.0.0":
            self.logger.info("Running v1->v2 migration...")
            # Migration logic here

    async def on_remove(self, devarmor: DevArmorAPI) -> None:
        """Clean up GitHub skill.

        Args:
            devarmor: DevArmor API instance
        """
        await super().on_remove(devarmor)
        self.logger.info("GitHub skill removed")

    async def validate_config(self, config: BaseSkillConfig) -> ValidationResult:
        """Validate GitHub-specific configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(valid=True)

        if not isinstance(config, GitHubSkillConfig):
            result.valid = False
            result.errors.append("Configuration must be GitHubSkillConfig")
            return result

        # Validate API URL
        if not config.github_api_url.startswith("http"):
            result.valid = False
            result.errors.append("github_api_url must be a valid URL")

        # Warn about missing token
        if not config.github_token:
            result.warnings.append("github_token not configured - API calls will be limited")

        # Validate rate limit margin
        if config.rate_limit_safety_margin < 0.05:
            result.warnings.append("rate_limit_safety_margin is very low - may hit rate limits")

        return result

    # ========== Skill-Specific Methods ==========

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub issue.

        Args:
            repo: Repository (owner/repo format)
            title: Issue title
            body: Issue body
            labels: Labels to add

        Returns:
            Created issue data

        Raises:
            SkillOperationBlockedError: If operation is blocked by policy
        """
        # Check policy before creating issue
        decision = await self.pre_action_check(
            "create-issue",
            {"repo": repo, "title": title},
        )
        if not decision.allowed:
            from devarmor import SkillOperationBlockedError

            raise SkillOperationBlockedError(
                self.name,
                f"Cannot create issue: {decision.reason}",
                operation="create-issue",
                reason=decision.reason,
            )

        # Simulate creating issue (in real skill, call GitHub API)
        issue_data = {
            "repo": repo,
            "title": title,
            "body": body,
            "labels": labels or self.config.default_labels,
            "number": 123,  # From API response
            "html_url": f"https://github.com/{repo}/issues/123",
        }

        # Publish event
        await self.publish_event("issue-created", {
            "repo": repo,
            "issue_number": issue_data["number"],
            "title": title,
        })

        self.logger.info(f"Created issue #{issue_data['number']} in {repo}")

        return issue_data

    async def list_issues(self, repo: str) -> list[Dict[str, Any]]:
        """List issues in a repository.

        Args:
            repo: Repository (owner/repo format)

        Returns:
            List of issue data
        """
        # Query shared state for issues created by all skills
        issues = await self.query_shared_state("issue", {"repo": repo})
        return issues


# ============================================================================
# CLI Implementation
# ============================================================================


class GitHubSkillCLI(BaseSkillCLI):
    """CLI for GitHub skill.

    Commands:
        github-skill create-issue --repo=foo/bar --title="Bug report"
        github-skill list-issues --repo=foo/bar
        github-skill config (show current configuration)
    """

    skill_name = "github-skill"
    description = "GitHub skill CLI - manage repositories and issues"

    def __init__(self, config: GitHubSkillConfig, skill: GitHubSkill, devarmor: DevArmorAPI):
        """Initialize CLI."""
        super().__init__(config=config, skill=skill, devarmor=devarmor)
        self.skill: GitHubSkill = skill  # type: ignore

    async def cmd_create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub issue.

        Args:
            repo: Repository (owner/repo format)
            title: Issue title
            body: Issue body (optional)
            labels: Comma-separated labels (optional)

        Returns:
            Created issue data
        """
        label_list = labels.split(",") if labels else None
        return await self.skill.create_issue(repo, title, body, label_list)

    async def cmd_list_issues(self, repo: str) -> Dict[str, Any]:
        """List issues in a repository.

        Args:
            repo: Repository (owner/repo format)

        Returns:
            List of issues
        """
        issues = await self.skill.list_issues(repo)
        return {
            "repo": repo,
            "count": len(issues),
            "issues": issues,
        }

    async def cmd_config(self) -> Dict[str, Any]:
        """Show current configuration.

        Returns:
            Current config
        """
        if not isinstance(self.config, GitHubSkillConfig):
            return {"error": "Invalid config type"}

        return {
            "api_url": self.config.github_api_url,
            "timeout": self.config.timeout,
            "auto_label_issues": self.config.auto_label_issues,
            "default_labels": self.config.default_labels,
            "rate_limit_safety_margin": self.config.rate_limit_safety_margin,
            "has_token": bool(self.config.github_token),
        }

    async def cmd_validate(self) -> Dict[str, Any]:
        """Validate configuration.

        Returns:
            Validation result
        """
        result = await self.skill.validate_config(self.config)
        return result.dict()


# ============================================================================
# Usage Example
# ============================================================================


async def example_usage() -> None:
    """Demonstrate using the GitHub skill."""
    # 1. Load configuration
    config = GitHubSkillConfig.load("github-skill")
    print(f"Loaded config: timeout={config.timeout}")

    # 2. Create skill
    skill = GitHubSkill(config=config)

    # 3. Validate configuration
    validation = await skill.validate_config(config)
    print(f"Config valid: {validation.valid}")
    if validation.warnings:
        print(f"Warnings: {validation.warnings}")

    # 4. Initialize with mock DevArmor
    from devarmor import MockDevArmorAPI

    devarmor = MockDevArmorAPI()
    await skill.on_install(devarmor)

    # 5. Create issue
    try:
        issue = await skill.create_issue(
            repo="rhyscraig/test-repo",
            title="Example issue",
            body="This is an example issue",
        )
        print(f"Created issue: #{issue['number']}")
    except Exception as e:
        print(f"Failed to create issue: {e}")

    # 6. Use CLI
    cli = GitHubSkillCLI(config, skill, devarmor)
    config_output = await cli.cmd_config()
    print(f"CLI config: {json.dumps(config_output, indent=2)}")

    # 7. Check events published
    print(f"Events published: {len(devarmor.events)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
