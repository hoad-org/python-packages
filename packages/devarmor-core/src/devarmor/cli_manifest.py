"""DevArmor Manifest CLI

Command-line tool for manifest management:
- Validate skill manifests
- Generate code from manifests
- Migrate existing skills to manifest-first
- Registry operations
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from devarmor.manifest_validator import SkillManifestValidator
from devarmor.codegen import SkillCodeGenerator


@click.group()
def cli():
    """DevArmor Manifest Management CLI"""
    pass


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option(
    "--verbose", "-v", is_flag=True, help="Verbose output"
)
def validate(manifest_path: str, verbose: bool):
    """Validate a skill manifest

    Example:
        devarmor manifest validate manifest.yaml
        devarmor manifest validate manifest.json --verbose
    """
    validator = SkillManifestValidator()
    result = validator.validate_file(Path(manifest_path))

    # Print results
    click.echo(SkillManifestValidator.format_errors(result))

    # Exit with appropriate code
    sys.exit(0 if result.is_valid else 1)


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=".",
    help="Output directory for generated files",
)
@click.option(
    "--force", "-f", is_flag=True, help="Overwrite existing files"
)
def generate(manifest_path: str, output_dir: str, force: bool):
    """Generate code from a manifest

    Generates:
    - Skill implementation class
    - Test file with stubs
    - Configuration file
    - Dockerfile
    - GitHub Actions workflow
    - Documentation (README, CONFIG.md, SECURITY.md)

    Example:
        devarmor manifest generate manifest.yaml -o ./generated
        devarmor manifest generate manifest.json --force
    """
    # Validate manifest first
    validator = SkillManifestValidator()
    result = validator.validate_file(Path(manifest_path))

    if not result.is_valid:
        click.echo(click.style("✗ Manifest validation failed", fg="red"))
        click.echo(SkillManifestValidator.format_errors(result))
        sys.exit(1)

    # Generate code
    click.echo(click.style("✓ Manifest valid", fg="green"))
    click.echo("Generating code files...")

    generator = SkillCodeGenerator(result.manifest)
    outputs = generator.generate_all()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    skipped_count = 0

    for output in outputs:
        file_path = output_path / output.path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and not force:
            click.echo(f"  ⊘ {output.path} (already exists, use --force to overwrite)")
            skipped_count += 1
        else:
            file_path.write_text(output.content)
            click.echo(f"  ✓ {output.path}")
            generated_count += 1

    click.echo(f"\nGenerated {generated_count} files, skipped {skipped_count}")


@cli.command()
@click.argument("skill_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output manifest path (default: manifest.yaml in skill dir)",
)
def migrate(skill_dir: str, output: Optional[str]):
    """Migrate existing skill to manifest-first design

    Interactive migration creates a manifest.yaml from existing skill code.

    Example:
        devarmor manifest migrate ./github-skill
        devarmor manifest migrate ./jira-skill -o ./jira-skill/manifest.yaml
    """
    skill_path = Path(skill_dir)

    click.echo(click.style("Skill Migration Tool", fg="cyan", bold=True))
    click.echo()

    # Gather information
    name = click.prompt("Skill name (kebab-case)", type=str)
    version = click.prompt("Skill version", type=str, default="1.0.0")
    display_name = click.prompt("Display name", type=str)
    description = click.prompt("Description", type=str)
    author = click.prompt("Author", type=str, default="")
    license_type = click.prompt("License", type=str, default="MIT")

    click.echo()
    click.echo("Scanning skill code...")

    # TODO: Implement code scanning to detect capabilities, events, state, etc.
    # For now, create minimal manifest

    manifest = {
        "apiVersion": "devarmor.io/v1",
        "kind": "Skill",
        "metadata": {
            "name": name,
            "version": version,
            "displayName": display_name,
            "description": description,
            "license": license_type,
        },
        "spec": {
            "capabilities": {
                "actions": [
                    {
                        "name": "TODO",
                        "description": "Add actions from skill code",
                        "input": {"type": "object"},
                    }
                ],
            },
            "security": {
                "isolation": {"processLevel": "subprocess"},
            },
        },
    }

    if author:
        manifest["metadata"]["author"] = author

    # Save manifest
    output_path = Path(output) if output else skill_path / "manifest.yaml"

    try:
        import yaml

        with open(output_path, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)
        click.echo(click.style(f"✓ Created manifest at {output_path}", fg="green"))
    except ImportError:
        # Fall back to JSON
        with open(output_path.with_suffix(".json"), "w") as f:
            json.dump(manifest, f, indent=2)
        click.echo(
            click.style(
                f"✓ Created manifest at {output_path.with_suffix('.json')}",
                fg="green",
            )
        )

    click.echo()
    click.echo("Next steps:")
    click.echo("1. Review and edit the manifest to add:")
    click.echo("   - capabilities.actions (your skill actions)")
    click.echo("   - capabilities.queries (your skill queries)")
    click.echo("   - events.publishes (events your skill emits)")
    click.echo("   - events.subscribes (events your skill listens to)")
    click.echo("   - state.maintains (state your skill maintains)")
    click.echo("2. Add configuration schema (configuration.schema)")
    click.echo("3. Add security requirements (security.*)")
    click.echo("4. Run: devarmor manifest generate manifest.yaml")
    click.echo("5. Review generated code and customize implementation")


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output format",
)
def inspect(manifest_path: str, format: str):
    """Inspect manifest structure

    Shows manifest contents and metadata.

    Example:
        devarmor manifest inspect manifest.yaml
        devarmor manifest inspect manifest.json --format yaml
    """
    validator = SkillManifestValidator()
    result = validator.validate_file(Path(manifest_path))

    if not result.manifest:
        click.echo(click.style("✗ Invalid manifest", fg="red"))
        sys.exit(1)

    manifest = result.manifest

    # Header
    meta = manifest.get("metadata", {})
    click.echo(click.style(f"Skill: {meta.get('name')}", fg="cyan", bold=True))
    click.echo(f"  Version: {meta.get('version')}")
    click.echo(f"  Description: {meta.get('description')}")
    click.echo()

    # Capabilities
    spec = manifest.get("spec", {})
    caps = spec.get("capabilities", {})

    if actions := caps.get("actions"):
        click.echo(click.style("Actions:", fg="yellow"))
        for action in actions:
            click.echo(f"  - {action.get('name')}: {action.get('description', '')}")
        click.echo()

    if queries := caps.get("queries"):
        click.echo(click.style("Queries:", fg="yellow"))
        for query in queries:
            click.echo(f"  - {query.get('name')}: {query.get('description', '')}")
        click.echo()

    # Events
    events = spec.get("events", {})

    if publishes := events.get("publishes"):
        click.echo(click.style("Publishes:", fg="yellow"))
        for event in publishes:
            click.echo(f"  - {event.get('name')}")
        click.echo()

    if subscribes := events.get("subscribes"):
        click.echo(click.style("Subscribes:", fg="yellow"))
        for sub in subscribes:
            click.echo(f"  - {sub.get('name')} → {sub.get('handler')}")
        click.echo()

    # Security
    security = spec.get("security", {})
    click.echo(click.style("Security:", fg="yellow"))
    iso = security.get("isolation", {})
    click.echo(f"  Process Level: {iso.get('processLevel', 'subprocess')}")
    if perms := security.get("permissions"):
        click.echo(f"  Permissions: {', '.join(perms)}")
    if auth := security.get("authentication"):
        types = [a.get("type") for a in auth]
        click.echo(f"  Authentication: {', '.join(types)}")
    click.echo()

    # Dependencies
    if deps := spec.get("dependencies"):
        click.echo(click.style("Dependencies:", fg="yellow"))
        for dep in deps:
            ver = dep.get("version", "any")
            optional = " (optional)" if dep.get("optional") else ""
            click.echo(f"  - {dep.get('name')} {ver}{optional}")


@cli.command()
@click.option(
    "--skill-dir",
    type=click.Path(exists=True),
    help="Search for manifests in directory",
)
def list_skills(skill_dir: Optional[str]):
    """List discovered skills

    Example:
        devarmor manifest list
        devarmor manifest list --skill-dir ./packages
    """
    search_path = Path(skill_dir) if skill_dir else Path.cwd()

    click.echo(click.style("Searching for skill manifests...", fg="cyan"))

    manifests = list(search_path.rglob("manifest.yaml")) + list(
        search_path.rglob("manifest.json")
    )

    if not manifests:
        click.echo("No manifests found")
        return

    validator = SkillManifestValidator()
    skills = []

    for manifest_path in manifests:
        result = validator.validate_file(manifest_path)
        if result.is_valid:
            meta = result.manifest.get("metadata", {})
            skills.append((meta.get("name"), meta.get("version"), manifest_path))

    click.echo()
    click.echo(click.style("Found Skills:", fg="yellow"))
    for name, version, path in sorted(skills):
        click.echo(f"  {name}:{version}")
        click.echo(f"    Path: {path}")


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo()
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
