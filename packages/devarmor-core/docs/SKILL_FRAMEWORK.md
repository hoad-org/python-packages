# DevArmor Skill Framework

## Overview

The DevArmor Skill Framework provides the foundational classes that all DevArmor-compliant skills must inherit from. It enables seamless integration with DevArmor's governance, policy enforcement, and lifecycle management systems.

**All skills must inherit from these base classes to be DevArmor-compliant.**

## Quick Start

### 1. Create Configuration

```python
from devarmor import BaseSkillConfig
from pydantic import Field

class MySkillConfig(BaseSkillConfig):
    """Configuration with 4-level hierarchy."""
    
    api_token: Optional[str] = Field(default=None)
    timeout: int = Field(default=30, ge=1, le=300)
    debug: bool = Field(default=False)

# Load from 4-level hierarchy
config = MySkillConfig.load("my-skill")
# Loads from: env vars > repo config > master config > defaults
```

### 2. Implement Skill

```python
from devarmor import BaseDevArmorSkill, ValidationResult

class MySkill(BaseDevArmorSkill):
    """Your skill implementation."""
    
    name = "my-skill"
    version = "1.0.0"
    description = "Does something amazing"
    author = "Your Name"
    
    async def validate_config(self, config: BaseSkillConfig) -> ValidationResult:
        """Validate skill-specific config."""
        result = ValidationResult(valid=True)
        # Custom validation logic
        return result
    
    async def on_install(self, devarmor: DevArmorAPI) -> None:
        """Initialize on install."""
        await super().on_install(devarmor)
        # Setup logic
    
    async def on_upgrade(self, old_version: str, devarmor: DevArmorAPI) -> None:
        """Migrate state on upgrade."""
        # Migration logic
    
    async def on_remove(self, devarmor: DevArmorAPI) -> None:
        """Clean up on remove."""
        # Cleanup logic
```

### 3. Build CLI (Optional)

```python
from devarmor import BaseSkillCLI

class MySkillCLI(BaseSkillCLI):
    """CLI for your skill."""
    
    skill_name = "my-skill"
    description = "My skill CLI"
    
    async def cmd_create(self, name: str) -> Dict[str, Any]:
        """Create a resource."""
        return {"status": "created", "name": name}
    
    async def cmd_delete(self, id: str) -> Dict[str, Any]:
        """Delete a resource."""
        return {"status": "deleted", "id": id}

# Execute
cli = MySkillCLI(config=config, skill=skill, devarmor=devarmor)
result = await cli.execute(["create", "--name=test"])
```

### 4. Write Tests

```python
from devarmor import SkillTestBase

class TestMySkill(SkillTestBase):
    """Tests for your skill."""
    
    skill_class = MySkill
    config_class = MySkillConfig
    
    @pytest.mark.asyncio
    async def test_install(self, skill, devarmor_api):
        """Test installation."""
        await skill.on_install(devarmor_api)
        # Assertions
    
    @pytest.mark.asyncio
    async def test_validate_config(self):
        """Test config validation."""
        config = self.mock_config()
        result = await self.skill_class().validate_config(config)
        assert result.valid
```

## Architecture

### 3-Pillar Design

Each skill has three independent pillars:

```
┌─────────────────────────────────────┐
│         CLI Layer (routing)         │
│   Validates input, routes, outputs  │
└──────────────────┬──────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
    ┌─────────────┐    ┌──────────────┐
    │   Config    │    │ Guardrails   │
    │  (4-level)  │    │(safety, rate)│
    └─────────────┘    └──────────────┘
```

Each pillar can be tested independently:
- **Config**: Test hierarchy without CLI or API
- **Skill**: Test lifecycle and policy checks without CLI
- **CLI**: Test routing and formatting without external calls

### Configuration Hierarchy (4 Levels)

```
Priority (highest to lowest):
1. Environment variables (SKILL_<NAME>_<KEY>=value)
2. Repo config (.claude/skillname.json)
3. Master config (~/.devarmor/skillname/config.json)
4. Code defaults (model field defaults)
```

**Example**: Setting `timeout` to 60

```bash
# 1. Via environment (highest priority)
SKILL_MY_SKILL_TIMEOUT=60

# 2. Via repo config
cat .claude/my-skill.json
# {"timeout": 60}

# 3. Via master config
cat ~/.devarmor/my-skill/config.json
# {"timeout": 60}

# 4. Via code defaults
class MySkillConfig(BaseSkillConfig):
    timeout: int = 60
```

**Loading**: `MySkillConfig.load("my-skill")` automatically merges all 4 levels with proper priority.

## Core Classes

### BaseSkillConfig

Pydantic-based configuration with 4-level hierarchy support.

```python
class MySkillConfig(BaseSkillConfig):
    """My skill configuration."""
    api_key: str = Field(...)
    timeout: int = Field(default=30, ge=1, le=300)

# Create with defaults
config = MySkillConfig(skill_name="my-skill")

# Load from hierarchy
config = MySkillConfig.load("my-skill", repo_config_dir=Path(".claude"))

# Override from environment
os.environ["SKILL_MY_SKILL_TIMEOUT"] = "60"
config = MySkillConfig.load("my-skill")  # timeout=60

# Save to master
config.save_to_master()  # ~/.devarmor/my-skill/config.json
```

**Key Methods**:
- `load(skill_name, repo_config_dir)`: Load from 4-level hierarchy
- `save_to_master()`: Save to master config location
- Pydantic validation: Field validation via Pydantic

### BaseDevArmorSkill

Abstract base class for all skills.

```python
class MySkill(BaseDevArmorSkill):
    name = "my-skill"
    version = "1.0.0"
    
    async def validate_config(self, config):
        """Implement this to validate config."""
        return ValidationResult(valid=True)
```

**Lifecycle Hooks** (all optional to override):
- `async on_install(devarmor)`: Called on first install
- `async on_upgrade(old_version, devarmor)`: Called on upgrade
- `async on_remove(devarmor)`: Called on removal

**Policy & Governance**:
- `async pre_action_check(action, params)`: Check if action is allowed
  - Raises: `SkillOperationBlockedError` if blocked
- `async publish_event(event_type, payload, severity)`: Publish skill events
- `async query_shared_state(entity_type, filters)`: Query state from other skills

**Info**:
- `get_info()`: Returns `SkillInfo` with metadata

### BaseSkillCLI

Async command routing and execution framework.

```python
class MySkillCLI(BaseSkillCLI):
    skill_name = "my-skill"
    
    async def cmd_create(self, name: str) -> Dict[str, Any]:
        """Create something."""
        return {"created": name}
    
    async def cmd_delete(self, id: str) -> Dict[str, Any]:
        """Delete something."""
        return {"deleted": id}

# Execute commands
cli = MySkillCLI(config=config, skill=skill, devarmor=devarmor)
result = await cli.execute(["create", "--name=test"])
```

**Key Methods**:
- `async execute(args, format)`: Execute a command
  - Args: `["command", "arg1", "arg2", ...]`
  - Format: `"text"`, `"json"`, `"yaml"`
- `format_output(data, format)`: Format output as string
- `help()`: Get help text for all commands

**Command Pattern**:
- Methods named `cmd_<name>` are exposed as commands
- Method name `cmd_create` -> command `create`
- Use async methods for long-running operations
- Return dict/str for output

### SkillTestBase

Testing utilities and fixtures.

```python
class TestMySkill(SkillTestBase):
    skill_class = MySkill
    config_class = MySkillConfig
    
    def test_something(self):
        # Use fixtures
        config = self.mock_config(timeout=45)
        api = self.mock_devarmor_api()
```

**Key Methods**:
- `mock_devarmor_api()`: Create mock API for testing
- `mock_config(**overrides)`: Create test config

**Mock API**:
- `async evaluate_action(skill_name, action, params)`: Mock policy check
- `async publish_event(skill_name, event_type, payload)`: Mock event pub
- `async query_shared_state(entity_type, filters)`: Mock state query

## Exception Hierarchy

All skill errors inherit from `SkillException` for easy catching.

```python
from devarmor import (
    SkillException,
    SkillConfigError,
    SkillAuthError,
    SkillOperationBlockedError,
    SkillRateLimitError,
    SkillValidationError,
)

try:
    # Skill operation
    pass
except SkillOperationBlockedError as e:
    # Operation blocked by policy
    print(f"Blocked: {e.reason}")
except SkillAuthError as e:
    # Auth failed
    print(f"Auth failed: {e.auth_type}")
except SkillException as e:
    # Any skill error
    print(f"Skill error: {e.message}")
```

## Common Patterns

### Pattern 1: Policy-Gated Operations

Always check policy before destructive operations:

```python
async def delete_resource(self, resource_id: str) -> None:
    """Delete a resource (with policy check)."""
    
    # Check policy first
    decision = await self.pre_action_check(
        "delete-resource",
        {"resource_id": resource_id}
    )
    
    if not decision.allowed:
        raise SkillOperationBlockedError(
            self.name,
            f"Cannot delete: {decision.reason}",
            operation="delete-resource",
        )
    
    # Do the deletion
    # ...
    
    # Publish event
    await self.publish_event("resource-deleted", {
        "resource_id": resource_id
    })
```

### Pattern 2: Configuration with Validation

```python
class MySkillConfig(BaseSkillConfig):
    """Config with validation."""
    
    api_key: str = Field(..., min_length=1)
    timeout: int = Field(default=30, ge=1, le=300)
    workers: int = Field(default=5, ge=1, le=50)

# Use validation in skill
async def validate_config(self, config):
    result = ValidationResult(valid=True)
    
    if isinstance(config, MySkillConfig):
        if config.timeout < config.workers * 5:
            result.warnings.append(
                "timeout may be too low for number of workers"
            )
    
    return result
```

### Pattern 3: Conditional CLI Methods

```python
class MySkillCLI(BaseSkillCLI):
    async def cmd_create(self, name: str) -> Dict[str, Any]:
        """Create (requires config)."""
        if not self.config:
            raise SkillValidationError(
                self.skill_name,
                "Config required",
            )
        # ...

    async def cmd_info(self) -> Dict[str, Any]:
        """Info (works without config)."""
        return {"version": self.skill.version}
```

### Pattern 4: Testing with Mocks

```python
class TestMySkill(SkillTestBase):
    @pytest.mark.asyncio
    async def test_operation_blocked(self):
        """Test policy blocking operation."""
        
        skill = self.skill_class()
        api = self.mock_devarmor_api()
        
        # Mock denied evaluation
        api.evaluate_action = AsyncMock(return_value=MagicMock(
            allowed=False,
            violated_policies=["cost-limit"],
        ))
        
        skill.devarmor = api
        
        # Should be blocked
        decision = await skill.pre_action_check("expensive-op")
        assert not decision.allowed
```

## Best Practices

### 1. Configuration

- Use Pydantic `Field()` for all config values
- Set meaningful defaults (never None for critical values)
- Validate in both config class and `validate_config()`
- Test 4-level hierarchy in tests

### 2. Lifecycle

- Call `await super().on_install()` before custom logic
- Implement migrations in `on_upgrade()` if schema changes
- Log all lifecycle events at INFO level
- Raise `LifecycleError` on failures

### 3. Policy Checks

- Call `pre_action_check()` before all destructive operations
- Include action parameters for better policy decisions
- Publish events after successful operations
- Use descriptive event types: `issue-created`, `resource-deleted`

### 4. Error Handling

- Raise specific `SkillException` subclasses
- Include context in `details` field
- Log errors at ERROR level with context
- Never expose secrets in error messages

### 5. Testing

- Achieve >85% test coverage
- Test config hierarchy separately
- Mock DevArmor API for unit tests
- Test lifecycle hooks independently
- Test CLI with sync and async commands
- Use `@pytest.mark.asyncio` for async tests

### 6. CLI

- Command methods must match `cmd_<name>` pattern
- Use async methods for long operations
- Return dict or str (automatically formatted)
- Provide help text via docstrings
- Test all commands in tests

## Integration with DevArmor

### Policy Evaluation

Before destructive operations, skills must check policy:

```python
decision = await skill.pre_action_check(
    action="create-instance",
    params={"instance_type": "t2.large", "region": "us-east-1"}
)

if not decision.allowed:
    # Operation blocked by policy
    # - Cost limit exceeded
    # - Security policy violation
    # - Rate limit reached
    # - Manual approval required
    raise SkillOperationBlockedError(...)
```

### Event Publishing

Publish events for important state changes:

```python
await skill.publish_event(
    event_type="instance-created",
    payload={
        "instance_id": "i-123456",
        "instance_type": "t2.large",
        "region": "us-east-1",
    },
    severity="info",
    visibility="org"  # organization-wide visibility
)
```

Events are indexed and queryable for:
- Audit trails
- Policy evaluation
- Cross-skill state discovery

### Shared State Query

Query state created by other skills:

```python
# Find EC2 instances created by any skill
instances = await skill.query_shared_state(
    entity_type="ec2-instance",
    filters={"region": "us-east-1"}
)

for instance in instances:
    print(f"Instance {instance['id']} by {instance['created_by_skill']}")
```

## Checklist for New Skills

Before releasing a new skill:

- [ ] Inherits from `BaseDevArmorSkill`
- [ ] Has `name`, `version`, `description`, `author`
- [ ] Implements `validate_config()`
- [ ] Config inherits from `BaseSkillConfig`
- [ ] All lifecycle hooks are implemented (or use defaults)
- [ ] Pre-action checks before destructive operations
- [ ] Events published for state changes
- [ ] CLI implemented (optional but recommended)
- [ ] >85% test coverage
- [ ] All code quality checks pass (lint, format, type-check)
- [ ] No hardcoded secrets
- [ ] Comprehensive docstrings
- [ ] SKILL.md with frontmatter
- [ ] Security.md documenting sensitive operations
- [ ] Examples in docs/

## See Also

- [Skill Development Guide](./SKILL_DEVELOPMENT.md)
- [Example Skill](../examples/example_skill.py)
- [Testing Guide](./TESTING.md)
- [DevArmor API](./API.md)
