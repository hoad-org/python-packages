"""Code Generation from Manifest

Generates skill implementations, tests, and configs from manifest declarations.
Supports multiple output formats: Python, Docker, CI/CD, documentation.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import jinja2


@dataclass
class CodegenOutput:
    """Generated code file"""

    path: str
    content: str
    executable: bool = False


class SkillCodeGenerator:
    """Generates skill code from manifest"""

    TEMPLATES = {
        "base_skill.py": """# Generated from manifest: {manifest_name}
# DO NOT EDIT - regenerate using: devarmor codegen {manifest_path}

from typing import Any, Dict, List, Optional
from devarmor import BaseDevArmorSkill, Event, SkillState
import asyncio
import logging

logger = logging.getLogger(__name__)


class {skill_class}(BaseDevArmorSkill):
    \"\"\"Skill: {skill_display_name}

    {skill_description}
    \"\"\"

    NAME = "{skill_name}"
    VERSION = "{skill_version}"

    # Capabilities
    PUBLISHES = {publishes}
    SUBSCRIBES = {subscribes}
    REQUIRED_POLICIES = {required_policies}

    # State management
    STATE_SCHEMA = {state_schema}
    MAINTAINED_STATE = {maintained_state}
    SHARED_STATE = {shared_state}

    # Configuration
    CONFIG_SCHEMA = {config_schema}
    CONFIG_DEFAULTS = {config_defaults}
    CONFIG_SECRETS = {config_secrets}

    # Security
    ISOLATION_LEVEL = "{isolation_level}"
    REQUIRED_PERMISSIONS = {required_permissions}
    AUTHENTICATION_METHODS = {auth_methods}

    async def initialize(self) -> None:
        \"\"\"Initialize skill - called once at startup\"\"\"
        logger.info(f"Initializing {{self.NAME}} v{{self.VERSION}}")
        # TODO: Add skill-specific initialization
        pass

    async def shutdown(self) -> None:
        \"\"\"Shutdown skill - called during graceful shutdown\"\"\"
        logger.info(f"Shutting down {{self.NAME}}")
        # TODO: Add cleanup
        pass

    # ============================================================================
    # Actions (mutable operations)
    # ============================================================================
{action_methods}

    # ============================================================================
    # Queries (read-only operations)
    # ============================================================================
{query_methods}

    # ============================================================================
    # Event Handlers
    # ============================================================================
{event_handlers}

    # ============================================================================
    # Health Checks
    # ============================================================================

    async def health_startup(self) -> bool:
        \"\"\"Startup readiness check\"\"\"
        logger.debug("Running startup health check")
        try:
            # TODO: Implement health check logic
            return True
        except Exception as e:
            logger.error(f"Startup health check failed: {{e}}")
            return False

    async def health_readiness(self) -> bool:
        \"\"\"Readiness check - called frequently\"\"\"
        try:
            # TODO: Implement readiness check
            return True
        except Exception as e:
            logger.debug(f"Readiness check failed: {{e}}")
            return False

    async def health_liveness(self) -> bool:
        \"\"\"Liveness check - skill is still running\"\"\"
        # TODO: Implement liveness check
        return True

    # ============================================================================
    # Internal Helpers
    # ============================================================================

    async def _emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        \"\"\"Emit an event to other skills\"\"\"
        await self.emit(event_name, payload)

    async def _get_state(self, key: str) -> Optional[Dict[str, Any]]:
        \"\"\"Get state from maintained state store\"\"\"
        try:
            return await self.state.get(key)
        except KeyError:
            return None

    async def _set_state(self, key: str, value: Dict[str, Any]) -> None:
        \"\"\"Save state to maintained state store\"\"\"
        await self.state.set(key, value)


# Module-level exports
__all__ = ["{skill_class}"]
""",
        "test_skill.py": """# Generated tests from manifest: {manifest_name}
# Ensure >85% coverage is maintained

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from {skill_module} import {skill_class}


@pytest.fixture
async def skill():
    \"\"\"Fixture providing skill instance\"\"\"
    skill = {skill_class}()
    skill.initialize = AsyncMock()
    skill.shutdown = AsyncMock()
    await skill.initialize()
    yield skill
    await skill.shutdown()


class TestSkillInitialization:
    \"\"\"Test skill lifecycle\"\"\"

    @pytest.mark.asyncio
    async def test_initialize(self, skill):
        assert skill is not None

    @pytest.mark.asyncio
    async def test_publishes(self, skill):
        assert {publishes} == set(skill.PUBLISHES)

    @pytest.mark.asyncio
    async def test_subscribes(self, skill):
        assert {subscribes} == skill.SUBSCRIBES


class TestActions:
    \"\"\"Test action methods\"\"\"
{action_tests}


class TestQueries:
    \"\"\"Test query methods\"\"\"
{query_tests}


class TestEventHandlers:
    \"\"\"Test event subscription handlers\"\"\"
{event_handler_tests}


class TestStateManagement:
    \"\"\"Test state get/set operations\"\"\"

    @pytest.mark.asyncio
    async def test_state_schema(self, skill):
        assert skill.STATE_SCHEMA is not None


class TestConfiguration:
    \"\"\"Test configuration loading\"\"\"

    @pytest.mark.asyncio
    async def test_config_schema(self, skill):
        assert skill.CONFIG_SCHEMA is not None

    @pytest.mark.asyncio
    async def test_config_defaults(self, skill):
        assert skill.CONFIG_DEFAULTS is not None


class TestHealthChecks:
    \"\"\"Test health check probes\"\"\"

    @pytest.mark.asyncio
    async def test_startup_probe(self, skill):
        result = await skill.health_startup()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_readiness_probe(self, skill):
        result = await skill.health_readiness()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_liveness_probe(self, skill):
        result = await skill.health_liveness()
        assert isinstance(result, bool)


class TestSecurity:
    \"\"\"Test security configuration\"\"\"

    @pytest.mark.asyncio
    async def test_isolation_level(self, skill):
        assert skill.ISOLATION_LEVEL in ["inline", "subprocess", "container"]

    @pytest.mark.asyncio
    async def test_required_permissions(self, skill):
        assert isinstance(skill.REQUIRED_PERMISSIONS, list)

    @pytest.mark.asyncio
    async def test_authentication(self, skill):
        assert isinstance(skill.AUTHENTICATION_METHODS, list)


class TestObservability:
    \"\"\"Test metrics and tracing\"\"\"

    @pytest.mark.asyncio
    async def test_metrics_exported(self, skill):
        # Verify metrics are being tracked
        pass

    @pytest.mark.asyncio
    async def test_logging_configured(self, skill):
        import logging
        assert logging.getLogger(f"{{skill.NAME}}").level >= logging.DEBUG
""",
        "dockerfile": """# Generated Dockerfile for {skill_name}:{skill_version}

FROM python:3.11-slim

WORKDIR /skill

# Install dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Copy skill code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD python -c "from {skill_module} import {skill_class}; import asyncio; asyncio.run({skill_class}().health_readiness())"

# Run skill
CMD ["python", "-m", "{skill_module}.main"]
""",
        "github_workflow.yaml": """# Generated GitHub Actions workflow for {skill_name}
# Runs: unit tests, coverage check, build, push

name: {skill_name} CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        run: pytest tests/ -v

      - name: Check coverage ({coverage_threshold}%)
        run: |
          pytest tests/ --cov={skill_module} --cov-fail-under={coverage_threshold}

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: |
          pip install ruff black mypy
          ruff check {skill_module} tests/
          black --check {skill_module} tests/
          mypy {skill_module} --strict

  build:
    needs: [test, lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        if: github.event_name == 'push'
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
""",
        "readme.md": """# {skill_display_name}

{skill_description}

## Features

{features}

## Installation

```bash
pip install {skill_name}
```

## Configuration

Configure via environment variables, config files, or DevArmor control plane:

```yaml
{skill_name}:
  # Configuration goes here
```

See [Configuration](./docs/CONFIGURATION.md) for details.

## Usage

### Actions

{action_docs}

### Queries

{query_docs}

## Security

This skill:
- Runs in: {isolation_level}
- Requires: {required_permissions}
- Authentication: {auth_methods}

See [Security](./docs/SECURITY.md) for details.

## Events

### Publishes

{publishes_docs}

### Subscribes

{subscribes_docs}

## Testing

```bash
pytest tests/ --cov={skill_module}
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)

## License

{license}
""",
    }

    def __init__(self, manifest: Dict[str, Any]):
        """Initialize generator with manifest

        Args:
            manifest: Skill manifest dictionary
        """
        self.manifest = manifest
        self.metadata = manifest.get("metadata", {})
        self.spec = manifest.get("spec", {})

        # Setup Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.DictLoader(self.TEMPLATES),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_all(self) -> List[CodegenOutput]:
        """Generate all output files

        Returns:
            List of generated files with content
        """
        outputs = []

        # Core skill implementation
        outputs.append(self._generate_skill_class())
        outputs.append(self._generate_tests())

        # Configuration
        outputs.append(self._generate_config_file())

        # Deployment
        outputs.append(self._generate_dockerfile())
        outputs.append(self._generate_github_workflow())

        # Documentation
        outputs.append(self._generate_readme())
        outputs.append(self._generate_configuration_docs())
        outputs.append(self._generate_security_docs())

        return outputs

    def _generate_skill_class(self) -> CodegenOutput:
        """Generate main skill class"""
        skill_name = self.metadata.get("name", "skill")
        skill_class = self._to_class_name(skill_name)
        skill_module = self._to_module_name(skill_name)

        # Generate action methods
        action_methods = self._generate_action_stubs()
        query_methods = self._generate_query_stubs()
        event_handlers = self._generate_event_handlers()

        template = self.env.get_template("base_skill.py")
        content = template.render(
            manifest_name=skill_name,
            skill_name=skill_name,
            skill_class=skill_class,
            skill_module=skill_module,
            skill_version=self.metadata.get("version", "0.1.0"),
            skill_display_name=self.metadata.get("displayName", skill_name),
            skill_description=self.metadata.get("description", ""),
            publishes=self._format_list(
                [e["name"] for e in self.spec.get("events", {}).get("publishes", [])]
            ),
            subscribes=self._format_dict(
                {s["name"]: s["handler"] for s in self.spec.get("events", {}).get("subscribes", [])}
            ),
            required_policies=self._format_list(
                self.spec.get("policies", {}).get("requires", [])
            ),
            state_schema=self._format_dict(self.spec.get("state", {}).get("maintains", [])),
            maintained_state=self._format_list(
                [s["name"] for s in self.spec.get("state", {}).get("maintains", [])]
            ),
            shared_state=self._format_list(
                [s["name"] for s in self.spec.get("state", {}).get("shares", [])]
            ),
            config_schema=self._format_dict(self.spec.get("configuration", {}).get("schema", {})),
            config_defaults=self._format_dict(self.spec.get("configuration", {}).get("defaults", {})),
            config_secrets=self._format_list(self.spec.get("configuration", {}).get("secrets", [])),
            isolation_level=self.spec.get("security", {})
            .get("isolation", {})
            .get("processLevel", "subprocess"),
            required_permissions=self._format_list(
                self.spec.get("security", {}).get("permissions", [])
            ),
            auth_methods=self._format_list(
                [a["type"] for a in self.spec.get("security", {}).get("authentication", [])]
            ),
            action_methods=action_methods,
            query_methods=query_methods,
            event_handlers=event_handlers,
        )

        return CodegenOutput(
            path=f"src/{skill_module}/__init__.py",
            content=content,
        )

    def _generate_tests(self) -> CodegenOutput:
        """Generate test file"""
        skill_name = self.metadata.get("name", "skill")
        skill_class = self._to_class_name(skill_name)
        skill_module = self._to_module_name(skill_name)

        template = self.env.get_template("test_skill.py")
        content = template.render(
            manifest_name=skill_name,
            skill_name=skill_name,
            skill_class=skill_class,
            skill_module=skill_module,
            publishes=self._format_list(
                [e["name"] for e in self.spec.get("events", {}).get("publishes", [])]
            ),
            subscribes=self._format_dict(
                {s["name"]: s["handler"] for s in self.spec.get("events", {}).get("subscribes", [])}
            ),
            action_tests=self._generate_action_tests(),
            query_tests=self._generate_query_tests(),
            event_handler_tests=self._generate_event_handler_tests(),
        )

        return CodegenOutput(
            path=f"tests/test_{skill_module}.py",
            content=content,
        )

    def _generate_config_file(self) -> CodegenOutput:
        """Generate default configuration file"""
        skill_name = self.metadata.get("name", "skill")
        defaults = self.spec.get("configuration", {}).get("defaults", {})

        content = "# Default configuration for " + skill_name + "\n\n"
        content += json.dumps(defaults, indent=2)

        return CodegenOutput(
            path=f"{skill_name}.config.json",
            content=content,
        )

    def _generate_dockerfile(self) -> CodegenOutput:
        """Generate Dockerfile"""
        skill_name = self.metadata.get("name", "skill")
        skill_class = self._to_class_name(skill_name)
        skill_module = self._to_module_name(skill_name)

        template = self.env.get_template("dockerfile")
        content = template.render(
            skill_name=skill_name,
            skill_version=self.metadata.get("version", "0.1.0"),
            skill_class=skill_class,
            skill_module=skill_module,
        )

        return CodegenOutput(
            path="Dockerfile",
            content=content,
        )

    def _generate_github_workflow(self) -> CodegenOutput:
        """Generate GitHub Actions workflow"""
        skill_name = self.metadata.get("name", "skill")
        skill_module = self._to_module_name(skill_name)

        template = self.env.get_template("github_workflow.yaml")
        content = template.render(
            skill_name=skill_name,
            skill_module=skill_module,
            coverage_threshold=self.spec.get("testing", {}).get("minimumCoverage", 85),
        )

        return CodegenOutput(
            path=".github/workflows/ci.yaml",
            content=content,
        )

    def _generate_readme(self) -> CodegenOutput:
        """Generate README.md"""
        skill_name = self.metadata.get("name", "skill")
        skill_module = self._to_module_name(skill_name)

        template = self.env.get_template("readme.md")
        content = template.render(
            skill_display_name=self.metadata.get("displayName", skill_name),
            skill_description=self.metadata.get("description", ""),
            skill_name=skill_name,
            skill_module=skill_module,
            isolation_level=self.spec.get("security", {})
            .get("isolation", {})
            .get("processLevel", "subprocess"),
            required_permissions=", ".join(self.spec.get("security", {}).get("permissions", [])),
            auth_methods=", ".join(
                [a["type"] for a in self.spec.get("security", {}).get("authentication", [])]
            ),
            license=self.metadata.get("license", "MIT"),
            features=self._generate_features_list(),
            action_docs=self._generate_action_docs(),
            query_docs=self._generate_query_docs(),
            publishes_docs=self._generate_publishes_docs(),
            subscribes_docs=self._generate_subscribes_docs(),
        )

        return CodegenOutput(
            path="README.md",
            content=content,
        )

    def _generate_configuration_docs(self) -> CodegenOutput:
        """Generate configuration documentation"""
        skill_name = self.metadata.get("name", "skill")
        schema = self.spec.get("configuration", {}).get("schema", {})

        content = f"# {skill_name} Configuration\n\n"
        content += self._schema_to_markdown(schema)

        return CodegenOutput(
            path="docs/CONFIGURATION.md",
            content=content,
        )

    def _generate_security_docs(self) -> CodegenOutput:
        """Generate security documentation"""
        skill_name = self.metadata.get("name", "skill")
        security = self.spec.get("security", {})

        content = f"# {skill_name} Security\n\n"
        content += f"## Isolation: {security.get('isolation', {}).get('processLevel', 'subprocess')}\n\n"

        if perms := security.get("permissions"):
            content += "## Required Permissions\n\n"
            for perm in perms:
                content += f"- `{perm}`\n"
            content += "\n"

        if auth := security.get("authentication"):
            content += "## Authentication Methods\n\n"
            for a in auth:
                content += f"- {a['type']}\n"

        return CodegenOutput(
            path="docs/SECURITY.md",
            content=content,
        )

    # Utility methods
    def _generate_action_stubs(self) -> str:
        """Generate stub methods for actions"""
        lines = []
        for action in self.spec.get("capabilities", {}).get("actions", []):
            name = action.get("name", "action")
            lines.append(f"    async def {name}(self, **kwargs) -> Dict[str, Any]:")
            lines.append(f'        """Implement {name} action"""')
            lines.append("        raise NotImplementedError()")
            lines.append("")
        return "\n".join(lines)

    def _generate_query_stubs(self) -> str:
        """Generate stub methods for queries"""
        lines = []
        for query in self.spec.get("capabilities", {}).get("queries", []):
            name = query.get("name", "query")
            lines.append(f"    async def {name}(self, **kwargs) -> Dict[str, Any]:")
            lines.append(f'        """Implement {name} query"""')
            lines.append("        raise NotImplementedError()")
            lines.append("")
        return "\n".join(lines)

    def _generate_event_handlers(self) -> str:
        """Generate event handler stubs"""
        lines = []
        for sub in self.spec.get("events", {}).get("subscribes", []):
            handler = sub.get("handler", "handle_event")
            event_name = sub.get("name", "event")
            lines.append(f"    async def {handler}(self, event: Event) -> None:")
            lines.append(f'        """Handle {event_name} event"""')
            lines.append("        # TODO: Implement event handling logic")
            lines.append("        pass")
            lines.append("")
        return "\n".join(lines)

    def _generate_action_tests(self) -> str:
        """Generate action test stubs"""
        lines = ["    # TODO: Add action tests"]
        for action in self.spec.get("capabilities", {}).get("actions", []):
            name = action.get("name", "action")
            lines.append(
                f"""
    @pytest.mark.asyncio
    async def test_{name}(self, skill):
        # TODO: Implement test
        pass
"""
            )
        return "\n".join(lines)

    def _generate_query_tests(self) -> str:
        """Generate query test stubs"""
        lines = ["    # TODO: Add query tests"]
        for query in self.spec.get("capabilities", {}).get("queries", []):
            name = query.get("name", "query")
            lines.append(
                f"""
    @pytest.mark.asyncio
    async def test_{name}(self, skill):
        # TODO: Implement test
        pass
"""
            )
        return "\n".join(lines)

    def _generate_event_handler_tests(self) -> str:
        """Generate event handler test stubs"""
        lines = ["    # TODO: Add event handler tests"]
        for sub in self.spec.get("events", {}).get("subscribes", []):
            handler = sub.get("handler", "handle_event")
            lines.append(
                f"""
    @pytest.mark.asyncio
    async def test_{handler}(self, skill):
        # TODO: Implement test
        pass
"""
            )
        return "\n".join(lines)

    def _generate_features_list(self) -> str:
        """Generate features list from manifest"""
        features = []
        for action in self.spec.get("capabilities", {}).get("actions", []):
            features.append(f"- {action.get('description', action.get('name'))}")
        return "\n".join(features)

    def _generate_action_docs(self) -> str:
        """Generate action documentation"""
        docs = []
        for action in self.spec.get("capabilities", {}).get("actions", []):
            docs.append(f"#### `{action['name']}`\n")
            docs.append(f"{action.get('description', 'No description')}\n")
        return "\n".join(docs)

    def _generate_query_docs(self) -> str:
        """Generate query documentation"""
        docs = []
        for query in self.spec.get("capabilities", {}).get("queries", []):
            docs.append(f"#### `{query['name']}`\n")
            docs.append(f"{query.get('description', 'No description')}\n")
        return "\n".join(docs)

    def _generate_publishes_docs(self) -> str:
        """Generate published events documentation"""
        docs = []
        for event in self.spec.get("events", {}).get("publishes", []):
            docs.append(f"- `{event['name']}` - {event.get('description', '')}\n")
        return "\n".join(docs)

    def _generate_subscribes_docs(self) -> str:
        """Generate subscribed events documentation"""
        docs = []
        for sub in self.spec.get("events", {}).get("subscribes", []):
            docs.append(f"- `{sub['name']}` → `{sub.get('handler', 'unknown')}`\n")
        return "\n".join(docs)

    def _schema_to_markdown(self, schema: Dict[str, Any]) -> str:
        """Convert JSON Schema to markdown"""
        md = []
        if props := schema.get("properties"):
            md.append("## Configuration Options\n")
            for name, prop in props.items():
                md.append(f"### `{name}`\n")
                md.append(f"{prop.get('description', '')}\n")
                md.append(f"Type: `{prop.get('type', 'unknown')}`\n\n")
        return "\n".join(md)

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Convert skill name to class name"""
        return "".join(word.capitalize() for word in name.split("-"))

    @staticmethod
    def _to_module_name(name: str) -> str:
        """Convert skill name to module name"""
        return name.replace("-", "_")

    @staticmethod
    def _format_list(items: List[Any]) -> str:
        """Format list for Python code"""
        return "[" + ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in items) + "]"

    @staticmethod
    def _format_dict(data: Dict[str, Any]) -> str:
        """Format dict for Python code"""
        return json.dumps(data, indent=4)
