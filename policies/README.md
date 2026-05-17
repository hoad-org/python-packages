# DevArmor Enterprise Policy Templates

Production-ready enterprise policy templates for enforcing governance, security, compliance, and cost controls across all deployed skills.

## Quick Start

### Validate Policies
```bash
python validate_policies.py --policy-dir ./
```

### Run Specific Policy Test
```bash
python validate_policies.py --test-dry-run cost_control.yaml --actor alice --action delete
```

### Generate Reports
```bash
# Summary of all policies
python validate_policies.py --report summary

# Test coverage analysis
python validate_policies.py --report coverage --output coverage.json
```

## Policy Files

### Core Policies

#### 1. `cost_control.yaml` (Production)
Enforces strict cost limits and rate limiting across all skills.

**Key Controls:**
- Global monthly budget: $30 USD
- Per-skill API calls: 100/minute
- Operation timeout: 30 seconds
- Warning threshold: 80% of budget

**Applied to:** github, confluence, jira, green, prcheck

**Constraints:** 9 rules covering budget enforcement, rate limiting, timeout, and burst protection

#### 2. `security.yaml`
Comprehensive security controls with approval gates and MFA requirements.

**Key Controls:**
- Block all database delete operations in production
- Bulk updates (>10 resources) require 2-person approval
- Credential changes require MFA verification
- Block external API calls to untrusted domains
- Allow read-only operations always

**Applied to:** All skills

**Constraints:** 13 rules covering deletion, privilege escalation, credentials, and anomaly detection

#### 3. `compliance.yaml`
Audit logging, retention policies, and multi-framework compliance alignment (SOC2, GDPR, HIPAA).

**Key Controls:**
- Complete audit trail for all C(R)UD operations
- 90-day minimum retention (configurable by sensitivity)
- Delete operations require 2-person approval
- Org-level isolation enforcement
- Data classification tracking
- GDPR, HIPAA, SOC2 compliance

**Applied to:** All skills

**Constraints:** 14 rules with framework-specific controls and immutable audit enforcement

#### 4. `development.yaml`
Permissive policy for development and staging environments.

**Key Differences from Production:**
- No cost limits (unlimited testing)
- Rate limit: 1000 API calls/minute (vs. 100 in production)
- Operation timeout: 60 seconds (vs. 30 in production)
- Notifications disabled
- Approval gates relaxed
- Extended external API allowlist (includes localhost, *.test, *.dev)

**Applied to:** staging, dev, test environments only

**Environment filter:** NOT production AND NOT preproduction

#### 5. `production.yaml`
Strict enforcement for production deployments with incident response automation.

**Key Controls:**
- Strict cost enforcement ($30/month)
- Rate limit: 100 API calls/minute
- Operation timeout: 30 seconds
- ALL mutations require approval
- Delete operations require 2-person approval + MFA
- Slack alerts for violations
- PagerDuty incident creation for critical violations
- Block off-hours deletions
- Require change tickets

**Applied to:** production, preproduction environments only

## Example Policies

Located in `examples/`:

### `terrorgem_phase0.yaml`
TerrorGems Phase 0 MVP policy (Live 2026-04-13)

**Budget:** £3-6/month (~$4-8 USD)

**Features:**
- Core game mechanics cost tracking
- Gamification event rate limiting (20 events/day)
- Jigsaw campaign mechanics audit
- Retention email tracking

**Test case count:** 6

### `terrorgem_phase1.yaml`
TerrorGems Phase 1 expansion policy (Live 2026-04-14)

**Budget:** £20-30/month (~$25-40 USD)

**Features:**
- Gamification enhancements (50 events/day)
- Creator MVP content tracking
- Web push notification limits
- Creator Pro tier cost tracking

**Test case count:** 6

### `enterprise_soc2.yaml`
Enterprise SOC2 Type II compliance policy

**Criteria Coverage:**
- CC: Common Criteria (security & availability)
- C: Confidentiality
- A: Availability
- L: Logical & operational availability

**Key Controls:**
- Change management (CC6.1, CC6.2)
- Access control review (CC7.2)
- Incident response (A1.2)
- Logical access (C1.1, C1.2)
- Audit trail enforcement (L1.1, L1.2)
- Encryption requirements

**Test case count:** 7

### `enterprise_security.yaml` (Planned)
Security-hardened policy for regulated industries (HIPAA, PCI-DSS)

## Policy Structure

Each policy file contains:

### Metadata
- `name`: Policy identifier
- `version`: Semantic versioning
- `description`: Multi-line description
- `enabled`: Boolean flag
- `priority`: Numeric priority (higher = evaluated first)

### Constraints
Array of policy rules with:
- `name`: Constraint identifier
- `rule`: Evaluation expression
- `action`: ALLOW, DENY, WARN, RATE_LIMIT, AUDIT, INCIDENT
- `message`: User-facing message with variable interpolation
- `tags`: Classification tags
- `enabled`: Boolean flag

### Skill Limits
Per-skill configuration:
- `api_rate_limit_per_minute`: Rate limit
- `operation_timeout_seconds`: Max duration
- `monthly_budget_cents`: Monthly spend limit
- `approval_required`: Boolean
- `external_apis_allowed`: Boolean

### Variables
Template variables for policy evaluation:
- `monthly_budget_cents`: Global budget limit
- `warning_threshold_percent`: Alert threshold
- `operation_timeout_seconds`: Timeout limit

### Test Cases
Validation test cases with:
- `name`: Test description
- `input`: Test input parameters
- `expected`: Expected outcome (ALLOW, DENY, WARN, RATE_LIMIT, etc.)

## Writing Custom Policies

### Basic Policy Template
```yaml
name: MyCustomPolicy
version: "1.0.0"
description: |
  Description of what this policy enforces.
enabled: true
priority: 100

constraints:
  - name: FirstRule
    rule: |
      your_condition_here
    action: deny
    message: "Your message here"
    tags: [custom, policy]
    enabled: true

skill_limits:
  github:
    api_rate_limit_per_minute: 100
    operation_timeout_seconds: 30

test_cases:
  - name: "Test case 1"
    input:
      condition: value
    expected: ALLOW
```

### Policy Actions

- **ALLOW**: Operation is permitted
- **DENY**: Operation is blocked
- **WARN**: Operation allowed with warning
- **RATE_LIMIT**: Operation subject to rate limiting
- **AUDIT**: Operation allowed but logged
- **INCIDENT**: Incident created (PagerDuty/Slack)
- **SUPPRESS**: Notification suppressed

### Common Patterns

#### Cost Control
```yaml
- name: BudgetLimit
  rule: |
    (organization.monthly_spend + estimated_cost) > monthly_budget
  action: deny
  message: "Budget exceeded"
```

#### Approval Gate
```yaml
- name: ApprovalRequired
  rule: |
    operation_type == "delete" AND approvals < 2
  action: deny
  message: "2-person approval required"
```

#### Rate Limiting
```yaml
- name: RateLimit
  rule: |
    skill.${skill_name}.api_calls_this_minute >= 100
  action: rate_limit
  message: "Rate limit exceeded"
  rate_limit:
    requests_per_minute: 100
    burst_size: 10
```

#### Audit Logging
```yaml
- name: AuditMutation
  rule: |
    operation_type in ["create", "update", "delete"]
  action: audit
  message: "Mutation logged"
  audit_level: info
```

## Deploying Policies

### Development
```bash
devarmor policy deploy ./development.yaml --environment=staging
```

### Production
```bash
devarmor policy deploy ./production.yaml --environment=production
```

### Custom Policy
```bash
devarmor policy deploy ./my_custom_policy.yaml --organization=acme
```

## Testing Policies

### Validation
```bash
# Validate YAML syntax
python validate_policies.py --validate cost_control.yaml

# Validate all policies
python validate_policies.py --policy-dir ./

# Verbose validation
python validate_policies.py --verbose
```

### Dry-Run Testing
```bash
# Test specific action
python validate_policies.py --test-dry-run production.yaml \
  --actor alice@example.com \
  --action delete

# Test with context
python validate_policies.py --test-dry-run security.yaml \
  --actor bob@example.com \
  --action rotate_credential
```

### Test Coverage
```bash
# Generate coverage report
python validate_policies.py --report coverage

# Output to file
python validate_policies.py --report coverage --output coverage.json
```

## Integration with Skills

### GitHub Skill
```python
from devarmor.policy import PolicyEngine
from devarmor.models import PolicyConfig

# Load policy
config = PolicyConfig.from_yaml("cost_control.yaml")
engine = PolicyEngine(config)

# Evaluate action
result = engine.evaluate_cost_control(
    resource_type="compute",
    estimated_cost=5.00,
    actor="alice@example.com"
)

if not result.allowed:
    logger.error(f"Policy violation: {result.reason}")
```

### Jira Skill
```python
# Evaluate security policy
result = engine.evaluate_security_policy(
    action="delete",
    actor="bob@example.com",
    target="JIRA-001"
)

if not result.allowed:
    # Check for approval requirements
    if "approval" in result.violated_policies:
        # Request approval workflow
        pass
```

## Monitoring & Alerts

### Slack Alerts
Policies automatically send alerts to configured Slack channels:

- `#devarmor-alerts`: Critical violations
- `#devarmor-warnings`: Warnings and rate limits
- `#devarmor-info`: Informational messages

### PagerDuty Integration
Critical violations trigger PagerDuty incidents with:
- Automatic escalation to on-call team
- Incident details and context
- Root cause analysis requirements

### Audit Logging
All policy evaluations logged with:
- Actor and action
- Resource and target
- Timestamp
- Evaluation result
- Violated policies (if any)

## Common Scenarios

### Scenario 1: Developer Pushes Code in Production
```
Policy: production.yaml
Action: Evaluate git push
Result: DENY (requires approval)
Message: "Production changes require approval"
Next: Developer requests approval from security team
```

### Scenario 2: Bulk Delete Operation
```
Policy: security.yaml, production.yaml
Action: Delete 50 items
Result: DENY (requires 2-person approval + MFA)
Message: "Delete operations require 2-person approval"
Next: Request approvals from 2 security team members
```

### Scenario 3: Credential Rotation
```
Policy: security.yaml, production.yaml
Action: Rotate API token
Result: DENY (requires MFA)
Message: "Credential changes require MFA verification"
Next: Complete MFA challenge and retry
```

### Scenario 4: Development Testing
```
Policy: development.yaml
Action: Delete test data (staging)
Result: ALLOW (no restrictions in dev)
Message: "Development: no approval required"
Next: Operation proceeds immediately
```

## Best Practices

### 1. Environment-Specific Policies
- Use `development.yaml` for staging/dev
- Use `production.yaml` for production
- Use `security.yaml` for all environments

### 2. Test Coverage
- Write test cases for all constraints
- Aim for >85% constraint coverage
- Test both allow and deny paths

### 3. Clear Messages
- Include context variables: `${actor}`, `${target}`, `${operation_type}`
- Provide actionable guidance
- Reference ticket systems: `DEVOPS-PROD-CHANGE`

### 4. Monitoring
- Enable Slack alerts for violations
- Configure PagerDuty for critical incidents
- Review audit logs weekly

### 5. Documentation
- Document custom policies in comments
- Include examples in description
- Link to runbooks for violations

## Troubleshooting

### Policy Not Applied
1. Check `enabled: true` in policy file
2. Verify policy is deployed: `devarmor policy list`
3. Check environment filter matches deployment

### Test Case Failing
1. Verify test inputs match constraint conditions
2. Check `expected` value matches rule action
3. Run validation: `python validate_policies.py --validate policy.yaml`

### Performance Issues
1. Reduce constraint count per policy
2. Optimize rule evaluation expressions
3. Check rate limiting configuration

### Audit Log Not Appearing
1. Verify `audit_logging.enabled: true`
2. Check audit log persistence
3. Review retention policies

## Reference

### Policy Variables
- `${skill_name}`: Name of skill
- `${actor}`: User performing action
- `${action}`: Action being performed
- `${target}`: Resource being targeted
- `${operation_type}`: Type of operation (create, read, update, delete)
- `${environment}`: Deployment environment
- `${timestamp}`: Current timestamp
- `${estimated_cost}`: Estimated operation cost
- `${organization.monthly_spend}`: Monthly budget tracking

### Environment Values
- `dev`: Local development
- `staging`: Staging/test environment
- `test`: Automated test environment
- `preproduction`: Pre-prod environment
- `production`: Production environment

### Classification Levels
- `public`: No restrictions
- `internal`: Internal use only
- `sensitive`: Customer or business sensitive
- `personal`: Personal data (GDPR)
- `hipaa`: Healthcare data
- `restricted`: Trade secrets, API keys

## Support

For questions or issues:
1. Check troubleshooting section above
2. Review policy examples
3. Contact DevArmor team: devarmor@example.com

## Version History

- **v1.0.0** (2026-05-17): Initial release
  - Core policies: cost control, security, compliance
  - Environment policies: development, production
  - Example policies: TerrorGems Phase 0/1, SOC2

## License

DevArmor policies are proprietary and subject to license agreement.
