# Cage Pod - Multi-Agent Repository Service
# Makefile for development and deployment

.PHONY: help install dev clean docker-build docker-up docker-down docker-down-clean docker-logs docker-logs-api docker-logs-db docker-logs-redis docker-logs-mcp docker-clean docker-shell docker-db docker-redis start-api start-db start-mcp restart-api health-check rag-reindex rag-reindex-paths rag-query rag-status db-init db-reset db-backup db-restore quick-start dev-docker deploy reset status update start ollama-pull-model ollama-list-models ollama-status

# Default target
help:
	@echo "Cage Pod - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  install    - Install dependencies with uv"
	@echo "  dev        - Start development server"
	@echo "  clean      - Clean up build artifacts"
	@echo ""
	@echo "Configuration:"
	@echo "  config-load-dev     - Load development configuration"
	@echo "  config-load-prod    - Load production configuration"
	@echo "  config-validate     - Validate current configuration"
	@echo "  config-example      - Create .env file from template"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build     - Build all Docker images"
	@echo "  docker-up        - Start all services with Docker Compose"
	@echo "  docker-down      - Stop all services"
	@echo "  docker-logs      - Show logs for all services"
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
	@echo "  rag-reindex      - Reindex RAG system (memory-bank)"
	@echo "  rag-reindex-paths - Reindex RAG system with custom paths (use PATHS=\"src/\" \"docs/\")"
	@echo "  rag-query        - Query RAG system"
	@echo "  rag-status       - Check RAG system status"
	@echo ""
	@echo "Ollama:"
	@echo "  ollama-pull-model   - Pull Ollama embedding model (bge-code-v1)"
	@echo "  ollama-list-models  - List installed Ollama models"
	@echo "  ollama-status       - Check Ollama service status and model availability"
	@echo ""
	@echo "Database:"
	@echo "  db-init          - Initialize database"
	@echo "  db-reset         - Reset database"
	@echo "  db-backup        - Backup database"
	@echo "  db-restore       - Restore database from backup"
	@echo ""
	@echo "Convenience Commands:"
	@echo "  start       			- Start all services (including observability)"
	@echo "  dev-docker       - Start services and show API logs"
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

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf src/*/__pycache__/
	rm -rf logs/
	find . -name "*.pyc" -delete

# Docker Commands

# Build all Docker images
docker-build:
	@echo "Building all Docker images..."
	docker-compose --profile dev --profile observability build --no-cache

# Start all services with Docker Compose
docker-up:
	@echo "Starting all services with Docker Compose..."
	docker-compose up -d
	@echo "✅ Services started. API available at http://localhost:8000"
	@echo "   Health check: http://localhost:8000/health"

# Start alias (includes observability stack)
start:
	@echo "Starting all services (including observability) with Docker Compose..."
	docker compose --profile dev --profile observability up -d --force-recreate
	@echo "✅ All services started, including observability (grafana, loki, promtail, traefik)"

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
	@docker exec cage-rag-api-1 curl -X POST http://localhost:8000/reindex \
		-H "Authorization: Bearer $$(docker exec cage-rag-api-1 env | grep POD_TOKEN | cut -d= -f2)" \
		-H "Content-Type: application/json" \
		-d '{"paths": ["memory-bank"], "force": true}' | jq .

# Reindex RAG system with custom paths
rag-reindex-paths:
	@echo "Reindexing RAG system with paths: $(PATHS)"
	@docker exec cage-rag-api-1 curl -X POST http://localhost:8000/reindex \
		-H "Authorization: Bearer $$(docker exec cage-rag-api-1 env | grep POD_TOKEN | cut -d= -f2)" \
		-H "Content-Type: application/json" \
		-d '{"paths": [$(PATHS)], "force": true}' | jq .

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

# Ollama Commands
ollama-pull-model:  ## Pull Ollama embedding model (bge-code-v1)
	@./scripts/pull-ollama-model.sh

ollama-list-models:  ## List installed Ollama models
	@docker compose exec ollama ollama list

ollama-status:  ## Check Ollama service status and model availability
	@echo "Checking Ollama service health..."
	@docker compose ps ollama
	@echo ""
	@echo "Installed models:"
	@docker compose exec ollama ollama list || echo "Ollama service not running"

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
