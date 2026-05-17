"""
Example: Jira ↔ GitHub Integration via DevArmor

This example demonstrates cross-skill coordination using DevArmor's event bus.
When a Jira issue is created, automatically comment on linked GitHub PRs.
When a GitHub PR is created, reference any Jira issues in the title.

Architecture:
  Jira Skill
    ├─ Publishes: jira.issue.created
    └─ Subscribes to: github.pr.opened

  GitHub Skill
    ├─ Publishes: github.pr.opened
    └─ Subscribes to: jira.issue.created

Real-world use case:
  1. Developer opens PR: "PROJ-123: Add feature X"
  2. GitHub skill publishes: github.pr.opened {title, pr_number}
  3. Jira skill receives event, links to issue PROJ-123
  4. Jira skill publishes: jira.pr.linked {issue_key, pr_url}
  5. GitHub skill receives event, comments on PR

Usage:
  # Setup
  devarmor install jira-skill@2.0.0
  devarmor install github-skill@2.0.0

  # Deploy
  cp jira_github_integration.py /path/to/jira-skill/src/

  # Configure
  cat > .devarmor/jira-github-policy.yaml << 'EOF'
  name: JiraGithubSync
  enabled: true
  constraints:
    - name: PrLinksJira
      rule: 'github.pr.title contains "PROJ-"'
      action: warn
      message: "Consider linking to Jira in PR title"
  EOF

  # Test
  pytest tests/test_integration.py -v
"""

import asyncio
from typing import Dict, Any
import re
import logging

from devarmor import (
    get_devarmor,
    EventBus,
    StateStore,
    DevArmorContext,
    IDevArmorCompliant,
)

logger = logging.getLogger(__name__)


class JiraGithubIntegration(IDevArmorCompliant):
    """
    Jira ↔ GitHub integration layer.

    Coordinates issue linking between Jira and GitHub via DevArmor events.
    """

    def __init__(self):
        self.event_bus: EventBus = None
        self.state_store: StateStore = None
        self.jira_client = None
        self.github_client = None

    async def on_install(self) -> None:
        """Initialize integration on skill install"""
        logger.info("Installing Jira-GitHub integration")

        # Initialize state tracking
        await self.state_store.initialize({
            "jira.github.linked_issues": {},  # {pr_url: issue_key}
            "jira.github.sync_count": 0,
            "jira.github.last_sync": None,
        })

        # Subscribe to GitHub events
        await self.event_bus.subscribe(
            "github.pr.opened",
            self.handle_github_pr_opened,
        )

        await self.event_bus.subscribe(
            "github.pr.closed",
            self.handle_github_pr_closed,
        )

        logger.info("Jira-GitHub integration ready")

    async def on_uninstall(self) -> None:
        """Cleanup on skill uninstall"""
        logger.info("Uninstalling Jira-GitHub integration")

        # Unsubscribe from events
        await self.event_bus.unsubscribe(
            "github.pr.opened",
            self.handle_github_pr_opened,
        )

        await self.event_bus.unsubscribe(
            "github.pr.closed",
            self.handle_github_pr_closed,
        )

    async def validate_action(
        self,
        action: str,
        params: Dict[str, Any],
        context: DevArmorContext,
    ) -> bool:
        """Validate actions - allow all for this example"""
        return True

    # ─────────────────────────────────────────────────────────────
    # Event Handlers
    # ─────────────────────────────────────────────────────────────

    async def handle_github_pr_opened(self, event: Dict[str, Any]) -> None:
        """
        Handle when GitHub PR is opened.

        If PR title contains Jira issue key (e.g., "PROJ-123"),
        automatically link the PR to that issue.
        """
        pr_number = event.get("number")
        pr_title = event.get("title", "")
        pr_url = event.get("url", "")

        logger.info(f"GitHub PR opened: #{pr_number} {pr_title}")

        # Extract Jira issue key from PR title
        jira_keys = self._extract_jira_keys(pr_title)

        if not jira_keys:
            logger.info(f"PR #{pr_number}: No Jira issue found in title")
            return

        # Link first issue found
        issue_key = jira_keys[0]
        logger.info(f"Linking PR #{pr_number} to {issue_key}")

        try:
            # Add comment to Jira issue
            await self._link_pr_to_issue(issue_key, pr_number, pr_url)

            # Track the link
            await self.state_store.set(
                f"jira.github.linked_issues.{pr_url}",
                issue_key
            )

            # Increment counter
            await self.state_store.increment("jira.github.sync_count")

            # Update last sync time
            from datetime import datetime
            await self.state_store.set(
                "jira.github.last_sync",
                datetime.utcnow().isoformat()
            )

            # Publish event for other skills
            await self.event_bus.publish("jira.github.linked", {
                "issue_key": issue_key,
                "pr_number": pr_number,
                "pr_url": pr_url,
                "action": "link",
            })

            logger.info(
                f"Successfully linked {issue_key} ↔ PR #{pr_number}"
            )

        except Exception as e:
            logger.error(
                f"Failed to link {issue_key} to PR #{pr_number}: {e}",
                exc_info=True
            )

    async def handle_github_pr_closed(self, event: Dict[str, Any]) -> None:
        """
        Handle when GitHub PR is closed.

        Update any linked Jira issues with PR closure information.
        """
        pr_number = event.get("number")
        pr_url = event.get("url", "")
        merged = event.get("merged", False)

        logger.info(f"GitHub PR closed: #{pr_number} (merged={merged})")

        # Find linked Jira issue
        linked_issue = await self.state_store.get(
            f"jira.github.linked_issues.{pr_url}",
            default=None
        )

        if not linked_issue:
            logger.info(f"PR #{pr_number}: No linked Jira issue")
            return

        try:
            # Add comment to Jira issue
            status = "merged" if merged else "closed"
            comment = f"GitHub PR #{pr_number} {status}"

            # Add transition if merged
            if merged:
                logger.info(f"Transitioning {linked_issue} to Done")
                # In real scenario, would transition issue status

            logger.info(f"Updated {linked_issue}: {comment}")

            # Publish event
            await self.event_bus.publish("jira.github.closed", {
                "issue_key": linked_issue,
                "pr_number": pr_number,
                "status": status,
            })

        except Exception as e:
            logger.error(f"Failed to update {linked_issue}: {e}")

    # ─────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────

    def _extract_jira_keys(self, text: str) -> list:
        """
        Extract Jira issue keys from text.

        Example: "PROJ-123: Add feature" → ["PROJ-123"]
        """
        # Jira key format: 1+ uppercase letters, dash, 1+ digits
        pattern = r"\b([A-Z][A-Z0-9]*)-(\d+)\b"
        matches = re.findall(pattern, text)
        return [f"{key}-{num}" for key, num in matches]

    async def _link_pr_to_issue(
        self,
        issue_key: str,
        pr_number: int,
        pr_url: str
    ) -> None:
        """
        Link GitHub PR to Jira issue by adding a comment.

        In a real implementation, would use Jira API:
        - Add comment with link to PR
        - Optionally link via issue linking API
        """
        comment_text = (
            f"Linked in GitHub: [PR #{pr_number}|{pr_url}]\n\n"
            f"This pull request implements this issue."
        )

        # In real scenario:
        # self.jira_client.add_comment(issue_key, comment_text)

        logger.info(f"Would add comment to {issue_key}: {comment_text}")


# ─────────────────────────────────────────────────────────────
# Example: Manual Workflow
# ─────────────────────────────────────────────────────────────

async def example_workflow():
    """
    Example workflow showing the integration in action.

    Usage:
      python jira_github_integration.py
    """
    devarmor = await get_devarmor()

    # Setup integration
    integration = JiraGithubIntegration()
    integration.event_bus = devarmor.event_bus
    integration.state_store = devarmor.state_store

    await integration.on_install()

    # Simulate GitHub PR being opened
    print("\n1. Opening GitHub PR: 'PROJ-123: Add authentication'")
    await devarmor.event_bus.publish("github.pr.opened", {
        "number": 42,
        "title": "PROJ-123: Add authentication",
        "url": "https://github.com/my-org/repo/pull/42",
        "author": "alice@example.com",
    })

    # Give event time to process
    await asyncio.sleep(1)

    # Check state
    linked_issues = await devarmor.state_store.query("jira.github.*")
    print(f"\n2. State after linking:\n{linked_issues}")

    # Simulate PR being merged
    print("\n3. Merging PR #42")
    await devarmor.event_bus.publish("github.pr.closed", {
        "number": 42,
        "url": "https://github.com/my-org/repo/pull/42",
        "merged": True,
    })

    await asyncio.sleep(1)

    # Check final state
    sync_count = await devarmor.state_store.get(
        "jira.github.sync_count"
    )
    print(f"\n4. Total syncs: {sync_count}")

    # Cleanup
    await integration.on_uninstall()


if __name__ == "__main__":
    asyncio.run(example_workflow())
