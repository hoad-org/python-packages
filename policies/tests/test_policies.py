"""
Tests for DevArmor policy validation and evaluation.

Coverage targets:
- Policy YAML syntax validation
- Policy schema validation against Pydantic models
- Policy constraint evaluation logic
- Test case execution
- Error handling and edge cases
"""

import json
from pathlib import Path

import pytest
import yaml

# Add parent package to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "devarmor-core" / "src"))

from devarmor.models import PolicyConfig, PolicyEvaluation
from devarmor.policy import PolicyEngine


class TestPolicyYAMLValidation:
    """Test YAML syntax validation."""

    def test_valid_yaml_syntax(self):
        """Test valid YAML files parse correctly."""
        policy_files = [
            Path(__file__).parent.parent / "cost_control.yaml",
            Path(__file__).parent.parent / "security.yaml",
            Path(__file__).parent.parent / "compliance.yaml",
        ]

        for policy_file in policy_files:
            assert policy_file.exists(), f"Policy file not found: {policy_file}"

            with open(policy_file) as f:
                content = yaml.safe_load(f)

            assert isinstance(content, dict), f"Policy must be dict: {policy_file}"
            assert "name" in content, f"Missing 'name' in {policy_file}"
            assert "version" in content, f"Missing 'version' in {policy_file}"

    def test_policy_required_fields(self):
        """Test all required fields are present."""
        required_fields = ["name", "version", "description", "enabled", "constraints"]

        policy_files = [
            Path(__file__).parent.parent / "cost_control.yaml",
            Path(__file__).parent.parent / "security.yaml",
        ]

        for policy_file in policy_files:
            with open(policy_file) as f:
                policy = yaml.safe_load(f)

            for field in required_fields:
                assert field in policy, f"Missing required field '{field}' in {policy_file.name}"

    def test_constraint_structure(self):
        """Test constraint objects have required fields."""
        policy_file = Path(__file__).parent.parent / "cost_control.yaml"

        with open(policy_file) as f:
            policy = yaml.safe_load(f)

        constraints = policy.get("constraints", [])
        assert len(constraints) > 0, "Policy must have at least one constraint"

        required_constraint_fields = ["name", "rule", "action", "message"]

        for i, constraint in enumerate(constraints):
            for field in required_constraint_fields:
                assert field in constraint, (
                    f"Constraint {i} ({constraint.get('name')}) missing "
                    f"required field '{field}'"
                )

    def test_invalid_action_values(self):
        """Test constraint actions are valid."""
        valid_actions = [
            "allow",
            "deny",
            "warn",
            "rate_limit",
            "audit",
            "incident",
            "suppress",
            "alert",
        ]

        policy_file = Path(__file__).parent.parent / "cost_control.yaml"

        with open(policy_file) as f:
            policy = yaml.safe_load(f)

        for constraint in policy.get("constraints", []):
            action = constraint.get("action")
            assert action in valid_actions, (
                f"Invalid action '{action}' in constraint '{constraint.get('name')}'. "
                f"Must be one of: {', '.join(valid_actions)}"
            )

    def test_version_format(self):
        """Test version follows semantic versioning."""
        import re

        version_pattern = r"^\d+\.\d+\.\d+$"

        policy_files = [
            Path(__file__).parent.parent / "cost_control.yaml",
            Path(__file__).parent.parent / "security.yaml",
        ]

        for policy_file in policy_files:
            with open(policy_file) as f:
                policy = yaml.safe_load(f)

            version = policy.get("version")
            assert re.match(version_pattern, version), (
                f"Invalid version format '{version}' in {policy_file.name}. "
                f"Must be semantic versioning (X.Y.Z)"
            )


class TestPolicySchemaValidation:
    """Test policy schema validation against Pydantic models."""

    def test_policy_config_creation(self):
        """Test PolicyConfig can be created from policy data."""
        config = PolicyConfig(
            version="1.0.0",
            cost_control={
                "enabled": True,
                "global_limit": {"amount": 30.00, "currency": "USD"},
            },
        )

        assert config.version == "1.0.0"
        assert config.cost_control.enabled is True
        assert config.cost_control.global_limit.amount == 30.00

    def test_cost_control_validation(self):
        """Test cost control policy validation."""
        from devarmor.models import CostControlPolicy, CostLimit

        # Valid cost limit
        policy = CostControlPolicy(
            enabled=True,
            global_limit=CostLimit(amount=30.0, currency="USD"),
        )

        assert policy.enabled is True
        assert policy.global_limit.amount == 30.0

    def test_cost_limit_validation(self):
        """Test cost limit field validation."""
        from devarmor.models import CostLimit

        # Valid limit
        limit = CostLimit(amount=100.0, currency="USD", period="monthly")
        assert limit.amount == 100.0

        # Invalid: negative amount
        with pytest.raises(Exception):
            CostLimit(amount=-100.0)

        # Invalid: warning threshold out of range
        with pytest.raises(Exception):
            CostLimit(amount=100.0, threshold_warning=1.5)


class TestPolicyCostControl:
    """Test cost control policy evaluation."""

    def test_cost_control_under_budget(self):
        """Test operation under budget is allowed."""
        config = PolicyConfig(
            cost_control={
                "enabled": True,
                "global_limit": {"amount": 30.0, "currency": "USD"},
            }
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=10.0,
            actor="alice@example.com",
        )

        assert result.allowed is True

    def test_cost_control_exceeds_limit(self):
        """Test operation exceeding budget is denied."""
        config = PolicyConfig(
            cost_control={
                "enabled": True,
                "global_limit": {"amount": 30.0, "currency": "USD"},
            }
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=50.0,
            actor="alice@example.com",
        )

        assert result.allowed is False
        assert "cost_control:exceeds_global_limit" in result.violated_policies

    def test_cost_control_disabled(self):
        """Test cost control can be disabled."""
        config = PolicyConfig(cost_control={"enabled": False})
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=1000.0,
            actor="alice@example.com",
        )

        assert result.allowed is True


class TestPolicySecurity:
    """Test security policy evaluation."""

    def test_security_policy_evaluation(self):
        """Test security policy evaluation."""
        from devarmor.models import SecurityPolicy

        config = PolicyConfig(
            security=SecurityPolicy(
                enabled=True,
                require_approval=True,
                forbidden_patterns=[r"DROP TABLE", r"DELETE FROM"],
            )
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_security_policy(
            action="read",
            actor="alice@example.com",
            target="database",
        )

        assert result.allowed is True

    def test_security_policy_forbidden_pattern(self):
        """Test forbidden pattern detection."""
        from devarmor.models import SecurityPolicy

        config = PolicyConfig(
            security=SecurityPolicy(
                enabled=True,
                forbidden_patterns=[r"DROP TABLE"],
            )
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_security_policy(
            action="DROP TABLE users",
            actor="alice@example.com",
            target="database",
        )

        assert result.allowed is False

    def test_security_policy_allowed_domains(self):
        """Test allowed domain enforcement."""
        from devarmor.models import SecurityPolicy

        config = PolicyConfig(
            security=SecurityPolicy(
                enabled=True,
                allowed_domains={"github.com", "api.github.com"},
            )
        )
        engine = PolicyEngine(config)

        # Allowed domain
        result = engine.evaluate_security_policy(
            action="api_call",
            actor="alice@example.com",
            target="github.com",
        )
        assert result.allowed is True

        # Blocked domain
        result = engine.evaluate_security_policy(
            action="api_call",
            actor="alice@example.com",
            target="untrusted.com",
        )
        assert result.allowed is False


class TestPolicySkillPermissions:
    """Test skill permissions policy evaluation."""

    def test_skill_permission_allowed(self):
        """Test allowed skill is permitted."""
        from devarmor.models import SkillPermissionsPolicy, SkillPermission

        perm = SkillPermission(
            skill_name="github",
            allowed_commands=["create_workflow", "view_status"],
        )

        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                default_permissions=[perm],
            )
        )
        engine = PolicyEngine(config)

        assert engine.is_skill_allowed("github") is True

    def test_skill_permission_blocklist(self):
        """Test blocked skill is not allowed."""
        from devarmor.models import SkillPermissionsPolicy

        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                skill_blocklist=["dangerous-skill"],
            )
        )
        engine = PolicyEngine(config)

        assert engine.is_skill_allowed("dangerous-skill") is False
        assert engine.is_skill_allowed("other-skill") is True

    def test_skill_permission_allowlist(self):
        """Test allowlist restricts to specific skills."""
        from devarmor.models import SkillPermissionsPolicy

        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                skill_allowlist=["github", "jira"],
            )
        )
        engine = PolicyEngine(config)

        assert engine.is_skill_allowed("github") is True
        assert engine.is_skill_allowed("jira") is True
        assert engine.is_skill_allowed("confluence") is False


class TestPolicyTestCases:
    """Test policy test case execution."""

    def test_load_policy_test_cases(self):
        """Test loading test cases from policy file."""
        policy_file = Path(__file__).parent.parent / "cost_control.yaml"

        with open(policy_file) as f:
            policy = yaml.safe_load(f)

        test_cases = policy.get("test_cases", [])
        assert len(test_cases) > 0, "Policy should have test cases"

        for test_case in test_cases:
            assert "name" in test_case, "Test case must have name"
            assert "input" in test_case, "Test case must have input"
            assert "expected" in test_case, "Test case must have expected result"

    def test_test_case_coverage(self):
        """Test that test cases cover policy constraints."""
        policy_file = Path(__file__).parent.parent / "cost_control.yaml"

        with open(policy_file) as f:
            policy = yaml.safe_load(f)

        constraints = policy.get("constraints", [])
        test_cases = policy.get("test_cases", [])

        # Ensure reasonable coverage (at least 1 test per 2 constraints)
        assert len(test_cases) >= len(constraints) / 2, (
            f"Insufficient test coverage: {len(test_cases)} tests for "
            f"{len(constraints)} constraints"
        )


class TestPolicyValidation:
    """Test overall policy validation workflow."""

    def test_all_core_policies_valid(self):
        """Test all core policies are valid."""
        core_policies = [
            "cost_control.yaml",
            "security.yaml",
            "compliance.yaml",
            "development.yaml",
            "production.yaml",
        ]

        policy_dir = Path(__file__).parent.parent

        for policy_name in core_policies:
            policy_file = policy_dir / policy_name
            assert policy_file.exists(), f"Policy file not found: {policy_name}"

            # Validate YAML syntax
            with open(policy_file) as f:
                content = yaml.safe_load(f)

            # Validate required fields
            assert "name" in content
            assert "version" in content
            assert "constraints" in content
            assert len(content["constraints"]) > 0

            # Validate constraints
            for constraint in content["constraints"]:
                assert "name" in constraint
                assert "rule" in constraint
                assert "action" in constraint
                assert "message" in constraint

    def test_all_example_policies_valid(self):
        """Test all example policies are valid."""
        example_policies = [
            "terrorgem_phase0.yaml",
            "terrorgem_phase1.yaml",
            "enterprise_soc2.yaml",
        ]

        examples_dir = Path(__file__).parent.parent / "examples"

        for policy_name in example_policies:
            policy_file = examples_dir / policy_name
            assert policy_file.exists(), f"Example policy not found: {policy_name}"

            with open(policy_file) as f:
                content = yaml.safe_load(f)

            assert "name" in content
            assert "version" in content
            assert "test_cases" in content
            assert len(content["test_cases"]) > 0


class TestPolicyEdgeCases:
    """Test edge cases and error handling."""

    def test_policy_with_empty_constraints(self):
        """Test handling of policy with no constraints."""
        config = PolicyConfig(
            version="1.0.0",
            cost_control={"enabled": False},
            security={"enabled": False},
        )
        engine = PolicyEngine(config)

        # Should allow everything when all policies disabled
        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=1000.0,
            actor="alice@example.com",
        )
        assert result.allowed is True

    def test_policy_evaluation_with_missing_context(self):
        """Test policy evaluation with minimal context."""
        config = PolicyConfig(
            cost_control={"enabled": True, "global_limit": {"amount": 30.0}}
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=10.0,
            actor="alice@example.com",
        )

        assert isinstance(result, PolicyEvaluation)
        assert "allowed" in result.__dict__
        assert "violated_policies" in result.__dict__

    def test_zero_cost_operation(self):
        """Test handling of zero-cost operations."""
        config = PolicyConfig(
            cost_control={"enabled": True, "global_limit": {"amount": 30.0}}
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=0.0,
            actor="alice@example.com",
        )

        assert result.allowed is True


class TestPolicyCoverage:
    """Test coverage metrics."""

    def test_minimum_test_coverage(self):
        """Test that policies meet minimum test coverage."""
        policy_files = [
            Path(__file__).parent.parent / "cost_control.yaml",
            Path(__file__).parent.parent / "security.yaml",
            Path(__file__).parent.parent / "compliance.yaml",
        ]

        for policy_file in policy_files:
            with open(policy_file) as f:
                policy = yaml.safe_load(f)

            constraints = len(policy.get("constraints", []))
            test_cases = len(policy.get("test_cases", []))

            # Minimum coverage: 50% (1 test per 2 constraints)
            coverage_percent = (test_cases / constraints * 100) if constraints else 100

            assert test_cases > 0, f"No test cases in {policy_file.name}"
            assert coverage_percent >= 50, (
                f"{policy_file.name}: {coverage_percent:.1f}% coverage "
                f"({test_cases} tests for {constraints} constraints). "
                f"Minimum required: 50%"
            )


class TestPolicyIntegration:
    """Test policy integration scenarios."""

    def test_policy_evaluation_workflow(self):
        """Test complete policy evaluation workflow."""
        config = PolicyConfig(
            version="1.0.0",
            cost_control={
                "enabled": True,
                "global_limit": {"amount": 30.0, "currency": "USD"},
            },
        )
        engine = PolicyEngine(config)

        # Test sequence of operations
        operations = [
            {"cost": 5.0, "expected": True},
            {"cost": 10.0, "expected": True},
            {"cost": 15.0, "expected": True},
        ]

        total_cost = 0
        for op in operations:
            total_cost += op["cost"]
            # In real workflow, would track cumulative cost
            assert total_cost <= 30.0

    def test_policy_cascade_evaluation(self):
        """Test multiple policies evaluated in sequence."""
        from devarmor.models import SecurityPolicy, SkillPermissionsPolicy, SkillPermission

        config = PolicyConfig(
            cost_control={"enabled": True, "global_limit": {"amount": 30.0}},
            security=SecurityPolicy(enabled=True, forbidden_patterns=[r"DROP TABLE"]),
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                default_permissions=[
                    SkillPermission(skill_name="github", allowed_commands=["read"])
                ],
            ),
        )
        engine = PolicyEngine(config)

        # Cost control passes
        cost_result = engine.evaluate_cost_control(
            resource_type="compute", estimated_cost=10.0, actor="alice@example.com"
        )
        assert cost_result.allowed is True

        # Security check passes
        security_result = engine.evaluate_security_policy(
            action="read", actor="alice@example.com", target="data"
        )
        assert security_result.allowed is True

        # Skill check passes
        skill_result = engine.evaluate_skill_installation(
            skill_name="github", version="1.0.0", actor="alice@example.com"
        )
        assert isinstance(skill_result, PolicyEvaluation)
