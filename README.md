# Cage: Pod-based Multi-Agent Repository Service

Cage is a system for managing multi-agent collaboration on code repositories. It provides a pod-based architecture with task management, structured file edits, Git integration, a CrewAI workflow, a RAG service, a REST API, CLI tools, and an MCP server for tool access.

## Key Features

- **Task Management:** JSON task files with validation, progress, and provenance
- **Editor Tool:** Structured file ops (GET/INSERT/UPDATE/DELETE) with locking
- **Git Integration:** Status/branch/commit/push/merge with provenance
- **CrewAI Workflow:** Plan → implement → review → commit
- **RAG (pgvector + Redis):** Semantic search over code/tasks with OpenAI embeddings
- **REST API:** Endpoints for tasks, files, git, crew, rag
- **CLI Tools:** Typer-based CLI for tasks/git/serve
- **MCP Server:** Streamable HTTP MCP server exposing RAG query as a tool

## Current Status

- ✅ Phase 1: Task File System — Complete
- ✅ Phase 2: Editor Tool — Complete
- ✅ Phase 3: Git Integration — Complete
- ✅ Phase 4: CrewAI Integration — Implemented (alpha)
- ✅ Phase 5: RAG System — Implemented (beta)
- 📋 Phase 6: Production Features — Planned

## Directory Structure

- `src/api/`: FastAPI REST API server
- `src/cli/`: Typer-based CLI tools
- `src/cage/`: Core Cage modules and data models
- `tasks/`: Task file storage and management
- `memory-bank/docs/`: Feature documentation (API, Editor, Git, RAG, MCP)
- `tests/`: Test suites
- `dockerfiles/` and `docker-compose.yml`: Containerization

## Getting Started

Choose Docker Compose (recommended) or local-only.

### Docker Compose (API + Postgres + Redis + MCP)

Prerequisites
- Docker and Docker Compose
- A Git repository to operate on (`REPO_PATH`)

Setup
```bash
# From project root
export REPO_PATH=/absolute/path/to/your/repo
export POD_TOKEN=dev-token                   # API auth token
export OPENAI_API_KEY=sk-...                 # Optional; enables RAG

docker-compose up -d
```

Verify
```bash
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8000/health
```

Index your repo for RAG (optional)
```bash
curl -X POST -H "Authorization: Bearer $POD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scope":"all"}' http://localhost:8000/rag/reindex
```

Useful make targets
```bash
make docker-logs-api     # Stream API logs
make docker-logs-mcp     # Stream MCP logs
make rag-reindex         # POST /rag/reindex
make rag-query           # Example RAG query
```

## Documentation

- Task Manager: `memory-bank/docs/features/task-manager.md`
- Editor Tool: `memory-bank/docs/features/editor-tool.md`
- Git Integration: `memory-bank/docs/features/git-integration.md`
- RAG System: `memory-bank/docs/features/rag-system-implementation.md`
- MCP Service: `memory-bank/docs/features/mcp-service.md`
- Project Context: `memory-bank/README.md`
- Postman Collection: `cage-api-complete-postman-collection.json`

## MCP Server

- Runs via Docker Compose (`mcp` service) on port `8765` by default.
- Exposes MCP tools (e.g., `rag_query`) for MCP-aware clients; it is not a human-facing API.
- Configuration:
  - `API_BASE_URL` (default: `http://api:8000` in compose)
  - `POD_TOKEN` (must match API)
  - Optional debug ports via env (`DEBUGPY_*`).
- Logs: `docker-compose logs mcp`.

Run manually (advanced)
```bash
python -m src.cage.mcp_server --host 0.0.0.0 --port 8765
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest --cov=src
```

### Environment notes
- Authentication: All protected endpoints require `Authorization: Bearer $POD_TOKEN`.
- RAG: Requires `DATABASE_URL`, `REDIS_URL`, and a valid `OPENAI_API_KEY`. Without these, RAG endpoints will return 503.

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `python -m pytest`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## License

See `LICENSE` if present.

## Roadmap

See `tasks/` for phase plans and progress tracking.
