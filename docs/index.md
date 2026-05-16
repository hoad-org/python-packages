# Hoad Python Packages

Welcome to the Hoad Python Packages repository. This is a curated index of Python packages and Claude skills built for the Hoad Cloud Platform.

## Quick Start

Install packages with:

```bash
pip install --index-url https://hoad-org.github.io/python-packages <package-name>
```

## Available Packages

Check the [packages](packages.md) page for a complete list of available packages, versions, and documentation.

## For Package Maintainers

To publish your package:

1. Add GitHub Actions workflows to your repository
2. Create a semantic version tag (v1.0.0)
3. Push the tag to trigger the publish workflow
4. Package is automatically built and published

Ensure your package:
- Has >85% test coverage
- Passes security checks (bandit, pip-audit)
- Passes code quality checks (mypy, ruff, black)
- Includes proper documentation

## Index Structure

This repository maintains a Python Package Index (PyPI-like) structure:

```
/packages/
  /package-name/
    package-name-1.0.0-py3-none-any.whl
    package-name-1.0.0.tar.gz
    metadata.json
```

Each package directory contains:
- Built distributions (.whl, .tar.gz)
- Metadata file with version info and dependencies
- Installation instructions
