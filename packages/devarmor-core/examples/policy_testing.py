"""
Example: Testing DevArmor Policies

Demonstrates how to test policies before deployment to catch issues early.
This example shows:

1. Loading and validating policy syntax
2. Running test cases
3. Simulating policy evaluation with sample data
4. Finding policy issues

Usage:
  python policy_testing.py
  # Tests policy in ./cost_control_policy.yaml

Typical workflow:
  1. Write policy (cost_control_policy.yaml)
  2. Define test cases (in YAML)
  3. Run tests: pytest tests/test_policies.py
  4. Fix any failing tests
  5. Simulate with real data
  6. Deploy to staging
  7. Monitor for 24 hours
  8. Deploy to production
"""

import asyncio
import yaml
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class PolicyTestCase:
    """A single test case for a policy"""
    name: str
    input_data: Dict[str, Any]
    expected_outcome: str  # ALLOW, DENY, WARN
    expected_message: str = ""


class PolicyTestRunner:
    """Run policy tests"""

    def __init__(self, policy_path: str):
        self.policy_path = policy_path
        self.policy = self._load_policy()
        self.test_cases = self._load_test_cases()

    def _load_policy(self) -> Dict[str, Any]:
        """Load policy from YAML file"""
        with open(self.policy_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_test_cases(self) -> List[PolicyTestCase]:
        """Load test cases from policy YAML"""
        test_cases = []

        for test_data in self.policy.get('test_cases', []):
            test = PolicyTestCase(
                name=test_data['name'],
                input_data=test_data['input'],
                expected_outcome=test_data['expected'],
                expected_message=test_data.get('expected_message', '')
            )
            test_cases.append(test)

        return test_cases

    def validate_syntax(self) -> Tuple[bool, List[str]]:
        """
        Validate policy YAML syntax.

        Returns: (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        if 'name' not in self.policy:
            errors.append("Missing required field: name")

        if 'constraints' not in self.policy:
            errors.append("Missing required field: constraints")

        # Check constraints
        for i, constraint in enumerate(self.policy.get('constraints', [])):
            if 'name' not in constraint:
                errors.append(f"Constraint {i}: missing 'name'")
            if 'rule' not in constraint:
                errors.append(f"Constraint {i}: missing 'rule'")
            if 'action' not in constraint:
                errors.append(f"Constraint {i}: missing 'action'")

            # Validate action
            valid_actions = ['allow', 'deny', 'warn', 'rate_limit']
            if constraint.get('action') not in valid_actions:
                errors.append(
                    f"Constraint '{constraint.get('name')}': "
                    f"invalid action '{constraint.get('action')}'. "
                    f"Must be one of: {', '.join(valid_actions)}"
                )

        return len(errors) == 0, errors

    def run_test_case(self, test: PolicyTestCase) -> Tuple[bool, str]:
        """
        Run a single test case.

        In a real implementation, this would evaluate the policy rule
        against the test input and check if it matches expected outcome.

        Returns: (passed, message)
        """
        # In real implementation, would evaluate policy rule
        # against input data and check decision

        # For this example, we just show the structure
        result = "ALLOW"  # Would be actual policy evaluation result

        passed = result == test.expected_outcome
        message = (
            f"Expected: {test.expected_outcome}, Got: {result}" if not passed
            else "PASSED"
        )

        return passed, message

    def run_all_tests(self) -> Tuple[int, int]:
        """
        Run all test cases.

        Returns: (passed_count, total_count)
        """
        passed = 0
        total = len(self.test_cases)

        print(f"\nRunning {total} test cases for policy '{self.policy['name']}':\n")

        for test in self.test_cases:
            test_passed, message = self.run_test_case(test)

            status = "✓ PASS" if test_passed else "✗ FAIL"
            print(f"{status}: {test.name}")
            print(f"       {message}\n")

            if test_passed:
                passed += 1

        return passed, total

    def simulate_policy(
        self,
        user: str,
        cost: int,
        monthly_spend: int,
        budget: int = 600
    ) -> Dict[str, Any]:
        """
        Simulate policy evaluation with sample data.

        This shows what would happen if a user tried to perform
        an action with the given cost and spend.

        Args:
            user: User identifier
            cost: Cost of this operation (in pence)
            monthly_spend: User's spend so far this month
            budget: User's monthly budget

        Returns: Dict with decision for each constraint
        """
        print(f"\nSimulating policy evaluation:")
        print(f"  User: {user}")
        print(f"  Cost: £{cost/100:.2f}")
        print(f"  Monthly spend: £{monthly_spend/100:.2f}")
        print(f"  Budget: £{budget/100:.2f}")
        print()

        results = {}

        for constraint in self.policy.get('constraints', []):
            name = constraint['name']
            rule = constraint['rule']
            action = constraint['action']

            # In real implementation, evaluate rule with variables:
            # ${user_id} → user
            # ${cost} → cost
            # ${monthly_budget} → budget
            # etc.

            # For demo, show the rule
            substituted_rule = (
                rule.replace('${cost}', str(cost))
                .replace('${monthly_budget}', str(budget))
                .replace('${user_id}', user)
            )

            # Evaluate some rules manually
            decision = self._evaluate_constraint(
                constraint,
                cost,
                monthly_spend,
                budget
            )

            results[name] = {
                'rule': substituted_rule,
                'action': action,
                'decision': decision,
            }

            print(f"{name}:")
            print(f"  Rule: {substituted_rule}")
            print(f"  Action: {action}")
            print(f"  Decision: {decision}\n")

        return results

    def _evaluate_constraint(
        self,
        constraint: Dict[str, Any],
        cost: int,
        monthly_spend: int,
        budget: int
    ) -> str:
        """
        Simple constraint evaluation (demo only).

        In real implementation, would use proper expression parser.
        """
        name = constraint['name']

        if name == 'MonthlyBudgetLimit':
            if monthly_spend + cost <= budget:
                return 'ALLOW'
            else:
                return 'DENY'

        elif name == 'ProjectBudgetLimit':
            if monthly_spend <= 100:  # Demo: assume 100 pence limit
                return 'ALLOW'
            else:
                return 'WARN'

        elif name == 'ExpensiveOperationWarning':
            if cost > 0:
                return 'WARN'
            else:
                return 'ALLOW'

        elif name == 'VeryExpensiveOperationThrottle':
            if cost > 50:
                return 'RATE_LIMIT'
            else:
                return 'ALLOW'

        elif name == 'BudgetExceededPrevention':
            if monthly_spend + cost > budget:
                return 'DENY'
            else:
                return 'ALLOW'

        return 'ALLOW'


# ─────────────────────────────────────────────────────────────
# Example Usage
# ─────────────────────────────────────────────────────────────

def main():
    """Run policy tests and simulations"""
    print("DevArmor Policy Testing Example")
    print("=" * 60)

    # Test the cost control policy
    runner = PolicyTestRunner('./examples/cost_control_policy.yaml')

    # 1. Validate syntax
    print("\n1. Validating policy syntax...")
    valid, errors = runner.validate_syntax()

    if valid:
        print("   ✓ Policy syntax is valid")
    else:
        print("   ✗ Policy syntax errors:")
        for error in errors:
            print(f"     - {error}")
        return

    # 2. Run test cases
    print("\n2. Running test cases...")
    passed, total = runner.run_all_tests()
    print(f"Result: {passed}/{total} tests passed")

    if passed < total:
        print("⚠ Some tests failed. Review policy before deploying.")
        return

    # 3. Simulate with real-world scenarios
    print("\n3. Simulating policy with real-world scenarios...\n")

    scenarios = [
        {
            'name': 'User under budget',
            'user': 'alice@example.com',
            'cost': 50,
            'monthly_spend': 250,
            'budget': 600,
        },
        {
            'name': 'User approaching budget',
            'user': 'bob@example.com',
            'cost': 100,
            'monthly_spend': 550,
            'budget': 600,
        },
        {
            'name': 'User would exceed budget',
            'user': 'charlie@example.com',
            'cost': 100,
            'monthly_spend': 600,
            'budget': 600,
        },
        {
            'name': 'Very expensive operation',
            'user': 'alice@example.com',
            'cost': 75,
            'monthly_spend': 100,
            'budget': 600,
        },
    ]

    for scenario in scenarios:
        print(f"Scenario: {scenario['name']}")
        print("-" * 60)
        runner.simulate_policy(
            user=scenario['user'],
            cost=scenario['cost'],
            monthly_spend=scenario['monthly_spend'],
            budget=scenario['budget']
        )

    # 4. Summary
    print("\n4. Summary")
    print("-" * 60)
    print(f"Policy name: {runner.policy['name']}")
    print(f"Version: {runner.policy.get('version', 'unknown')}")
    print(f"Constraints: {len(runner.policy.get('constraints', []))}")
    print(f"Test cases: {len(runner.test_cases)}")
    print()
    print("✓ Policy ready for deployment!")
    print()
    print("Next steps:")
    print("  1. Deploy to staging:")
    print("     devarmor policy deploy ./cost_control_policy.yaml --environment=staging")
    print()
    print("  2. Monitor for 24 hours:")
    print("     devarmor policy metrics cost_control --watch")
    print()
    print("  3. Deploy to production:")
    print("     devarmor policy deploy ./cost_control_policy.yaml --environment=production")


if __name__ == '__main__':
    main()
