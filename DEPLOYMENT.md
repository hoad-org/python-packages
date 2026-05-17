# Python Packages Repository Deployment Guide

## GitHub Pages Configuration

This repository uses GitHub Pages to serve packages as a PEP 503-compliant index.

### Settings Required

1. **Repository Settings → Pages**
   - Source: Deploy from branch
   - Branch: `main`
   - Folder: `/ (root)`

2. **Repository Settings → General**
   - Ensure "Discussions" is disabled (optional)
   - Public repository (required for public packages)

### Access URLs

- **Package Index:** https://hoad-org.github.io/python-packages/
- **Simple Index (PEP 503):** https://hoad-org.github.io/python-packages/simple/
- **Documentation:** https://hoad-org.github.io/python-packages/docs/

## Publishing Process

### From Package Repository (e.g., claude-github-skill)

1. **Tag Release:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Workflow Execution:**
   - GitHub Actions `publish.yml` triggers
   - Package built and tested
   - Distribution files created
   - Uploaded to python-packages repo

3. **Auto-Update:**
   - Package metadata stored in `packages/<name>/metadata.json`
   - Build index workflow regenerates documentation
   - PEP 503 index auto-updated
   - GitHub Pages deployed

## Directory Structure

```
python-packages/
├── packages/
│   ├── devarmor-core/
│   │   ├── src/devarmor/
│   │   ├── tests/
│   │   ├── docs/
│   │   ├── examples/
│   │   ├── devarmor_core-0.1.0-py3-none-any.whl
│   │   ├── devarmor_core-0.1.0.tar.gz
│   │   ├── metadata.json
│   │   ├── pyproject.toml
│   │   └── Makefile
│   ├── claude-github-skill/
│   │   ├── claude_github_skill-1.0.0-py3-none-any.whl
│   │   ├── claude_github_skill-1.0.0.tar.gz
│   │   └── metadata.json
│   └── [other packages]
├── simple/
│   ├── devarmor-core/
│   │   └── index.html (PEP 503)
│   ├── claude-github-skill/
│   │   └── index.html (PEP 503)
│   └── [other packages]
├── bin/
│   └── devarmor (CLI installer/updater)
├── docs/
│   ├── index.md
│   └── packages.md (auto-generated)
├── index.html (root index)
├── Makefile (aggregate targets for all packages)
├── pyproject.toml
└── .nojekyll (tells GitHub Pages not to use Jekyll)
```

## Metadata Format

Each package includes `metadata.json`:

```json
{
  "name": "claude-github-skill",
  "version": "1.0.0",
  "repository": "https://github.com/hoad-org/claude-github-skill",
  "published_at": "2026-05-16T14:30:00Z",
  "python_requires": ">=3.12"
}
```

## Installation

### From Custom Index

```bash
# Install DevArmor Core
pip install --index-url https://hoad-org.github.io/python-packages devarmor-core

# Or other packages
pip install --index-url https://hoad-org.github.io/python-packages claude-github-skill
```

### In requirements.txt

```
-i https://hoad-org.github.io/python-packages
devarmor-core>=0.1.0
```

### With pip.conf

```ini
[global]
index-url = https://hoad-org.github.io/python-packages
```

### Using DevArmor CLI Installer

```bash
# Download and run installer
curl -fsSL https://raw.githubusercontent.com/rhyscraig/python-packages/main/bin/devarmor | python3

# Install from CLI
devarmor install

# Check for updates
devarmor check

# Upgrade
devarmor upgrade
```

## Troubleshooting

### Package not appearing

1. Check `python-packages` repo has latest commits
2. Verify GitHub Pages is enabled and deployed
3. Check build-index workflow ran successfully
4. Clear pip cache: `pip cache purge`

### PEP 503 Compliance Issues

1. Verify simple/index.html was generated
2. Check package names match PEP 503 (lowercase, hyphens)
3. Ensure .nojekyll file exists in root

### Installation fails

1. Verify index URL is correct
2. Check Python version requirement
3. Run with `--verbose` flag for debugging

```bash
pip install --verbose --index-url https://hoad-org.github.io/python-packages claude-github-skill
```

## Performance Notes

- GitHub Pages serves static files (fast)
- No external dependencies
- Works offline (after initial index fetch)
- Compatible with all pip versions
- Supports all package formats (.whl, .tar.gz)

## Security

- All packages undergo security scanning before publication
- Source repositories must pass bandit and pip-audit
- Metadata immutable (git history preserved)
- HTTPS enforced by GitHub Pages
