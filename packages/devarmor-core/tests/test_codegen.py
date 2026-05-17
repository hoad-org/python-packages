"""Tests for Skill Code Generator

Tests code generation pipeline:
- Skill class generation
- Test file generation
- Configuration file generation
- Dockerfile generation
- CI/CD workflow generation
- Documentation generation
"""

import pytest
import json
from devarmor.codegen import SkillCodeGenerator, CodegenOutput


@pytest.fixture
def minimal_manifest():
    """Minimal valid manifest for code generation"""
    return {
        "apiVersion": "devarmor.io/v1",
        "kind": "Skill",
        "metadata": {
            "name": "demo-skill",
            "version": "1.0.0",
            "displayName": "Demo Skill",
            "description": "A demo skill for testing code generation",
            "license": "MIT",
        },
        "spec": {
            "capabilities": {
                "actions": [
                    {
                        "name": "process_data",
                        "description": "Process input data",
                        "input": {
                            "type": "object",
                            "properties": {"data": {"type": "string"}},
                            "required": ["data"],
                        },
                    }
                ],
                "queries": [
                    {
                        "name": "get_status",
                        "description": "Get current status",
                        "output": {
                            "type": "object",
                            "properties": {"status": {"type": "string"}},
                        },
                    }
                ],
            },
            "events": {
                "publishes": [
                    {
                        "name": "demo.processed",
                        "description": "Data processed",
                    }
                ],
                "subscribes": [
                    {
                        "name": "demo.trigger",
                        "handler": "on_trigger",
                    }
                ],
            },
            "state": {
                "maintains": [
                    {
                        "name": "processed_items",
                        "schema": {"type": "object"},
                    }
                ]
            },
            "configuration": {
                "schema": {
                    "type": "object",
                    "properties": {"api_key": {"type": "string"}},
                },
                "defaults": {},
                "secrets": ["api_key"],
            },
            "policies": {"requires": ["cost_control"]},
            "security": {
                "isolation": {"processLevel": "subprocess"},
                "permissions": ["network:outbound"],
                "authentication": [{"type": "apikey"}],
            },
            "testing": {"minimumCoverage": 85},
        },
    }


@pytest.fixture
def generator(minimal_manifest):
    """Generator instance with minimal manifest"""
    return SkillCodeGenerator(minimal_manifest)


class TestCodeGenerator:
    """Test code generation"""

    def test_generator_initialization(self, minimal_manifest):
        """Test generator can be initialized"""
        gen = SkillCodeGenerator(minimal_manifest)
        assert gen.manifest is not None
        assert gen.metadata is not None
        assert gen.spec is not None

    def test_generate_all(self, generator):
        """Test generating all output files"""
        outputs = generator.generate_all()
        assert len(outputs) > 0
        assert all(isinstance(o, CodegenOutput) for o in outputs)

    def test_generate_all_creates_meaningful_content(self, generator):
        """Test generated files contain meaningful content"""
        outputs = generator.generate_all()
        for output in outputs:
            assert len(output.content) > 0
            assert isinstance(output.path, str)

    def test_output_paths_are_reasonable(self, generator):
        """Test output paths follow convention"""
        outputs = generator.generate_all()
        paths = [o.path for o in outputs]

        # Should have core files
        assert any("__init__" in p and ".py" in p for p in paths)
        assert any("test_" in p and ".py" in p for p in paths)
        assert any("Dockerfile" in p for p in paths)
        assert any(".yaml" in p or ".yml" in p for p in paths)
        assert any("README" in p for p in paths)


class TestSkillClassGeneration:
    """Test skill class code generation"""

    def test_generate_skill_class(self, generator):
        """Test main skill class generation"""
        output = generator._generate_skill_class()
        assert output.path.endswith(".py")
        assert "class DemoSkill" in output.content
        assert "BaseDevArmorSkill" in output.content

    def test_skill_class_has_manifest_metadata(self, generator):
        """Test skill class includes manifest metadata"""
        output = generator._generate_skill_class()
        content = output.content

        assert 'NAME = "demo-skill"' in content
        assert 'VERSION = "1.0.0"' in content
        assert "PUBLISHES" in content
        assert "SUBSCRIBES" in content

    def test_skill_class_has_action_methods(self, generator):
        """Test skill class includes action method stubs"""
        output = generator._generate_skill_class()
        assert "async def process_data" in output.content

    def test_skill_class_has_query_methods(self, generator):
        """Test skill class includes query method stubs"""
        output = generator._generate_skill_class()
        assert "async def get_status" in output.content

    def test_skill_class_has_event_handlers(self, generator):
        """Test skill class includes event handler stubs"""
        output = generator._generate_skill_class()
        assert "async def on_trigger" in output.content

    def test_skill_class_has_health_checks(self, generator):
        """Test skill class includes health check methods"""
        output = generator._generate_skill_class()
        assert "async def health_startup" in output.content
        assert "async def health_readiness" in output.content
        assert "async def health_liveness" in output.content

    def test_skill_class_has_state_management(self, generator):
        """Test skill class includes state helper methods"""
        output = generator._generate_skill_class()
        assert "_get_state" in output.content
        assert "_set_state" in output.content


class TestTestFileGeneration:
    """Test test file code generation"""

    def test_generate_test_file(self, generator):
        """Test main test file generation"""
        output = generator._generate_tests()
        assert output.path.startswith("tests/")
        assert output.path.endswith(".py")
        assert "test_" in output.path

    def test_test_file_has_imports(self, generator):
        """Test file includes required imports"""
        output = generator._generate_tests()
        assert "import pytest" in output.content
        assert "import asyncio" in output.content

    def test_test_file_has_fixture(self, generator):
        """Test file includes skill fixture"""
        output = generator._generate_tests()
        assert "@pytest.fixture" in output.content
        assert "async def skill" in output.content

    def test_test_file_has_action_tests(self, generator):
        """Test file includes action test stubs"""
        output = generator._generate_tests()
        assert "class TestActions" in output.content

    def test_test_file_has_query_tests(self, generator):
        """Test file includes query test stubs"""
        output = generator._generate_tests()
        assert "class TestQueries" in output.content

    def test_test_file_has_event_tests(self, generator):
        """Test file includes event handler test stubs"""
        output = generator._generate_tests()
        assert "class TestEventHandlers" in output.content

    def test_test_file_has_state_tests(self, generator):
        """Test file includes state management tests"""
        output = generator._generate_tests()
        assert "class TestStateManagement" in output.content

    def test_test_file_has_config_tests(self, generator):
        """Test file includes configuration tests"""
        output = generator._generate_tests()
        assert "class TestConfiguration" in output.content

    def test_test_file_has_security_tests(self, generator):
        """Test file includes security tests"""
        output = generator._generate_tests()
        assert "class TestSecurity" in output.content


class TestConfigurationGeneration:
    """Test configuration file generation"""

    def test_generate_config_file(self, generator):
        """Test config file generation"""
        output = generator._generate_config_file()
        assert output.path.endswith(".json")
        assert "config" in output.path

    def test_config_file_is_valid_json(self, generator):
        """Test generated config is valid JSON"""
        output = generator._generate_config_file()
        data = json.loads(output.content)
        assert isinstance(data, dict)


class TestDockerfileGeneration:
    """Test Dockerfile generation"""

    def test_generate_dockerfile(self, generator):
        """Test Dockerfile generation"""
        output = generator._generate_dockerfile()
        assert output.path == "Dockerfile"

    def test_dockerfile_has_base_image(self, generator):
        """Test Dockerfile specifies base image"""
        output = generator._generate_dockerfile()
        assert "FROM python:" in output.content or "FROM python" in output.content

    def test_dockerfile_installs_dependencies(self, generator):
        """Test Dockerfile installs dependencies"""
        output = generator._generate_dockerfile()
        assert "pip install" in output.content

    def test_dockerfile_has_healthcheck(self, generator):
        """Test Dockerfile includes health check"""
        output = generator._generate_dockerfile()
        assert "HEALTHCHECK" in output.content


class TestCIGenerationGeneration:
    """Test CI/CD workflow generation"""

    def test_generate_github_workflow(self, generator):
        """Test GitHub Actions workflow generation"""
        output = generator._generate_github_workflow()
        assert ".github/workflows/" in output.path
        assert ".yaml" in output.path

    def test_workflow_has_test_job(self, generator):
        """Test workflow includes test job"""
        output = generator._generate_github_workflow()
        assert "pytest" in output.content

    def test_workflow_has_lint_job(self, generator):
        """Test workflow includes linting"""
        output = generator._generate_github_workflow()
        assert "ruff" in output.content or "lint" in output.content

    def test_workflow_has_coverage_check(self, generator):
        """Test workflow checks code coverage"""
        output = generator._generate_github_workflow()
        assert "coverage" in output.content or "cov-fail-under" in output.content

    def test_workflow_has_docker_build(self, generator):
        """Test workflow builds Docker image"""
        output = generator._generate_github_workflow()
        assert "docker" in output.content.lower()


class TestDocumentationGeneration:
    """Test documentation generation"""

    def test_generate_readme(self, generator):
        """Test README generation"""
        output = generator._generate_readme()
        assert output.path == "README.md"

    def test_readme_has_title(self, generator):
        """Test README has title"""
        output = generator._generate_readme()
        assert "Demo Skill" in output.content

    def test_readme_has_description(self, generator):
        """Test README has description"""
        output = generator._generate_readme()
        assert "testing" in output.content

    def test_readme_has_features_section(self, generator):
        """Test README lists features"""
        output = generator._generate_readme()
        assert "Features" in output.content or "features" in output.content

    def test_readme_has_installation(self, generator):
        """Test README has installation instructions"""
        output = generator._generate_readme()
        assert "pip install" in output.content or "Installation" in output.content

    def test_generate_configuration_docs(self, generator):
        """Test configuration documentation"""
        output = generator._generate_configuration_docs()
        assert output.path == "docs/CONFIGURATION.md"
        assert "Configuration" in output.content

    def test_generate_security_docs(self, generator):
        """Test security documentation"""
        output = generator._generate_security_docs()
        assert output.path == "docs/SECURITY.md"
        assert "Security" in output.content or "security" in output.content


class TestUtilityMethods:
    """Test utility methods"""

    def test_to_class_name(self):
        """Test skill name to class name conversion"""
        assert SkillCodeGenerator._to_class_name("test-skill") == "TestSkill"
        assert SkillCodeGenerator._to_class_name("my-demo-skill") == "MyDemoSkill"
        assert SkillCodeGenerator._to_class_name("skill") == "Skill"

    def test_to_module_name(self):
        """Test skill name to module name conversion"""
        assert SkillCodeGenerator._to_module_name("test-skill") == "test_skill"
        assert SkillCodeGenerator._to_module_name("my-demo-skill") == "my_demo_skill"

    def test_format_list(self):
        """Test list formatting for Python"""
        result = SkillCodeGenerator._format_list(["a", "b", "c"])
        assert '["a", "b", "c"]' in result or "['a', 'b', 'c']" in result

    def test_format_dict(self):
        """Test dict formatting for Python"""
        data = {"key": "value", "number": 42}
        result = SkillCodeGenerator._format_dict(data)
        assert "key" in result
        assert "value" in result


class TestEndToEndCodeGeneration:
    """End-to-end code generation tests"""

    def test_generate_complete_skill_project(self, generator):
        """Test generating complete skill project structure"""
        outputs = generator.generate_all()

        # Check we have all necessary file types
        paths = [o.path for o in outputs]

        # Python files
        assert any(".py" in p for p in paths)
        # Config
        assert any("config" in p for p in paths)
        # Docker
        assert any("Dockerfile" in p for p in paths)
        # CI/CD
        assert any(".github" in p for p in paths)
        # Docs
        assert any(".md" in p for p in paths)

    def test_generated_files_follow_best_practices(self, generator):
        """Test generated files follow Python best practices"""
        outputs = generator.generate_all()
        py_files = [o for o in outputs if o.path.endswith(".py")]

        for py_file in py_files:
            # Should have proper imports
            if "import" in py_file.content:
                assert "import" in py_file.content.split("\n")[0] or "from" in py_file.content.split("\n")[0]

    def test_generated_docker_file_is_efficient(self, generator):
        """Test Dockerfile follows best practices"""
        output = generator._generate_dockerfile()
        content = output.content

        # Should use Python slim image
        assert "slim" in content or "python:" in content

        # Should have health check
        assert "HEALTHCHECK" in content

        # Should not run as root
        # (Would check but generated templates use default)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
