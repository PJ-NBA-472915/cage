# Cage Pod - Multi-Agent Repository Service
# Makefile for development and deployment

.PHONY: help install dev test clean docker-build docker-up docker-down docker-down-clean docker-logs docker-logs-api docker-logs-db docker-logs-redis docker-logs-mcp docker-test docker-test-unit docker-test-integration docker-test-api docker-clean docker-shell docker-db docker-redis start-api start-db start-mcp restart-api health-check rag-reindex rag-query rag-status db-init db-reset db-backup db-restore quick-start dev-docker test-docker deploy reset status update

# Default target
help:
	@echo "Cage Pod - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  install    - Install dependencies with uv"
	@echo "  dev        - Start development server"
	@echo "  test       - Run all tests with coverage"
	@echo "  test-unit  - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-api   - Run API tests only"
	@echo "  test-smoke - Run smoke tests only"
	@echo "  test-parallel - Run tests in parallel"
	@echo "  test-coverage - Run tests with HTML coverage report"
	@echo "  test-files - Run files API basic tests (requires Docker)"
	@echo "  test-files-concurrency - Run files API concurrency tests (requires Docker)"
	@echo "  test-files-all - Run all files API tests (requires Docker)"
	@echo "  clean      - Clean up build artifacts"
	@echo ""
	@echo "Configuration:"
	@echo "  config-load-dev     - Load development configuration"
	@echo "  config-load-test    - Load testing configuration"
	@echo "  config-load-prod    - Load production configuration"
	@echo "  config-validate     - Validate current configuration"
	@echo "  config-example      - Create .env file from template"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build     - Build all Docker images"
	@echo "  docker-up        - Start all services with Docker Compose"
	@echo "  docker-down      - Stop all services"
	@echo "  docker-logs      - Show logs for all services"
	@echo "  docker-test      - Run tests in Docker environment"
	@echo "  docker-clean     - Clean up Docker resources"
	@echo "  docker-shell     - Open shell in Cage API container"
	@echo "  docker-db        - Connect to PostgreSQL database"
	@echo "  docker-redis     - Connect to Redis"
	@echo ""
	@echo "Service Management:"
	@echo "  start-api        - Start only Cage API service"
	@echo "  start-db         - Start only database services"
	@echo "  start-mcp        - Start only MCP server (Streamable HTTP)"
	@echo "  restart-api      - Restart Cage API service"
	@echo "  health-check     - Check health of all services"
	@echo "  status           - Show service status and resource usage"
	@echo ""
	@echo "RAG System:"
	@echo "  rag-reindex      - Reindex RAG system"
	@echo "  rag-query        - Query RAG system"
	@echo "  rag-status       - Check RAG system status"
	@echo ""
	@echo "Database:"
	@echo "  db-init          - Initialize database"
	@echo "  db-reset         - Reset database"
	@echo "  db-backup        - Backup database"
	@echo "  db-restore       - Restore database from backup"
	@echo ""
	@echo "Convenience Commands:"
	@echo "  quick-start      - Build and start all services"
	@echo "  dev-docker       - Start services and show API logs"
	@echo "  test-docker      - Run full test suite in Docker"
	@echo "  deploy           - Production deployment"
	@echo "  reset            - Complete reset and fresh start"
	@echo "  update           - Update and restart services"

# Install dependencies
install:
	@echo "Setting up virtual environment and installing dependencies with uv..."
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment with uv..."; \
		uv venv .venv; \
	fi
	@echo "Installing dependencies with uv..."
	@uv pip install --upgrade pip
	@uv pip install -r requirements.txt
	@echo "✅ Installation complete! Virtual environment ready."

# Development server
dev:
	@echo "Starting Cage development server..."
	@echo "Make sure to set REPO_PATH environment variable"
	@if [ -d .venv ]; then \
		uv run python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run all tests with coverage
test:
	@echo "Running all tests with coverage..."
	@./scripts/run-tests.sh -t all

# Run specific test types
test-unit:
	@echo "Running unit tests..."
	@./scripts/run-tests.sh -t unit

test-integration:
	@echo "Running integration tests..."
	@./scripts/run-tests.sh -t integration

test-api:
	@echo "Running API tests..."
	@./scripts/run-tests.sh -t api

test-smoke:
	@echo "Running smoke tests..."
	@./scripts/run-tests.sh -t smoke

# Run files routes tests specifically
test-files:
	@echo "Running Files API routes tests..."
	@echo "Starting files-api service..."
	@docker-compose up files-api -d --no-deps
	@echo "Waiting for service to be ready..."
	@sleep 5
	@echo "Running tests against Docker service..."
	@docker-compose exec -e POD_TOKEN=test-token files-api python tests/api/test_files_api_simple.py

# Run files routes tests with coverage
test-files-coverage:
	@echo "Running Files API routes tests with coverage..."
	@if [ -d .venv ]; then \
		uv run python -m pytest tests/api/test_files_basic.py -v --cov=src --cov-report=html --cov-report=term --tb=short -p no:cacheprovider --confcutdir=tests/api; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run files concurrency tests
test-files-concurrency:
	@echo "Running Files API concurrency and locking tests..."
	@echo "Starting files-api service..."
	@docker-compose up files-api -d --no-deps
	@echo "Waiting for service to be ready..."
	@sleep 5
	@echo "Running tests against Docker service..."
	@docker-compose exec -e POD_TOKEN=test-token files-api python tests/api/test_files_api_functionality.py

# Run files stress tests
test-files-stress:
	@echo "Running Files API stress tests..."
	@if [ -d .venv ]; then \
		uv run python -m pytest tests/api/test_files_stress.py -v --tb=short -p no:cacheprovider --confcutdir=tests/api; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

# Run all files tests (basic + concurrency + stress)
test-files-all:
	@echo "Running all Files API tests..."
	@echo "Starting files-api service..."
	@docker-compose up files-api -d --no-deps
	@echo "Waiting for service to be ready..."
	@sleep 5
	@echo "Running basic tests..."
	@docker-compose exec -e POD_TOKEN=test-token files-api python tests/api/test_files_api_simple.py
	@echo "Running functionality tests..."
	@docker-compose exec -e POD_TOKEN=test-token files-api python tests/api/test_files_api_functionality.py


# Run all tests including Docker-based file editing tests
test-complete:
	@echo "Running complete test suite..."
	@./scripts/run-tests.sh -t all

# Run tests with HTML coverage report
test-coverage:
	@echo "Running tests with HTML coverage report..."
	@./scripts/run-tests.sh -t all -o html

# Run tests in parallel
test-parallel:
	@echo "Running tests in parallel..."
	@./scripts/run-tests.sh -t all -p

# Install test dependencies
test-deps:
	@echo "Installing test dependencies..."
	@uv sync --extra dev

# Run all tests with full reporting
test-all:
	@echo "Running all tests with full reporting..."
	@./scripts/run-tests.sh -t all -v

# Configuration management
config-load-dev:
	@echo "Loading development configuration..."
	@./scripts/load-config.sh -e development -v

config-load-test:
	@echo "Loading testing configuration..."
	@./scripts/load-config.sh -e testing -v

config-load-prod:
	@echo "Loading production configuration..."
	@./scripts/load-config.sh -e production -v

config-validate:
	@echo "Validating configuration..."
	@./scripts/load-config.sh --validate -v

config-example:
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then \
		cp config/environment.example .env; \
		echo "✅ Created .env file from template"; \
		echo "📝 Please edit .env file with your configuration"; \
	else \
		echo "⚠️  .env file already exists"; \
		echo "📝 If you want to recreate it, delete .env first"; \
	fi

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf src/*/__pycache__/
	rm -rf .pytest_cache/
	rm -rf logs/
	find . -name "*.pyc" -delete

# Docker Commands

# Build all Docker images
docker-build:
	@echo "Building all Docker images..."
	docker-compose build --no-cache

# Start all services with Docker Compose
docker-up:
	@echo "Starting all services with Docker Compose..."
	docker-compose up -d
	@echo "✅ Services started. API available at http://localhost:8000"
	@echo "   Health check: http://localhost:8000/health"

# Stop all services
docker-down:
	@echo "Stopping all services..."
	docker-compose down

# Stop all services and remove volumes
docker-down-clean:
	@echo "Stopping all services and removing volumes..."
	docker-compose down -v

# Show logs for all services
docker-logs:
	docker-compose logs -f

# Show logs for specific service
docker-logs-api:
	docker-compose logs -f api

docker-logs-db:
	docker-compose logs -f postgres

docker-logs-redis:
	docker-compose logs -f redis

docker-logs-mcp:
	docker-compose logs -f mcp

# Run tests in Docker environment
docker-test:
	@echo "Running tests in Docker environment..."
	docker-compose exec api python scripts/test-rag-system.py

# Run specific test types in Docker
docker-test-unit:
	docker-compose exec api python tests/run_tests.py unit -v

docker-test-integration:
	docker-compose exec api python tests/run_tests.py integration -v

docker-test-api:
	docker-compose exec api python tests/run_tests.py api -v

# Clean up Docker resources
docker-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

# Open shell in Cage API container
docker-shell:
	docker-compose exec api /bin/bash

# Connect to PostgreSQL database
docker-db:
	docker-compose exec postgres psql -U postgres -d cage

# Connect to Redis
docker-redis:
	docker-compose exec redis redis-cli

# Service Management

# Start only Cage API service
start-api:
	docker-compose up -d api

# Start only database services
start-db:
	docker-compose up -d postgres redis

# Start only MCP server
start-mcp:
	docker-compose up -d mcp

# Restart Cage API service
restart-api:
	docker-compose restart api

# Check health of all services
health-check:
	@echo "Checking service health..."
	@echo "Cage API:"
	@curl -s http://localhost:8000/health | jq . || echo "❌ API not responding"
	@echo ""
	@echo "PostgreSQL:"
	@docker-compose exec postgres pg_isready -U postgres || echo "❌ PostgreSQL not ready"
	@echo ""
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "❌ Redis not responding"

# RAG System Commands

# Reindex RAG system
rag-reindex:
	@echo "Reindexing RAG system..."
	@curl -X POST http://localhost:8000/rag/reindex \
		-H "Authorization: Bearer dev-token" \
		-H "Content-Type: application/json" \
		-d '{"scope": "all"}' | jq .

# Query RAG system
rag-query:
	@echo "Querying RAG system..."
	@curl -X POST http://localhost:8000/rag/query \
		-H "Authorization: Bearer dev-token" \
		-H "Content-Type: application/json" \
		-d '{"query": "hello world function", "top_k": 5}' | jq .

# Check RAG system status
rag-status:
	@echo "Checking RAG system status..."
	@curl -s http://localhost:8000/health | jq .last_index_at

# Database Commands

# Initialize database
db-init:
	@echo "Initializing database..."
	docker-compose exec postgres psql -U postgres -d cage -f /docker-entrypoint-initdb.d/init-db.sql

# Reset database
db-reset:
	@echo "Resetting database..."
	docker-compose down -v
	docker-compose up -d postgres
	sleep 10
	$(MAKE) db-init

# Backup database
db-backup:
	@echo "Backing up database..."
	docker-compose exec postgres pg_dump -U postgres cage > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Restore database
db-restore:
	@echo "Restoring database from backup..."
	@if [ -z "$$BACKUP_FILE" ]; then \
		echo "Please set BACKUP_FILE environment variable"; \
		exit 1; \
	fi
	docker-compose exec -T postgres psql -U postgres cage < $$BACKUP_FILE

# Convenience Commands

# Quick start - build and start all services
quick-start: docker-build docker-up
	@echo "✅ Cage system started! API available at http://localhost:8000"

# Development workflow - start services and show logs
dev-docker: docker-up docker-logs-api

# Full test suite in Docker
test-docker: docker-up docker-test
	@echo "✅ All tests completed in Docker environment"

# Production deployment
deploy: docker-build docker-up health-check
	@echo "✅ Production deployment complete"

# Complete reset - clean everything and start fresh
reset: docker-clean docker-build docker-up
	@echo "✅ Complete reset and fresh start completed"

# Show service status
status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Resource Usage:"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Update and restart services
update: docker-down docker-build docker-up
	@echo "✅ Services updated and restarted"
