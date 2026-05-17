"""Skill Manifest Validation

Validates skill manifests against the DevArmor skill manifest schema.
Provides detailed error reporting for invalid manifests.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError
except ImportError:
    raise ImportError(
        "jsonschema is required for manifest validation. "
        "Install: pip install jsonschema"
    )

import yaml


@dataclass
class ValidationError:
    """Represents a single validation error"""

    path: str
    message: str
    value: Any
    constraint: str


@dataclass
class ManifestValidationResult:
    """Result of manifest validation"""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    manifest: Optional[Dict[str, Any]] = None


class SkillManifestValidator:
    """Validates skill manifests against DevArmor schema"""

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema

        Args:
            schema_path: Path to manifest schema JSON. If None, uses bundled schema.
        """
        if schema_path is None:
            # Use bundled schema
            schema_path = Path(__file__).parent.parent.parent.parent / "schema" / "skill-manifest-schema.json"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found at {schema_path}")

        with open(schema_path) as f:
            self.schema = json.load(f)

        self.validator = Draft7Validator(self.schema)

    def validate_file(self, manifest_path: Path) -> ManifestValidationResult:
        """Validate manifest from file

        Args:
            manifest_path: Path to YAML or JSON manifest

        Returns:
            ValidationResult with errors and manifest data
        """
        if not manifest_path.exists():
            return ManifestValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        path="<root>",
                        message=f"Manifest file not found: {manifest_path}",
                        value=None,
                        constraint="file_exists",
                    )
                ],
                warnings=[],
            )

        try:
            with open(manifest_path) as f:
                if manifest_path.suffix in [".yaml", ".yml"]:
                    manifest = yaml.safe_load(f)
                else:
                    manifest = json.load(f)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return ManifestValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        path="<root>",
                        message=f"Invalid manifest format: {e}",
                        value=None,
                        constraint="format",
                    )
                ],
                warnings=[],
            )

        return self.validate_manifest(manifest)

    def validate_manifest(self, manifest: Dict[str, Any]) -> ManifestValidationResult:
        """Validate manifest dictionary

        Args:
            manifest: Manifest data

        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []

        # Collect all validation errors
        for error in self.validator.iter_errors(manifest):
            path = ".".join(str(p) for p in error.absolute_path) or "<root>"
            errors.append(
                ValidationError(
                    path=path,
                    message=error.message,
                    value=error.instance,
                    constraint=error.validator,
                )
            )

        # Run semantic validations
        if manifest:
            semantic_warnings = self._validate_semantic_rules(manifest)
            warnings.extend(semantic_warnings)

        return ManifestValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            manifest=manifest if len(errors) == 0 else None,
        )

    def _validate_semantic_rules(self, manifest: Dict[str, Any]) -> List[str]:
        """Validate semantic rules beyond schema

        Args:
            manifest: Manifest data

        Returns:
            List of warning messages
        """
        warnings: List[str] = []

        if not manifest:
            return warnings

        metadata = manifest.get("metadata", {})
        spec = manifest.get("spec", {})

        # Check for event circular dependencies
        events = spec.get("events", {})
        publishes = {e["name"] for e in events.get("publishes", [])}
        subscribes = {s["name"] for s in events.get("subscribes", [])}

        if publishes & subscribes:
            overlapping = publishes & subscribes
            warnings.append(
                f"Skill publishes and subscribes to same events: {overlapping}. "
                "This may indicate a circular dependency."
            )

        # Check for unused state
        state = spec.get("state", {})
        maintains = {s["name"] for s in state.get("maintains", [])}
        shares = {s["name"] for s in state.get("shares", [])}

        if not maintains and not subscribes:
            warnings.append(
                "Skill neither maintains state nor subscribes to events. "
                "It may be stateless."
            )

        # Check for security isolation vs dependencies
        security = spec.get("security", {})
        isolation = security.get("isolation", {})
        process_level = isolation.get("processLevel", "subprocess")
        dependencies = spec.get("dependencies", [])

        if process_level == "container" and dependencies:
            warnings.append(
                "Skill uses container isolation with dependencies. "
                "Ensure all dependencies are available in container."
            )

        # Check for reasonable timeouts
        capabilities = spec.get("capabilities", {})
        for action in capabilities.get("actions", []):
            timeout = action.get("timeout", 300)
            if timeout > 3600:
                warnings.append(
                    f"Action {action['name']} has timeout {timeout}s > 1 hour. "
                    "Consider breaking into smaller operations."
                )

        # Check for policies
        policies = spec.get("policies", {})
        requires = policies.get("requires", [])

        if not requires:
            warnings.append(
                "Skill does not require any policies. "
                "Consider adding cost_control, security, or compliance policies."
            )

        return warnings

    def validate_manifest_path(self, skill_dir: Path) -> ManifestValidationResult:
        """Validate manifest.yaml in skill directory

        Args:
            skill_dir: Path to skill directory

        Returns:
            ValidationResult
        """
        manifest_path = skill_dir / "manifest.yaml"
        if not manifest_path.exists():
            manifest_path = skill_dir / "manifest.json"

        if not manifest_path.exists():
            return ManifestValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        path="<root>",
                        message=f"No manifest.yaml or manifest.json found in {skill_dir}",
                        value=None,
                        constraint="manifest_exists",
                    )
                ],
                warnings=[],
            )

        return self.validate_file(manifest_path)

    @staticmethod
    def format_errors(result: ManifestValidationResult) -> str:
        """Format validation errors for display

        Args:
            result: ValidationResult

        Returns:
            Formatted error message
        """
        lines = []

        if result.is_valid:
            lines.append("✓ Manifest is valid")
        else:
            lines.append(f"✗ Manifest validation failed ({len(result.errors)} errors):\n")

            for error in result.errors:
                lines.append(f"  [{error.path}]")
                lines.append(f"  {error.message}")
                if error.constraint:
                    lines.append(f"  Constraint: {error.constraint}")
                lines.append("")

        if result.warnings:
            lines.append(f"⚠ {len(result.warnings)} warnings:\n")
            for warning in result.warnings:
                lines.append(f"  • {warning}")
                lines.append("")

        return "\n".join(lines)


def validate_manifest_file(manifest_path: str) -> int:
    """CLI entry point for manifest validation

    Args:
        manifest_path: Path to manifest file

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    validator = SkillManifestValidator()
    result = validator.validate_file(Path(manifest_path))

    print(SkillManifestValidator.format_errors(result))

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m devarmor.manifest_validator <manifest_path>")
        sys.exit(1)

    sys.exit(validate_manifest_file(sys.argv[1]))
