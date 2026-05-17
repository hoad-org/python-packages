# DevArmor Documentation Index

Complete reference for implementing, deploying, and operating DevArmor in production.

---

## Quick Navigation

### For Skill Developers

Start here to integrate your skill with DevArmor:

1. **[SKILL_INTEGRATION_GUIDE.md](SKILL_INTEGRATION_GUIDE.md)** ⭐ START HERE
   - How to implement IDevArmorCompliant interface
   - Publishing and subscribing to events
   - Configuration management
   - Testing integration
   - Real-world Jira + GitHub example

2. **[API_REFERENCE.md](API_REFERENCE.md)**
   - Complete Python API documentation
   - EventBus, StateStore, PolicyEngine APIs
   - Configuration API
   - Error handling
   - Code examples for each API

3. **[POLICY_CONFIGURATION.md](POLICY_CONFIGURATION.md)**
   - Understanding policies
   - Policy expression language
   - Pre-built templates (cost control, security, compliance)
   - Testing policies before deployment

### For Operators

Deploy and manage DevArmor in production:

1. **[OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md)** ⭐ START HERE
   - Installation and initial setup
   - Installing, upgrading, removing skills
   - Policy deployment and monitoring
   - Troubleshooting common issues
   - Incident response procedures
   - Backup and disaster recovery

2. **[DEVARMOR_ARCHITECTURE.md](DEVARMOR_ARCHITECTURE.md)**
   - 3-layer architecture overview
   - Installation, execution, orchestration layers
   - Control flows and data models
   - Event bus and state store details
   - Security model and threat analysis

3. **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)**
   - Step-by-step migration from standalone skills
   - Timeline and phasing
   - Backward compatibility
   - Rollback procedures
   - Training materials

### For Architects

Understand the system at depth:

1. **[DEVARMOR_ARCHITECTURE.md](DEVARMOR_ARCHITECTURE.md)** ⭐ START HERE
   - System design and components
   - 3-layer architecture (Installation, Execution, Orchestration)
   - Control flow diagrams
   - Data flow (events, state, audit)
   - Security model and isolation boundaries
   - Scalability considerations

2. **[POLICY_CONFIGURATION.md](POLICY_CONFIGURATION.md)**
   - Policy engine design
   - Expression language
   - Policy evaluation and enforcement
   - Audit integration

### For DevOps/SRE

Monitor and maintain DevArmor:

1. **[OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md)** ⭐ START HERE
   - Monitoring and observability
   - Health checks and metrics
   - Alerting and incident response
   - Capacity planning
   - Maintenance procedures

2. **[DEVARMOR_ARCHITECTURE.md](DEVARMOR_ARCHITECTURE.md)**
   - Performance targets and SLAs
   - Horizontal scaling strategies
   - State store sharding
   - Event processing optimization

---

## Document Descriptions

### DEVARMOR_ARCHITECTURE.md

**Audience:** Architects, DevOps, Senior Engineers

**Content:**
- 3-layer architecture (Installation, Execution, Orchestration)
- Installation process (skill install, upgrade, remove)
- Execution layer (configuration, guardrails, API validation)
- Orchestration layer (event bus, state store, policy engine, audit)
- Control flow diagrams for install, action validation, event flow
- Security model and threat analysis
- Scalability and performance targets
- State store sharding and distributed deployment

**Length:** ~800 lines (30-45 min read)

**When to read:**
- System design review
- Architecture decisions
- Performance tuning
- Scaling planning
- Security assessment

### SKILL_INTEGRATION_GUIDE.md

**Audience:** Skill Developers

**Content:**
- Quick start (5 minutes)
- Step-by-step integration (configuration, interface, registration, events, testing)
- 4-level configuration hierarchy explained
- Event publishing and subscription
- Real-world Jira + GitHub integration example
- Testing DevArmor integration
- Troubleshooting guide

**Length:** ~600 lines (30-40 min read)

**When to read:**
- Adding DevArmor to a skill
- First-time integration
- Understanding event-driven patterns
- Integrating with other skills

**Prerequisites:** DEVARMOR_ARCHITECTURE.md

### POLICY_CONFIGURATION.md

**Audience:** Operators, Policy Managers, Architects

**Content:**
- YAML schema reference
- Pre-built templates: CostControl, Security, Compliance, RateLimiting
- Expression language for policies
- Writing custom policies
- Policy inheritance and overrides
- Testing policies before deployment
- Real-world examples from Terrorgem phases
- Compliance and audit integration

**Length:** ~500 lines (25-35 min read)

**When to read:**
- Writing policies for your environment
- Customizing enforcement
- Setting budgets and limits
- Implementing compliance controls

**Prerequisites:** DEVARMOR_ARCHITECTURE.md

### OPERATOR_RUNBOOK.md

**Audience:** Operators, DevOps, SRE

**Content:**
- Installation and setup
- Managing skills (install, upgrade, remove, health monitoring)
- Managing policies (deploy, test, troubleshoot)
- Monitoring and observability (health dashboard, metrics, audit logs)
- Troubleshooting (common issues, incident response)
- Disaster recovery (backup, restore, rollback)
- Maintenance (daily, weekly, monthly tasks)
- Capacity planning

**Length:** ~700 lines (35-45 min read)

**When to read:**
- Installing DevArmor for the first time
- Deploying a new skill
- Responding to incidents
- Planning maintenance windows
- Troubleshooting issues

**Prerequisites:** DEVARMOR_ARCHITECTURE.md (light read)

### API_REFERENCE.md

**Audience:** Skill Developers, Advanced Users

**Content:**
- Core DevArmorClient class
- Configuration API (4-level hierarchy)
- Event Bus API (publish, subscribe)
- State Store API (get, set, query, transactions)
- Policy Engine API (evaluate)
- Audit Log API (query, export)
- Error handling and exceptions
- Retry and timeout behavior
- Rate limiting and quotas
- Code examples for each API

**Length:** ~400 lines (20-25 min read)

**When to read:**
- Writing skill code with DevArmor
- Debugging API calls
- Understanding error handling
- Building complex workflows

**Prerequisites:** SKILL_INTEGRATION_GUIDE.md

### MIGRATION_GUIDE.md

**Audience:** Operators, Architects, Team Leads

**Content:**
- Phase-based migration plan (4 weeks)
- Backward compatibility notes
- Configuration migration
- Policy rollout strategy (logging → warnings → enforcement)
- Rollback procedures
- Training materials
- Post-migration checklist
- Success metrics

**Length:** ~400 lines (20-30 min read)

**When to read:**
- Planning transition to DevArmor
- Migrating existing skill deployments
- Coordinating team adoption
- Planning rollback if needed

**Prerequisites:** All other documentation

---

## Learning Paths

### Path 1: Integrate Your First Skill (4 Hours)

For skill developers new to DevArmor:

1. Read: DEVARMOR_ARCHITECTURE.md (45 min)
2. Read: SKILL_INTEGRATION_GUIDE.md (40 min)
3. Hands-on: Implement integration (90 min)
4. Test: Run tests locally (30 min)
5. Deploy: To staging (30 min)

**Output:** Skill integrated with DevArmor, tested locally and in staging

### Path 2: Deploy DevArmor to Production (6 Hours)

For operators deploying DevArmor:

1. Read: DEVARMOR_ARCHITECTURE.md (45 min)
2. Read: OPERATOR_RUNBOOK.md (45 min)
3. Install: DevArmor core locally (20 min)
4. Configure: Policies and settings (30 min)
5. Deploy: Pilot skill to staging (30 min)
6. Hands-on: Monitoring and troubleshooting (60 min)

**Output:** DevArmor running in staging, ready for production rollout

### Path 3: Understand the Architecture (2 Hours)

For architects and technical leads:

1. Read: DEVARMOR_ARCHITECTURE.md (45 min)
2. Review: Control flow diagrams (20 min)
3. Review: POLICY_CONFIGURATION.md (30 min)
4. Review: SKILL_INTEGRATION_GUIDE.md (25 min)

**Output:** Deep understanding of system design, ready for design reviews

### Path 4: Complete DevArmor Implementation (10 Hours)

For comprehensive understanding:

1. DEVARMOR_ARCHITECTURE.md (45 min)
2. SKILL_INTEGRATION_GUIDE.md (40 min)
3. POLICY_CONFIGURATION.md (35 min)
4. OPERATOR_RUNBOOK.md (45 min)
5. API_REFERENCE.md (25 min)
6. MIGRATION_GUIDE.md (30 min)
7. Hands-on implementation (90 min)

**Output:** Complete understanding, able to design, implement, deploy, and operate DevArmor

---

## Common Tasks & Where to Find Them

### "How do I integrate my skill?"
→ [SKILL_INTEGRATION_GUIDE.md](SKILL_INTEGRATION_GUIDE.md) - Step 2-7

### "How do I write a policy?"
→ [POLICY_CONFIGURATION.md](POLICY_CONFIGURATION.md) - Writing Custom Policies section

### "How do I install DevArmor?"
→ [OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md) - Installation & Setup section

### "How do I upgrade a skill with zero downtime?"
→ [OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md) - Upgrading a Skill section

### "How do I troubleshoot a policy issue?"
→ [POLICY_CONFIGURATION.md](POLICY_CONFIGURATION.md) - Testing Policies section

### "How do I respond to an incident?"
→ [OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md) - Incident Response section

### "How do I understand event flows?"
→ [DEVARMOR_ARCHITECTURE.md](DEVARMOR_ARCHITECTURE.md) - Inter-Skill Event Flow section

### "What's the API for state management?"
→ [API_REFERENCE.md](API_REFERENCE.md) - State Store API section

### "How do I migrate from standalone skills?"
→ [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Phase-by-phase plan

### "How do I publish/subscribe to events?"
→ [SKILL_INTEGRATION_GUIDE.md](SKILL_INTEGRATION_GUIDE.md) - Step 4 & Real-World Example

---

## Examples

Working examples in `/examples/`:

1. **cost_control_policy.yaml**
   - Complete, production-ready cost control policy
   - Terrorgem Phase 0 budget constraints
   - Test cases included

2. **jira_github_integration.py**
   - Real-world Jira ↔ GitHub integration
   - Event publishing and subscription
   - Cross-skill coordination
   - Can be run standalone

3. **policy_testing.py**
   - Policy validation and testing
   - Test case execution
   - Simulation with sample data
   - Shows testing workflow

---

## Document Relationships

```
DEVARMOR_ARCHITECTURE.md
├─ Provides foundation for all other docs
├─ Referenced by: All other documents
└─ Required reading for: Architects, DevOps, understanding overall design

SKILL_INTEGRATION_GUIDE.md
├─ Depends on: DEVARMOR_ARCHITECTURE.md
├─ Uses: API_REFERENCE.md, examples/
└─ For: Skill developers

POLICY_CONFIGURATION.md
├─ Depends on: DEVARMOR_ARCHITECTURE.md
├─ Uses: examples/cost_control_policy.yaml
└─ For: Operators, architects

OPERATOR_RUNBOOK.md
├─ Depends on: DEVARMOR_ARCHITECTURE.md (light)
├─ Uses: POLICY_CONFIGURATION.md, MIGRATION_GUIDE.md
└─ For: Operators, DevOps, SRE

API_REFERENCE.md
├─ Depends on: SKILL_INTEGRATION_GUIDE.md
├─ Uses: DEVARMOR_ARCHITECTURE.md for context
└─ For: Skill developers, advanced users

MIGRATION_GUIDE.md
├─ Depends on: All other documents
├─ Uses: OPERATOR_RUNBOOK.md, SKILL_INTEGRATION_GUIDE.md
└─ For: Teams adopting DevArmor
```

---

## Quick Reference

### Installation Command
```bash
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core>=1.0.0
```

### Key Concepts
- **3-Layer Architecture**: Installation → Execution → Orchestration
- **4-Level Config**: Code defaults → Master config → Repo config → Environment
- **Event Bus**: Pub/sub for inter-skill coordination
- **State Store**: Shared, queryable state across skills
- **Policy Engine**: YAML-based constraint enforcement
- **Audit Log**: Immutable record of all actions

### Core Operations
```bash
# Skill management
devarmor install skill@version
devarmor skill upgrade skill version1 -> version2
devarmor skill remove skill

# Policy management
devarmor policy deploy ./policy.yaml
devarmor policy test policy-name
devarmor policy show policy-name

# Monitoring
devarmor health
devarmor skill monitor skill-name
devarmor audit-log query "condition"
```

### Common Configuration Files
```
~/.devarmor/config.json                    # Master configuration
~/.devarmor/skills/skill-name.json        # Per-skill master config
.devarmor/skill-name.json                 # Per-skill repo config
.devarmor/policies/policy-name.yaml       # Policies
```

---

## Version Information

- **DevArmor Core Version**: 1.0.0
- **Documentation Version**: 1.0.0
- **Last Updated**: 2026-05-17
- **Status**: Production Ready

---

## Getting Help

**Technical questions?**
- See API_REFERENCE.md for API-specific questions
- See SKILL_INTEGRATION_GUIDE.md for integration questions
- See examples/ for working code

**Operational questions?**
- See OPERATOR_RUNBOOK.md for operations
- See POLICY_CONFIGURATION.md for policies
- See MIGRATION_GUIDE.md for adoption

**Architecture/Design questions?**
- See DEVARMOR_ARCHITECTURE.md for system design
- See examples/ for architecture patterns

---

## Next Steps

1. **Choose your learning path** above based on your role
2. **Start reading** the first document in your path
3. **Try hands-on** examples while reading
4. **Reference** specific documents as needed for your tasks
5. **Iterate** and refine based on your needs

Good luck with DevArmor!
