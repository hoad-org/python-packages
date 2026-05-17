.PHONY: help install dev-install test coverage lint format type-check check security clean \
         publish-devarmor test-devarmor check-devarmor build-wheels

help:
	@echo "Hoad Python Packages Repository"
	@echo ""
	@echo "Available Targets:"
	@echo ""
	@echo "  Repository Management"
	@echo "  --------------------"
	@echo "  make help              Show this help message"
	@echo ""
	@echo "  DevArmor Core Package"
	@echo "  -------------------"
	@echo "  make test-devarmor     Run all devarmor-core tests"
	@echo "  make coverage-devarmor Run tests with coverage report (must be >85%)"
	@echo "  make lint-devarmor     Check code with ruff"
	@echo "  make format-devarmor   Format code with black"
	@echo "  make type-check-devarmor Check types with mypy"
	@echo "  make check-devarmor    Run all quality checks (lint, format, type-check)"
	@echo "  make security-devarmor Security scan with bandit"
	@echo "  make build-devarmor    Build devarmor-core wheel and source distributions"
	@echo "  make publish-devarmor  Build and publish devarmor-core wheel"
	@echo "  make clean-devarmor    Clean devarmor-core build artifacts"
	@echo ""
	@echo "  All Packages"
	@echo "  -----------"
	@echo "  make test              Run tests for all packages"
	@echo "  make coverage          Run coverage for all packages"
	@echo "  make check             Run quality checks for all packages"
	@echo "  make build-wheels      Build wheels for all packages"
	@echo "  make clean             Clean all build artifacts"
	@echo ""

# DevArmor Core targets
DEVARMOR_DIR := packages/devarmor-core

test-devarmor:
	cd $(DEVARMOR_DIR) && python -m pytest tests/ -v

coverage-devarmor:
	cd $(DEVARMOR_DIR) && python -m pytest tests/ --cov=src/devarmor --cov-report=term-missing --cov-report=html --cov-fail-under=85

lint-devarmor:
	cd $(DEVARMOR_DIR) && python -m ruff check src/ tests/

format-devarmor:
	cd $(DEVARMOR_DIR) && python -m black src/ tests/

format-check-devarmor:
	cd $(DEVARMOR_DIR) && python -m black --check src/ tests/

type-check-devarmor:
	cd $(DEVARMOR_DIR) && python -m mypy src/devarmor

check-devarmor: lint-devarmor format-check-devarmor type-check-devarmor
	@echo "✓ All devarmor-core checks passed!"

security-devarmor:
	cd $(DEVARMOR_DIR) && python -m bandit -r src/ -ll

build-devarmor:
	cd $(DEVARMOR_DIR) && python -m pip wheel --no-deps --wheel-dir dist . && python setup.py sdist --dist-dir dist

publish-devarmor: check-devarmor coverage-devarmor build-devarmor
	@echo "✓ devarmor-core ready to publish"
	@echo "  Wheel: $(DEVARMOR_DIR)/dist/devarmor_core-*.whl"
	@echo "  Source: $(DEVARMOR_DIR)/dist/devarmor-core-*.tar.gz"

clean-devarmor:
	cd $(DEVARMOR_DIR) && make clean
	rm -rf $(DEVARMOR_DIR)/dist $(DEVARMOR_DIR)/*.egg-info

# Aggregate targets
test:
	$(MAKE) test-devarmor

coverage:
	$(MAKE) coverage-devarmor

check:
	$(MAKE) check-devarmor

build-wheels: build-devarmor

clean: clean-devarmor

.DEFAULT_GOAL := help
