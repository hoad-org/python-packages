.PHONY: help install dev-install test coverage lint format type-check check security clean

help:
	@echo "DevArmor Core - Available Targets"
	@echo ""
	@echo "  make install       Install package in production mode"
	@echo "  make dev-install   Install package with development dependencies"
	@echo "  make test          Run test suite"
	@echo "  make coverage      Run tests with coverage report"
	@echo "  make lint          Check code with ruff"
	@echo "  make format        Format code with black"
	@echo "  make type-check    Check types with mypy"
	@echo "  make check         Run all quality checks (lint, format, type-check)"
	@echo "  make security      Security scan with bandit"
	@echo "  make clean         Remove build artifacts and caches"
	@echo ""

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest

coverage:
	pytest --cov=src/devarmor --cov-report=term-missing --cov-report=html

lint:
	ruff check src/ tests/

format:
	black src/ tests/

format-check:
	black --check src/ tests/

type-check:
	mypy src/devarmor

check: lint format-check type-check
	@echo "All checks passed!"

security:
	bandit -r src/ -ll

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

.DEFAULT_GOAL := help
