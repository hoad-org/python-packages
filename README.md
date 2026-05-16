# Hoad Python Packages Repository

A curated Python package repository hosting Claude skills and utilities built for the Hoad Cloud Platform.

## Installation

Install packages from this repository using pip:

```bash
pip install --index-url https://hoad-org.github.io/python-packages claude-github-skill
```

Or add to `requirements.txt`:

```
-i https://hoad-org.github.io/python-packages
claude-github-skill
```

## Available Packages

See [packages/](packages/) directory for available packages and versions.

## Publishing a Package

1. Create a semantic version tag in your package repository:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. The publish workflow automatically:
   - Builds the package
   - Runs security and quality checks
   - Publishes to this repository
   - Generates documentation

## Repository Structure

```
python-packages/
├── packages/
│   ├── claude-github-skill/
│   │   ├── claude_github_skill-1.0.0-py3-none-any.whl
│   │   ├── claude_github_skill-1.0.0.tar.gz
│   │   └── metadata.json
│   └── ...
├── docs/
│   ├── index.md
│   └── packages/
├── .github/
│   └── workflows/
│       └── build-index.yml
└── README.md
```

## Metadata

Each package includes a `metadata.json` with:
- Package name and version
- Python version requirements
- Repository URL
- Publication timestamp
- Dependencies

## GitHub Pages

This repository is published as a Python package index via GitHub Pages at:
https://hoad-org.github.io/python-packages

## Security

All packages undergo:
- Automated security scanning (bandit, pip-audit)
- Code quality checks (coverage >85%, type checking)
- Linting and formatting validation
- Dependency audits

Only packages passing all checks are published.

## Contributing

To add your package:
1. Ensure it has the required GitHub Actions workflows
2. Create a semantic version tag
3. The package is automatically published on success

## License

Each package maintains its own license. See individual package repositories.
