# Cage Pod - Multi-Agent Repository Service
# Makefile for development and deployment

.PHONY: help install dev test clean docker-build docker-up docker-down docker-down-clean docker-logs docker-logs-api docker-logs-db docker-logs-redis docker-logs-mcp docker-test docker-test-unit docker-test-integration docker-test-api docker-clean docker-shell docker-db docker-redis start-api start-db start-mcp restart-api health-check rag-reindex rag-query rag-status db-init db-reset db-backup db-restore quick-start dev-docker test-docker deploy reset status update

# Default target
help:
	@echo "Cage Pod - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Start development server"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up build artifacts"
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
