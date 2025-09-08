# Cage: Pod-based Multi-Agent Repository Service

Cage is a comprehensive system for managing multi-agent collaboration on code repositories. It provides a pod-based architecture with task management, file editing capabilities, Git integration, and AI agent orchestration through CrewAI.

## Key Features:

- **Task Management System:** Complete task file system with JSON-based storage, validation, and progress tracking
- **Editor Tool:** Structured file operations (GET/INSERT/UPDATE/DELETE) with locking mechanism
- **Git Integration:** Comprehensive Git operations with commit trail tracking
- **CrewAI Integration:** AI agent workflows for planning and execution
- **RAG System:** Retrieval Augmented Generation with vector search and embeddings
- **REST API:** Full REST API for programmatic access to all features
- **CLI Tools:** Command-line interface for interactive management
- **Multi-Agent Collaboration:** File locking and coordination for concurrent agent work

## Current Status:

### ✅ Phase 1: Task File System (Complete)
- Task file data models with Pydantic validation
- REST API endpoints for task management
- CLI tools for interactive task operations
- Automatic progress calculation and status tracking
- JSON schema validation and error handling

### 🚧 Phase 2: Editor Tool (Planned)
- Internal Python functions for file operations
- CLI tools for structured file editing
- Basic locking mechanism for multi-agent collaboration

### 📋 Phase 3: Git Integration (Planned)
- Git operations as internal Python functions
- Commit trail tracking in task provenance
- Integration with Editor Tool functions

### 📋 Phase 4: CrewAI Integration (Planned)
- AI agent workflows for task planning and execution
- Integration with Editor Tool and Git functions
- Automated task management and coordination

### 📋 Phase 5: RAG System (Planned)
- Vector search and embeddings with Postgres + pgvector
- Redis for hot indexes and caching
- Code and documentation indexing

### 📋 Phase 6: Production Features (Planned)
- Webhooks and event system
- Advanced security and monitoring
- Production deployment capabilities

## Directory Structure:

- `src/api/`: FastAPI REST API server
- `src/cli/`: Typer-based CLI tools
- `src/cage/`: Core Cage modules and data models
- `tasks/`: Task file storage and management
- `memory-bank/`: Project context, specifications, and rules
- `docs/`: Comprehensive documentation
- `tests/`: Test suites for all components

## Getting Started:

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)
- Git repository

### Installation
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

### Quick Start

#### 1. Start the API Server
```bash
# Start the API server
python -m src.api.main

# Server will be available at http://localhost:8000
```

#### 2. Use CLI Tools
```bash
# Create a new task
python -m src.cli.main task-create 2025-09-08-example-task "Example Task" \
  --summary "A sample task for demonstration" \
  --tags "example,demo"

# List all tasks
python -m src.cli.main task-list

# Show task details
python -m src.cli.main task-show 2025-09-08-example-task

# Update task status
python -m src.cli.main task-update 2025-09-08-example-task --status in-progress
```

#### 3. Use the REST API
```bash
# Health check
curl -H "Authorization: Bearer dev-token" http://localhost:8000/health

# Create a task
curl -X POST -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "2025-09-08-api-task", "status": "confirmed"}' \
  http://localhost:8000/tasks/confirm

# Get task details
curl -H "Authorization: Bearer dev-token" \
  http://localhost:8000/tasks/2025-09-08-api-task
```

## Documentation:

- **[Task Manager System](docs/features/task-manager.md)**: Complete documentation for the task management system
- **[API Design](docs/api-design.md)**: REST API documentation and design
- **[CLI Reference](docs/cli-reference.md)**: Command-line interface documentation
- **[Memory Bank](memory-bank/README.md)**: Project context and specifications

## Development:

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest --cov=src
```

### Development Server
```bash
# Start development server with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Contributing:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `python -m pytest`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## License:

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap:

See the [Phase Implementation Plan](tasks/) for detailed roadmap and progress tracking. Each phase builds upon the previous one, creating a comprehensive multi-agent repository service.
