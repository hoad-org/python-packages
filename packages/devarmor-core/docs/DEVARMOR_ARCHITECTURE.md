# DevArmor Architecture

## Overview

DevArmor is an enterprise control plane for Claude skills, providing policy-driven enforcement, compliance automation, and cross-skill coordination. It implements a three-layer architecture: **Installation**, **Execution**, and **Orchestration**.

## 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│        (Cross-skill events, state, coordination)                │
├─────────────────────────────────────────────────────────────────┤
│  Event Bus    │  State Store  │  Policy Engine  │  Audit Log    │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │ pub/sub
                           │
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER                              │
│        (Per-skill: configuration, guardrails, validation)       │
├─────────────────────────────────────────────────────────────────┤
│  Skill CLI    │  Config Layer  │  Guardrails  │  API Client     │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │ loads, calls
                           │
┌─────────────────────────────────────────────────────────────────┐
│                  INSTALLATION LAYER                             │
│        (Dependency resolution, configuration injection)         │
├─────────────────────────────────────────────────────────────────┤
│  Package Manager  │  Config Injector  │  Loader  │  Validator   │
└─────────────────────────────────────────────────────────────────┘
```

## Installation Layer

**Purpose**: Manage skill lifecycle (install, upgrade, remove) with zero-downtime and full rollback capability.

### Installation Process

```
devarmor install jira-skill@2.0.0
        │
        ├─→ Resolve dependencies
        │   └─→ Check conflicts with existing skills
        │
        ├─→ Validate package integrity
        │   ├─→ Verify signatures
        │   ├─→ Check Python version compatibility
        │   └─→ Scan for security issues
        │
        ├─→ Extract to isolated namespace
        │   └─→ /usr/local/lib/devarmor/skills/jira-skill/
        │
        ├─→ Inject DevArmor compliance layer
        │   ├─→ Load IDevArmorCompliant interface
        │   ├─→ Register with policy engine
        │   └─→ Initialize event subscriptions
        │
        ├─→ Load configuration (4-level hierarchy)
        │   ├─→ Code defaults
        │   ├─→ Master config (~/.devarmor/skills/jira.json)
        │   ├─→ Repo config (.devarmor/jira.json)
        │   └─→ Environment variables (ENV)
        │
        └─→ Run smoke tests
            └─→ Validate API connectivity
```

### Upgrade Process (Zero-Downtime)

```
devarmor upgrade jira-skill 2.0.0 → 2.1.0
        │
        ├─→ Install 2.1.0 parallel to 2.0.0
        │   └─→ /usr/local/lib/devarmor/skills/jira-skill@2.1.0/
        │
        ├─→ Run canary tests
        │   ├─→ Test API connectivity
        │   ├─→ Test configuration compatibility
        │   ├─→ Test event subscriptions
        │   └─→ Test policy compliance
        │
        ├─→ Once canary passes: switch traffic
        │   └─→ Update active symlink: jira-skill → jira-skill@2.1.0
        │
        └─→ Keep 2.0.0 for rollback
            └─→ Storage: /usr/local/lib/devarmor/skills/jira-skill@2.0.0/
```

## Execution Layer

**Purpose**: Per-skill: configuration management, guardrails enforcement, and API validation.

### Skill Command Execution

```
User Input: "Claude, create a Jira issue"
        │
        ├─→ CLI Routes Command
        │   └─→ jira-skill.create_issue(...)
        │
        ├─→ Load Configuration (4-level hierarchy)
        │   ├─→ Code defaults: timeout=30s, rate_limit=100/min
        │   ├─→ Master config (~/.devarmor/skills/jira.json): timeout=60s
        │   ├─→ Repo config (.devarmor/jira.json): project=PROJ
        │   └─→ Environment: PROJECT_KEY=MY_PROJECT
        │   Result: {timeout: 60s, rate_limit: 100/min, project: MY_PROJECT}
        │
        ├─→ Guardrails Validation
        │   ├─→ Cost check: Creating issue costs 0 credits ✓
        │   ├─→ Rate limit: 2/100 requests this minute ✓
        │   ├─→ Permission check: user_id in allowed_users ✓
        │   └─→ Confirmation gate: "Create issue in MY_PROJECT?" [User confirms]
        │
        ├─→ API Call
        │   └─→ POST /rest/api/3/issues {fields: {...}}
        │
        └─→ Post-Action
            ├─→ Emit event: "jira.issue.created"
            ├─→ Update state: {issue_count: +1}
            └─→ Log to audit: "user created issue PROJ-123"
```

### 4-Level Configuration Hierarchy

**Priority (highest to lowest):**

```
┌─ Environment Variables (highest priority)
│  PROJECT_KEY=MY_PROJECT
│  JIRA_TIMEOUT=120
│
├─ Repo Config (.devarmor/jira.json)
│  {"project": "MY_PROJECT"}
│
├─ Master Config (~/.devarmor/skills/jira.json)
│  {"timeout": 60, "rate_limit": 100}
│
└─ Code Defaults (lowest priority)
   timeout=30, rate_limit=100
```

**Resolution Algorithm**:

```python
def load_config(skill_name):
    # Start with code defaults
    config = get_code_defaults(skill_name)
    
    # Override with master config
    if file_exists(f"~/.devarmor/skills/{skill_name}.json"):
        master = load_json(f"~/.devarmor/skills/{skill_name}.json")
        config.update(master)
    
    # Override with repo config
    if file_exists(f".devarmor/{skill_name}.json"):
        repo = load_json(f".devarmor/{skill_name}.json")
        config.update(repo)
    
    # Override with environment variables
    for key in config:
        env_key = f"{skill_name.upper()}_{key.upper()}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    
    return config
```

### Guardrails Enforcement

**Three-Gate System:**

```
┌─────────────────┐
│  Rate Limit     │  "You've used 2/100 requests this minute"
│  (automatic)    │  ✓ Allow if under limit
└────────┬────────┘
         │
         ├─ ✗ Fail (rate limited)
         │
         ▼
┌─────────────────┐
│  Cost Check     │  "This costs 10 credits, you have 500"
│  (automatic)    │  ✓ Allow if sufficient credits
└────────┬────────┘
         │
         ├─ ✗ Fail (insufficient credits)
         │
         ▼
┌─────────────────┐
│  Confirmation   │  "Create issue in MY_PROJECT?"
│  Gate (if       │  ✓ Allow if user confirms
│  destructive)   │  ✗ Cancel if user declines
└─────────────────┘
```

## Orchestration Layer

**Purpose**: Cross-skill coordination, state sharing, policy enforcement, and compliance auditing.

### Event Bus (Pub/Sub)

Skills publish events; other skills or policies subscribe.

```
Jira Skill creates issue PROJ-123
        │
        └─→ Emit: jira.issue.created
            {
              "skill": "jira",
              "action": "issue.created",
              "timestamp": "2026-05-17T14:30:00Z",
              "user": "alice@example.com",
              "cost": 0,
              "data": {
                "issue_key": "PROJ-123",
                "project": "MY_PROJECT"
              }
            }
            │
            ├─→ GitHub skill subscribes: "Update linked PR"
            │   └─→ POST /repos/my-org/my-repo/issues/456/comments
            │       "See Jira PROJ-123"
            │
            └─→ Audit log subscribes: "Record action"
                └─→ Write to audit: user=alice, action=jira.issue.created
```

### State Store

Shared, queryable state across all skills.

```
State Table:
┌──────────────────┬─────────────────────────────────────┐
│ Key              │ Value                               │
├──────────────────┼─────────────────────────────────────┤
│ jira.issue.count │ 42                                  │
│ github.pr.count  │ 15                                  │
│ user.alice.cost  │ 250 credits used this month        │
│ policy.last_run  │ 2026-05-17T14:20:00Z               │
└──────────────────┴─────────────────────────────────────┘

Query Examples:
  state.get("jira.issue.count")
  → 42

  state.increment("user.alice.cost", 10)
  → user now at 260 credits

  state.set("policy.last_run", now())
  → timestamp updated
```

### Policy Engine

Evaluates YAML policies and enforces constraints.

```yaml
# Cost Control Policy (example)
name: CostControl
enabled: true
constraints:
  - name: MonthlyBudget
    rule: user.${user_id}.cost <= 500
    action: deny
    message: "Monthly credit limit exceeded"

  - name: ProjectSpend
    rule: project.${project}.cost <= 100
    action: warn
    message: "Project approaching monthly budget"

  - name: RateLimitProtection
    rule: user.${user_id}.requests_per_minute <= 100
    action: deny
    message: "Rate limit exceeded"

# Security Policy
name: Security
enabled: true
constraints:
  - name: NoCredentialLogging
    rule: audit.log.content != /password|token|secret/
    action: deny
    message: "Cannot log sensitive information"

  - name: ApprovedUsers
    rule: user.${user_id} in ["alice@example.com", "bob@example.com"]
    action: deny
    message: "User not approved for this action"
```

### Audit Log

All actions logged for compliance and forensics.

```
Entry Format:
{
  "timestamp": "2026-05-17T14:30:00Z",
  "user": "alice@example.com",
  "skill": "jira",
  "action": "issue.created",
  "resource": "PROJ-123",
  "status": "success",
  "cost": 0,
  "duration_ms": 245,
  "policy_decisions": [
    {"policy": "CostControl", "decision": "allow"},
    {"policy": "Security", "decision": "allow"}
  ],
  "audit_trail": "user=alice, action=jira.issue.created, ..."
}

Query Examples:
  # Find all Jira actions by alice
  audit.query("user=alice AND skill=jira", limit=100)
  
  # Find cost overruns
  audit.query("cost > 100 AND status=success", limit=50)
  
  # Compliance report for May
  audit.query("timestamp >= 2026-05-01 AND timestamp < 2026-06-01")
```

## Control Flow Diagrams

### Install Flow

```
User runs: devarmor install jira-skill@2.0.0
│
├─→ [1] Check Dependencies
│   ├─ Does python>=3.12 exist? (yes)
│   ├─ Do we have network? (yes)
│   └─ Do we have 500MB free? (yes)
│
├─→ [2] Download & Verify
│   ├─ Download from PyPI: jira-skill-2.0.0-py3.whl
│   ├─ Verify SHA256 hash
│   └─ Scan with bandit (security)
│
├─→ [3] Extract & Prepare
│   ├─ Extract to /usr/local/lib/devarmor/skills/jira-skill/
│   └─ Create entry point: devarmor jira <command>
│
├─→ [4] Load Compliance
│   ├─ Import IDevArmorCompliant
│   ├─ Register skill.on_install() hook
│   ├─ Load event subscriptions
│   └─ Initialize state store keys
│
├─→ [5] Configuration
│   ├─ Load ~/.devarmor/skills/jira.json
│   ├─ Load .devarmor/jira.json
│   ├─ Load environment variables
│   └─ Validate against schema
│
├─→ [6] Smoke Test
│   ├─ Test API connectivity
│   ├─ Test authentication
│   └─ Test basic command: jira project list
│
└─→ Success! Jira skill ready for use.
   Installed: /usr/local/lib/devarmor/skills/jira-skill/
   Command: devarmor jira <command>
```

### Action Validation Flow

```
User: "Create a Jira issue"
│
├─→ [1] Parse & Route
│   └─ CLI: jira.create_issue(project=PROJ, ...)
│
├─→ [2] Load Config
│   ├─ Start: {default_timeout: 30}
│   ├─ Merge: {~/.devarmor/skills/jira.json}
│   ├─ Merge: {.devarmor/jira.json}
│   └─ Merge: {env vars}
│   Result: {timeout: 60, project: PROJ, ...}
│
├─→ [3] Pre-Action Guardrails
│   │
│   ├─→ Rate Limit Check
│   │   ├─ Query: state.get("jira.user.alice.req_per_min")
│   │   ├─ Value: 2 requests (limit is 100)
│   │   ├─ Decision: ALLOW
│   │   └─ Action: Increment counter
│   │
│   ├─→ Cost Check
│   │   ├─ Cost: 0 credits (read operation)
│   │   ├─ User balance: 500 credits
│   │   ├─ Decision: ALLOW
│   │   └─ Action: None (no debit)
│   │
│   └─→ Permission Check
│       ├─ Policy: ApprovedUsers
│       ├─ User: alice@example.com
│       ├─ Allowed: [alice, bob]
│       ├─ Decision: ALLOW
│       └─ Action: None
│
├─→ [4] Confirmation Gate (if destructive)
│   ├─ Prompt: "Create issue in PROJ?" 
│   ├─ User confirms: "yes"
│   └─ Decision: PROCEED
│
├─→ [5] Execute Action
│   └─ POST /rest/api/3/issues {...}
│       └─ Response: {issue_key: "PROJ-123"}
│
├─→ [6] Post-Action
│   │
│   ├─→ Emit Events
│   │   └─ Event: jira.issue.created
│   │       {issue_key: PROJ-123, user: alice, cost: 0}
│   │
│   ├─→ Update State
│   │   ├─ Increment: jira.issue.count
│   │   └─ Set: jira.last_issue = PROJ-123
│   │
│   └─→ Log to Audit
│       {timestamp: now, user: alice, action: issue.created, ...}
│
└─→ Success! Issue PROJ-123 created.
   Events: 2 subscribers notified (github, slack)
```

### Inter-Skill Event Flow

```
Jira Skill: Issue created PROJ-123
│
└─→ Emit: jira.issue.created
    {
      "issue_key": "PROJ-123",
      "project": "MY_PROJECT",
      "user": "alice@example.com"
    }
    │
    ├─→ GitHub Skill listens
    │   ├─ Trigger: "jira.issue.created"
    │   ├─ Action: Link issue to PR
    │   │   POST /repos/my-org/my-repo/issues/456/comments
    │   │   "Tracked in Jira PROJ-123"
    │   └─ Emit: github.issue_comment.created
    │
    ├─→ Slack Skill listens
    │   ├─ Trigger: "jira.issue.created"
    │   ├─ Action: Post to #engineering
    │   │   "New issue: PROJ-123"
    │   └─ Emit: slack.message.sent
    │
    └─→ Audit Logger listens
        ├─ Trigger: *
        ├─ Action: Log entry
        │   {timestamp, user, skill, action, resource}
        └─ State: Write audit.log
```

## Security Model

### Threat Analysis

| Threat | Mitigation |
|--------|-----------|
| **Unauthorized API calls** | Policy engine + confirmation gates |
| **Cost overruns** | Credit system + rate limiting |
| **Credential leakage** | No creds in code; env vars only |
| **Skill conflicts** | Namespace isolation + state transactions |
| **Audit tampering** | Immutable append-only log |
| **Privilege escalation** | Per-user permission matrix in policy |
| **Rate limit bypass** | Distributed rate limit in state store |

### Isolation Boundaries

```
┌─────────────────────────────────────────┐
│  Jira Skill Namespace                   │
│  /usr/local/lib/devarmor/skills/jira/  │
│  - Config: ~/.devarmor/skills/jira.json│
│  - State keys: jira.* (isolated)        │
│  - Events: jira.* (scoped)              │
│  - Permissions: jira.* (role-based)     │
└─────────────────────────────────────────┘
   ↕ (via Event Bus + State Store)
┌─────────────────────────────────────────┐
│  GitHub Skill Namespace                 │
│  /usr/local/lib/devarmor/skills/github/ │
│  - Config: ~/.devarmor/skills/github.json
│  - State keys: github.* (isolated)      │
│  - Events: github.* (scoped)            │
│  - Permissions: github.* (role-based)   │
└─────────────────────────────────────────┘
```

## Scalability Considerations

### Performance Targets

| Operation | Target | Implementation |
|-----------|--------|-----------------|
| Config load | <100ms | In-memory cache with 1h TTL |
| Policy eval | <50ms per constraint | Compiled regex + state cache |
| Event pub | <10ms | Async queue with batch flush |
| Audit write | <5ms | Write-ahead log |
| Skill install | <30s | Parallel downloads + validation |

### Horizontal Scaling

```
Distributed DevArmor Cluster:

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Node 1     │ │  Node 2     │ │  Node 3     │
│ (Jira)      │ │ (GitHub)    │ │ (Slack)     │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    ┌───▼────┐  ┌──────▼──────┐  ┌───▼────┐
    │ Event  │  │ State Store │  │ Audit  │
    │ Bus    │  │ (Redis)     │  │ Log    │
    │(nats)  │  │             │  │(S3)    │
    └────────┘  └─────────────┘  └────────┘
```

### State Store Sharding

```
State keys by skill:

jira.*        → shard-0
github.*      → shard-1
slack.*       → shard-2
user.alice.*  → shard-0
user.bob.*    → shard-1

Query: state.get("user.alice.cost")
  → Hash("user.alice.cost") = shard-0
  → Query shard-0 Redis instance
  → Return: 250
```

## References

- **Installation**: See OPERATOR_RUNBOOK.md
- **Policies**: See POLICY_CONFIGURATION.md
- **Integration**: See SKILL_INTEGRATION_GUIDE.md
- **API**: See API_REFERENCE.md
