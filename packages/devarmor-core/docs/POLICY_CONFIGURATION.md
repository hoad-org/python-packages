# Policy Configuration Guide

## YAML Schema Reference

### Top-Level Structure

```yaml
name: PolicyName              # Required: unique policy identifier
version: "1.0.0"             # Optional: semantic version
description: |               # Optional: human-readable description
  This policy controls...
enabled: true                # Optional: default true
priority: 100                # Optional: higher = evaluated first (default 100)
environment: production      # Optional: only apply in this environment

constraints:                 # Required: list of constraint rules
  - name: RuleName
    rule: "expression"
    action: deny|allow|warn
    message: "User-facing message"

# Optional: variable definitions
variables:
  monthly_budget: 500
  rate_limit: 100

# Optional: templates for reuse
templates:
  cost_check: "cost <= ${monthly_budget}"
```

### Constraint Structure

```yaml
constraints:
  - name: UniqueName           # Required: identifier for this constraint
    
    rule: |                    # Required: boolean expression
      user.${user_id}.cost <= 500
    
    action: deny               # Required: deny|allow|warn|rate_limit|custom
    
    message: "Message"         # Required: shown to user if denied
    
    enabled: true              # Optional: default true
    
    tags:                       # Optional: for filtering/grouping
      - cost-control
      - compliance
    
    skip_confirmation: false    # Optional: if true, don't ask user
    
    rate_limit:                 # Optional: if action: rate_limit
      requests_per_minute: 100
      burst_size: 10
    
    notify:                      # Optional: notify on violation
      - email: admin@example.com
      - slack: #security
```

---

## Pre-Built Policy Templates

### 1. Cost Control Policy

Controls spending and resource usage.

**File**: `.devarmor/policies/cost-control.yaml`

```yaml
name: CostControl
version: "1.0.0"
description: Enforce budget limits and prevent cost overruns
enabled: true
priority: 100

constraints:
  # Monthly budget enforcement
  - name: MonthlyBudgetLimit
    rule: |
      user.${user_id}.cost_this_month <= 500
    action: deny
    message: "Monthly credit limit exceeded (limit: 500 credits)"
    tags: [cost-control, billing]
  
  # Project-level budget
  - name: ProjectBudgetLimit
    rule: |
      project.${project_id}.cost_this_month <= 100
    action: warn
    message: |
      Project approaching budget limit
      (used: ${project.${project_id}.cost_this_month}/100 credits)
    tags: [cost-control, billing]
  
  # Rate limiting for expensive operations
  - name: ExpensiveOperationLimit
    rule: |
      action == "create_resource" AND cost > 50
      AND user.${user_id}.requests_per_minute >= 5
    action: rate_limit
    message: "Rate limited: expensive operations (max 5/min)"
    rate_limit:
      requests_per_minute: 5
      burst_size: 2
    tags: [cost-control, rate-limit]
  
  # Warn on high-cost single operations
  - name: HighCostWarning
    rule: |
      cost > 50
    action: warn
    message: "Warning: This operation costs ${cost} credits"
    skip_confirmation: false
    tags: [cost-control, billing]

variables:
  monthly_budget: 500
  project_budget: 100
  high_cost_threshold: 50
```

### 2. Security Policy

Control access and prevent unauthorized operations.

**File**: `.devarmor/policies/security.yaml`

```yaml
name: Security
version: "1.0.0"
description: Prevent unauthorized access and protect credentials
enabled: true
priority: 200  # Higher priority than cost control

constraints:
  # Whitelist approved users
  - name: ApprovedUsersOnly
    rule: |
      user.${user_id} in [
        "alice@example.com",
        "bob@example.com",
        "devops@example.com"
      ]
    action: deny
    message: "User not approved for this action"
    tags: [security, access-control]
  
  # Prevent credential logging
  - name: NoCredentialLogging
    rule: |
      audit.log.content !~ /password|token|secret|api_key/i
    action: deny
    message: "Cannot log sensitive information"
    tags: [security, compliance]
  
  # Require approval for destructive operations
  - name: DestructiveOpsRequireApproval
    rule: |
      action in ["delete_resource", "destroy_instance"]
      AND requires_approval == true
    action: deny
    message: "Destructive operations require approval"
    skip_confirmation: false
    tags: [security, critical]
  
  # Prevent access to sensitive projects
  - name: SensitiveProjectAccess
    rule: |
      project.${project_id} in ["payments", "security", "hr"]
      AND has_required_role("admin")
    action: deny
    message: "Project restricted to administrators"
    tags: [security, access-control]
  
  # IP whitelist (if available)
  - name: IpWhitelist
    rule: |
      client.ip in [
        "10.0.0.0/8",
        "203.0.113.0/24"
      ]
    action: deny
    message: "Access from unauthorized IP address"
    tags: [security, network]

variables:
  approved_users:
    - alice@example.com
    - bob@example.com
    - devops@example.com
  sensitive_projects:
    - payments
    - security
    - hr
```

### 3. Compliance Policy

Ensure audit logging and compliance requirements.

**File**: `.devarmor/policies/compliance.yaml`

```yaml
name: Compliance
version: "1.0.0"
description: Ensure audit logging and compliance with regulations
enabled: true
priority: 150

constraints:
  # All actions must be audited
  - name: AuditLogging
    rule: |
      audit.enabled == true
    action: deny
    message: "Action must be audited"
    tags: [compliance, audit]
  
  # Audit log retention
  - name: AuditRetention
    rule: |
      audit.retention_days >= 365
    action: deny
    message: "Audit logs must be retained for 1+ year"
    tags: [compliance, audit]
  
  # Require comment on manual operations
  - name: ManualOperationComments
    rule: |
      is_automated == false
      IMPLIES comment != null AND comment.length > 10
    action: warn
    message: "Please provide a comment explaining this manual operation"
    skip_confirmation: false
    tags: [compliance, documentation]
  
  # Data residency (example: EU only)
  - name: DataResidency
    rule: |
      resource.region in ["eu-west-1", "eu-central-1", "eu-north-1"]
    action: deny
    message: "Resources must be in EU regions (GDPR compliance)"
    tags: [compliance, data-residency]
  
  # Encryption required
  - name: EncryptionRequired
    rule: |
      resource.encrypted == true
    action: deny
    message: "All resources must be encrypted"
    tags: [compliance, encryption]

variables:
  min_retention_days: 365
  required_regions: [eu-west-1, eu-central-1, eu-north-1]
```

### 4. Rate Limiting Policy

Prevent abuse and resource exhaustion.

**File**: `.devarmor/policies/rate-limiting.yaml`

```yaml
name: RateLimiting
version: "1.0.0"
description: Prevent abuse and API rate limit violations
enabled: true
priority: 50  # Lower priority than cost/security

constraints:
  # Per-user request rate limit
  - name: PerUserRateLimit
    rule: |
      user.${user_id}.requests_per_minute <= 100
    action: rate_limit
    message: "Rate limit: 100 requests per minute"
    rate_limit:
      requests_per_minute: 100
      burst_size: 10
    tags: [rate-limit, abuse-prevention]
  
  # Per-skill rate limit
  - name: PerSkillRateLimit
    rule: |
      skill.${skill_name}.requests_per_minute <= 500
    action: rate_limit
    message: "Skill rate limit: 500 requests per minute"
    rate_limit:
      requests_per_minute: 500
      burst_size: 50
    tags: [rate-limit, abuse-prevention]
  
  # Concurrent operation limit
  - name: ConcurrentOperationLimit
    rule: |
      user.${user_id}.concurrent_operations <= 5
    action: deny
    message: "Maximum 5 concurrent operations allowed"
    tags: [rate-limit, concurrency]
  
  # Expensive operation throttling
  - name: ExpensiveOpThrottle
    rule: |
      action == "search" AND query.complexity > 5
      IMPLIES requests_per_minute <= 10
    action: rate_limit
    message: "Complex searches limited to 10 per minute"
    rate_limit:
      requests_per_minute: 10
      burst_size: 2
    tags: [rate-limit, performance]

variables:
  per_user_limit: 100
  per_skill_limit: 500
  max_concurrent: 5
```

---

## Writing Custom Policies

### Expression Language

DevArmor policies use a simple expression language supporting:

**Operators:**
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `AND`, `OR`, `NOT`, `IMPLIES`
- Pattern: `=~` (regex match), `!~` (regex not match)
- Membership: `in`, `not in`
- Null: `is null`, `is not null`

**Variables:**
- User: `user.${user_id}`, `user.${user_id}.cost`, `user.${user_id}.role`
- Project: `project.${project_id}`, `project.${project_id}.budget`
- Skill: `skill.${skill_name}`
- Action: `action`, `cost`, `resource`
- Context: `timestamp`, `client.ip`, `is_automated`

**Functions:**
- String: `length(str)`, `contains(str, substring)`
- Array: `contains(arr, item)`, `length(arr)`
- Role: `has_required_role("admin")`
- Date: `days_since(date)`, `hours_since(date)`

**Examples:**

```yaml
# Simple comparison
rule: "cost <= 50"

# Logical operators
rule: |
  user.${user_id}.cost <= 500
  AND project.${project_id}.budget > 0

# Pattern matching
rule: |
  audit.log.content !~ /password|token|secret/i

# Nested conditions
rule: |
  action == "delete_resource"
  IMPLIES has_required_role("admin") AND confirmation == true

# Array membership
rule: |
  user.${user_id} in ["alice@example.com", "bob@example.com"]

# Time-based
rule: |
  days_since(user.${user_id}.last_trained) >= 365
  IMPLIES requires_training == true
```

### Custom Policy Example: Terrorgem Phase 0

```yaml
name: TerrorgemPhase0
version: "0.1.0"
description: |
  Cost control for Terrorgem Phase 0 (MVP).
  Enforce £3-6/month budget during initial deployment.
enabled: true
priority: 100

constraints:
  # Phase 0 monthly budget
  - name: Phase0MonthlyBudget
    rule: |
      environment == "production"
      IMPLIES cost_tracker.month.total <= 360  # 6 GBP in pence
    action: warn
    message: |
      Terrorgem Phase 0 monthly budget approaching limit
      (used: £${cost_tracker.month.total / 100}, limit: £6)
    tags: [terrorgem-phase-0, budget]
  
  # Restrict to free-tier resources
  - name: FreeTierResourcesOnly
    rule: |
      resource.tier in ["free", "shared", "included"]
      OR cost_per_month == 0
    action: deny
    message: "Phase 0: Only free-tier resources allowed"
    tags: [terrorgem-phase-0, cost-control]
  
  # Prevent expensive operations during Phase 0
  - name: NoExpensiveOps
    rule: |
      action not in [
        "deploy_to_production",
        "create_multi_region",
        "enable_advanced_monitoring"
      ]
    action: allow
    message: "This operation not available in Phase 0"
    tags: [terrorgem-phase-0, feature-gate]
  
  # Single-region deployment only
  - name: SingleRegionPhase0
    rule: |
      deployment.regions.length == 1
    action: deny
    message: "Phase 0: Single region deployments only"
    tags: [terrorgem-phase-0, deployment]

variables:
  phase_0_budget_gbp: 6
  free_tier_resources: ["lambda", "dynamodb-free", "api-gateway"]
```

---

## Policy Inheritance and Override Rules

### Basic Inheritance

```
Global Policy (.devarmor/policies/base.yaml)
         ↓
Org Policy (.devarmor/policies/org.yaml)
         ↓
Project Policy (.devarmor/policies/project.yaml)
         ↓
Final Effective Policy
```

**Loading order:**
```yaml
# 1. Load all policy files from .devarmor/policies/
# 2. Sort by priority (higher first)
# 3. Merge constraints (later overrides earlier)
# 4. Apply to action
```

### Override Examples

**Base policy (cost-control.yaml):**
```yaml
constraints:
  - name: MonthlyBudget
    rule: "cost <= 500"
    action: deny
```

**Project override (.devarmor/policies/project-cost-control.yaml):**
```yaml
constraints:
  - name: MonthlyBudget
    rule: "cost <= 1000"  # Override: higher budget
    action: deny
```

**Result:** Project uses 1000 budget, not 500.

### Composition Example

You can build complex policies from simpler ones:

```yaml
# .devarmor/policies/terrorgem.yaml
name: TerrorgemAll
enabled: true

# Extend other policies
extends:
  - cost-control
  - security
  - compliance

# Add or override constraints
constraints:
  - name: TerrorgemSpecific
    rule: "project.name contains 'terrorgem'"
    action: allow
```

---

## Testing Policies Before Deployment

### Test a Policy Locally

```bash
# Validate policy syntax
devarmor policy validate .devarmor/policies/cost-control.yaml

# Test policy against sample data
devarmor policy test cost-control \
  --user=alice@example.com \
  --action=create_resource \
  --cost=50
# Output: ALLOW (rule MonthlyBudget passed)

# Test with multiple constraints
devarmor policy test cost-control \
  --user=alice@example.com \
  --action=create_resource \
  --cost=50 \
  --monthly_spend=450
# Output: WARN (rule ProjectBudgetLimit triggered)
```

### Dry-Run Deployment

```bash
# Deploy policy but don't enforce it
devarmor policy deploy cost-control --dry-run

# See what would happen
devarmor policy simulate cost-control \
  --user=alice@example.com \
  --action=create_resource \
  --cost=100 \
  --monthly_spend=450
# Output:
# MonthlyBudgetLimit: ALLOW
# ProjectBudgetLimit: WARN (90/100 used)
# HighCostWarning: WARN (cost is 100 > 50)
```

### Create Test Cases

**File: `.devarmor/policies/tests/cost-control.test.yaml`**

```yaml
tests:
  - name: "User under budget"
    input:
      user: alice@example.com
      cost: 50
      monthly_spend: 250
      budget: 500
    expected_outcome: ALLOW
  
  - name: "User over budget"
    input:
      user: alice@example.com
      cost: 50
      monthly_spend: 475
      budget: 500
    expected_outcome: DENY
    expected_message: "Monthly credit limit exceeded"
  
  - name: "High-cost warning"
    input:
      user: alice@example.com
      cost: 75
      monthly_spend: 100
      budget: 500
    expected_outcome: WARN
    expected_message: "This operation costs 75 credits"
```

**Run tests:**
```bash
devarmor policy test-suite cost-control
# cost-control: 3/3 tests passed ✓
```

---

## Real-World Policy Examples from Terrorgem

### Phase 0 Deployment Policy

```yaml
name: TerrorgemPhase0Deployment
version: "1.0.0"
description: |
  Enforce deployment constraints for Terrorgem Phase 0.
  Restrict to free-tier resources, single region, no premium features.
enabled: true

constraints:
  # Budget enforcement
  - name: MonthlyBudget
    rule: "cost <= 600"  # £6/month in pence
    action: deny
    message: "Phase 0 budget exceeded (£6/month limit)"
  
  # Free tier enforcement
  - name: FreeTierCompute
    rule: |
      compute.instance_type in [
        "lambda", "free-tier-ec2-t2-micro", "cloud-run-free"
      ]
    action: deny
    message: "Phase 0: Only free-tier compute allowed"
  
  # Single region
  - name: SingleRegion
    rule: "deployment.regions.length == 1"
    action: deny
    message: "Phase 0: Single region only"
  
  # No multi-AZ
  - name: SingleAz
    rule: "deployment.multi_az == false"
    action: deny
    message: "Phase 0: Multi-AZ not allowed"
```

### Creator MVP Phase 2 Policy

```yaml
name: TerrorgemPhase2CreatorMvp
version: "1.0.0"
description: |
  Phase 2 policies for Creator MVP:
  - Up to 10 creators (cost: £10-15/month)
  - Basic analytics
  - Email notifications
  - No premium features yet
enabled: true

constraints:
  # Budget for 10 creators
  - name: MonthlyBudget
    rule: "cost <= 1500"  # £15/month
    action: deny
    message: "Phase 2 budget exceeded (£15/month limit)"
  
  # Creator limit
  - name: CreatorLimit
    rule: "creator_count <= 10"
    action: deny
    message: "Phase 2: Maximum 10 creators"
  
  # Disable premium features
  - name: NoPremiumFeatures
    rule: |
      feature in [
        "advanced_analytics",
        "custom_branding",
        "api_access",
        "white_label",
        "custom_domain"
      ]
      IMPLIES action == "deny"
    action: deny
    message: "Feature not available in Phase 2"
  
  # Allow basic email notifications
  - name: EmailNotifications
    rule: |
      feature == "email_notifications"
      IMPLIES email_per_day <= 1000
    action: allow
    message: "Email notifications allowed (1000/day limit)"
```

---

## Compliance & Audit Integration

### Audit Log Queries

All policy decisions are logged. Query them:

```bash
# Find all denials
devarmor audit-log query "decision=deny" --limit=100

# Find cost limit violations
devarmor audit-log query \
  "policy=CostControl AND decision=deny" \
  --limit=50 \
  --format=table

# Export for compliance report
devarmor audit-log query \
  "timestamp >= 2026-05-01 AND timestamp < 2026-06-01" \
  --format=csv \
  --output=may-compliance.csv
```

### Compliance Reporting

Generate compliance reports automatically:

```bash
# Daily compliance summary
devarmor compliance-report daily > daily-compliance.md

# Monthly audit for regulations
devarmor compliance-report monthly \
  --policies=compliance,security \
  --format=pdf > monthly-audit.pdf
```

---

## Next Steps

1. **Read DEVARMOR_ARCHITECTURE.md** - Understand the control plane
2. **Read SKILL_INTEGRATION_GUIDE.md** - Integrate your skill
3. **See examples/cost_control_policy.yaml** - Working example
4. **Read OPERATOR_RUNBOOK.md** - Deploy policies to production
