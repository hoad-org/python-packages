# DevArmor Core

Skill Governance Platform - Policy-driven management, installation, and lifecycle orchestration for skills.

## Overview

DevArmor Core provides:

- **Async-First API** - All operations support asyncio for high-performance applications
- **Policy Engine** - Evaluate cost control, security, and skill permission policies
- **Skill Lifecycle** - Install, upgrade, and remove skills with full state management
- **Event System** - Publish and subscribe to skill lifecycle events
- **Audit Logging** - Comprehensive audit trail of all decisions and actions
- **Configuration Hierarchy** - 4-level config system (code defaults → master → repo → env vars)

## Quick Start

### Installation

```bash
pip install devarmor-core
```

### Basic Usage

```python
import asyncio
from devarmor import DevArmorAPI

async def main():
    # Initialize API
    api = DevArmorAPI()
    await api.initialize()
    
    # Install a skill
    result = await api.install_skill(
        skill_name="my-skill",
        version="1.0.0",
        actor="user"
    )
    print(f"Installed: {result}")
    
    # List installed skills
    skills = await api.list_installed_skills()
    print(f"Installed skills: {skills}")
    
    # Get system status
    status = await api.get_system_status()
    print(f"Status: {status}")

asyncio.run(main())
```

## Configuration

DevArmor uses a 4-level configuration hierarchy:

1. **Code Defaults** - Built-in defaults in the package
2. **Master Config** - `~/.devarmor/config.yaml` (applies to all projects)
3. **Repo Config** - `.devarmor/config.yaml` (project-specific)
4. **Environment Variables** - `DEVARMOR_*` (highest priority)

### Example Configuration

```yaml
# .devarmor/config.yaml
cost_control:
  enabled: true
  global_limit:
    amount: 100.0
    currency: USD
    period: monthly

security:
  enabled: true
  require_approval: true
  forbidden_patterns:
    - "DROP.*TABLE"
    - "DELETE.*FROM"

skill_permissions:
  enabled: true
  skill_allowlist:
    - safe-skill
    - another-safe-skill
  skill_blocklist:
    - dangerous-skill
```

### Environment Variables

```bash
export DEVARMOR_COST_CONTROL_ENABLED=true
export DEVARMOR_SECURITY_REQUIRE_APPROVAL=false
export DEVARMOR_SKILL_PERMISSIONS_SKILL_ALLOWLIST='["skill1", "skill2"]'
```

## Core Components

### DevArmorAPI

Main entry point for all operations:

```python
api = DevArmorAPI(
    config_dir=Path("~/.devarmor"),
    skills_dir=Path("~/.devarmor/skills"),
    log_dir=Path("~/.devarmor/audit")
)

# Initialize before use
await api.initialize()

# Install skill
await api.install_skill(skill_name="skill1", version="1.0.0")

# Upgrade skill
await api.upgrade_skill(skill_name="skill1", new_version="2.0.0")

# Remove skill
await api.remove_skill(skill_name="skill1")

# List installed skills
skills = await api.list_installed_skills()

# Subscribe to events
subscriber_id = await api.subscribe_to_events(
    callback=async_callback_function
)

# Get system status
status = await api.get_system_status()
```

### PolicyEngine

Evaluate policies and make authorization decisions:

```python
from devarmor import PolicyEngine, PolicyConfig

config = PolicyConfig()
engine = PolicyEngine(config)

# Evaluate skill installation
evaluation = engine.evaluate_skill_installation(
    skill_name="test-skill",
    version="1.0.0",
    actor="user"
)

if not evaluation.allowed:
    print(f"Installation denied: {evaluation.violated_policies}")
```

### SkillLifecycleManager

Manage skill installation, upgrades, and removal:

```python
from devarmor import SkillLifecycleManager

manager = SkillLifecycleManager()

# Install
skill_info = await manager.install_skill(
    skill_name="test-skill",
    version="1.0.0"
)

# List installed
skills = manager.list_installed_skills()

# Check if installed
if manager.is_skill_installed("test-skill"):
    print("Skill is installed")
```

### EventBus

Publish and subscribe to events:

```python
from devarmor import EventBus

bus = EventBus()

# Subscribe to events
async def on_event(event):
    print(f"Event: {event.event_type}")

subscriber_id = bus.subscribe(on_event)

# Publish skill installed event
await bus.publish_skill_installed(
    skill_name="test-skill",
    version="1.0.0",
    actor="user"
)

# Unsubscribe
bus.unsubscribe(subscriber_id)
```

### AuditLogger

Log all decisions and actions:

```python
from devarmor import AuditLogger

logger = AuditLogger()

# Log action
entry = logger.log_action(
    actor="user",
    action="install",
    resource="skill1",
    result="success",
    details={"version": "1.0.0"}
)

# Get recent entries
entries = logger.get_entries(limit=10)

# Filter by actor
user_actions = logger.get_entries_for_actor("user")

# Export to JSON
logger.export_to_json(Path("audit.json"))
```

## Error Handling

All errors inherit from `DevArmorError`:

```python
from devarmor import (
    PolicyViolation,
    AccessDenied,
    LifecycleError,
    StateError,
)

try:
    await api.install_skill(skill_name="dangerous", version="1.0.0")
except PolicyViolation as e:
    print(f"Policy violation: {e.violated_policies}")
except AccessDenied as e:
    print(f"Access denied: {e}")
except LifecycleError as e:
    print(f"Lifecycle error: {e}")
except StateError as e:
    print(f"Invalid state transition: {e}")
```

## Development

### Installation with Development Dependencies

```bash
make dev-install
```

### Run Tests

```bash
make test
```

### Generate Coverage Report

```bash
make coverage
```

### Check Code Quality

```bash
make check          # Run all checks
make lint          # Linting
make format        # Format code
make type-check    # Type checking
make security      # Security scan
```

## Testing

The package includes comprehensive test coverage:

- **test_config.py** - Configuration loading and hierarchy
- **test_policy.py** - Policy engine evaluation
- **test_lifecycle.py** - Skill lifecycle management
- **test_events.py** - Event publishing and subscription
- **test_audit.py** - Audit logging
- **integration/test_end_to_end.py** - End-to-end workflows

Run tests with:

```bash
pytest              # Run all tests
pytest -v          # Verbose output
pytest -cov        # With coverage report
```

## Architecture

DevArmor Core uses a 3-pillar architecture:

```
┌─────────────────────────────────────┐
│        CLI / API Layer              │
│   (DevArmorAPI - routing)           │
└──────────────────┬──────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
    ┌─────────────┐    ┌──────────────┐
    │   Config    │    │ Guardrails   │
    │  (4-level)  │    │  (policies)  │
    └─────────────┘    └──────────────┘
```

Each pillar is independent and can be tested in isolation.

## License

MIT

## Author

Craig Hoad

## References

- [DevArmor Architecture](../../docs/ARCHITECTURE.md)
- [Configuration Guide](../../docs/CONFIG.md)
- [Policy Specification](../../docs/POLICIES.md)
