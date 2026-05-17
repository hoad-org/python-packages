"""Tests for policy engine."""

from devarmor.models import (
    CostControlPolicy,
    CostLimit,
    PolicyConfig,
    PolicyEvaluation,
    SecurityPolicy,
    SkillPermission,
    SkillPermissionsPolicy,
)
from devarmor.policy import PolicyEngine


class TestPolicyEngine:
    """Test PolicyEngine class."""

    def test_evaluate_skill_installation_allowed(self) -> None:
        """Test evaluating skill installation when allowed."""
        config = PolicyConfig(
            security=SecurityPolicy(require_approval=False),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_installation(
            skill_name="test-skill",
            version="1.0.0",
            actor="user",
        )

        assert isinstance(result, PolicyEvaluation)
        assert result.allowed is True
        assert len(result.violated_policies) == 0

    def test_evaluate_skill_installation_security_required(self) -> None:
        """Test that skill installation requires security approval."""
        config = PolicyConfig(
            security=SecurityPolicy(require_approval=True),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_installation(
            skill_name="test-skill",
            version="1.0.0",
            actor="user",
        )

        assert result.allowed is False
        assert "security:require_approval" in result.violated_policies

    def test_evaluate_skill_installation_blocked_skill(self) -> None:
        """Test that blocked skills cannot be installed."""
        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                skill_blocklist=["blocked-skill"],
            ),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_installation(
            skill_name="blocked-skill",
            version="1.0.0",
            actor="user",
        )

        assert result.allowed is False
        assert "skill_permissions:blocked" in result.violated_policies

    def test_evaluate_skill_installation_allowlist(self) -> None:
        """Test that only allowlisted skills can be installed."""
        config = PolicyConfig(
            security=SecurityPolicy(require_approval=False),
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                skill_allowlist=["allowed-skill"],
            ),
        )
        engine = PolicyEngine(config)

        # Allowed skill
        result = engine.evaluate_skill_installation(
            skill_name="allowed-skill",
            version="1.0.0",
            actor="user",
        )
        assert result.allowed is True

        # Not in allowlist
        result = engine.evaluate_skill_installation(
            skill_name="other-skill",
            version="1.0.0",
            actor="user",
        )
        assert result.allowed is False

    def test_evaluate_skill_upgrade(self) -> None:
        """Test evaluating skill upgrade."""
        config = PolicyConfig()
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_upgrade(
            skill_name="test-skill",
            old_version="1.0.0",
            new_version="2.0.0",
            actor="user",
        )

        assert isinstance(result, PolicyEvaluation)

    def test_evaluate_skill_removal_requires_approval(self) -> None:
        """Test that skill removal requires approval."""
        config = PolicyConfig(
            security=SecurityPolicy(require_approval=True),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_removal(
            skill_name="test-skill",
            actor="user",
        )

        assert result.allowed is False
        assert "security:require_approval" in result.violated_policies

    def test_evaluate_skill_removal_allowed(self) -> None:
        """Test skill removal when allowed."""
        config = PolicyConfig(
            security=SecurityPolicy(require_approval=False),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_skill_removal(
            skill_name="test-skill",
            actor="user",
        )

        assert result.allowed is True

    def test_evaluate_cost_control_under_limit(self) -> None:
        """Test cost control when under limit."""

        config = PolicyConfig(
            cost_control=CostControlPolicy(
                enabled=True,
                global_limit=CostLimit(amount=100.0),
            ),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=50.0,
            actor="user",
        )

        assert result.allowed is True

    def test_evaluate_cost_control_exceeds_limit(self) -> None:
        """Test cost control when exceeding limit."""

        config = PolicyConfig(
            cost_control=CostControlPolicy(
                enabled=True,
                global_limit=CostLimit(amount=100.0),
            ),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=150.0,
            actor="user",
        )

        assert result.allowed is False
        assert "cost_control:exceeds_global_limit" in result.violated_policies

    def test_evaluate_cost_control_disabled(self) -> None:
        """Test cost control when disabled."""

        config = PolicyConfig(
            cost_control=CostControlPolicy(enabled=False),
        )
        engine = PolicyEngine(config)

        result = engine.evaluate_cost_control(
            resource_type="compute",
            estimated_cost=999999.0,
            actor="user",
        )

        assert result.allowed is True

    def test_evaluate_security_policy_forbidden_pattern(self) -> None:
        """Test security policy with forbidden patterns."""
        config = PolicyConfig(
            security=SecurityPolicy(
                forbidden_patterns=["DROP", "DELETE"],
            ),
        )
        engine = PolicyEngine(config)

        # Should fail for forbidden pattern
        result = engine.evaluate_security_policy(
            action="DROP TABLE users",
            actor="user",
            target="database",
        )

        assert result.allowed is False

    def test_evaluate_security_policy_allowed_domains(self) -> None:
        """Test security policy with allowed domains."""
        config = PolicyConfig(
            security=SecurityPolicy(
                allowed_domains={"api.example.com", "data.example.com"},
            ),
        )
        engine = PolicyEngine(config)

        # Allowed domain
        result = engine.evaluate_security_policy(
            action="call_api",
            actor="user",
            target="api.example.com",
        )
        assert result.allowed is True

        # Not allowed domain
        result = engine.evaluate_security_policy(
            action="call_api",
            actor="user",
            target="evil.com",
        )
        assert result.allowed is False

    def test_get_skill_permission(self) -> None:
        """Test getting skill permission."""
        perm = SkillPermission(skill_name="test-skill", allowed_commands=["install", "upgrade"])
        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                default_permissions=[perm],
            ),
        )
        engine = PolicyEngine(config)

        result = engine.get_skill_permission("test-skill")

        assert result is not None
        assert result.skill_name == "test-skill"

    def test_get_skill_permission_not_found(self) -> None:
        """Test getting skill permission when not found."""
        config = PolicyConfig()
        engine = PolicyEngine(config)

        result = engine.get_skill_permission("nonexistent")

        assert result is None

    def test_is_skill_allowed(self) -> None:
        """Test checking if skill is allowed."""
        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(
                enabled=True,
                skill_blocklist=["blocked"],
                skill_allowlist=["allowed"],
            ),
        )
        engine = PolicyEngine(config)

        assert engine.is_skill_allowed("allowed") is True
        assert engine.is_skill_allowed("blocked") is False

    def test_is_skill_allowed_disabled(self) -> None:
        """Test checking if skill is allowed when policy disabled."""
        config = PolicyConfig(
            skill_permissions=SkillPermissionsPolicy(enabled=False),
        )
        engine = PolicyEngine(config)

        assert engine.is_skill_allowed("anything") is True
