# DevArmor Operator Runbook

A step-by-step guide for operators to manage, deploy, and troubleshoot DevArmor in production.

---

## Installation & Setup

### Prerequisites

```bash
# Check Python version (3.12+)
python --version
# Python 3.12.3

# Check pip
pip --version
# pip 24.0

# Check disk space (minimum 2GB)
df -h / | tail -1
# /dev/disk1s5s1  233Gi  150Gi   83Gi  65% /
```

### Install DevArmor Core

```bash
# Option 1: From PyPI index
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core>=1.0.0

# Option 2: From Git (development)
git clone https://github.com/rhyscraig/devarmor-core.git
cd devarmor-core
pip install -e .

# Verify installation
devarmor --version
# DevArmor 1.0.0
```

### Initial Configuration

```bash
# Create configuration directories
mkdir -p ~/.devarmor/skills
mkdir -p ~/.devarmor/policies
mkdir -p ~/.devarmor/state

# Initialize system config
cat > ~/.devarmor/config.json << 'EOF'
{
  "environment": "production",
  "state_store": {
    "type": "redis",
    "url": "redis://localhost:6379/0"
  },
  "event_bus": {
    "type": "nats",
    "url": "nats://localhost:4222"
  },
  "audit_log": {
    "type": "file",
    "path": "/var/log/devarmor/audit.log"
  }
}
EOF

# Verify configuration
devarmor config show
```

---

## Managing Skills

### Installing a Skill

#### Basic Installation

```bash
# Install specific version
devarmor install jira-skill@2.0.0

# Install latest version
devarmor install jira-skill

# Expected output:
# Installing jira-skill@2.0.0...
#   ✓ Resolving dependencies
#   ✓ Verifying package integrity
#   ✓ Extracting skill files
#   ✓ Loading compliance layer
#   ✓ Running smoke tests
# ✓ Installation successful
# Location: /usr/local/lib/devarmor/skills/jira-skill/
```

#### Installation with Configuration

```bash
# Install and configure in one step
devarmor install jira-skill@2.0.0 \
  --config ~/.devarmor/skills/jira.json \
  --skip-smoke-tests=false \
  --validate-policies=true

# Verify installation
devarmor skill list
# jira-skill    v2.0.0    installed    /usr/local/.../jira-skill/
# github-skill  v2.0.0    installed    /usr/local/.../github-skill/
```

#### Installation with Policy Binding

```bash
# Install with policy enforcement
devarmor install jira-skill@2.0.0 \
  --apply-policy=CostControl \
  --apply-policy=Security

# Verify policy binding
devarmor policy-binding jira-skill
# Policy Bindings:
#   CostControl (enabled)
#   Security (enabled)
```

### Upgrading a Skill (Zero-Downtime)

#### Pre-Upgrade Checklist

```bash
# 1. Check current version
devarmor skill info jira-skill
# Name:     jira-skill
# Version:  2.0.0
# Status:   healthy
# Uptime:   45 days

# 2. Check for active operations
devarmor skill health jira-skill
# Operations: 0 active
# Queue: 0 pending
# Status: idle ✓ (safe to upgrade)

# 3. Create backup of state
devarmor state export jira.* > backup-jira-state.json

# 4. Review changelog
devarmor skill changelog jira-skill 2.0.0 2.1.0
```

#### Upgrade Procedure

```bash
# 1. Install new version in parallel
devarmor install jira-skill@2.1.0 --parallel

# 2. Run canary tests
devarmor skill test jira-skill@2.1.0
# test_api_connectivity: PASS
# test_configuration_compatibility: PASS
# test_event_subscriptions: PASS
# test_policy_compliance: PASS
# ✓ All canary tests passed

# 3. Switch traffic to new version
devarmor skill upgrade jira-skill 2.0.0 -> 2.1.0

# 4. Monitor for errors
devarmor skill monitor jira-skill --duration=5m
# Error rate: 0.0%
# Latency (p99): 245ms
# Status: healthy ✓

# 5. Decommission old version (optional)
devarmor skill remove jira-skill@2.0.0 --keep-rollback=true
```

#### Zero-Downtime Upgrade Mechanics

```
Timeline:
├─ T+0s: Install 2.1.0 parallel to 2.0.0
│        (new requests go to 2.0.0)
├─ T+10s: Run canary tests on 2.1.0
├─ T+30s: Canary passed, switch traffic
│        (new requests go to 2.1.0)
└─ T+5m: Keep 2.0.0 for rollback
         (zero requests to 2.0.0)

Error Handling:
├─ Canary fails → Stay on 2.0.0
└─ Traffic switch fails → Automatic rollback to 2.0.0
```

### Removing a Skill

#### Safe Removal

```bash
# 1. Check dependencies
devarmor skill dependencies jira-skill
# github-skill depends on jira.issue.created events
# slack-skill depends on jira.issue.created events

# 2. Drain active operations
devarmor skill drain jira-skill --timeout=60s
# Waiting for 5 active operations...
# Waiting for 2 active operations...
# ✓ All operations completed

# 3. Unsubscribe from events
devarmor skill unsubscribe-all jira-skill

# 4. Archive audit logs
devarmor audit-log archive --skill=jira-skill

# 5. Remove skill
devarmor skill remove jira-skill --archive-config=true
# Removed: /usr/local/lib/devarmor/skills/jira-skill/
# Archived config: ~/.devarmor/archived/jira-skill-2.0.0/
```

### Health Monitoring

```bash
# Check skill health
devarmor skill health jira-skill
# Name:           jira-skill
# Version:        2.0.0
# Status:         healthy
# Uptime:         45 days
# Operations:     12 active
# Error rate:     0.0%
# Latency (p50):  145ms
# Latency (p99):  245ms

# Watch skill in real-time
devarmor skill monitor jira-skill --live
# Updates every 2 seconds, press Ctrl+C to exit
```

---

## Managing Policies

### Deploying Policies

#### Basic Policy Deployment

```bash
# Deploy a single policy
devarmor policy deploy .devarmor/policies/cost-control.yaml
# Validating syntax... ✓
# Checking compatibility... ✓
# Loading policy... ✓
# ✓ Policy deployed: CostControl

# Verify deployment
devarmor policy show CostControl
```

#### Multi-Environment Deployment

```bash
# Deploy to staging first
devarmor policy deploy .devarmor/policies/cost-control.yaml \
  --environment=staging \
  --dry-run=true
# [DRY RUN] Would deploy CostControl to staging

# Deploy to production
devarmor policy deploy .devarmor/policies/cost-control.yaml \
  --environment=production \
  --require-approval=true
# Awaiting approval... (in Slack/email)
# ✓ Policy deployed to production
```

#### Testing Policies Before Deployment

```bash
# 1. Validate syntax
devarmor policy validate .devarmor/policies/cost-control.yaml
# ✓ Valid YAML syntax
# ✓ All constraints have names
# ✓ All rules are valid expressions

# 2. Run test cases
devarmor policy test-suite .devarmor/policies/cost-control.yaml
# Running 5 test cases...
# test_user_under_budget: PASS
# test_user_over_budget: PASS
# test_high_cost_warning: PASS
# test_rate_limit_exceeded: PASS
# test_monthly_reset: PASS
# ✓ All tests passed

# 3. Simulate on real data
devarmor policy simulate cost-control \
  --user=alice@example.com \
  --action=create_resource \
  --cost=100 \
  --monthly_spend=450
# MonthlyBudget: ALLOW (450+100=550, limit=500)
# ProjectBudget: WARN (approaching limit)
# HighCostWarning: WARN (cost=100 > 50)
```

### Policy Status & Monitoring

```bash
# List all policies
devarmor policy list
# Name                  Status      Priority
# CostControl           enabled     100
# Security              enabled     200
# Compliance            enabled     150
# RateLimiting          disabled    50

# Check policy decisions (audit trail)
devarmor policy decisions --limit=50
# Timestamp              User    Decision  Policy           Rule
# 2026-05-17T14:30:00Z   alice   ALLOW     CostControl      MonthlyBudget
# 2026-05-17T14:31:00Z   bob     DENY      CostControl      MonthlyBudget
# 2026-05-17T14:32:00Z   alice   WARN      CostControl      ProjectBudget

# Policy evaluation metrics
devarmor policy metrics
# CostControl:
#   Total evaluations: 15,234
#   Allows: 15,100 (98.8%)
#   Denies: 50 (0.3%)
#   Warns: 84 (0.5%)
```

### Troubleshooting Policies

#### Policy Not Evaluating

```bash
# 1. Check if policy is enabled
devarmor policy show CostControl | grep enabled
# enabled: true ✓

# 2. Check policy syntax
devarmor policy validate .devarmor/policies/cost-control.yaml
# ✓ Valid syntax

# 3. Check if policy is bound to skill
devarmor policy-binding jira-skill
# Policies applied to jira-skill:
#   CostControl (enabled)

# 4. Check audit logs for evaluation
devarmor audit-log query "policy=CostControl" --limit=10
# See if CostControl was evaluated for recent actions
```

#### False Denials/Warnings

```bash
# 1. Check state values
devarmor state get "user.alice.cost"
# Value: 450

# 2. Run policy simulation with actual values
devarmor policy simulate cost-control \
  --user=alice@example.com \
  --cost=100 \
  --monthly_spend=450
# Output: DENY (would exceed limit)

# 3. Check policy rule syntax
devarmor policy show CostControl | grep -A 3 MonthlyBudget
# rule: "user.${user_id}.cost <= 500"

# 4. If still wrong, update policy
devarmor policy update cost-control \
  --constraint=MonthlyBudget \
  --rule="user.\${user_id}.cost <= 600"
```

---

## Monitoring & Observability

### Health Dashboard

```bash
# Show complete health status
devarmor health
# DevArmor Status: HEALTHY
#
# Core Services:
#   Event Bus (nats):     UP (523 connected)
#   State Store (redis):  UP (12.5GB used)
#   Audit Log (s3):       UP (456K entries)
#
# Skills:
#   jira-skill@2.0.0:     HEALTHY (0 errors)
#   github-skill@2.0.0:   HEALTHY (0 errors)
#   slack-skill@1.0.0:    HEALTHY (0 errors)
#
# Policies:
#   CostControl:          ENABLED (98.8% allow)
#   Security:             ENABLED (99.9% allow)
#   Compliance:           ENABLED (100% allow)
#
# Events (last hour):
#   Published: 12,345
#   Processed: 12,344
#   Failed: 1
#   Latency (p99): 45ms
```

### Audit Logging

```bash
# Query audit logs
devarmor audit-log query "action=issue.created AND status=success"
# 2026-05-17T14:30:00Z  alice  jira.issue.created    PROJ-123  success
# 2026-05-17T14:31:00Z  bob    jira.issue.created    PROJ-124  success

# Export audit logs for compliance
devarmor audit-log export \
  --start=2026-05-01 \
  --end=2026-05-31 \
  --format=csv \
  --output=may-2026-audit.csv

# Find failed operations
devarmor audit-log query "status=failed"
# Shows all failed operations with reasons

# User activity report
devarmor audit-log report user:alice@example.com
# Actions: 234
# Cost: 120 credits
# Errors: 2
# Rate limit hits: 0
```

### Metrics & Performance

```bash
# Event bus metrics
devarmor metrics event-bus
# Published events (1h): 12,345
# Processed events (1h): 12,344
# Failed events (1h): 1
# Avg latency: 35ms
# p99 latency: 145ms

# State store metrics
devarmor metrics state-store
# Keys: 5,234
# Memory: 12.5GB
# Hit rate: 98.7%
# Avg access time: 2ms

# Policy evaluation metrics
devarmor metrics policy
# Total evaluations: 15,234
# Avg evaluation time: 5ms
# Cache hit rate: 92.3%
```

---

## Troubleshooting & Incident Response

### Common Issues

#### Issue: "Skill installation failed"

```
Error: Failed to verify package integrity
```

**Solution:**
```bash
# 1. Check network
ping -c 1 pypi.org

# 2. Check package exists
devarmor package info jira-skill@2.0.0

# 3. Try again with verbose output
devarmor install jira-skill@2.0.0 --verbose

# 4. If still failing, try from git
git clone https://github.com/rhyscraig/jira-skill.git
cd jira-skill
pip install -e .
```

#### Issue: "Policy evaluation too slow"

```
Error: Policy evaluation took 2000ms (target: <50ms)
```

**Solution:**
```bash
# 1. Check policy complexity
devarmor policy analyze cost-control
# Constraint: MonthlyBudget
# Complexity: O(1) simple lookup
# Evaluation time: 5ms

# 2. Disable unnecessary policies
devarmor policy disable RateLimiting
# If you have separate rate limiting in the skill

# 3. Cache policy evaluations
devarmor config set policy.cache_ttl=300
# Cache results for 5 minutes
```

#### Issue: "Event processing lag"

```
Error: Event queue lag > 100ms (backlog: 5,000 events)
```

**Solution:**
```bash
# 1. Check event queue depth
devarmor event-bus status
# Queue depth: 5,000
# Processing rate: 100/sec
# Estimated catch-up time: 50 seconds

# 2. Add event processors
devarmor event-bus scale --processors=5

# 3. Check for slow subscribers
devarmor event-bus analyze
# github.pr.opened -> github-skill: 500ms (too slow!)

# 4. Optimize the subscriber
# (See SKILL_INTEGRATION_GUIDE.md for optimization tips)
```

### Incident Response

#### High Error Rate

```bash
# 1. Detect the issue
devarmor alert triggered
# Alert: High error rate (5% > threshold 1%)
# Skill: jira-skill@2.0.0
# Duration: 5 minutes

# 2. Check what changed
devarmor skill recent-changes jira-skill
# 2 hours ago: Upgraded to 2.0.0
# 3 hours ago: Deployed cost-control policy

# 3. Check logs
devarmor skill logs jira-skill --tail=100
# [ERROR] API authentication failed: 401 Unauthorized

# 4. Immediate action: rollback
devarmor skill rollback jira-skill 2.0.0 2.1.0
# Rolling back to 2.0.0...
# ✓ Rolled back successfully
# Error rate dropped to 0.1% ✓
```

#### Cost Overrun

```bash
# 1. Alert triggered
devarmor alert triggered
# Alert: User over monthly budget
# User: alice@example.com
# Used: 520 credits (limit: 500)

# 2. Check recent actions
devarmor audit-log query "user=alice" --limit=50
# Find expensive operations

# 3. Temporarily increase limit
devarmor policy update cost-control \
  --user=alice@example.com \
  --override-budget=600 \
  --duration=24h

# 4. Review & adjust
devarmor user-report alice@example.com
# Suggests: Increase budget to 600 for better performance
```

#### Credential Leak

```bash
# 1. Detect leaked credential in logs
devarmor audit-log query "content~password|token" --limit=100

# 2. Immediately revoke credentials
devarmor skill revoke-credentials jira-skill

# 3. Issue new credentials
devarmor skill issue-credentials jira-skill --api-key

# 4. Update configuration
devarmor config update jira-skill \
  --api-key=NEW_KEY

# 5. Audit who accessed the logs
devarmor audit-log query \
  "action=log_read AND resource=audit.log" \
  --since=1h
```

---

## Disaster Recovery

### Backup & Restore

```bash
# Create full backup
devarmor backup create --location=/backups/devarmor-2026-05-17.tar.gz
# Backing up:
#   Skills: 3
#   Policies: 5
#   State: 5,234 keys
#   Audit logs: 1.2MB
# ✓ Backup complete (2.5MB)

# Restore from backup
devarmor backup restore /backups/devarmor-2026-05-17.tar.gz
# Restoring...
# ✓ Restore complete
# ✓ All skills operational
```

### State Recovery

```bash
# Export state before making changes
devarmor state export jira.* > jira-state-backup.json

# If something goes wrong, restore
devarmor state restore jira-state-backup.json
# Restored: jira.issue.count=42, jira.last_issue=PROJ-123
```

### Rollback Procedure

**See ROLLBACK-PROCEDURES.md in project memory.**

```bash
# Quick rollback steps:
# 1. Identify problem (see incident response above)
# 2. Rollback skill: devarmor skill rollback jira-skill 2.1.0 2.0.0
# 3. Rollback policy: devarmor policy rollback cost-control v2 v1
# 4. Restore state: devarmor state restore backup.json
# 5. Monitor: devarmor health --live
```

---

## Maintenance

### Regular Tasks

**Daily:**
```bash
# Check health
devarmor health | grep -v HEALTHY

# Review alerts
devarmor alert list --since=24h
```

**Weekly:**
```bash
# Review audit logs for anomalies
devarmor audit-log report --period=week

# Check skill versions for updates
devarmor package list --available-updates

# Verify policy compliance
devarmor policy metrics
```

**Monthly:**
```bash
# Generate compliance report
devarmor compliance-report monthly > monthly-report.md

# Archive old logs
devarmor audit-log archive --older-than=90d

# Review cost trends
devarmor cost-report monthly
```

### Capacity Planning

```bash
# Check resource usage trends
devarmor metrics history --metric=state_store.memory --period=90d
# Avg: 8.5GB, Peak: 12.5GB, Growth: 150MB/day
# Recommendation: Increase to 32GB storage

# Forecast: When will we hit 95% capacity?
devarmor metrics forecast --metric=state_store.memory --threshold=95
# ETA: 2026-07-15 (59 days)
```

---

## Next Steps

1. **DEVARMOR_ARCHITECTURE.md** - Understand the system
2. **SKILL_INTEGRATION_GUIDE.md** - Integrate your skills
3. **POLICY_CONFIGURATION.md** - Write your policies
4. **API_REFERENCE.md** - Complete command reference
