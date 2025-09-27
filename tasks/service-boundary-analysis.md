# Service Boundary Analysis

## Current Monolithic API Routes → Service Mapping

### Files API Service
**Domain**: File operations, content management, file locking
**Dependencies**: File system, Git operations for commits
**Routes**:
- `POST /files/edit` - File operations (INSERT, UPDATE, DELETE)
- `POST /files/commit` - Commit file changes
- `GET /files/sha` - Get file SHA for validation
- `GET /diff` - Get diff for change validation

**Shared Dependencies**:
- EditorTool (file operations)
- GitTool (for commits)
- File system access

### Git API Service  
**Domain**: Git operations, version control, repository management
**Dependencies**: Git repository, file system
**Routes**:
- `GET /git/status` - Repository status
- `GET /git/branch` - Current branch info
- `POST /git/branch` - Create/switch branches
- `POST /git/commit` - Commit changes
- `POST /git/push` - Push to remote
- `POST /git/pull` - Pull from remote
- `POST /git/merge` - Merge branches
- `GET /git/history` - Commit history
- `POST /git/revert` - Revert changes
- `POST /git/open_pr` - Create pull request

**Shared Dependencies**:
- GitTool
- File system access
- Git repository

### RAG API Service
**Domain**: Retrieval-Augmented Generation, document search, knowledge base
**Dependencies**: PostgreSQL (with pgvector), Redis, OpenAI API
**Routes**:
- `POST /rag/query` - Search documents
- `POST /rag/reindex` - Reindex documents
- `GET /rag/blobs/{sha}` - Get blob content

**Shared Dependencies**:
- RAGService
- PostgreSQL connection pool
- Redis client
- OpenAI client

### Lock API Service (NEW)
**Domain**: Code generation, application building, Golang development
**Dependencies**: Golang toolchain, file system, templates
**Routes**:
- `POST /lock/generate` - Generate Golang application
- `POST /lock/build` - Build Golang application
- `GET /lock/templates` - List available templates
- `POST /lock/validate` - Validate generated code

**Shared Dependencies**:
- Golang toolchain (go build, go mod)
- Template engine
- File system access

### Task Management Service (Shared/Common)
**Domain**: Task orchestration, project management
**Dependencies**: Task files, JSON storage
**Routes**:
- `POST /tasks/create` - Create new task
- `POST /tasks/confirm` - Confirm task
- `PATCH /tasks/{task_id}` - Update task
- `GET /tasks/{task_id}` - Get task details
- `GET /tasks` - List tasks
- `POST /tasks/update` - Update task comprehensive
- `POST /tracker/rebuild` - Rebuild task tracker

**Shared Dependencies**:
- TaskManager
- TaskFile models
- JSON file storage

### Crew/Agent Service (Shared/Common)
**Domain**: AI agent orchestration, crew management
**Dependencies**: CrewAI, agent models
**Routes**:
- `POST /crew/plan` - Create execution plan
- `POST /crew/apply` - Apply plan
- `GET /crew/runs/{run_id}` - Get run details
- `POST /crew/runs/{run_id}/artefacts` - Upload artefacts
- `POST /crew/request` - Test individual agent
- `GET /crew/agents` - List available agents
- `GET /crew/agents/{agent_name}` - Get agent details

**Shared Dependencies**:
- CrewTool
- ModularCrewTool
- Agent models

### Common/Shared Routes
**Domain**: System health, webhooks, execution
**Routes**:
- `GET /health` - Health check (all services)
- `GET /about` - System information
- `POST /webhooks` - Webhook handling
- `POST /runner/exec` - Execute commands

## Cross-Service Dependencies

### High Coupling Areas
1. **Files ↔ Git**: Files service needs Git for commits
2. **Tasks ↔ All Services**: Task management coordinates all services
3. **Crew ↔ All Services**: Agents orchestrate work across services

### Shared Models/Components
- TaskManager, TaskFile
- EditorTool, GitTool
- RAGService
- CrewTool, ModularCrewTool
- Authentication (POD_TOKEN)

### Refactoring Strategy
1. **Phase 1**: Extract services with minimal shared dependencies
2. **Phase 2**: Create shared client libraries for cross-service calls
3. **Phase 3**: Implement service discovery and communication patterns
4. **Phase 4**: Add circuit breakers and resilience patterns

## Service Communication Patterns

### Synchronous (HTTP)
- Files → Git (for commits)
- Crew → All services (for orchestration)
- Tasks → All services (for coordination)

### Asynchronous (Future)
- Event-driven architecture
- Message queues for long-running operations
- Webhook notifications

## Security Considerations
- POD_TOKEN authentication across all services
- Service-to-service authentication
- Network isolation between services
- Shared secret management
