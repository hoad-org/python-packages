# Migration Guide: Adopting DevArmor

Step-by-step guide to migrate existing Claude skills to use DevArmor for policy-driven enforcement and cross-skill coordination.

---

## Overview

This guide helps you transition from standalone skills to DevArmor-managed skills. The migration is **backward compatible** and can be done **without breaking changes**.

### What Changes

| Before | After |
|--------|-------|
| Standalone skill | DevArmor-managed skill |
| No cross-skill coordination | Events + State sharing |
| Manual permission checks | Automatic policy enforcement |
| No audit trail | Full audit logging |
| Manual rate limiting | Automatic rate limiting |
| Separate configurations | 4-level configuration hierarchy |

### What Stays the Same

- Skill API and commands remain unchanged
- Configuration files are compatible
- No changes to authentication
- Backward compatible with older versions

---

## Phase 1: Preparation (Week 1)

### 1. Inventory Current Skills

```bash
# List all installed skills
devarmor skill list

# For each skill, note:
# - Current version
# - Deployment location
# - Configuration files
# - Dependencies
```

### 2. Review DevArmor Documentation

Read in this order:
1. DEVARMOR_ARCHITECTURE.md (15 min)
2. SKILL_INTEGRATION_GUIDE.md (30 min)
3. POLICY_CONFIGURATION.md (20 min)
4. This migration guide (20 min)

### 3. Plan Migration Timeline

```
Week 1: Preparation (you are here)
Week 2: Pilot (single skill)
Week 3-4: Production rollout (remaining skills)
```

### 4. Communication

- **For DevOps**: Prepare upgrade runbooks (see OPERATOR_RUNBOOK.md)
- **For Users**: Communicate zero-downtime upgrade process
- **For Leads**: Review compliance/audit changes

---

## Phase 2: Pilot Migration (Week 2)

### Step 1: Choose Pilot Skill

Select **one** non-critical skill to migrate first:

**Good candidates:**
- Jira skill (no upstream dependencies)
- Slack skill (logs only, non-destructive)

**Avoid first:**
- Billing/payment skills
- Infrastructure modification skills
- Any skill with multiple dependent skills

### Step 2: Set Up DevArmor Locally

```bash
# Install DevArmor core
pip install devarmor-core>=1.0.0

# Create local configuration
mkdir -p ~/.devarmor/skills
mkdir -p ~/.devarmor/policies

# Initialize
devarmor config init
# Creates ~/.devarmor/config.json
```

### Step 3: Update Skill Dependencies

Update the pilot skill's `pyproject.toml`:

```toml
[project]
dependencies = [
    "devarmor-core>=1.0.0",  # NEW
    "jira>=3.0.0",
    "pydantic>=2.0.0",
]
```

### Step 4: Implement IDevArmorCompliant

Create `src/devarmor_integration.py` (see SKILL_INTEGRATION_GUIDE.md).

**Minimal implementation:**
```python
from devarmor import IDevArmorCompliant, DevArmorContext

class SkillDevArmorIntegration(IDevArmorCompliant):
    async def on_install(self) -> None:
        """Initialize DevArmor state/subscriptions"""
        print(f"{self.skill_name} installing")
    
    async def on_uninstall(self) -> None:
        """Cleanup"""
        print(f"{self.skill_name} uninstalling")
    
    async def validate_action(
        self,
        action: str,
        params: dict,
        context: DevArmorContext
    ) -> bool:
        """Allow all actions initially"""
        return True
```

### Step 5: Register with DevArmor

Update `src/cli.py`:

```python
from devarmor import get_devarmor, devarmor_registry
from devarmor_integration import SkillDevArmorIntegration

async def initialize():
    devarmor = await get_devarmor()
    integration = SkillDevArmorIntegration()
    devarmor_registry.register("jira-skill", integration)
```

### Step 6: Test Locally

```bash
# Run existing tests (should all pass)
pytest tests/ -v

# Test DevArmor integration
devarmor test jira-skill

# Manual testing
devarmor jira issue list  # Should work as before
```

### Step 7: Deploy to Staging

```bash
# Build new version
make build

# Install to staging
devarmor install jira-skill-devarmor@1.0.0-rc1 \
  --environment=staging

# Run smoke tests
devarmor skill test jira-skill --environment=staging

# Monitor for 24 hours
devarmor skill monitor jira-skill --environment=staging --duration=24h
```

### Step 8: Review & Approve

**Checklist:**
- [ ] All tests pass
- [ ] No new errors in staging logs
- [ ] Configuration loaded correctly
- [ ] Events publishing
- [ ] Audit logging working
- [ ] No performance regression
- [ ] Documentation updated

---

## Phase 3: Production Rollout (Weeks 3-4)

### Week 3: First Skills (non-critical)

#### Skill 1: Jira Skill

```bash
# Pre-upgrade
devarmor skill backup jira-skill --output=jira-skill-backup.tar.gz

# Upgrade
devarmor skill upgrade jira-skill 2.0.0 -> 2.0.0-devarmor

# Verify
devarmor skill health jira-skill --continuous --duration=1h

# If all good
devarmor skill confirm-upgrade jira-skill

# If problems
devarmor skill rollback jira-skill
```

#### Skill 2: Slack Skill

(Same procedure as Jira)

#### Skill 3: GitHub Skill

(Same procedure as Jira)

### Week 4: Remaining Skills

Repeat process for remaining skills, rolling out 1-2 per day.

---

## Configuration Migration

### Old Setup (Standalone)

```
~/.jira/config.json
~/.github/config.json
./local-config.json
```

### New Setup (DevArmor)

```
~/.devarmor/config.json          (master config)
~/.devarmor/skills/jira.json     (Jira skill config)
~/.devarmor/skills/github.json   (GitHub skill config)
~/.devarmor/policies/*.yaml      (policies)
.devarmor/jira.json              (repo override)
.devarmor/github.json            (repo override)
```

### Migration Procedure

```bash
# 1. Backup old configs
cp -r ~/{.jira,.github} ~/.devarmor/archived/

# 2. Convert to new format
devarmor config migrate ~/.jira/config.json \
  --output=~/.devarmor/skills/jira.json

# 3. Verify configuration
devarmor config show jira-skill

# 4. Test with old config still present
# DevArmor loads both, prefers new format

# 5. Once verified, remove old configs
# (Keep for 30 days as backup)
```

---

## Policy Rollout Strategy

### Phase 1: Logging Only (No Enforcement)

First 2 weeks: Log policy decisions but don't enforce them.

```yaml
# .devarmor/policies/cost-control.yaml
constraints:
  - name: MonthlyBudget
    rule: "cost <= 500"
    action: warn           # Log only, don't deny
    message: "Would exceed budget"
```

**Purpose:** Understand impact without breaking users

```bash
# See what would have been denied
devarmor audit-log query "decision=warn" --limit=100
```

### Phase 2: Warnings (Week 3)

Enable warnings to alert users.

```yaml
constraints:
  - name: MonthlyBudget
    rule: "cost <= 500"
    action: warn           # Show warning, don't deny
    message: "Approaching budget limit"
```

### Phase 3: Enforcement (Week 4)

Enable full enforcement.

```yaml
constraints:
  - name: MonthlyBudget
    rule: "cost <= 500"
    action: deny           # Enforce limit
    message: "Budget exceeded"
```

---

## Backward Compatibility

### Coexistence Period (Month 1)

Old and new skills can coexist:

```bash
# Old version still works
devarmor jira@2.0.0 issue list

# New DevArmor version
devarmor jira@2.0.0-devarmor issue list

# Both can be deployed
devarmor skill list
# jira@2.0.0 (legacy)
# jira@2.0.0-devarmor (new)
```

### Decommissioning Old Versions (Month 2)

```bash
# Once stable, remove old versions
devarmor skill remove jira@2.0.0

# Archive for audit
devarmor skill archive jira@2.0.0
```

---

## Rollback Procedures

### Quick Rollback (< 1 minute)

```bash
# If new version is broken
devarmor skill rollback jira-skill 2.0.0-devarmor -> 2.0.0

# Automatic:
# - Switch traffic back to 2.0.0
# - Restore old configuration
# - Restart event subscriptions
```

### Full Rollback (If needed)

```bash
# 1. Stop new version
devarmor skill stop jira-skill@2.0.0-devarmor

# 2. Restore from backup
devarmor backup restore jira-skill-backup.tar.gz

# 3. Start old version
devarmor skill start jira-skill@2.0.0

# 4. Restore state
devarmor state restore jira-state-backup.json
```

---

## Troubleshooting Migration Issues

### Issue: "DevArmor dependency not found"

```
ImportError: No module named 'devarmor'
```

**Solution:**
```bash
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core
```

### Issue: "Configuration not loading"

```
ConfigError: Failed to load configuration
```

**Solution:**
```bash
# Verify configuration files exist
ls -la ~/.devarmor/skills/jira.json
ls -la .devarmor/jira.json

# Check syntax
devarmor config validate jira-skill

# Show all sources
devarmor config show jira-skill --verbose
```

### Issue: "Events not publishing"

```
EventBusError: Failed to publish event
```

**Solution:**
```bash
# Check event bus connectivity
devarmor health

# Verify subscription
devarmor event-bus list-subscriptions

# Test publish
devarmor event-bus test publish jira.test
```

### Issue: "Policy denying all actions"

```
PolicyError: All actions denied by policy
```

**Solution:**
```bash
# Check policy status
devarmor policy show

# Verify policy syntax
devarmor policy validate .devarmor/policies/*.yaml

# Test policy with sample data
devarmor policy test cost-control \
  --user=alice@example.com \
  --cost=50 \
  --budget=500

# If wrong, disable policy temporarily
devarmor policy disable CostControl
```

---

## Training & Documentation

### For Users

Create a one-pager explaining:
- What's changing (mostly transparent)
- New compliance/audit features
- Policy enforcement (costs, budgets)
- How to request exceptions

**Example:** `/docs/DEVARMOR_USER_GUIDE.md`

### For DevOps

Provide:
- Installation & configuration runbook
- Monitoring & alerting setup
- Incident response procedures
- Cost tracking & reporting

**Example:** See OPERATOR_RUNBOOK.md

### For Developers

Provide:
- Integration guide (SKILL_INTEGRATION_GUIDE.md)
- API reference (API_REFERENCE.md)
- Working examples (examples/)
- Testing patterns

---

## Timeline Summary

```
Week 1: Preparation
├─ Read documentation
├─ Set up DevArmor locally
└─ Plan migration

Week 2: Pilot (1 skill)
├─ Implement DevArmor integration
├─ Test locally
├─ Deploy to staging
└─ Monitor 24 hours

Week 3: Production Rollout Phase 1
├─ Jira skill (critical)
├─ Slack skill (non-critical)
└─ GitHub skill (non-critical)

Week 4: Production Rollout Phase 2
├─ Remaining skills (1-2 per day)
└─ Monitoring & support

Month 2: Consolidation
├─ Decommission old versions
├─ Update documentation
└─ Train team
```

---

## Post-Migration Checklist

- [ ] All skills upgraded to DevArmor version
- [ ] Old versions removed (archived for 30 days minimum)
- [ ] Policies in place (logging, warnings, enforcement)
- [ ] Audit logging working
- [ ] Cross-skill events tested
- [ ] Team trained on new system
- [ ] Documentation updated
- [ ] Monitoring & alerting in place
- [ ] Incident response runbooks ready
- [ ] Cost tracking validated

---

## Success Metrics

### Adoption
- 100% of skills on DevArmor
- 0% downtime during rollout
- 0 critical incidents

### Compliance
- 100% of actions audited
- Policy enforcement in place
- 0 policy bypass attempts

### Performance
- No latency regression (< 5%)
- Event processing lag < 100ms
- State store latency < 50ms

### Cost
- Cost tracking accurate
- No unexpected spend
- Budget compliance > 95%

---

## Contact & Support

**Questions during migration?**
- See SKILL_INTEGRATION_GUIDE.md for technical questions
- See OPERATOR_RUNBOOK.md for operational questions
- See POLICY_CONFIGURATION.md for policy questions

**Incident during migration?**
- See OPERATOR_RUNBOOK.md Troubleshooting section
- See ROLLBACK-PROCEDURES.md for recovery

---

## Next Steps

1. **Read SKILL_INTEGRATION_GUIDE.md** - Detailed integration steps
2. **Review OPERATOR_RUNBOOK.md** - Deployment procedures
3. **Check examples/** - Working examples from Terrorgem
4. **Schedule kickoff meeting** - Start Phase 1
