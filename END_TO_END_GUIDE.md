# Cage: Complete End-to-End Usage Guide

This guide provides a comprehensive walkthrough of the Cage system based on the current implementation. Cage is a Pod-based Multi-Agent Repository Service that provides task management, file editing, Git integration, and AI agent orchestration.

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation & Setup](#installation--setup)
4. [Quick Start](#quick-start)
5. [Core Features](#core-features)
6. [API Reference](#api-reference)
7. [CLI Reference](#cli-reference)
8. [Advanced Workflows](#advanced-workflows)
9. [Troubleshooting](#troubleshooting)
10. [Development](#development)

## System Overview

Cage is designed as a single-repository microservice that provides:

- **Task Management**: JSON-based task files with progress tracking
- **Editor Tool**: Structured file operations (GET/INSERT/UPDATE/DELETE) with locking
- **Git Integration**: Comprehensive Git operations with commit trail tracking
- **CrewAI Integration**: AI agent workflows for planning and execution
- **RAG System**: Vector search and embeddings for code and documentation
- **REST API**: Complete API surface for programmatic access
- **CLI Tools**: Command-line interface for interactive management

### Current Implementation Status

✅ **Phase 1: Task File System** - Complete

✅ **Phase 2: Editor Tool** - Complete  

✅ **Phase 3: Git Integration** - Complete

✅ **Phase 4: CrewAI Integration** - Complete

✅ **Phase 5: RAG System** - Complete

🚧 **Phase 6: Production Features** - In Progress

## Prerequisites

### System Requirements
- Python 3.11+
- Git
- Podman (preferred) or Docker
- PostgreSQL 13+ (with pgvector extension)
- Redis 6+

### Environment Variables
```bash
# Required
REPO_PATH=/path/to/your/repository
POD_TOKEN=your-secure-token
DATABASE_URL=postgresql://user:password@localhost:5432/cage
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-openai-api-key

# Optional
POD_ID=your-pod-id
EMBEDDINGS_PROVIDER=openai
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

## Installation & Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd cage

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Start PostgreSQL and Redis (using Docker/Podman)
make start-db

# Initialize database with pgvector extension
make db-init
```

### 3. Environment Configuration

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your configuration
```

## Quick Start

### 1. Start the System

```bash
# Option A: Start all services with Docker Compose
make quick-start

# Option B: Start services individually
make start-db
make start-api
```

### 2. Verify Installation

```bash
# Check health
curl -H "Authorization: Bearer dev-token" http://localhost:8000/health

# Check status
make status
```

### 3. Create Your First Task

```bash
# Using CLI
python -m src.cli.main task-create 2025-09-11-hello-world "Hello World Task" \
  --summary "My first Cage task" \
  --tags "example,demo"

# Using API
curl -X POST -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "2025-09-11-api-task", "status": "confirmed"}' \
  http://localhost:8000/tasks/confirm
```

## Core Features

### 1. Task Management System

The task management system provides complete lifecycle management for tasks with JSON-based storage and validation.

#### Key Components:
- **Task Files**: JSON files in `tasks/` directory with Pydantic validation
- **Progress Tracking**: Automatic progress calculation based on completed todo items
- **Status Management**: Task status transitions (planned → in-progress → done)
- **Metadata**: Rich metadata including timestamps, tags, and provenance

#### Task File Structure:
```json
{
  "id": "2025-09-11-example-task",
  "title": "Example Task",
  "status": "in-progress",
  "progress_percent": 50,
  "created_at": "2025-09-11 10:00",
  "updated_at": "2025-09-11 10:30",
  "summary": "Task description",
  "tags": ["example", "demo"],
  "todo": [
    {
      "text": "Complete step 1",
      "status": "done",
      "date_started": "2025-09-11 10:00",
      "date_stopped": "2025-09-11 10:15"
    }
  ],
  "changelog": [
    {
      "timestamp": "2025-09-11 10:00",
      "text": "Task created"
    }
  ]
}
```

### 2. Editor Tool System

The editor tool provides structured file operations with multi-agent locking for safe concurrent access.

#### Key Features:
- **Structured Operations**: GET/INSERT/UPDATE/DELETE operations with selector-based targeting
- **File Locking**: Redis-based locking mechanism for concurrent access
- **Conflict Detection**: Stale preimage checking to prevent conflicts
- **Task Integration**: Operations are tracked in task files

#### Supported Operations:
- **GET**: Retrieve file content or specific sections
- **INSERT**: Add content at specific locations
- **UPDATE**: Modify existing content
- **DELETE**: Remove content or entire files

### 3. Git Integration

Comprehensive Git operations with commit trail tracking and integration with the task system.

#### Key Features:
- **Branch Management**: Create, switch, and merge branches
- **Commit Operations**: Staged commits with detailed messages
- **History Tracking**: Complete commit history and diff tracking
- **Task Integration**: Git operations are logged in task provenance

### 4. CrewAI Integration

AI agent workflows for automated task planning, implementation, and review.

#### Key Features:
- **Agent Teams**: Planner, Implementer, Reviewer, and Committer agents
- **Workflow Orchestration**: Automated task execution workflows
- **Code Generation**: AI-powered code generation and modification
- **Review Process**: Automated code review and quality checks

### 5. RAG System

Retrieval-Augmented Generation system with vector search and embeddings.

#### Key Features:
- **Vector Search**: PostgreSQL with pgvector for semantic search
- **Code Indexing**: Intelligent chunking for code and documentation
- **Redis Caching**: Hot indexes for fast retrieval
- **Metadata Tracking**: Complete blob metadata with commit SHAs

## API Reference

### Authentication
All API endpoints require Bearer token authentication:
```bash
curl -H "Authorization: Bearer your-token" http://localhost:8000/endpoint
```

### Core Endpoints

#### Health & Status
```bash
# Health check
GET /health

# System status
GET /status

# About information
GET /about
```

#### Task Management
```bash
# List all tasks
GET /tasks

# Get specific task
GET /tasks/{task_id}

# Create task
POST /tasks
{
  "task_id": "2025-09-11-example",
  "title": "Example Task",
  "summary": "Task description",
  "tags": ["example"]
}

# Update task
PUT /tasks/{task_id}
{
  "status": "in-progress",
  "progress_percent": 50
}

# Delete task
DELETE /tasks/{task_id}
```

#### Editor Operations
```bash
# Get file content
GET /editor/files/{file_path}

# Insert content
POST /editor/files/{file_path}/insert
{
  "content": "New content",
  "position": 10
}

# Update content
PUT /editor/files/{file_path}/update
{
  "content": "Updated content",
  "selector": "line:10-15"
}

# Delete content
DELETE /editor/files/{file_path}/delete
{
  "selector": "line:10-15"
}
```

#### Git Operations
```bash
# Get Git status
GET /git/status

# Create branch
POST /git/branches
{
  "name": "feature-branch",
  "base": "main"
}

# Commit changes
POST /git/commit
{
  "message": "Commit message",
  "files": ["file1.py", "file2.py"]
}

# Get commit history
GET /git/history
```

#### RAG System
```bash
# Query RAG system
POST /rag/query
{
  "query": "How does authentication work?",
  "top_k": 5
}

# Reindex repository
POST /rag/reindex

# Get RAG status
GET /rag/status
```

## CLI Reference

### Task Management Commands

```bash
# Create a new task
python -m src.cli.main task-create <task-id> <title> [options]

# List all tasks
python -m src.cli.main task-list

# Show task details
python -m src.cli.main task-show <task-id>

# Update task
python -m src.cli.main task-update <task-id> [options]

# Delete task
python -m src.cli.main task-delete <task-id>
```

### Editor Commands

```bash
# Get file content
python -m src.cli.main editor-get <file-path>

# Insert content
python -m src.cli.main editor-insert <file-path> <content> --position <line>

# Update content
python -m src.cli.main editor-update <file-path> <content> --selector <selector>

# Delete content
python -m src.cli.main editor-delete <file-path> --selector <selector>
```

### Git Commands

```bash
# Git status
python -m src.cli.main git-status

# Create branch
python -m src.cli.main git-branch <name> [base]

# Commit changes
python -m src.cli.main git-commit <message> [files...]

# Show history
python -m src.cli.main git-history
```

### CrewAI Commands

```bash
# Run workflow
python -m src.cli.main crew-run <workflow-name> [options]

# List workflows
python -m src.cli.main crew-list

# Show workflow details
python -m src.cli.main crew-show <workflow-name>
```

### RAG Commands

```bash
# Query RAG system
python -m src.cli.main rag-query <query> [options]

# Reindex repository
python -m src.cli.main rag-reindex

# RAG status
python -m src.cli.main rag-status
```

## Advanced Workflows

### 1. Complete Development Workflow

```bash
# 1. Create a new task
python -m src.cli.main task-create 2025-09-11-feature-implementation "Implement New Feature"

# 2. Start working on the task
python -m src.cli.main task-update 2025-09-11-feature-implementation --status in-progress

# 3. Create a feature branch
python -m src.cli.main git-branch feature/new-feature main

# 4. Make code changes using editor
python -m src.cli.main editor-insert src/new_feature.py "def new_function():\n    pass" --position 1

# 5. Query RAG for help
python -m src.cli.main rag-query "How to implement authentication in Python?"

# 6. Run CrewAI workflow for code review
python -m src.cli.main crew-run code-review --task 2025-09-11-feature-implementation

# 7. Commit changes
python -m src.cli.main git-commit "Add new feature implementation"

# 8. Mark task as complete
python -m src.cli.main task-update 2025-09-11-feature-implementation --status done
```

### 2. Multi-Agent Collaboration

```bash
# Agent 1: Creates task and starts work
python -m src.cli.main task-create 2025-09-11-collaborative-task "Collaborative Task"
python -m src.cli.main task-update 2025-09-11-collaborative-task --status in-progress

# Agent 2: Checks for available work
python -m src.cli.main task-list --status in-progress

# Agent 2: Locks file for editing
python -m src.cli.main editor-lock src/shared_file.py

# Agent 2: Makes changes
python -m src.cli.main editor-update src/shared_file.py "Updated content" --selector "line:10-15"

# Agent 2: Releases lock
python -m src.cli.main editor-unlock src/shared_file.py

# Agent 1: Reviews changes and commits
python -m src.cli.main git-commit "Collaborative changes"
```

### 3. RAG-Powered Development

```bash
# 1. Index your codebase
python -m src.cli.main rag-reindex

# 2. Query for specific patterns
python -m src.cli.main rag-query "How is error handling implemented in this codebase?"

# 3. Get code examples
python -m src.cli.main rag-query "Show me examples of API endpoint implementations"

# 4. Find related code
python -m src.cli.main rag-query "Find all functions that use the database connection"
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check database status
make status

# Restart database
make restart-db

# Check logs
make docker-logs-db
```

#### 2. Redis Connection Issues
```bash
# Check Redis status
make status

# Restart Redis
make restart-redis

# Check logs
make docker-logs-redis
```

#### 3. API Authentication Issues
```bash
# Verify POD_TOKEN is set
echo $POD_TOKEN

# Check API logs
make docker-logs-api
```

#### 4. File Locking Issues
```bash
# Check for stale locks
python -m src.cli.main editor-status

# Clear all locks (use with caution)
python -m src.cli.main editor-clear-locks
```

### Logs and Debugging

```bash
# View all logs
make docker-logs

# View specific service logs
make docker-logs-api
make docker-logs-db
make docker-logs-redis

# Check system status
make status

# Health check
curl -H "Authorization: Bearer dev-token" http://localhost:8000/health
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run specific test suites
make test-unit
make test-integration
make test-api

# Run with coverage
make test-coverage
```

### Development Server

```bash
# Start development server with auto-reload
make dev

# Or manually
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality

```bash
# Run linting
make lint

# Format code
make format

# Type checking
make type-check
```

### Database Management

```bash
# Initialize database
make db-init

# Reset database
make db-reset

# Backup database
make db-backup

# Restore database
make db-restore
```

## Next Steps

1. **Explore the API**: Use the Postman collection (`cage-api-complete-postman-collection.json`) to explore all available endpoints
2. **Try the CLI**: Experiment with different CLI commands to understand the system capabilities
3. **Create Workflows**: Build custom workflows using the CrewAI integration
4. **Index Your Code**: Use the RAG system to index and search your codebase
5. **Monitor Progress**: Use the task management system to track your work

## Support

- **Documentation**: Check the `memory-bank/docs/` directory for detailed feature documentation
- **Specifications**: Review `memory-bank/context/spec/cage/` for complete system specifications
- **Issues**: Report issues through the project's issue tracker
- **Community**: Join the project's community discussions

---

This guide covers the complete end-to-end usage of the Cage system. The system is designed to be flexible and extensible, allowing you to build sophisticated multi-agent workflows for repository management and code development.
