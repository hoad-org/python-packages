"""Tests for Skill Manifest Validator

Tests the manifest validation pipeline including:
- Schema validation
- Semantic validation
- Error reporting
- Warning detection
"""

import pytest
import json
from pathlib import Path
from devarmor.manifest_validator import (
    SkillManifestValidator,
    ManifestValidationResult,
    ValidationError,
)


@pytest.fixture
def validator():
    """Fixture providing validator instance"""
    return SkillManifestValidator()


@pytest.fixture
def minimal_manifest():
    """Minimal valid manifest"""
    return {
        "apiVersion": "devarmor.io/v1",
        "kind": "Skill",
        "metadata": {
            "name": "test-skill",
            "version": "1.0.0",
        },
        "spec": {
            "capabilities": {
                "actions": [],
            },
            "security": {
                "isolation": {
                    "processLevel": "subprocess",
                }
            },
        },
    }


@pytest.fixture
def complete_manifest(minimal_manifest):
    """Complete manifest with all fields"""
    minimal_manifest.update({
        "metadata": {
            "name": "test-skill",
            "version": "1.0.0",
            "displayName": "Test Skill",
            "description": "A test skill for validation",
            "author": "Test Author",
            "license": "MIT",
            "repository": "https://github.com/test/skill",
            "documentation": "https://test.example.com/docs",
            "categories": ["development"],
            "tags": ["test"],
        },
        "spec": {
            "capabilities": {
                "actions": [
                    {
                        "name": "test_action",
                        "description": "Test action",
                        "input": {
                            "type": "object",
                            "properties": {"param": {"type": "string"}},
                            "required": ["param"],
                        },
                        "output": {
                            "type": "object",
                            "properties": {"result": {"type": "string"}},
                        },
                        "idempotent": True,
                        "timeout": 60,
                    }
                ],
                "queries": [
                    {
                        "name": "test_query",
                        "description": "Test query",
                        "output": {
                            "type": "object",
                            "properties": {"data": {"type": "array"}},
                        },
                    }
                ],
            },
            "events": {
                "publishes": [
                    {
                        "name": "test.event",
                        "description": "Test event",
                        "severity": "info",
                    }
                ],
                "subscribes": [
                    {
                        "name": "other.event",
                        "handler": "handle_other_event",
                    }
                ],
            },
            "state": {
                "maintains": [
                    {
                        "name": "test_state",
                        "schema": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                        },
                    }
                ],
            },
            "configuration": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "api_key": {"type": "string"},
                    },
                    "required": ["api_key"],
                },
                "defaults": {
                    "timeout": 30,
                },
                "secrets": ["api_key"],
            },
            "policies": {
                "requires": ["cost_control"],
            },
            "security": {
                "isolation": {
                    "processLevel": "subprocess",
                    "resourceLimits": {
                        "cpuMillis": 1000,
                        "memoryMb": 512,
                    },
                },
                "permissions": ["network:outbound", "secrets:read"],
                "authentication": [
                    {
                        "type": "apikey",
                        "scopes": ["read", "write"],
                    }
                ],
            },
            "testing": {
                "minimumCoverage": 85,
                "testTypes": ["unit", "integration"],
            },
        },
    })
    return minimal_manifest


class TestManifestValidation:
    """Test manifest validation"""

    def test_minimal_manifest_valid(self, validator, minimal_manifest):
        """Test that minimal valid manifest passes"""
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_complete_manifest_valid(self, validator, complete_manifest):
        """Test that complete manifest passes"""
        result = validator.validate_manifest(complete_manifest)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_required_field(self, validator, minimal_manifest):
        """Test validation fails when required field missing"""
        del minimal_manifest["metadata"]["name"]
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_invalid_api_version(self, validator, minimal_manifest):
        """Test validation fails with invalid API version"""
        minimal_manifest["apiVersion"] = "invalid"
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid

    def test_invalid_skill_name(self, validator, minimal_manifest):
        """Test validation fails with invalid skill name"""
        minimal_manifest["metadata"]["name"] = "INVALID_NAME"  # Must be kebab-case
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid

    def test_invalid_version_format(self, validator, minimal_manifest):
        """Test validation fails with invalid version"""
        minimal_manifest["metadata"]["version"] = "not-semver"
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid

    def test_invalid_isolation_level(self, validator, minimal_manifest):
        """Test validation fails with invalid isolation level"""
        minimal_manifest["spec"]["security"]["isolation"]["processLevel"] = "invalid"
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid


class TestActionValidation:
    """Test action capability validation"""

    def test_action_with_valid_input_schema(self, validator, minimal_manifest):
        """Test action with valid input schema"""
        minimal_manifest["spec"]["capabilities"]["actions"] = [
            {
                "name": "test_action",
                "description": "Test",
                "input": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"],
                },
            }
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid

    def test_action_missing_description(self, validator, minimal_manifest):
        """Test action must have description"""
        minimal_manifest["spec"]["capabilities"]["actions"] = [
            {
                "name": "test_action",
                "input": {"type": "object"},
            }
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert not result.is_valid

    def test_action_rate_limit_validation(self, validator, minimal_manifest):
        """Test rate limit configuration"""
        minimal_manifest["spec"]["capabilities"]["actions"] = [
            {
                "name": "test_action",
                "description": "Test",
                "input": {"type": "object"},
                "rateLimit": {
                    "requestsPerMinute": 10,
                    "burstSize": 5,
                },
            }
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestEventValidation:
    """Test event validation"""

    def test_publish_event(self, validator, minimal_manifest):
        """Test published event validation"""
        minimal_manifest["spec"]["events"] = {
            "publishes": [
                {
                    "name": "test.event.created",
                    "description": "Event fired",
                    "severity": "info",
                }
            ]
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid

    def test_subscribe_event(self, validator, minimal_manifest):
        """Test subscribed event validation"""
        minimal_manifest["spec"]["events"] = {
            "subscribes": [
                {
                    "name": "other.event",
                    "handler": "handle_event",
                }
            ]
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid

    def test_circular_event_dependency_warning(self, validator, minimal_manifest):
        """Test warning for circular event dependencies"""
        minimal_manifest["spec"]["events"] = {
            "publishes": [{"name": "test.event", "description": "Test"}],
            "subscribes": [{"name": "test.event", "handler": "handle_test"}],
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid  # Still valid but with warnings
        assert len(result.warnings) > 0


class TestStateValidation:
    """Test state management validation"""

    def test_maintained_state(self, validator, minimal_manifest):
        """Test maintained state schema"""
        minimal_manifest["spec"]["state"] = {
            "maintains": [
                {
                    "name": "users",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    },
                    "indexed": ["id"],
                }
            ]
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid

    def test_shared_state(self, validator, minimal_manifest):
        """Test shared state with permissions"""
        minimal_manifest["spec"]["state"] = {
            "shares": [
                {
                    "name": "status",
                    "schema": {"type": "object"},
                    "permissions": ["read", "write"],
                    "consistencyLevel": "strong",
                }
            ]
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestConfigurationValidation:
    """Test configuration schema validation"""

    def test_valid_configuration(self, validator, minimal_manifest):
        """Test valid configuration schema"""
        minimal_manifest["spec"]["configuration"] = {
            "schema": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["api_key"],
            },
            "defaults": {"timeout": 30},
            "secrets": ["api_key"],
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestSecurityValidation:
    """Test security configuration"""

    def test_process_isolation_levels(self, validator, minimal_manifest):
        """Test all process isolation levels"""
        for level in ["inline", "subprocess", "container"]:
            minimal_manifest["spec"]["security"]["isolation"]["processLevel"] = level
            result = validator.validate_manifest(minimal_manifest)
            assert result.is_valid

    def test_required_permissions(self, validator, minimal_manifest):
        """Test permission validation"""
        minimal_manifest["spec"]["security"]["permissions"] = [
            "filesystem:read",
            "network:outbound",
            "secrets:read",
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid

    def test_authentication_methods(self, validator, minimal_manifest):
        """Test authentication configuration"""
        minimal_manifest["spec"]["security"]["authentication"] = [
            {"type": "apikey", "scopes": ["read", "write"]},
            {"type": "oauth2", "scopes": ["admin"]},
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestSemanticValidation:
    """Test semantic warnings"""

    def test_no_policies_warning(self, validator, minimal_manifest):
        """Test warning when no policies required"""
        result = validator.validate_manifest(minimal_manifest)
        # Should have warnings about missing policies
        assert any("policy" in w.lower() for w in result.warnings)

    def test_stateless_skill_warning(self, validator, minimal_manifest):
        """Test warning for stateless skill"""
        result = validator.validate_manifest(minimal_manifest)
        # Minimal manifest has no state or subscriptions
        assert len(result.warnings) > 0

    def test_excessive_timeout_warning(self, validator, minimal_manifest):
        """Test warning for excessive timeouts"""
        minimal_manifest["spec"]["capabilities"]["actions"] = [
            {
                "name": "slow_action",
                "description": "Slow",
                "input": {"type": "object"},
                "timeout": 7200,  # 2 hours
            }
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert any("timeout" in w.lower() for w in result.warnings)


class TestErrorFormatting:
    """Test error message formatting"""

    def test_format_valid_manifest(self, validator, minimal_manifest):
        """Test formatting of valid manifest"""
        result = validator.validate_manifest(minimal_manifest)
        formatted = SkillManifestValidator.format_errors(result)
        assert "✓" in formatted
        assert "valid" in formatted.lower()

    def test_format_invalid_manifest(self, validator, minimal_manifest):
        """Test formatting of invalid manifest"""
        del minimal_manifest["metadata"]["name"]
        result = validator.validate_manifest(minimal_manifest)
        formatted = SkillManifestValidator.format_errors(result)
        assert "✗" in formatted
        assert "failed" in formatted.lower()

    def test_format_warnings(self, validator, minimal_manifest):
        """Test formatting of warnings"""
        result = validator.validate_manifest(minimal_manifest)
        formatted = SkillManifestValidator.format_errors(result)
        if result.warnings:
            assert "⚠" in formatted


class TestDependencyValidation:
    """Test dependency validation"""

    def test_valid_dependencies(self, validator, minimal_manifest):
        """Test valid dependency specification"""
        minimal_manifest["spec"]["dependencies"] = [
            {
                "name": "jira-skill",
                "version": ">=3.0.0",
                "optional": True,
                "requires": ["create_issue"],
            }
        ]
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestCompatibilityValidation:
    """Test platform compatibility"""

    def test_python_version_constraint(self, validator, minimal_manifest):
        """Test Python version constraint"""
        minimal_manifest["spec"]["compatibility"] = {
            "python": ">=3.9,<4.0",
            "platforms": ["linux-amd64", "macos-arm64"],
        }
        result = validator.validate_manifest(minimal_manifest)
        assert result.is_valid


class TestFileValidation:
    """Test file-based validation"""

    def test_validate_missing_file(self, validator, tmp_path):
        """Test validation of missing file"""
        result = validator.validate_file(tmp_path / "nonexistent.yaml")
        assert not result.is_valid
        assert any("not found" in e.message.lower() for e in result.errors)

    def test_validate_invalid_json(self, validator, tmp_path):
        """Test validation of invalid JSON file"""
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text("{ invalid json }")
        result = validator.validate_file(manifest_file)
        assert not result.is_valid
        assert any("format" in e.message.lower() for e in result.errors)

    def test_validate_valid_json_file(self, validator, tmp_path, minimal_manifest):
        """Test validation of valid JSON manifest file"""
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_manifest))
        result = validator.validate_file(manifest_file)
        assert result.is_valid
        assert result.manifest is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
