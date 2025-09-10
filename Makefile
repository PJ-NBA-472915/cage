# Cage Pod - Multi-Agent Repository Service
# Makefile for development and deployment

.PHONY: help install dev test clean build run stop logs

# Default target
help:
	@echo "Cage Pod - Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Start development server"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up build artifacts"
	@echo "  build      - Build container image"
	@echo "  run        - Run container"
	@echo "  stop       - Stop container"
	@echo "  logs       - Show container logs"

# Install dependencies
install:
	@echo "Setting up virtual environment and installing dependencies..."
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Activating virtual environment and installing dependencies..."
	@. .venv/bin/activate && pip install --upgrade pip
	@. .venv/bin/activate && pip install -r requirements.txt
	@. .venv/bin/activate && pip install -r requirements-test.txt
	@echo "✅ Installation complete! Virtual environment ready."

# Development server
dev:
	@echo "Starting Cage development server..."
	@echo "Make sure to set REPO_PATH environment variable"
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run tests
test:
	@echo "Running complete test suite in virtual environment..."
	@if [ -f .venv/bin/activate ]; then \
		echo "Activating virtual environment..."; \
		. .venv/bin/activate && python tests/run_tests.py; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run specific test types
test-unit:
	@echo "Running unit tests..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py unit -v; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

test-integration:
	@echo "Running integration tests..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py integration -v; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

test-api:
	@echo "Running API tests..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py api -v; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

test-cli:
	@echo "Running CLI tests..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py cli -v; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py all -v --coverage; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run tests in parallel
test-parallel:
	@echo "Running tests in parallel..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py all -v --parallel; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Install test dependencies
test-deps:
	@echo "Installing test dependencies..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && pip install -r requirements-test.txt; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run all tests with full reporting
test-all:
	@echo "Running all tests with full reporting..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python tests/run_tests.py all -v --coverage --parallel; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf src/*/__pycache__/
	rm -rf .pytest_cache/
	rm -rf logs/
	find . -name "*.pyc" -delete

# Build container image
build:
	podman build -t cage-pod:latest .

# Run container
run:
	podman run -d \
		--name cage-pod \
		-p 8000:8000 \
		-v $(PWD)/repo:/work/repo \
		-e REPO_PATH=/work/repo \
		-e POD_ID=dev-pod \
		-e POD_TOKEN=dev-token \
		cage-pod:latest

# Stop container
stop:
	podman stop cage-pod || true
	podman rm cage-pod || true

# Show logs
logs:
	podman logs -f cage-pod

# Development with podman-compose
dev-compose:
	podman-compose up --build

# Stop development
dev-stop:
	podman-compose down