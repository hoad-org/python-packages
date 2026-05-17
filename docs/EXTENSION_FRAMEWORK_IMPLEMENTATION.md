# DevArmor Extension Framework - Implementation Guide

> **Status**: Ready for Implementation  
> **Version**: 1.0.0  
> **Last Updated**: May 17, 2026

This guide explains the complete DevArmor Extension Framework that transforms skills into first-class DevArmor citizens through manifest-based integration.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Getting Started](#getting-started)
4. [Manifest System](#manifest-system)
5. [Code Generation](#code-generation)
6. [Skill Migration](#skill-migration)
7. [DevArmor Discovery & Loading](#devarmor-discovery--loading)
8. [Policy Framework](#policy-framework)
9. [State Management](#state-management)
10. [Event Routing](#event-routing)
11. [Testing & Validation](#testing--validation)
12. [Deployment](#deployment)
13. [Examples](#examples)

---

## Overview

The DevArmor Extension Framework provides a unified architecture for skills to integrate deeply with the DevArmor control plane through:

- **Manifest-Based Declaration**: Skills declare capabilities, events, state, policies, and security requirements in a single YAML file
- **Code Generation**: Manifests automatically generate boilerplate code, tests, Docker files, CI/CD workflows, and documentation
- **Discovery & Auto-Wiring**: DevArmor automatically discovers skills, validates manifests, resolves dependencies, and wires event routing
- **Unified Policy Enforcement**: Policies declare rules that are automatically enforced at install-time, action-time, and event-time
- **Intelligent State Sharing**: Skills declare state they maintain and share, with automatic permission gates and consistency controls
- **Performance & Observability**: Auto-instrumented metrics, tracing, structured logging across all skills
- **Zero Boilerplate Development**: Developers write only business logic; all infrastructure code is generated from manifest

## Core Concepts

### 1. Skill Manifest

A YAML/JSON contract that declares everything a skill does:

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: github-skill
  version: 2.0.0
  displayName: GitHub Operations
  description: Repository and workflow management

spec:
  # What the skill can do
  capabilities:
    actions:
      - name: create_repo
        description: Create a new repository
        input: { ... }
        output: { ... }
    queries:
      - name: list_repos
        description: List all repositories
        output: { ... }

  # Events the skill emits and listens to
  events:
    publishes:
      - name: repo.created
        description: Fired when repository created
    subscribes:
      - name: jira.issue.created
        handler: on_jira_issue

  # State the skill manages
  state:
    maintains:
      - name: repositories
        schema: { ... }
    shares:
      - name: deployment_status
        permissions: [read]

  # Configuration the skill requires
  configuration:
    schema: { ... }
    secrets: [github_token]

  # Policies that must be satisfied
  policies:
    requires: [cost_control, security]

  # Security requirements
  security:
    isolation:
      processLevel: subprocess
    permissions: [network:outbound, secrets:read]
    authentication:
      - type: apikey
        scopes: [repo, workflow]

  # Dependencies on other skills
  dependencies:
    - name: jira-skill
      version: ">=3.0.0"

  # Health checks
  health:
    readinessProbe:
      handler: check_api
      periodSeconds: 30

  # Metrics and tracing
  observability:
    metrics:
      - name: github_api_calls_total
        type: counter
    tracing:
      enabled: true
      samplingRate: 0.1

  # Testing requirements
  testing:
    minimumCoverage: 85
    testTypes: [unit, integration]

  # Deployment configuration
  deployment:
    replicas: 2
    upgradeStrategy: rolling
```

### 2. Generated Skill Class

The manifest generates a complete skill implementation:

```python
# Generated from manifest
class GitHubSkill(BaseDevArmorSkill):
    NAME = "github-skill"
    VERSION = "2.0.0"
    
    # Capabilities from manifest
    PUBLISHES = ['repo.created', 'repo.deleted', ...]
    SUBSCRIBES = {'jira.issue.created': handle_jira_issue}
    REQUIRED_POLICIES = ['cost_control', 'security']
    
    # State schemas from manifest
    STATE_SCHEMA = {...}
    
    # Configuration from manifest
    CONFIG_SCHEMA = {...}
    CONFIG_DEFAULTS = {...}
    CONFIG_SECRETS = ['github_token']
    
    # Security from manifest
    ISOLATION_LEVEL = 'subprocess'
    REQUIRED_PERMISSIONS = ['network:outbound', 'secrets:read']
    
    # Generated method stubs - developer implements
    async def create_repo(self, org: str, name: str) -> Dict:
        """Developer implements action logic"""
        raise NotImplementedError()
    
    async def list_repos(self, org: str) -> Dict:
        """Developer implements query logic"""
        raise NotImplementedError()
    
    @on_event('jira.issue.created')
    async def handle_jira_issue(self, event: Event) -> None:
        """Developer implements event handling"""
        pass
    
    # Generated helpers
    async def emit_event(self, name: str, payload: dict) -> None:
        """Emit event to other skills"""
        await self.emit(name, payload)
    
    async def get_state(self, key: str) -> Optional[Dict]:
        """Get skill state"""
        return await self.state.get(key)
    
    async def set_state(self, key: str, value: Dict) -> None:
        """Save skill state"""
        await self.state.set(key, value)
```

### 3. IDevArmorExtension Interface

All skills implement this protocol:

```python
class IDevArmorExtension(Protocol):
    """Universal skill interface"""
    
    # Lifecycle
    async def initialize(self) -> None:
        """Called once at startup"""
    
    async def shutdown(self) -> None:
        """Called during graceful shutdown"""
    
    # Action execution
    async def execute_action(
        self, action: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a named action"""
    
    # Query execution
    async def query(
        self, query: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a named query"""
    
    # Event handling
    async def on_event(self, event: Event) -> None:
        """Process an event"""
    
    # Policy validation
    async def validate_policy(
        self, policy: str, context: Dict
    ) -> PolicyDecision:
        """Validate action against policy"""
    
    # Health checks
    async def health_startup(self) -> bool:
        """Startup readiness"""
    
    async def health_readiness(self) -> bool:
        """Is skill ready for traffic"""
    
    async def health_liveness(self) -> bool:
        """Is skill still alive"""
    
    # Configuration
    async def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
    
    async def set_config(self, config: Dict[str, Any]) -> None:
        """Update configuration"""
    
    # Telemetry
    async def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
    
    async def get_traces(self) -> List[Trace]:
        """Get traces for debugging"""
```

---

## Getting Started

### 1. Create a Manifest

Create `manifest.yaml` in your skill directory:

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: my-skill
  version: 1.0.0
  displayName: My Skill
  description: What my skill does

spec:
  capabilities:
    actions:
      - name: do_something
        description: Perform an action
        input:
          type: object
          properties:
            param:
              type: string
          required: [param]
  
  security:
    isolation:
      processLevel: subprocess
```

### 2. Validate Manifest

```bash
devarmor manifest validate manifest.yaml
```

### 3. Generate Code

```bash
devarmor manifest generate manifest.yaml -o ./generated
```

This generates:
- `src/my_skill/__init__.py` - Skill implementation class
- `tests/test_my_skill.py` - Test file with stubs
- `Dockerfile` - Container definition
- `.github/workflows/ci.yaml` - CI/CD pipeline
- `README.md` - Documentation
- `docs/CONFIGURATION.md` - Config docs
- `docs/SECURITY.md` - Security docs

### 4. Implement Business Logic

Edit the generated skill class and implement action/query methods:

```python
class MySkill(BaseDevArmorSkill):
    async def do_something(self, param: str) -> Dict:
        # Implement your logic
        return {"result": f"Processed: {param}"}
```

### 5. Write Tests

Edit generated test file to test your implementations:

```python
@pytest.mark.asyncio
async def test_do_something(self, skill):
    result = await skill.do_something("test")
    assert result["result"] == "Processed: test"
```

### 6. Deploy

```bash
# Run tests
pytest tests/ --cov

# Build Docker image
docker build -t my-skill:1.0.0 .

# Deploy to DevArmor
devarmor skill install ./
```

---

## Manifest System

### Manifest Schema

The complete manifest schema is defined in `schema/skill-manifest-schema.json`.

Key sections:

#### `metadata`
- `name` (required): Unique skill identifier (kebab-case)
- `version` (required): Semantic version (e.g., 1.0.0)
- `displayName`: Human-readable name
- `description`: What the skill does
- `license`: SPDX license identifier
- `categories`: For discovery (cloud, security, automation, etc.)

#### `spec.capabilities`
- `actions`: Mutable operations the skill performs
  - `name`: Action identifier
  - `description`: What it does
  - `input`: JSON Schema for parameters
  - `output`: JSON Schema for results
  - `idempotent`: Safe to retry
  - `timeout`: Max execution seconds
  - `rateLimit`: Request limits
- `queries`: Read-only data access
  - Similar structure to actions
  - Support caching with TTL

#### `spec.events`
- `publishes`: Events this skill emits
  - `name`: Event name (e.g., repo.created)
  - `description`: When it fires
  - `severity`: info, warning, error, critical
  - `schema`: Event payload schema
- `subscribes`: Events this skill listens to
  - `name`: Event pattern (supports wildcards)
  - `handler`: Method name to call
  - `filter`: Optional CEL expression
  - `retryPolicy`: Automatic retries

#### `spec.state`
- `maintains`: State this skill owns
  - `name`: State identifier
  - `schema`: JSON Schema
  - `ttlSeconds`: Auto-expiry
  - `indexed`: Fields to index
- `shares`: State shared with other skills
  - Same structure
  - `permissions`: read, write, delete
  - `consistencyLevel`: strong, eventual

#### `spec.security`
- `isolation`: Process/network isolation
  - `processLevel`: inline, subprocess, container
  - `resourceLimits`: CPU, memory, files
  - `networkRules`: Allowed destinations
- `permissions`: Required permissions
- `authentication`: Auth methods (apikey, oauth2, jwt, etc.)

### Validation

Manifests are validated at multiple levels:

```bash
# Schema validation
devarmor manifest validate manifest.yaml

# Detailed validation with warnings
devarmor manifest validate manifest.yaml --verbose

# Inspect manifest
devarmor manifest inspect manifest.yaml
```

---

## Code Generation

The code generation pipeline converts manifests to complete projects:

### Generated Files

```
skill-project/
├── src/
│   └── my_skill/
│       ├── __init__.py          # Main skill class
│       ├── config.py            # Configuration loading
│       └── types.py             # Type definitions
├── tests/
│   ├── test_skill.py            # Test stubs (>85% coverage)
│   └── conftest.py              # Test fixtures
├── docs/
│   ├── CONFIGURATION.md         # Config schema docs
│   ├── SECURITY.md              # Security requirements
│   └── ARCHITECTURE.md          # Design docs
├── Dockerfile                   # Container image
├── .github/workflows/
│   └── ci.yaml                  # Test/build/deploy
├── manifest.yaml                # Skill declaration
├── pyproject.toml               # Python project config
├── README.md                    # User documentation
└── .devarmor.yaml              # DevArmor-specific config
```

### Code Generation Commands

```bash
# Generate all files
devarmor manifest generate manifest.yaml

# Generate to specific directory
devarmor manifest generate manifest.yaml -o ./build

# Force overwrite existing files
devarmor manifest generate manifest.yaml --force

# Generate specific file types
devarmor manifest generate manifest.yaml --types python,docker,docs
```

---

## Skill Migration

### Migrate Existing Skill to Manifest-First

```bash
# Interactive migration wizard
devarmor manifest migrate ./my-existing-skill

# Custom output path
devarmor manifest migrate ./my-skill -o ./my-skill/manifest.yaml
```

The wizard guides you through:
1. Basic metadata (name, version, description)
2. Capability detection (actions, queries)
3. Event configuration (publishes, subscribes)
4. State management (maintained, shared)
5. Security requirements
6. Configuration schema

After migration:
1. Review generated `manifest.yaml`
2. Add missing capabilities
3. Validate: `devarmor manifest validate manifest.yaml`
4. Generate code: `devarmor manifest generate manifest.yaml`
5. Migrate implementation to generated skill class

---

## DevArmor Discovery & Loading

### Skill Discovery Process

When DevArmor starts, it:

```
1. Scan configured skill paths for manifest.yaml/manifest.json
   ↓
2. Load and validate each manifest against schema
   ↓
3. Check manifest compatibility (DevArmor version, Python version)
   ↓
4. Resolve dependency graph (topological sort)
   ↓
5. Check all dependencies are available
   ↓
6. Load skills in dependency order
   ↓
7. Wire event routing (publish → subscribe matching)
   ↓
8. Validate policies are satisfied
   ↓
9. Start health checks
   ↓
10. Ready for requests
```

### Discovery Configuration

```yaml
# devarmor-config.yaml
skillPaths:
  - /opt/devarmor/skills
  - ~/my-skills
  - ./packages/*/

skillRegistry:
  url: https://registry.devarmor.io
  auth: token

autoDiscovery: true
autoUpgrade: false  # Manual upgrades only
```

### Dependency Resolution

Manifests declare dependencies:

```yaml
dependencies:
  - name: jira-skill
    version: ">=3.0.0"      # Semver constraint
    optional: false         # Must be available
    requires:
      - create_issue        # Needs this capability
      - link_issue

  - name: slack-skill
    version: ">=2.0.0"
    optional: true          # Graceful degradation if missing
```

DevArmor:
1. Builds dependency graph
2. Detects cycles
3. Performs topological sort
4. Loads in dependency order
5. Validates all required capabilities exist

---

## Policy Framework

### Policy Declaration

Manifests declare required policies:

```yaml
policies:
  requires:
    - cost_control        # Enforce budget limits
    - security            # Enforce access controls
    - compliance          # Enforce regulatory rules
  
  enforces:
    - name: rate_limit
      type: custom
      rules:
        - action: RATE_LIMIT
          limit: "100 requests/minute"
  
  validates:
    - target: delete_repository
      rule: "request.org in ['trusted-orgs']"
      action: DENY

    - target: deploy_version
      rule: "request.version matches '^v\\d+\\.\\d+\\.\\d+$'"
      action: WARN
```

### Policy Enforcement Points

**1. Install Time**
```python
# Policies checked during skill installation
if not policies.validate_skill(skill_manifest):
    raise PolicyViolation("Skill requires unapproved policies")
```

**2. Action Time**
```python
# Before action executes
policy_result = await policies.validate_action(
    skill=skill_name,
    action=action_name,
    params=request_params
)

if policy_result == PolicyDecision.DENY:
    raise ActionDenied("Policy violation")
```

**3. Event Time**
```python
# Before event is delivered
if not policies.validate_event(event):
    logger.warning(f"Event {event.name} denied by policy")
    return  # Event dropped
```

### Policy Actions

- `ALLOW` - Allow the action
- `DENY` - Reject the action
- `WARN` - Log a warning but allow
- `RATE_LIMIT` - Apply rate limiting
- `AUDIT` - Log for compliance

---

## State Management

### State Declaration

```yaml
state:
  maintains:
    # State this skill owns and manages
    - name: repositories
      schema:
        type: object
        properties:
          org:
            type: string
          repo:
            type: string
      ttlSeconds: 86400       # Auto-expiry
      indexed: [org, repo]    # Index for queries

  shares:
    # State available to other skills
    - name: deployment_status
      schema:
        type: object
        properties:
          current_version:
            type: string
          status:
            type: string
      permissions: [read]     # read, write, delete
      consistencyLevel: strong # strong, eventual
```

### State Operations

```python
class GitHubSkill(BaseDevArmorSkill):
    # Get state
    repos = await self.get_state("repositories")
    
    # Set state
    await self.set_state("repositories", {
        "org": "hoad-org",
        "repo": "python-packages"
    })
    
    # Query state (if shared)
    status = await self.query_shared_state(
        skill="jira-skill",
        state="deployment_status"
    )
    
    # List state
    all_repos = await self.list_state("repositories")
    
    # Delete state
    await self.delete_state("repositories", key)
```

### State Consistency

- `strong`: Synchronous writes, guaranteed consistency (slower)
- `eventual`: Asynchronous replication, eventual consistency (faster)

---

## Event Routing

### Event Declaration

```yaml
events:
  publishes:
    # Events this skill emits
    - name: github.repo.created
      description: Fired when repository created
      severity: info
      schema:
        type: object
        properties:
          org:
            type: string
          repo:
            type: string

  subscribes:
    # Events this skill listens to
    - name: jira.issue.created
      handler: on_jira_issue_created
      filter: "issue.type == 'Task'"
      retryPolicy:
        maxRetries: 3
        backoffMultiplier: 2.0
        initialDelayMs: 1000
```

### Event Handling

```python
class GitHubSkill(BaseDevArmorSkill):
    @on_event('jira.issue.created')
    async def on_jira_issue_created(self, event: Event) -> None:
        """Handle incoming event"""
        issue = event.payload
        
        # Create repository for issue
        repo = await self.create_repo(
            org=issue['project'],
            name=issue['key']
        )
        
        # Emit event to other skills
        await self.emit('github.repo.created', {
            'org': issue['project'],
            'repo': repo['name']
        })
    
    # Emit from action
    async def create_repo(self, org: str, name: str) -> Dict:
        result = await self._create_repo(org, name)
        
        # Notify other skills
        await self.emit('github.repo.created', {
            'org': org,
            'repo': name
        })
        
        return result
```

### Auto-Wiring

DevArmor automatically:
1. Detects all publish/subscribe declarations
2. Creates event topic for each published event
3. Connects subscribers to their topics
4. Validates no circular dependencies
5. Sets up async event delivery
6. Applies retry policies
7. Logs event flows

---

## Testing & Validation

### Generated Tests

All skills have >85% coverage from generated tests:

```python
class TestGitHubSkill(unittest.TestCase):
    @pytest.fixture
    async def skill(self):
        skill = GitHubSkill()
        await skill.initialize()
        yield skill
        await skill.shutdown()

    # Tests for actions
    @pytest.mark.asyncio
    async def test_create_repository(self, skill):
        # Test implementation

    # Tests for queries
    @pytest.mark.asyncio
    async def test_list_repositories(self, skill):
        # Test implementation

    # Tests for events
    @pytest.mark.asyncio
    async def test_on_jira_issue(self, skill):
        # Test implementation

    # Tests for state
    @pytest.mark.asyncio
    async def test_state_management(self, skill):
        # Test implementation

    # Tests for configuration
    @pytest.mark.asyncio
    async def test_config_loading(self, skill):
        # Test implementation

    # Tests for security
    @pytest.mark.asyncio
    async def test_security_isolation(self, skill):
        # Test implementation
```

### Test Execution

```bash
# Run all tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=html

# Check minimum coverage
pytest tests/ --cov=src --cov-fail-under=85

# Run specific test
pytest tests/test_github_skill.py::TestGitHubSkill::test_create_repository
```

### Manifest Compliance Testing

```bash
# Validate manifest against schema
devarmor manifest validate manifest.yaml

# Check semantic rules
devarmor manifest validate manifest.yaml --verbose

# Inspect manifest structure
devarmor manifest inspect manifest.yaml
```

---

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t github-skill:2.0.0 .

# Run locally
docker run -e GITHUB_TOKEN=xxx github-skill:2.0.0

# Push to registry
docker tag github-skill:2.0.0 gcr.io/myproject/github-skill:2.0.0
docker push gcr.io/myproject/github-skill:2.0.0
```

### Kubernetes Deployment

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: github-skill
  namespace: devarmor
spec:
  deployment:
    replicas: 2
    upgradeStrategy: rolling
    updatePolicy: manual
    scheduling:
      nodeSelector:
        workload: integration
      tolerations:
        - key: workload
          operator: Equal
          value: integration
  healthChecks:
    readiness:
      failureThreshold: 3
      periodSeconds: 10
    liveness:
      failureThreshold: 3
      periodSeconds: 60
```

### Upgrade Strategy

```yaml
deployment:
  upgradeStrategy: rolling    # new replicas start before old stop
  updatePolicy: manual        # require explicit approval

# Execution:
# 1. Start new version in parallel
# 2. Route 10% traffic to new version
# 3. Monitor metrics for errors
# 4. Gradually increase traffic
# 5. Stop old version
# 6. Automatic rollback if errors exceed threshold
```

---

## Examples

### Example 1: Simple Echo Skill

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: echo-skill
  version: 1.0.0
  displayName: Echo Skill
  description: Simple echo for testing

spec:
  capabilities:
    actions:
      - name: echo
        description: Echo back the input
        input:
          type: object
          properties:
            message:
              type: string
          required: [message]
        output:
          type: object
          properties:
            echo:
              type: string

  security:
    isolation:
      processLevel: inline
```

```python
class EchoSkill(BaseDevArmorSkill):
    async def echo(self, message: str) -> Dict:
        return {"echo": message}
```

### Example 2: Skill with Events

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: logger-skill
  version: 1.0.0

spec:
  events:
    subscribes:
      - name: "*.created"
        handler: on_created
      - name: "*.deleted"
        handler: on_deleted

  security:
    isolation:
      processLevel: subprocess
```

```python
class LoggerSkill(BaseDevArmorSkill):
    async def on_created(self, event: Event) -> None:
        logger.info(f"{event.name} created: {event.payload}")
    
    async def on_deleted(self, event: Event) -> None:
        logger.info(f"{event.name} deleted: {event.payload}")
```

### Example 3: Skill with State & Sharing

```yaml
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: cache-skill
  version: 1.0.0

spec:
  state:
    maintains:
      - name: cache
        schema:
          type: object
        ttlSeconds: 3600
        indexed: [key]
    
    shares:
      - name: cache
        permissions: [read, write]

  capabilities:
    actions:
      - name: set
        description: Set cache value
      - name: get
        description: Get cache value
```

```python
class CacheSkill(BaseDevArmorSkill):
    async def set(self, key: str, value: Any) -> Dict:
        await self.set_state("cache", {"key": key, "value": value})
        return {"status": "set"}
    
    async def get(self, key: str) -> Dict:
        item = await self.get_state("cache")
        return {"value": item.get("value")}
```

---

## Workflow: New Skill Creation

### Step 1: Create Manifest
```bash
mkdir my-skill && cd my-skill
cat > manifest.yaml << 'EOF'
apiVersion: devarmor.io/v1
kind: Skill
metadata:
  name: my-skill
  version: 1.0.0
  displayName: My Skill
  description: Does something useful

spec:
  capabilities:
    actions:
      - name: do_work
        description: Do some work
        input:
          type: object
          properties:
            input:
              type: string
  
  security:
    isolation:
      processLevel: subprocess
EOF
```

### Step 2: Validate
```bash
devarmor manifest validate manifest.yaml
```

### Step 3: Generate Code
```bash
devarmor manifest generate manifest.yaml
```

### Step 4: Implement
```bash
# Edit src/my_skill/__init__.py
# Implement the do_work method
# Add your business logic
```

### Step 5: Test
```bash
# Edit tests/test_my_skill.py
# Add tests for your implementations
pytest tests/ --cov
```

### Step 6: Deploy
```bash
# Build Docker image
docker build -t my-skill:1.0.0 .

# Deploy to DevArmor
devarmor skill install ./
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      DevArmor Control Plane                  │
│                                                               │
│  ┌──────────────────┐                                        │
│  │  Skill Registry  │  ← Manifest discovery & indexing      │
│  └──────────────────┘                                        │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  Policy Engine                           │               │
│  │  - Install-time validation               │               │
│  │  - Action-time enforcement               │               │
│  │  - Event-time filtering                  │               │
│  └──────────────────────────────────────────┘               │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  Event Router                            │               │
│  │  - Publish/subscribe wiring              │               │
│  │  - Async delivery                        │               │
│  │  - Retry policies                        │               │
│  └──────────────────────────────────────────┘               │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  State Manager                           │               │
│  │  - Maintains skill state                 │               │
│  │  - Cross-skill queries                   │               │
│  │  - TTL and consistency                   │               │
│  └──────────────────────────────────────────┘               │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  Observability Pipeline                  │               │
│  │  - Metrics collection                    │               │
│  │  - Distributed tracing                   │               │
│  │  - Structured logging                    │               │
│  └──────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
           ↑              ↑              ↑              ↑
           │              │              │              │
      ┌────────┐  ┌────────────┐  ┌────────┐  ┌──────────────┐
      │ Skill 1│  │  Skill 2   │  │ Skill 3│  │   Skill N    │
      │        │  │            │  │        │  │              │
      │ Manifest   Manifest │ Manifest │  Manifest
      │ Generated  Generated │ Generated │  Generated
      │ Classes    Classes   │ Classes   │  Classes
      │        │  │            │  │        │  │              │
      └────────┘  └────────────┘  └────────┘  └──────────────┘
```

---

## Next Steps

1. **Implement Manifest Validator** ✓
2. **Implement Code Generator** ✓
3. **Create CLI Tools** ✓
4. **Migrate Existing Skills** → Run migration on 9 existing skills
5. **Build Skill Registry** → Implement registry API in devarmor-core
6. **Deploy Framework** → Release as part of devarmor v1.5.0

---

## Support & Contribution

For questions or contributions to the framework:

1. Check the [examples](./examples/) directory
2. Review existing skill manifests in `schema/examples/`
3. Submit issues to the [DevArmor repository](https://github.com/hoad-org/devarmor)
4. Join the community on [Slack](https://devarmor.io/community)

---

**Document Version**: 1.0.0  
**Last Updated**: May 17, 2026  
**Status**: Ready for Implementation
