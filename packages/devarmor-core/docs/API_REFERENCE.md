# DevArmor API Reference

Complete reference for the DevArmor Python API.

---

## Core Classes

### DevArmorClient

Main entry point for DevArmor integration.

```python
class DevArmorClient:
    """DevArmor control plane client"""
```

#### `async def get_devarmor() -> DevArmorClient`

Get the singleton DevArmorClient instance.

```python
from devarmor import get_devarmor

client = await get_devarmor()
# Returns singleton instance
```

**Returns:** `DevArmorClient` singleton

**Example:**
```python
async def main():
    devarmor = await get_devarmor()
    print(f"DevArmor version: {devarmor.version}")
```

---

### Configuration API

#### `config: DevArmorConfig`

Access configuration with 4-level hierarchy.

```python
from devarmor import get_devarmor, DevArmorConfig

async def main():
    devarmor = await get_devarmor()
    config = devarmor.config
    
    # Get configuration value
    timeout = config.get("timeout", default=30)  # Returns int or default
    
    # Get all configuration
    all_config = config.to_dict()
    
    # Watch for changes
    config.watch("timeout", callback=on_timeout_changed)
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `get(key: str, default=None) -> Any` | Get config value with hierarchy |
| `set` | `set(key: str, value: Any) -> None` | Set config value (highest priority) |
| `to_dict` | `to_dict() -> dict` | Get all configuration as dict |
| `watch` | `watch(key: str, callback: Callable) -> None` | Watch for config changes |
| `reload` | `async reload() -> None` | Reload config from files |

**Example:**
```python
# Configuration hierarchy (priority: lowest to highest)
# 1. Code defaults:     timeout=30
# 2. Master config:     timeout=60
# 3. Repo config:       timeout=120
# 4. Environment:       TIMEOUT=180

# Result: config.get("timeout") returns 180

# Get all sources
config.get("timeout", return_sources=True)
# Returns: (180, {
#     "code_default": 30,
#     "master_config": 60,
#     "repo_config": 120,
#     "environment": 180
# })
```

---

### Event Bus API

Publish and subscribe to inter-skill events.

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    event_bus = devarmor.event_bus
    
    # Subscribe to events
    await event_bus.subscribe("jira.issue.created", handle_issue)
    
    # Publish events
    await event_bus.publish("github.pr.opened", {
        "pr_number": 123,
        "title": "Add feature X"
    })
```

**Methods:**

#### `async def subscribe(event_name: str, callback: Callable) -> None`

Subscribe to events.

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_name` | str | Event name (e.g., "jira.issue.created") |
| `callback` | Callable | Async function called when event fires |

**Returns:** None

**Raises:**
- `EventBusError` - If subscription fails

**Example:**
```python
async def handle_issue_created(event: Dict[str, Any]) -> None:
    """Handle when issue is created"""
    issue_key = event["issue_key"]
    print(f"Issue created: {issue_key}")

await event_bus.subscribe("jira.issue.created", handle_issue_created)
```

#### `async def publish(event_name: str, data: Dict[str, Any]) -> str`

Publish an event.

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_name` | str | Event name (e.g., "jira.issue.created") |
| `data` | Dict | Event data/payload |

**Returns:** Event ID (UUID)

**Raises:**
- `EventBusError` - If publish fails
- `ValidationError` - If data invalid

**Example:**
```python
event_id = await event_bus.publish("jira.issue.created", {
    "issue_key": "PROJ-123",
    "summary": "Add feature X",
    "user": "alice@example.com"
})
print(f"Published event: {event_id}")
```

#### `async def unsubscribe(event_name: str, callback: Callable) -> None`

Unsubscribe from events.

**Example:**
```python
await event_bus.unsubscribe("jira.issue.created", handle_issue_created)
```

#### `async def list_subscriptions() -> List[str]`

List all subscriptions.

**Returns:** List of (skill, event_name) tuples

**Example:**
```python
subs = await event_bus.list_subscriptions()
# Returns: [
#     ("jira-skill", "github.pr.opened"),
#     ("github-skill", "jira.issue.created"),
#     ("slack-skill", "jira.issue.created")
# ]
```

---

### State Store API

Shared, queryable state across all skills.

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    state = devarmor.state_store
    
    # Get state
    count = await state.get("jira.issue.count")
    
    # Set state
    await state.set("jira.last_issue", "PROJ-123")
    
    # Increment counter
    await state.increment("user.alice.cost", 10)
```

**Methods:**

#### `async def get(key: str, default=None) -> Any`

Get a state value.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | str | State key (e.g., "jira.issue.count") |
| `default` | Any | Default if key not found |

**Returns:** State value or default

**Raises:**
- `KeyError` - If key not found and no default

**Example:**
```python
cost = await state.get("user.alice.cost", default=0)
# Returns: 250 (or 0 if not set)
```

#### `async def set(key: str, value: Any) -> None`

Set a state value.

**Example:**
```python
await state.set("jira.last_issue", "PROJ-123")
```

#### `async def increment(key: str, amount: int = 1) -> int`

Increment a numeric value.

**Returns:** New value

**Example:**
```python
new_count = await state.increment("jira.issue.count")
# Increments by 1, returns new value
```

#### `async def decrement(key: str, amount: int = 1) -> int`

Decrement a numeric value.

**Example:**
```python
await state.decrement("user.alice.credits", 10)
```

#### `async def query(pattern: str) -> Dict[str, Any]`

Query state by key pattern.

| Parameter | Type | Description |
|-----------|------|-------------|
| `pattern` | str | Key pattern with wildcards (e.g., "user.*.cost") |

**Returns:** Dict of matching keys and values

**Example:**
```python
user_data = await state.query("user.alice.*")
# Returns: {
#     "user.alice.cost": 250,
#     "user.alice.requests_per_minute": 5,
#     "user.alice.last_action": "2026-05-17T14:30:00Z"
# }
```

#### `async def delete(key: str) -> None`

Delete a state value.

**Example:**
```python
await state.delete("user.alice.temporary")
```

#### `async def transaction(fn: Callable) -> Any`

Execute state operations in transaction.

**Example:**
```python
async def transfer_credits():
    async with state.transaction() as txn:
        alice_balance = await txn.get("user.alice.credits")
        bob_balance = await txn.get("user.bob.credits")
        
        await txn.set("user.alice.credits", alice_balance - 10)
        await txn.set("user.bob.credits", bob_balance + 10)
    # Commits on success, rolls back on error
```

---

### Policy Engine API

Evaluate and manage policies.

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    policy_engine = devarmor.policy_engine
    
    # Evaluate action
    decision = await policy_engine.evaluate({
        "user": "alice@example.com",
        "action": "create_resource",
        "cost": 100
    })
```

#### `async def evaluate(context: Dict[str, Any]) -> PolicyDecision`

Evaluate policies for an action.

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | Dict | Action context (user, action, cost, etc.) |

**Returns:** `PolicyDecision` object

**Example:**
```python
decision = await policy_engine.evaluate({
    "user": "alice@example.com",
    "action": "jira.issue.create",
    "cost": 0,
    "project": "MY_PROJECT"
})

# Check decision
if decision.allowed:
    print("Action allowed")
else:
    print(f"Action denied: {decision.message}")

# Check warnings
for warning in decision.warnings:
    print(f"Warning: {warning.message}")
```

#### `class PolicyDecision`

Result of policy evaluation.

```python
class PolicyDecision:
    allowed: bool          # True if action allowed
    message: str          # Reason if denied
    warnings: List[Dict]  # Warnings/advice
    decisions: List[Dict] # Which policies evaluated
    timestamp: datetime   # When evaluated
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `allowed` | bool | Action allowed? |
| `message` | str | Denial message |
| `warnings` | List | Warning list |
| `decisions` | List | Policy evaluations |

---

### Audit Log API

Query and manage audit logs.

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    audit = devarmor.audit_log
    
    # Query audit logs
    entries = await audit.query("user=alice AND action=issue.created")
    
    # Export logs
    await audit.export("audit-export.csv", format="csv")
```

**Methods:**

#### `async def query(filter_expr: str, limit: int = 100) -> List[AuditEntry]`

Query audit logs.

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter_expr` | str | Filter expression (see OPERATOR_RUNBOOK.md) |
| `limit` | int | Max results (default: 100, max: 10000) |

**Returns:** List of AuditEntry objects

**Example:**
```python
# Query by user
entries = await audit.query("user=alice@example.com", limit=50)

# Query by action
entries = await audit.query("action=jira.issue.created")

# Query by date range
entries = await audit.query(
    "timestamp >= 2026-05-01 AND timestamp < 2026-06-01"
)
```

#### `async def export(output_path: str, format: str = "json") -> str`

Export audit logs.

| Parameter | Type | Description |
|-----------|------|-------------|
| `output_path` | str | File path to save to |
| `format` | str | Format: json, csv, parquet |

**Returns:** Path to exported file

**Example:**
```python
path = await audit.export(
    "audit-may-2026.csv",
    format="csv"
)
print(f"Exported to: {path}")
```

---

## DevArmorContext

Context for an action being evaluated.

```python
class DevArmorContext:
    user: str              # User ID/email
    action: str            # Action name (e.g., "jira.issue.create")
    skill: str            # Skill name (e.g., "jira-skill")
    params: Dict[str, Any] # Action parameters
    timestamp: datetime    # When action started
    cost: int             # Estimated/actual cost
```

**Creating a context:**
```python
context = devarmor.create_context(
    user="alice@example.com",
    action="jira.issue.create",
    params={"project": "MY_PROJECT", "summary": "New issue"}
)
```

---

## IDevArmorCompliant Interface

Interface for skills to implement DevArmor compliance.

```python
class IDevArmorCompliant:
    """Skill must implement these methods"""
    
    async def on_install(self) -> None:
        """Called when skill is installed"""
    
    async def on_uninstall(self) -> None:
        """Called when skill is uninstalled"""
    
    async def validate_action(
        self,
        action: str,
        params: Dict[str, Any],
        context: DevArmorContext
    ) -> bool:
        """Validate action before execution. Return True to allow."""
```

**Example implementation:**
```python
class MySkillCompliance(IDevArmorCompliant):
    async def on_install(self) -> None:
        print("Installing my-skill")
    
    async def on_uninstall(self) -> None:
        print("Uninstalling my-skill")
    
    async def validate_action(self, action, params, context):
        # Custom validation logic
        return True
```

---

## Error Handling

### Exception Hierarchy

```python
DevArmorError                   # Base exception
├── ConfigError                # Configuration issue
├── EventBusError              # Event bus failure
├── PolicyError                # Policy evaluation error
├── StateStoreError            # State store failure
├── AuditLogError              # Audit log failure
├── SkillError                 # Skill-related error
└── ValidationError            # Validation failure
```

**Example:**
```python
from devarmor import DevArmorError, PolicyError

try:
    decision = await policy_engine.evaluate(context)
except PolicyError as e:
    print(f"Policy error: {e}")
except DevArmorError as e:
    print(f"DevArmor error: {e}")
```

---

## Retry & Timeout Behavior

### Automatic Retries

DevArmor automatically retries transient failures:

| Operation | Max Retries | Backoff | Conditions |
|-----------|-------------|---------|-----------|
| Event publish | 3 | Exponential | Network errors |
| State get/set | 5 | Linear | Timeout, connection reset |
| Policy eval | 2 | Exponential | Timeout |
| Audit write | 5 | Exponential | Write failure |

**Example:**
```python
# This will retry up to 3 times on network error
await event_bus.publish("jira.issue.created", data)
```

### Timeouts

| Operation | Default Timeout | Configurable |
|-----------|-----------------|--------------|
| Event publish | 10s | Yes (config: event_bus.timeout) |
| State operation | 5s | Yes (config: state_store.timeout) |
| Policy evaluation | 1s | Yes (config: policy.timeout) |
| Skill command | 30s | Yes (config: skill.timeout) |

**Example:**
```python
# Override timeout
config.set("event_bus.timeout", 30)  # 30 second timeout

# Or via environment variable
os.environ["EVENT_BUS_TIMEOUT"] = "30"
```

---

## Rate Limiting & Quotas

### Rate Limit Headers

All API responses include rate limit info:

```python
response = await event_bus.publish(...)
# Headers:
#   X-RateLimit-Limit: 1000
#   X-RateLimit-Remaining: 999
#   X-RateLimit-Reset: 2026-05-17T15:00:00Z
```

### Quota Information

```python
# Check remaining quota
remaining = devarmor.get_quota("events_per_hour")
# Returns: 945 events remaining this hour

# Check reset time
reset_time = devarmor.get_quota_reset("events_per_hour")
# Returns: datetime when quota resets
```

---

## Code Examples

### Example 1: Publish & Subscribe

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    event_bus = devarmor.event_bus
    
    # Define handler
    async def on_pr_opened(event):
        print(f"PR opened: #{event['number']}")
    
    # Subscribe
    await event_bus.subscribe("github.pr.opened", on_pr_opened)
    
    # Publish (e.g., from another skill)
    await event_bus.publish("github.pr.opened", {
        "number": 123,
        "title": "Add feature X"
    })
```

### Example 2: Policy Evaluation

```python
from devarmor import get_devarmor, PolicyError

async def create_issue(project, summary):
    devarmor = await get_devarmor()
    
    # Create context
    context = devarmor.create_context(
        user="alice@example.com",
        action="jira.issue.create",
        params={"project": project}
    )
    
    # Evaluate policies
    try:
        decision = await devarmor.policy_engine.evaluate(context.to_dict())
        if not decision.allowed:
            raise PolicyError(decision.message)
    except PolicyError as e:
        print(f"Action denied: {e}")
        return
    
    # Proceed with action
    issue = jira_client.create_issue(project, summary)
    
    # Publish event
    await devarmor.event_bus.publish("jira.issue.created", {
        "issue_key": issue.key,
        "project": project
    })
```

### Example 3: State Management

```python
from devarmor import get_devarmor

async def main():
    devarmor = await get_devarmor()
    state = devarmor.state_store
    
    # Increment counter
    count = await state.increment("jira.issue.count")
    print(f"Total issues: {count}")
    
    # Update user cost
    await state.increment("user.alice.cost", 10)
    
    # Query related state
    user_data = await state.query("user.alice.*")
    print(user_data)
```

---

## Next Steps

1. **SKILL_INTEGRATION_GUIDE.md** - Integrate your skill
2. **POLICY_CONFIGURATION.md** - Write policies
3. **OPERATOR_RUNBOOK.md** - Deploy to production
4. **examples/** - Working examples
