# Cage: Pod-based Multi-Agent Repository Service

Cage is a comprehensive AI-powered development platform with microservices for file operations, RAG queries, crew management, Git operations, and Model Context Protocol (MCP) integration.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.11+ (for local development)
- `uv` package manager

### Start the Platform

```bash
# Set environment variables
export POD_TOKEN="your-secret-token-here"
export REPO_PATH="/path/to/your/repository"  # Optional
export OPENAI_API_KEY="your-openai-key"      # Optional

# Start all services
docker-compose --profile dev up -d --build

# Verify services are running
docker-compose --profile dev ps
```

### Verify Installation

```bash
# Test service health
curl http://localhost:8010/health  # Files API
curl http://localhost:8011/health  # Git API
curl http://localhost:8012/health  # RAG API
curl http://localhost:8013/health  # Lock API
curl http://localhost:8014/health  # Crew API
curl http://localhost:8765/mcp/health  # MCP Server
```

## 📋 Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| **files-api** | 8010 | File operations & content management |
| **git-api** | 8011 | Git operations & repository management |
| **rag-api** | 8012 | Retrieval-Augmented Generation & semantic search |
| **lock-api** | 8013 | Application generation & templating |
| **crew-api** | 8014 | AI agent & crew management |
| **mcp** | 8765 | Model Context Protocol integration |
| **postgres** | 6432 | Primary database with vector support |
| **redis** | 6379 | Caching & session storage |

## 🔑 Key Features

- **Task Management**: JSON task files with validation, progress, and provenance
- **Editor Tool**: Structured file ops (GET/INSERT/UPDATE/DELETE) with locking
- **Git Integration**: Status/branch/commit/push/merge with provenance
- **CrewAI Workflow**: Modular agent system with individual testing and dynamic crew construction
- **RAG System**: Semantic search over code/tasks with OpenAI embeddings (pgvector + Redis)
- **REST API**: Endpoints for tasks, files, git, crew, rag, and individual agent testing
- **MCP Server**: Streamable HTTP MCP server exposing RAG query as a tool
- **Standardized Logging**: Structured JSONL logging across all services
- **Authentication**: Token-based authentication with request tracing
- **Error Handling**: RFC 7807 Problem Details format

## 📚 Documentation

### Getting Started
- **[Getting Started Guide](memory-bank/guides/getting-started.md)**: Detailed setup instructions
- **[Debugging Guide](memory-bank/guides/debugging.md)**: Troubleshooting and debugging services

### Service Documentation
- **[Crew API](memory-bank/guides/features/crew-api.md)**: AI agent and crew management
- **[MCP Server](memory-bank/guides/features/mcp-server.md)**: Model Context Protocol integration
- **[Task Manager](memory-bank/guides/features/task-manager.md)**: Task management system
- **[Editor Tool](memory-bank/guides/features/editor-tool.md)**: File editing operations
- **[Git Integration](memory-bank/guides/features/git-integration.md)**: Git operations
- **[RAG System](memory-bank/guides/features/rag-system-implementation.md)**: Semantic search

### Project Context
- **[Memory Bank](memory-bank/readme.md)**: Project knowledge base and context
- **[Platform Status](memory-bank/reports/platform-status.md)**: Current platform status

## 🧪 Testing

Testing infrastructure has been temporarily removed. Tests will be re-added as the project goals and direction are clarified.

## 🔧 Development

### Local Development (Individual Services)

```bash
# Install dependencies
uv sync

# Run individual services
cd src/apps/files_api && uvicorn main:app --host 0.0.0.0 --port 8010 --reload
cd src/apps/git_api && uvicorn main:app --host 0.0.0.0 --port 8011 --reload
cd src/apps/rag_api && uvicorn main:app --host 0.0.0.0 --port 8012 --reload
cd src/apps/lock_api && uvicorn main:app --host 0.0.0.0 --port 8013 --reload
cd src/apps/crew_api && uvicorn main:app --host 0.0.0.0 --port 8014 --reload

# MCP Server
python -m src.cage.mcp.server --host 0.0.0.0 --port 8765 --log-level INFO
```

### Docker Development

```bash
# Start specific services
docker-compose --profile dev up files-api rag-api -d

# View logs
docker-compose --profile dev logs -f files-api

# Rebuild service
docker-compose --profile dev build files-api

# Stop all services
docker-compose --profile dev down
```

## 📊 Monitoring & Logging

All services use structured JSONL logging:

```bash
# View real-time logs
tail -f logs/files-api/files-api.jsonl | jq

# Filter by log level
grep '"level":"ERROR"' logs/files-api/files-api.jsonl | jq

# Monitor all services
tail -f logs/*/*.jsonl | jq
```

## 🔐 Authentication

All API endpoints require Bearer token authentication:

```bash
# Set your token
export POD_TOKEN="your-secret-token-here"

# Use in requests
curl -H "Authorization: Bearer $POD_TOKEN" \
     -H "X-Request-ID: $(uuidgen)" \
     http://localhost:8010/health
```

## 🤖 MCP Integration

The MCP server provides AI agents with tools to interact with the platform:

```bash
# List available tools
curl -X POST http://localhost:8765/mcp/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# Query knowledge base
curl -X POST http://localhost:8765/mcp/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "rag_query",
      "arguments": {"query": "machine learning", "limit": 5}
    }
  }'
```

See [MCP Server documentation](memory-bank/guides/features/mcp-server.md) for detailed integration guide.

## 🛠️ Troubleshooting

### Common Issues

**Services won't start:**
```bash
docker-compose --profile dev ps
docker-compose --profile dev logs service-name
docker-compose --profile dev restart service-name
```

**Authentication errors:**
```bash
echo $POD_TOKEN
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8010/health
```

**Database issues:**
```bash
docker-compose --profile dev logs postgres
docker-compose --profile dev exec postgres psql -U postgres -c "SELECT 1;"
```

See [Debugging Guide](memory-bank/guides/debugging.md) for comprehensive troubleshooting.

## 🎯 API Documentation

Once running, access interactive API documentation:

- **Files API**: http://localhost:8010/docs
- **Git API**: http://localhost:8011/docs
- **RAG API**: http://localhost:8012/docs
- **Lock API**: http://localhost:8013/docs
- **Crew API**: http://localhost:8014/docs
- **MCP Server**: http://localhost:8765/mcp/about

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run quality checks: `uv run pre-commit run --all-files`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push and open a Pull Request

## 📄 License

See `LICENSE` if present.

## 🚀 Roadmap

See `tasks/` for phase plans and progress tracking.

---

**Status**: ✅ OPERATIONAL - All core services running

- 10 services online: traefik, postgres, redis, ollama, files-api, git-api, rag-api, lock-api, crew-api, mcp
- Testing infrastructure temporarily removed (see Testing section above)

For detailed platform status, see [Platform Status Report](memory-bank/reports/platform-status.md)
