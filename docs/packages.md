# Available Packages

This page documents all Python packages available from the Hoad Python Packages repository.

**Repository:** https://github.com/rhyscraig/python-packages  
**Index URL:** https://hoad-org.github.io/python-packages

## Installation

Install packages using pip with the custom index:

```bash
# Install a specific package
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core

# Or multiple packages
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core claude-github-skill

# Add to requirements.txt
-i https://hoad-org.github.io/python-packages
devarmor-core>=0.1.0
```

## Packages

### DevArmor Core

**Version:** 0.1.0  
**Python:** >=3.9  
**Status:** Production Ready  
**Repository:** https://github.com/rhyscraig/python-packages

Enterprise control plane for Claude skills with policy-driven enforcement, compliance automation, and cross-skill coordination.

#### Key Features

- **3-Layer Architecture:** Installation, Execution, Orchestration
- **4-Level Configuration Hierarchy:** Code defaults → Master config → Repo config → Environment variables
- **Event-Driven Coordination:** Pub/sub event bus for inter-skill communication
- **Shared State Store:** Cross-skill state management with persistence
- **Policy Engine:** Cost control, security, compliance policies
- **Audit Logging:** Complete audit trail of all actions
- **Automatic Guardrails:** Rate limiting, cost tracking, permission checks
- **Zero-Downtime Upgrades:** Update skills without service interruption
- **Full Rollback:** Automatic and manual rollback capability

#### Installation

```bash
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core>=0.1.0
```

Or use the DevArmor CLI installer:

```bash
curl -fsSL https://raw.githubusercontent.com/rhyscraig/python-packages/main/bin/devarmor | python3
devarmor install
```

#### Quick Start

```python
from devarmor import get_devarmor

# Initialize DevArmor
devarmor = await get_devarmor()

# Publish skill events
await devarmor.event_bus.publish("skill.action.completed", {
    "skill": "my-skill",
    "action": "create_resource",
    "status": "success"
})

# Query shared state
counter = await devarmor.state_store.get("action_counter")

# Evaluate policies
decision = await devarmor.policy_engine.evaluate({
    "user": "alice@example.com",
    "action": "create_resource",
    "resource_cost": 100  # dollars
})

if decision.allowed:
    # Proceed with action
    await execute_action()
else:
    # Action denied by policy
    await log_policy_violation(decision.reason)
```

#### Documentation

- **[Architecture Guide](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/DEVARMOR_ARCHITECTURE.md)** - System design and control flows
- **[Skill Integration Guide](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/SKILL_INTEGRATION_GUIDE.md)** - How to integrate your skill
- **[Policy Configuration](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/POLICY_CONFIGURATION.md)** - Write and manage policies
- **[Operator Runbook](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/OPERATOR_RUNBOOK.md)** - Deploy and operate DevArmor
- **[API Reference](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/API_REFERENCE.md)** - Complete Python API
- **[Migration Guide](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/docs/MIGRATION_GUIDE.md)** - Transition existing skills

#### Examples

See the [examples/](https://github.com/rhyscraig/python-packages/blob/main/packages/devarmor-core/examples/) directory for working examples:
- Terrorgem skill integration
- Policy enforcement patterns
- Event handling workflows
- State coordination across skills

#### Requirements

- Python >= 3.9
- pydantic >= 1.9.0
- pyyaml >= 6.0

---

### Claude GitHub Skill

**Version:** 1.0.0  
**Python:** >=3.12  
**Status:** Production Ready  
**Repository:** https://github.com/hoad-org/claude-github-skill

Enterprise-grade GitHub governance engine for enforcing organizational standards, automating naming conventions, and managing repositories.

#### Features

- Convention enforcement (branches, repos, PRs)
- Standards compliance auditing
- Smart auto-fix suggestions
- Security gates for dangerous operations
- Repository cataloging

#### Installation

```bash
pip install --index-url https://hoad-org.github.io/python-packages claude-github-skill
```

#### Documentation

See the [GitHub Skill README](https://github.com/hoad-org/claude-github-skill#readme) for complete documentation.

---

## Publishing a Package

To publish a new package to this repository:

1. **Create a semantic version tag** in your package repository:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **The publish workflow automatically:**
   - Builds the package
   - Runs security and quality checks (coverage >85%, linting, type checking)
   - Publishes to this repository
   - Generates documentation

3. **Package metadata** is stored in `packages/<name>/metadata.json`:
   ```json
   {
     "name": "package-name",
     "version": "1.0.0",
     "description": "Package description",
     "python_requires": ">=3.9",
     "repository": "https://github.com/org/repo",
     "published_at": "2026-05-17T12:00:00Z",
     "dependencies": ["pydantic>=1.9.0"]
   }
   ```

## Repository Structure

```
python-packages/
├── packages/
│   ├── devarmor-core/
│   │   ├── src/devarmor/
│   │   ├── tests/
│   │   ├── docs/
│   │   ├── pyproject.toml
│   │   └── metadata.json
│   └── claude-github-skill/
├── docs/
│   ├── index.md
│   └── packages.md (this file)
├── bin/
│   └── devarmor (CLI installer)
├── .github/
│   └── workflows/
│       ├── build-index.yml
│       └── pip-index.yml
├── Makefile
├── README.md
└── pyproject.toml
```

## Quality Standards

All published packages undergo:

- **Security Scanning:** bandit, pip-audit
- **Code Quality:** ruff (linting), black (formatting)
- **Type Checking:** mypy --strict
- **Test Coverage:** >85% required (pytest)
- **Dependency Audits:** pip-audit for vulnerabilities

Only packages passing all checks are published.

## Maintenance

### For Package Maintainers

Each package provides a local Makefile with targets for development:

```bash
cd packages/devarmor-core

# Run tests
make test

# Check coverage
make coverage

# Quality checks
make check

# Security scan
make security

# Build wheel
make build

# Clean artifacts
make clean
```

### For Repository Maintainers

The root Makefile provides aggregate targets:

```bash
# Test all packages
make test

# Coverage for all packages
make coverage

# Quality checks for all packages
make check

# Build all wheels
make build-wheels

# Clean all artifacts
make clean
```

## Contributing

To contribute a new package:

1. Create a new directory under `packages/`
2. Include a `pyproject.toml` with proper metadata
3. Write tests (minimum 85% coverage)
4. Create a `metadata.json` with package information
5. Ensure all quality checks pass
6. Submit a pull request

## Support

- **Issues:** Report bugs on the [GitHub repository](https://github.com/rhyscraig/python-packages/issues)
- **Documentation:** See individual package documentation
- **Security:** Report security issues to security@hoad.org

## License

Each package maintains its own license. See individual package repositories.

---

*This page is automatically generated. Last updated: [AUTO_UPDATE]*
