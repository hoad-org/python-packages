# Skill Integration Guide

## Quick Start (5 Minutes)

To integrate an existing skill with DevArmor:

1. **Add DevArmor dependency**
   ```bash
   pip install devarmor-core>=1.0.0
   ```

2. **Implement IDevArmorCompliant interface**
   ```python
   from devarmor import IDevArmorCompliant, DevArmorConfig
   
   class JiraSkill(IDevArmorCompliant):
       async def on_install(self) -> None:
           """Called when skill is installed"""
       
       async def on_uninstall(self) -> None:
           """Called when skill is uninstalled"""
       
       async def validate_action(self, action: str, params: dict) -> bool:
           """Validate action before execution"""
   ```

3. **Register with DevArmor**
   ```python
   from devarmor import devarmor_registry
   
   devarmor_registry.register(JiraSkill())
   ```

4. **Publish and subscribe to events**
   ```python
   # Publish
   await devarmor.event_bus.publish("jira.issue.created", {...})
   
   # Subscribe
   await devarmor.event_bus.subscribe("github.pr.opened", handle_github_pr)
   ```

5. **Test integration**
   ```bash
   devarmor test jira-skill
   ```

---

## Detailed Integration Steps

### Step 1: Update Dependencies

Add DevArmor to your skill's `setup.py` or `pyproject.toml`:

**pyproject.toml:**
```toml
[project]
name = "jira-skill"
version = "2.0.0"
dependencies = [
    "devarmor-core>=1.0.0",
    "jira>=3.0.0",
    "pydantic>=2.0.0",
]
```

**setup.py:**
```python
setup(
    name="jira-skill",
    version="2.0.0",
    install_requires=[
        "devarmor-core>=1.0.0",
        "jira>=3.0.0",
        "pydantic>=2.0.0",
    ],
)
```

### Step 2: Implement IDevArmorCompliant Interface

Create a new file `src/devarmor_integration.py`:

```python
"""DevArmor integration for Jira skill"""
from typing import Any, Dict, Optional
import logging

from devarmor import (
    IDevArmorCompliant,
    DevArmorConfig,
    DevArmorContext,
    EventBus,
    StateStore,
)

logger = logging.getLogger(__name__)


class JiraDevArmorIntegration(IDevArmorCompliant):
    """DevArmor compliance layer for Jira skill"""
    
    def __init__(self, config: DevArmorConfig):
        self.config = config
        self.event_bus: Optional[EventBus] = None
        self.state_store: Optional[StateStore] = None
    
    async def on_install(self) -> None:
        """
        Called when skill is installed.
        
        Use this to:
        - Initialize state keys
        - Register event subscriptions
        - Set up audit trails
        - Register guardrails
        """
        logger.info("Jira skill installing with DevArmor")
        
        # Initialize state keys
        await self.state_store.initialize({
            "jira.issue.count": 0,
            "jira.last_issue": None,
            "jira.user.*.cost": 0,  # Per-user cost tracking
        })
        
        # Register guardrails
        self.config.register_guardrail(
            name="jira_rate_limit",
            rule="jira.user.${user_id}.requests_per_minute < 100",
            action="deny",
            message="Jira rate limit exceeded (100/min)",
        )
        
        # Subscribe to events from other skills
        await self.event_bus.subscribe(
            "github.pr.opened",
            self._on_github_pr_opened
        )
    
    async def on_uninstall(self) -> None:
        """
        Called when skill is uninstalled.
        
        Use this to:
        - Cleanup state keys
        - Unsubscribe from events
        - Archive audit logs
        """
        logger.info("Jira skill uninstalling")
        
        # Unsubscribe from events
        await self.event_bus.unsubscribe(
            "github.pr.opened",
            self._on_github_pr_opened
        )
        
        # Archive audit logs for this skill
        await self.state_store.archive_logs("jira")
    
    async def validate_action(
        self,
        action: str,
        params: Dict[str, Any],
        context: DevArmorContext,
    ) -> bool:
        """
        Validate action before execution.
        
        Return True to allow, False to deny.
        DevArmor will handle confirmation gates automatically.
        """
        # Example: deny if project not in allowlist
        if action == "create_issue":
            allowed_projects = self.config.get(
                "allowed_projects",
                ["PROJ"],
            )
            if params.get("project") not in allowed_projects:
                logger.warning(
                    f"Denied: project {params['project']} "
                    f"not in {allowed_projects}"
                )
                return False
        
        return True
    
    async def _on_github_pr_opened(self, event: Dict[str, Any]) -> None:
        """Handle GitHub PR opened events"""
        logger.info(f"GitHub PR opened: {event['pr_number']}")
        
        # Example: automatically link PR to Jira
        pr_title = event.get("title", "")
        if "PROJ-" in pr_title:
            # Extract issue key and link it
            issue_key = pr_title.split("PROJ-")[1].split()[0]
            logger.info(f"Linking to {issue_key}")
```

### Step 3: Register with DevArmor

Update your skill's CLI entry point (`src/cli.py`):

```python
"""Jira skill CLI"""
import asyncio
from devarmor import get_devarmor, devarmor_registry
from devarmor_integration import JiraDevArmorIntegration
from jira_client import JiraClient

# Global instances
devarmor_client = None
jira_client = None


async def initialize_devarmor():
    """Initialize DevArmor integration"""
    global devarmor_client
    
    devarmor_client = await get_devarmor()
    
    # Register this skill
    integration = JiraDevArmorIntegration(
        config=devarmor_client.config,
    )
    
    devarmor_registry.register(
        skill_name="jira",
        integration=integration,
    )
    
    # Inject dependencies
    integration.event_bus = devarmor_client.event_bus
    integration.state_store = devarmor_client.state_store


async def create_issue(project: str, summary: str, **kwargs):
    """Create a Jira issue with DevArmor compliance"""
    
    # Ensure DevArmor is initialized
    if devarmor_client is None:
        await initialize_devarmor()
    
    # Validate action (will check policies, rate limits, etc)
    context = devarmor_client.create_context(
        user="current_user",
        action="jira.issue.create",
        params={"project": project, "summary": summary},
    )
    
    if not await devarmor_client.validate_action(context):
        raise PermissionError("Action denied by policy")
    
    # Create the issue
    issue = jira_client.create_issue(
        project=project,
        summary=summary,
        **kwargs
    )
    
    # Publish event for other skills
    await devarmor_client.event_bus.publish(
        "jira.issue.created",
        {
            "issue_key": issue.key,
            "project": project,
            "summary": summary,
            "user": context.user,
            "timestamp": context.timestamp,
        }
    )
    
    # Update state
    await devarmor_client.state_store.increment("jira.issue.count")
    await devarmor_client.state_store.set(
        "jira.last_issue",
        issue.key
    )
    
    return issue


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jira skill CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # create-issue subcommand
    create_parser = subparsers.add_parser("create-issue")
    create_parser.add_argument("--project", required=True)
    create_parser.add_argument("--summary", required=True)
    create_parser.add_argument("--description", default="")
    
    args = parser.parse_args()
    
    if args.command == "create-issue":
        issue = asyncio.run(create_issue(
            project=args.project,
            summary=args.summary,
            description=args.description,
        ))
        print(f"Created: {issue.key}")


if __name__ == "__main__":
    main()
```

### Step 4: Implement Event Publishing/Subscribing

Update your skill to publish and subscribe to events:

```python
# File: src/event_handlers.py

import asyncio
from typing import Dict, Any
from devarmor import get_devarmor

devarmor = None


async def setup_event_handlers():
    """Setup event subscriptions"""
    global devarmor
    devarmor = await get_devarmor()
    
    # Subscribe to events from other skills
    await devarmor.event_bus.subscribe(
        "github.pr.opened",
        handle_github_pr_opened,
    )
    
    await devarmor.event_bus.subscribe(
        "github.issue.created",
        handle_github_issue_created,
    )


async def handle_github_pr_opened(event: Dict[str, Any]) -> None:
    """Handle when GitHub PR is opened"""
    pr_title = event.get("title", "")
    pr_number = event.get("number")
    
    # If PR title contains Jira issue key, link them
    if "PROJ-" in pr_title:
        issue_key = pr_title.split("PROJ-")[1].split()[0]
        print(f"Linking PR #{pr_number} to {issue_key}")
        
        # The actual linking would happen here
        # This demonstrates cross-skill coordination


async def handle_github_issue_created(event: Dict[str, Any]) -> None:
    """Handle when GitHub issue is created"""
    issue_title = event.get("title", "")
    issue_number = event.get("number")
    
    print(f"GitHub issue #{issue_number}: {issue_title}")


# Called during skill initialization
asyncio.run(setup_event_handlers())
```

### Step 5: Write Tests for DevArmor Integration

Create `tests/test_devarmor_integration.py`:

```python
"""Tests for DevArmor integration"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from devarmor import DevArmorConfig, DevArmorContext
from devarmor_integration import JiraDevArmorIntegration


@pytest.fixture
def config():
    """Create mock DevArmor config"""
    return MagicMock(spec=DevArmorConfig)


@pytest.fixture
def integration(config):
    """Create integration instance"""
    return JiraDevArmorIntegration(config)


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_state_store():
    """Create mock state store"""
    store = AsyncMock()
    store.initialize = AsyncMock()
    store.increment = AsyncMock()
    store.set = AsyncMock()
    return store


@pytest.mark.asyncio
async def test_on_install_initializes_state(integration, mock_state_store):
    """Test that on_install initializes state keys"""
    integration.state_store = mock_state_store
    integration.event_bus = AsyncMock()
    
    await integration.on_install()
    
    # Verify state initialization
    mock_state_store.initialize.assert_called_once()
    init_call = mock_state_store.initialize.call_args[0][0]
    assert "jira.issue.count" in init_call
    assert init_call["jira.issue.count"] == 0


@pytest.mark.asyncio
async def test_validate_action_denies_unknown_project(integration):
    """Test that validate_action denies unknown projects"""
    integration.config.get = MagicMock(return_value=["PROJ"])
    
    context = MagicMock(spec=DevArmorContext)
    result = await integration.validate_action(
        action="create_issue",
        params={"project": "UNKNOWN"},
        context=context,
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_validate_action_allows_known_project(integration):
    """Test that validate_action allows known projects"""
    integration.config.get = MagicMock(return_value=["PROJ"])
    
    context = MagicMock(spec=DevArmorContext)
    result = await integration.validate_action(
        action="create_issue",
        params={"project": "PROJ"},
        context=context,
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_event_subscription_on_install(
    integration,
    mock_event_bus,
):
    """Test that on_install subscribes to events"""
    integration.event_bus = mock_event_bus
    integration.state_store = AsyncMock()
    integration.config.register_guardrail = MagicMock()
    
    await integration.on_install()
    
    # Verify event subscription
    mock_event_bus.subscribe.assert_called()
    call_args = mock_event_bus.subscribe.call_args[0]
    assert call_args[0] == "github.pr.opened"


@pytest.mark.asyncio
async def test_on_uninstall_unsubscribes(integration, mock_event_bus):
    """Test that on_uninstall unsubscribes from events"""
    integration.event_bus = mock_event_bus
    integration.state_store = AsyncMock()
    
    await integration.on_uninstall()
    
    # Verify event unsubscription
    mock_event_bus.unsubscribe.assert_called()
```

### Step 6: Configuration Files

Create `.devarmor/jira.json` in your repository:

```json
{
  "project": "MY_PROJECT",
  "rate_limit": 100,
  "timeout": 60,
  "allowed_projects": [
    "MY_PROJECT",
    "INFRA",
    "OPS"
  ],
  "api_version": "3",
  "cost_per_issue": 0,
  "cost_per_search": 0,
  "cost_per_transition": 5
}
```

And create a master config template at `~/.devarmor/skills/jira.json`:

```json
{
  "rate_limit": 100,
  "timeout": 60,
  "batch_size": 10,
  "retry_count": 3,
  "cache_ttl": 3600
}
```

### Step 7: Test DevArmor Integration

```bash
# Run integration tests
pytest tests/test_devarmor_integration.py -v

# Run full test suite with coverage
make test coverage

# Test skill with DevArmor
devarmor test jira-skill

# Verify policy compliance
devarmor policy-check jira-skill cost_control
```

---

## Real-World Example: Jira + GitHub Integration

Here's a complete workflow showing how Jira and GitHub skills coordinate via DevArmor.

### Setup

1. **Install both skills**
   ```bash
   devarmor install jira-skill@2.0.0
   devarmor install github-skill@2.0.0
   ```

2. **Configure policies**
   Create `.devarmor/policy-jira-github.yaml`:
   ```yaml
   name: JiraGitHubSync
   enabled: true
   constraints:
     - name: PrLinksJira
       rule: "github.pr.title contains JIRA-*"
       action: warn
       message: "PR title should reference Jira issue"
     
     - name: IssueLinksGithub
       rule: "jira.issue.description contains github.com/my-org"
       action: warn
       message: "Consider linking to GitHub repository"
   ```

3. **Implement cross-skill event handlers**

   **Jira Skill** (when issue is created):
   ```python
   async def create_issue(project, summary):
       # ... create in Jira ...
       
       # Publish event for GitHub skill
       await devarmor.event_bus.publish("jira.issue.created", {
           "issue_key": "PROJ-123",
           "summary": summary,
           "project": project,
       })
   ```

   **GitHub Skill** (subscribes to jira.issue.created):
   ```python
   async def on_jira_issue_created(event):
       # Automatically comment on linked PRs
       issue_key = event["issue_key"]
       
       # Find PRs with this issue key
       prs = github.search_prs(f"PROJ-123 in:title")
       
       for pr in prs:
           # Add comment linking to Jira
           github.add_comment(
               pr.number,
               f"Tracked in Jira: {issue_key}"
           )
           
           # Publish event
           await devarmor.event_bus.publish("github.pr.commented", {
               "pr_number": pr.number,
               "comment_text": f"Tracked in Jira: {issue_key}",
           })
   ```

### Result

```
User: "Create a Jira issue PROJ-123"
  │
  ├─→ Jira Skill
  │   ├─ Create issue in Jira
  │   ├─ Publish: jira.issue.created
  │   └─ Update state: jira.issue.count++
  │
  └─→ GitHub Skill (subscribed)
      ├─ Find linked PRs (PROJ-123 in title)
      ├─ Comment: "Tracked in Jira: PROJ-123"
      ├─ Publish: github.pr.commented
      └─ Emit audit: "github.pr.commented, user=alice"
```

---

## Troubleshooting

### Issue: "DevArmor not found"

```
ImportError: cannot import name 'get_devarmor' from 'devarmor'
```

**Solution**: Ensure devarmor-core is installed:
```bash
pip install devarmor-core>=1.0.0
```

### Issue: "Event subscription failed"

```
RuntimeError: Event bus not initialized
```

**Solution**: Initialize DevArmor before subscribing:
```python
async def main():
    await initialize_devarmor()
    # Now event_bus is ready
```

### Issue: "Policy validation failed"

```
PolicyError: Cost limit exceeded (used: 100, limit: 50)
```

**Solution**: Check state store values:
```bash
devarmor state get "user.alice.cost"
# Returns: 100

devarmor policy eval cost_control --user=alice
# Shows: DENY (cost 100 > limit 50)
```

### Issue: "Configuration not loading"

```
ConfigError: No configuration found for jira-skill
```

**Solution**: Verify configuration hierarchy:
```bash
# Check what's being loaded
devarmor config show jira-skill --verbose

# Verify files exist
ls -la ~/.devarmor/skills/jira.json
ls -la .devarmor/jira.json

# Check environment variables
env | grep JIRA_
```

---

## Next Steps

1. **Read POLICY_CONFIGURATION.md** - Learn how to write policies
2. **Read OPERATOR_RUNBOOK.md** - Deploy skills to production
3. **Read API_REFERENCE.md** - Complete API documentation
4. **See examples/** - Real working examples from Terrorgem
