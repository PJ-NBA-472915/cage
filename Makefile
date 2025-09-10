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
	pip install -r requirements.txt

# Development server
dev:
	@echo "Starting Cage development server..."
	@echo "Make sure to set REPO_PATH environment variable"
	python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	python tests/run_tests.py

# Run specific test types
test-unit:
	python tests/run_tests.py unit -v

test-integration:
	python tests/run_tests.py integration -v

test-api:
	python tests/run_tests.py api -v

test-cli:
	python tests/run_tests.py cli -v

# Run tests with coverage
test-coverage:
	python tests/run_tests.py all -v --coverage

# Run tests in parallel
test-parallel:
	python tests/run_tests.py all -v --parallel

# Install test dependencies
test-deps:
	pip install -r requirements-test.txt

# Run all tests with full reporting
test-all:
	python tests/run_tests.py all -v --coverage --parallel

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