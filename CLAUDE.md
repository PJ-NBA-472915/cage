# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cage is a **pod-based multi-agent repository service** that provides AI-powered development capabilities through a microservices architecture. It uses the **Model Context Protocol (MCP)** as the sole external entrypoint, with internal microservices handling file operations, Git management, RAG queries, and CrewAI agent orchestration.

**Key Philosophy**: Files are the source of truth. The repository working tree is authoritative, with PostgreSQL and Redis serving as ephemeral/cached data stores that can be rebuilt from files.

## Common Commands

### Docker Operations (Primary Development Workflow)

```bash
# Start all services (required for development)
docker compose --profile dev up -d --build

# View service status
docker compose --profile dev ps

# View logs for a specific service
docker compose --profile dev logs -f files-api
docker compose --profile dev logs -f mcp

# Restart a service after code changes
docker compose --profile dev restart files-api

# Stop all services
docker compose --profile dev down

# Complete reset (clean volumes)
docker compose --profile dev down -v
```

### Testing

Testing infrastructure has been temporarily removed to reduce development overhead. Critical tests will be re-added once project goals and direction are clarified.

### Local Development (Individual Services)

```bash
# Install dependencies
uv sync

# Run individual services locally (for debugging)
cd src/apps/files_api && uvicorn main:app --host 0.0.0.0 --port 8010 --reload
cd src/apps/git_api && uvicorn main:app --host 0.0.0.0 --port 8011 --reload
cd src/apps/rag_api && uvicorn main:app --host 0.0.0.0 --port 8012 --reload
cd src/apps/lock_api && uvicorn main:app --host 0.0.0.0 --port 8013 --reload
cd src/apps/crew_api && uvicorn main:app --host 0.0.0.0 --port 8014 --reload

# Run MCP server
python -m src.cage.mcp.server --host 0.0.0.0 --port 8765 --log-level INFO
```

### Configuration

```bash
# Set required environment variables
export POD_TOKEN="your-secret-token-here"
export REPO_PATH="/path/to/your/repository"
export OPENAI_API_KEY="your-openai-key"  # Optional, for RAG

# Create .env from template
make config-example
```

### Health Checks

```bash
# Check all service health
curl http://localhost:8010/health  # Files API
curl http://localhost:8011/health  # Git API
curl http://localhost:8012/health  # RAG API
curl http://localhost:8013/health  # Lock API
curl http://localhost:8014/health  # Crew API
curl http://localhost:8765/mcp/health  # MCP Server

# Or use Makefile
make health-check
```

## Architecture

### Network Isolation & Security Model

Cage implements **strict network isolation** with two networks:

**External Network (cage-external)**:
- **MCP Server** (port 8765) - ONLY externally accessible service
- Grafana (port 3000) - Observability UI (dev mode only)
- Traefik (ports 80, 443, 8080) - Reverse proxy with HTTPS

**Internal Network (cage-internal)**:
- All microservices communicate only on this network
- PostgreSQL (with pgvector extension)
- Redis (caching + locks)
- Logging stack (Loki, Promtail)

**Security Principles**:
- External agents can ONLY access the MCP server
- MCP server exposes ONLY crew/agent/run management tools
- File and Git operations performed by crews/agents internally
- No direct file or Git access through MCP
- All writes via Editor Tool (no raw shell access)
- Bearer token authentication for all services

### Service Architecture

```
External Agents (Claude, Manager)
         │
         ↓ MCP (port 8765)
    MCP Server (ONLY external-facing)
         │
         ↓ crew management
      Crew API
         │
         ↓ orchestrates
  CrewAI Orchestrator
  (planner → implementer → reviewer → committer)
         │
         ↓ uses internal APIs
┌────────┴────────┬────────┬────────┐
│                 │        │        │
Files API    Git API   RAG API   Lock API
(editor)    (commits) (pgvector) (templates)
│
↓
Repository Working Tree (source of truth)
```

### Services & Ports

| Service | Port | Purpose | Network |
|---------|------|---------|---------|
| **files-api** | 8010 | File operations with Editor Tool | Internal only |
| **git-api** | 8011 | Git operations & commits | Internal only |
| **rag-api** | 8012 | Semantic search with OpenAI embeddings | Internal only |
| **lock-api** | 8013 | Application generation & templates (Golang) | Internal only |
| **crew-api** | 8014 | AI agent & crew management | Internal only |
| **mcp** | 8765 | Model Context Protocol gateway | External + Internal |
| **postgres** | 6432 | Database with pgvector | Internal only |
| **redis** | 6379 | Caching & sessions | Internal only |
| **traefik** | 80, 443, 8080 | Reverse proxy with HTTPS | External + Internal |

### Key Components

**Editor Tool** (`src/cage/tools/editor_tool.py`):
- Structured file operations: GET, INSERT, UPDATE, DELETE
- Selectors: region (line ranges), regex, (AST planned)
- File locking with optimistic concurrency control
- All file modifications logged with provenance
- Pre/post hash tracking for conflict detection

**Git Tool** (`src/cage/tools/git_tool.py`):
- Git operations: status, branch, commit, push, merge
- Task provenance tracking in commits
- No raw shell access - all operations via structured API

**Task System** (`src/cage/models/task_*.py`):
- JSON task files with validation
- Progress tracking and provenance
- Changelog with file operation history
- Stored in repository as `.cage/tasks/`

**CrewAI Integration** (`src/cage/agents/`):
- Modular agent system with roles: planner, implementer, reviewer, committer
- Individual agent testing support
- Dynamic crew construction
- Bridges to internal services (FilesBridge, LocksBridge)

**RAG System**:
- Semantic search over code and tasks
- OpenAI embeddings stored in pgvector
- Redis caching for performance
- Can be fully rebuilt from repository files

## Development Patterns

### File Operations

Always use the Editor Tool for file modifications:

```python
from src.cage.tools.editor_tool import EditorTool, FileOperation, OperationType

editor = EditorTool(repo_path=Path("/work/repo"))

# Update a region
operation = FileOperation(
    operation=OperationType.UPDATE,
    path="src/module/foo.py",
    selector={"mode": "region", "start": 120, "end": 145},
    payload={"content": "def bar():\n    return 42\n"},
    intent="refactor: extract method",
    author="agent:implementer",
    correlation_id="task-uuid-update"
)

result = editor.execute_operation(operation)
```

### Authentication

All API requests require Bearer token:

```bash
curl -H "Authorization: Bearer $POD_TOKEN" \
     -H "X-Request-ID: $(uuidgen)" \
     http://localhost:8010/health
```

### Logging

All services use **structured JSONL logging**:

```bash
# View logs with jq for readability
tail -f logs/files-api/files-api.jsonl | jq

# Filter by log level
grep '"level":"ERROR"' logs/files-api/files-api.jsonl | jq

# Monitor all services
tail -f logs/*/*.jsonl | jq
```

Log format:
```json
{
  "ts": "2025-09-30T12:55:45.123Z",
  "level": "INFO",
  "service": "files-api",
  "request_id": "abc-123",
  "route": "/files",
  "msg": "File operation completed"
}
```

### Error Handling

All services return **RFC 7807 Problem Details** format:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 400,
  "detail": "Invalid file path",
  "instance": "/files/edit"
}
```

## Testing Strategy

**Current Status**: Testing infrastructure has been temporarily removed to reduce development overhead while clarifying project goals and direction.

**Future Plans**: Critical tests will be re-added based on:
- Clarified project objectives
- Core functionality requirements
- Integration points
- Performance and reliability needs

## Project Structure

```
cage/
├── src/
│   ├── apps/              # Microservice applications
│   │   ├── files_api/     # File operations service
│   │   ├── git_api/       # Git operations service
│   │   ├── rag_api/       # RAG/semantic search service
│   │   ├── lock_api/      # Lock & template service (Golang)
│   │   └── crew_api/      # Crew management service
│   └── cage/
│       ├── agents/        # CrewAI agent implementations
│       ├── models/        # Task and data models
│       ├── tools/         # Editor, Git, Crew tools
│       ├── mcp/           # MCP server implementation
│       └── utils/         # Shared utilities (logging, etc.)
├── memory-bank/          # Project knowledge base
│   ├── guides/           # Feature documentation
│   ├── context/spec/     # Technical specifications
│   └── reports/          # Status reports
├── docker-compose.yml    # Main orchestration file
├── Dockerfile            # Multi-stage build for all services
├── Makefile              # Development shortcuts
└── pyproject.toml        # Python dependencies & config
```

## Important Conventions

### User Permissions

Docker containers use **group-based security**:
- `cage` group: Shared group for all services
- `worker` user: Has read-write access to `/work/repo` (files-api, git-api, crew-api)
- `system` user: Read-only access, no repo access (mcp)

### Dependency Management

- **Always use `uv`** for Python dependency management
- Update dependencies in `pyproject.toml`
- Lock with `uv lock`
- Install with `uv sync`

### Code Quality

```bash
# Run formatter
uv run black src/ tests/

# Run linter
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Pre-commit hooks
make setup-precommit
```

### Configuration Profiles

Docker Compose profiles:
- `dev` - All services with hot reload
- `prod` - Production configuration
- `observability` - Adds Loki, Promtail, Grafana

```bash
# Start with observability
docker compose --profile dev --profile observability up -d
```

## MCP Integration

The MCP server provides tools for AI agents:

```bash
# List available tools
curl -X POST http://localhost:8765/mcp/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# Query RAG system
curl -X POST http://localhost:8765/mcp/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "rag_query",
      "arguments": {"query": "authentication", "limit": 5}
    }
  }'
```

## Debugging

### Remote Debugging (MCP Server)

The MCP server supports remote debugging with debugpy:

```bash
# Enable debug mode
export DEBUGPY_ENABLED=1
export DEBUGPY_WAIT_FOR_CLIENT=1  # Optional: wait for debugger

# Port 5679 is exposed for debugpy
# Connect with VS Code or PyCharm
```

### Service Logs

```bash
# Real-time logs for a service
docker compose --profile dev logs -f files-api

# Check service health
docker compose --profile dev ps
docker compose --profile dev exec files-api curl http://localhost:8000/health
```

### Database Access

```bash
# Connect to PostgreSQL
docker compose --profile dev exec postgres psql -U postgres -d cage

# Common queries
SELECT * FROM pg_extension;  # Check pgvector is installed
\dt                          # List tables
```

### Redis Access

```bash
# Connect to Redis
docker compose --profile dev exec redis redis-cli

# Common commands
KEYS *              # List all keys
GET key_name        # Get value
FLUSHALL            # Clear all (development only)
```

## Troubleshooting

**Services won't start**:
- Check `docker compose --profile dev ps` for status
- View logs: `docker compose --profile dev logs service-name`
- Verify environment variables: `echo $POD_TOKEN`
- Check port conflicts: `lsof -i :8765`

**Authentication errors**:
- Ensure POD_TOKEN is set in environment and docker-compose.yml
- Check headers include `Authorization: Bearer $POD_TOKEN`

**File operation failures**:
- Verify REPO_PATH is mounted correctly in docker-compose.yml
- Check file permissions in container
- Review file locks: may need to wait for lock expiration

**Service failures**:
- Ensure services are running: `docker compose --profile dev up -d`
- Check service logs: `docker compose --profile dev logs service-name`
- Verify environment variables are set (POD_TOKEN, REPO_PATH)

## Documentation

Comprehensive guides in `memory-bank/`:
- **Getting Started**: `memory-bank/guides/getting-started.md`
- **Debugging**: `memory-bank/guides/debugging.md`
- **Crew API**: `memory-bank/guides/features/crew-api.md`
- **MCP Server**: `memory-bank/guides/features/mcp-server.md`
- **Editor Tool**: `memory-bank/guides/features/editor-tool.md`
- **RAG System**: `memory-bank/guides/features/rag-system-implementation.md`
- **Technical Specs**: `memory-bank/context/spec/cage/100_SPLIT/*.md`

API documentation (when services running):
- Files API: http://localhost:8010/docs
- Git API: http://localhost:8011/docs
- RAG API: http://localhost:8012/docs
- Lock API: http://localhost:8013/docs
- Crew API: http://localhost:8014/docs
- MCP Server: http://localhost:8765/mcp/about
