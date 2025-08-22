# Cage Platform Makefile
# Common development and testing commands
# Uses devbox for dependency management

.PHONY: help install test test-unit test-integration test-functional test-coverage clean build podman-build podman-run podman-stop lint format check-deps install-deps setup-dev devbox-shell podman-logs podman-exec podman-inspect

# Default target
help:
	@echo "Cage Platform - Available Commands:"
	@echo ""
	@echo "Development Setup:"
	@echo "  setup-dev      - Set up development environment with devbox"
	@echo "  setup-cursor-rules - Set up .cursor/rules link to memory-bank/rules"
	@echo "  install-deps   - Install dependencies via devbox"
	@echo "  check-deps     - Check if all dependencies are installed"
	@echo "  devbox-shell   - Start devbox shell with development environment"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-functional - Run functional tests only"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  test-fast      - Run fast tests (exclude slow markers)"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code with black"
	@echo "  check-format   - Check code formatting without changing files"
	@echo ""
	@echo "Container Operations (podman):"
	@echo "  podman-build   - Build container image with podman"
	@echo "  podman-run     - Run container locally with podman"
	@echo "  podman-stop    - Stop running containers"
	@echo "  podman-clean   - Clean up container resources"
	@echo "  podman-logs    - Show container logs"
	@echo "  podman-exec    - Execute command in container"
	@echo "  podman-inspect - Inspect container details"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          - Clean up generated files and caches"
	@echo "  status         - Show project status and active tasks"
	@echo ""

# Development Environment Setup
setup-dev: check-devbox
	@echo "Setting up development environment with devbox..."
	@if command -v devbox > /dev/null; then \
		devbox install; \
		echo "Development environment setup complete!"; \
		echo "Activate with: devbox shell"; \
	else \
		echo "❌ devbox not found. Please install devbox first."; \
		echo "Visit: https://www.jetpack.io/devbox/docs/installing_devbox/"; \
		exit 1; \
	fi

setup-cursor-rules:
	@echo "Setting up .cursor/rules link to memory-bank/rules..."
	@if [ -f "memory-bank/scripts/setup-cursor-rules.sh" ]; then \
		./memory-bank/scripts/setup-cursor-rules.sh; \
	else \
		echo "❌ Setup script not found at memory-bank/scripts/setup-cursor-rules.sh"; \
		exit 1; \
	fi

install-deps: check-devbox
	@echo "Installing dependencies via devbox..."
	@if command -v devbox > /dev/null; then \
		devbox install; \
	else \
		echo "❌ devbox not found. Please install devbox first."; \
		exit 1; \
	fi

check-deps:
	@echo "Checking dependencies..."
	@if command -v devbox > /dev/null; then \
		devbox run -- python -c "import pytest; print('✅ pytest installed')" && \
		devbox run -- python -c "import pytest_asyncio; print('✅ pytest-asyncio installed')" && \
		devbox run -- python -c "import pytest_cov; print('✅ pytest-cov installed')" && \
		devbox run -- python -c "import pytest_mock; print('✅ pytest-mock installed')" && \
		devbox run -- python -c "import pytest_xdist; print('✅ pytest-xdist installed')" && \
		devbox run -- python -c "import aiohttp; print('✅ aiohttp installed')" && \
		echo "✅ All dependencies installed"; \
	else \
		echo "❌ devbox not found. Please install devbox first."; \
		exit 1; \
	fi
check-devbox:
	@devbox --version > /dev/null 2>&1 || (echo "❌ devbox is required but not installed"; exit 1)
	@echo "✅ devbox found: $(shell devbox --version)"

check-python:
	@devbox run -- python --version > /dev/null 2>&1 || (echo "❌ Python not available in devbox"; exit 1)
	@echo "✅ Python available in devbox: $(shell devbox run -- python --version)"

check-podman:
	@podman --version > /dev/null 2>&1 || (echo "❌ podman is required but not installed"; exit 1)
	@echo "✅ podman found: $(shell podman --version)"

# Testing Commands
test: check-deps
	@echo "Running all tests..."
	devbox run -- pytest -v

test-unit: check-deps
	@echo "Running unit tests..."
	devbox run -- pytest tests/unit/ -v -m unit

test-integration: check-deps
	@echo "Running integration tests..."
	devbox run -- pytest tests/integration/ -v -m integration

test-functional: check-deps
	@echo "Running functional tests..."
	devbox run -- pytest tests/functional/ -v -m functional

test-coverage: check-deps
	@echo "Running tests with coverage..."
	devbox run -- pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml -v

test-fast: check-deps
	@echo "Running fast tests (excluding slow markers)..."
	devbox run -- pytest -m "not slow" -v
	@echo "Running fast tests (excluding slow markers)..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && pytest -m "not slow" -v; \
	else \
		pytest -m "not slow" -v; \
	fi

# Code Quality
lint: check-deps
	@echo "Running linting checks..."
	@if command -v flake8 > /dev/null; then \
		flake8 . --exclude=venv,__pycache__,.git; \
	else \
		echo "⚠️  flake8 not installed. Install with: pip install flake8"; \
	fi

format: check-deps
	@echo "Formatting code with black..."
	@if command -v black > /dev/null; then \
		black . --exclude=venv; \
	else \
		echo "⚠️  black not installed. Install with: pip install black"; \
	fi

check-format: check-deps
	@echo "Checking code formatting..."
	@if command -v black > /dev/null; then \
		black --check . --exclude=venv || (echo "❌ Code formatting check failed. Run 'make format' to fix"; exit 1); \
		echo "✅ Code formatting check passed"; \
	else \
		echo "⚠️  black not installed. Install with: pip install black"; \
	fi

# Container Operations (using podman)
podman-build: check-podman
	@echo "Building container image with podman..."
	podman build -t cage:latest .

podman-run:
	@echo "Running container with podman..."
	podman run -d --name cage-container -p 8080:8080 -e GEMINI_API_KEY=test-key cage:latest

podman-stop:
	@echo "Stopping containers..."
	podman stop cage-container 2>/dev/null || true
	podman rm cage-container 2>/dev/null || true

podman-clean: podman-stop
	@echo "Cleaning up container resources..."
	podman system prune -f

# Additional podman-specific commands
podman-logs:
	@echo "Showing container logs..."
	podman logs cage-container 2>/dev/null || echo "Container not running"

podman-exec:
	@echo "Executing command in running container..."
	@if podman ps | grep -q cage-container; then \
		echo "Container is running. Use: podman exec -it cage-container /bin/bash"; \
	else \
		echo "Container is not running. Start it first with: make podman-run"; \
	fi

podman-inspect:
	@echo "Inspecting container..."
	podman inspect cage-container 2>/dev/null || echo "Container not found"

# Utilities
clean:
	@echo "Cleaning up generated files and caches..."
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

status:
	@echo "Cage Platform Status:"
	@echo "====================="
	@echo "Python version: $(shell python3 --version 2>/dev/null || echo 'Not installed')"
	@echo "Virtual environment: $(shell if [ -d "venv" ]; then echo "✅ Active"; else echo "❌ Not found"; fi)"
	@echo "Dependencies: $(shell if python -c "import pytest" 2>/dev/null; then echo "✅ Installed"; else echo "❌ Missing"; fi)"
	@echo "Podman: $(shell if command -v podman > /dev/null; then echo "✅ Available"; else echo "❌ Not found"; fi)"
	@echo ""
	@echo "Active Tasks:"
	@if [ -d ".cursor/tasks" ]; then \
		echo "✅ Cursor tasks directory found"; \
		ls -la .cursor/tasks/ 2>/dev/null | grep -v "^total" | head -5 || echo "No task files found"; \
	else \
		echo "❌ Cursor tasks directory not found"; \
	fi

# Pre-commit hooks
pre-commit: check-format lint test-fast
	@echo "✅ Pre-commit checks passed!"

# CI/CD pipeline
ci: check-deps check-format lint test test-coverage
	@echo "✅ CI pipeline completed successfully!"

# Development workflow
dev: setup-dev
	@echo "Development environment ready!"
	@echo "Next steps:"
	@echo "  1. Activate devbox environment: devbox shell"
	@echo "  2. Run tests: make test"
	@echo "  3. Start development: make podman-run"

# Devbox shell
devbox-shell: check-devbox
	@echo "Starting devbox shell..."
	@echo "This will activate the development environment with all dependencies."
	@echo "Type 'exit' to leave the shell."
	devbox shell

# Quick start for new developers
quickstart: dev
	@echo "🚀 Quick start complete!"
	@echo "Run 'make help' to see all available commands"
