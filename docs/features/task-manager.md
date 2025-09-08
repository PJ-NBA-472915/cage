# Task Manager System

The Task Manager is the foundational system of Cage that provides comprehensive task file management, validation, and tracking capabilities. It implements the core task file system specified in the Cage specification and serves as the foundation for all other Cage features.

## Overview

The Task Manager system provides:
- **File-based task storage** using JSON files in the `tasks/` directory
- **Schema validation** against the Cage task file specification
- **REST API endpoints** for programmatic access
- **CLI tools** for interactive task management
- **Automatic progress calculation** from todo items
- **Status tracking** and reporting capabilities

## Architecture

### Core Components

1. **Task Models** (`src/cage/task_models.py`)
   - Pydantic data models for type safety and validation
   - Automatic progress calculation from todo items
   - Timestamp validation and schema compliance

2. **Task Manager** (`src/cage/task_models.py` - TaskManager class)
   - File-based CRUD operations
   - Schema validation using JSON Schema
   - Status tracking and reporting

3. **REST API** (`src/api/main.py`)
   - FastAPI endpoints for task management
   - Authentication with POD_TOKEN
   - Error handling and validation

4. **CLI Tools** (`src/cli/main.py`)
   - Interactive task management commands
   - Rich output formatting
   - Filtering and search capabilities

## Data Models

### TaskFile

The core task model with the following structure:

```python
class TaskFile(BaseModel):
    id: str                    # Format: YYYY-MM-DD-task-slug
    title: str                 # Task title
    owner: str                 # Task owner
    status: str                # planned|in-progress|blocked|review|done|abandoned
    created_at: str            # ISO timestamp
    updated_at: str            # ISO timestamp
    progress_percent: int      # 0-100, auto-calculated from todo items
    tags: List[str]           # Task tags
    summary: str              # Task summary
    success_criteria: List[TaskCriteria]     # Success criteria with checkboxes
    acceptance_checks: List[TaskCriteria]    # Acceptance checks with checkboxes
    subtasks: List[str]       # Subtask descriptions
    todo: List[TaskTodoItem]  # Todo items with status and timing
    changelog: List[TaskChangelogEntry]      # Change history
    decisions: List[str]      # Decision log
    lessons_learned: List[str] # Lessons learned
    issues_risks: List[str]   # Issues and risks
    next_steps: List[str]     # Next steps
    references: List[str]     # Reference links
    prompts: List[TaskPrompt] # User prompt history
    locks: List[TaskLock]     # File locks for collaboration
    migration: TaskMigration  # Migration tracking
    metadata: Dict[str, Any]  # Additional metadata
```

### Supporting Models

- **TaskCriteria**: Success criteria and acceptance checks with boolean status
- **TaskTodoItem**: Todo items with status (not-started|done|blocked|failed) and timing
- **TaskChangelogEntry**: Change history with timestamps and optional lock information
- **TaskPrompt**: User prompt history for audit trail
- **TaskLock**: File locks for multi-agent collaboration
- **TaskMigration**: Migration tracking information

## API Endpoints

### Task Management

#### Create/Update Task
```http
POST /tasks/confirm
Authorization: Bearer <POD_TOKEN>
Content-Type: application/json

{
  "task_id": "2025-09-08-example-task",
  "status": "confirmed"
}
```

**Response:**
```json
{
  "status": "success",
  "task_id": "2025-09-08-example-task",
  "action": "created"
}
```

#### Get Task
```http
GET /tasks/{task_id}
Authorization: Bearer <POD_TOKEN>
```

**Response:**
```json
{
  "id": "2025-09-08-example-task",
  "title": "Example Task",
  "owner": "system",
  "status": "planned",
  "progress_percent": 0,
  "created_at": "2025-09-08T16:29:18.578054",
  "updated_at": "2025-09-08T16:29:18.578054",
  "tags": ["example", "test"],
  "summary": "An example task",
  "success_criteria": [],
  "acceptance_checks": [],
  "subtasks": [],
  "todo": [],
  "changelog": [],
  "decisions": [],
  "lessons_learned": [],
  "issues_risks": [],
  "next_steps": [],
  "references": [],
  "prompts": [],
  "locks": [],
  "migration": {"migrated": false, "source_path": null, "method": null, "migrated_at": null},
  "metadata": {}
}
```

#### Update Task
```http
PATCH /tasks/{task_id}
Authorization: Bearer <POD_TOKEN>
Content-Type: application/json

{
  "status": "in-progress",
  "progress_percent": 50,
  "title": "Updated Task Title"
}
```

**Response:**
```json
{
  "status": "success",
  "task_id": "2025-09-08-example-task",
  "updated_fields": ["status", "progress_percent", "title"]
}
```

#### List Tasks
```http
GET /tasks
Authorization: Bearer <POD_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "tasks": [
    {
      "id": "2025-09-08-example-task",
      "title": "Example Task",
      "status": "in-progress",
      "progress_percent": 50,
      "updated_at": "2025-09-08T16:29:18.578054"
    }
  ],
  "count": 1
}
```

#### Rebuild Tracker
```http
POST /tracker/rebuild
Authorization: Bearer <POD_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "message": "Tracker rebuilt successfully",
  "active_tasks": 3,
  "recently_completed": 1
}
```

## CLI Commands

### Task Creation
```bash
# Create a new task
python -m src.cli.main task-create 2025-09-08-example-task "Example Task" \
  --summary "An example task for demonstration" \
  --tags "example,test,demo" \
  --owner "user"

✅ Created task: 2025-09-08-example-task
   Title: Example Task
   Owner: user
   Status: planned
```

### Task Listing
```bash
# List all tasks
python -m src.cli.main task-list

📋 Tasks (3):
--------------------------------------------------------------------------------
🔄 2025-09-08-example-task    | Example Task                  |  50% | in-progress
📋 2025-09-08-test-task       | Test Task                     |   0% | planned
✅ 2025-09-08-completed-task  | Completed Task                | 100% | done
--------------------------------------------------------------------------------

# Filter by status
python -m src.cli.main task-list --status in-progress --limit 5
```

### Task Details
```bash
# Show detailed task information
python -m src.cli.main task-show 2025-09-08-example-task

📋 Task: 2025-09-08-example-task
============================================================
Title: Example Task
Owner: user
Status: in-progress
Progress: 50%
Created: 2025-09-08T16:29:18.578054
Updated: 2025-09-08T16:29:18.578054
Tags: example, test, demo

Summary:
  An example task for demonstration

Todo Items (2):
  1. ✅ Complete initial setup (done)
  2. ⭕ Implement core functionality (not-started)

Success Criteria:
  1. ⭕ Task is fully functional
  2. ⭕ All tests pass
============================================================
```

### Task Updates
```bash
# Update task status
python -m src.cli.main task-update 2025-09-08-example-task --status done

# Update multiple fields
python -m src.cli.main task-update 2025-09-08-example-task \
  --status in-progress \
  --progress 75 \
  --title "Updated Task Title"

✅ Updated task: 2025-09-08-example-task
   status: in-progress
   progress: 75
   title: Updated Task Title
```

### Tracker Management
```bash
# Rebuild the task tracker
python -m src.cli.main tracker-rebuild

✅ Rebuilt task tracker
   Active tasks: 3
   Recently completed: 1
```

## File Structure

### Task Files
Tasks are stored as JSON files in the `tasks/` directory:

```
tasks/
├── _schema.json                    # JSON Schema for validation
├── _status.json                    # Generated status tracker
├── _blank_task.json               # Template for new tasks
├── 2025-09-08-example-task.json   # Individual task files
├── 2025-09-08-test-task.json
└── ...
```

### Task File Format
Each task file follows the JSON schema defined in `tasks/_schema.json`:

```json
{
  "id": "2025-09-08-example-task",
  "title": "Example Task",
  "owner": "user",
  "status": "in-progress",
  "created_at": "2025-09-08T16:29:18.578054",
  "updated_at": "2025-09-08T16:29:18.578054",
  "progress_percent": 50,
  "tags": ["example", "test"],
  "summary": "An example task for demonstration",
  "success_criteria": [
    {"text": "Task is fully functional", "checked": false},
    {"text": "All tests pass", "checked": false}
  ],
  "acceptance_checks": [
    {"text": "Code is reviewed and approved", "checked": false},
    {"text": "Documentation is updated", "checked": false}
  ],
  "subtasks": [
    "Complete initial setup",
    "Implement core functionality",
    "Add tests and documentation"
  ],
  "todo": [
    {
      "text": "Complete initial setup",
      "status": "done",
      "date_started": "2025-09-08T16:30:00.000000",
      "date_stopped": "2025-09-08T16:35:00.000000"
    },
    {
      "text": "Implement core functionality",
      "status": "not-started",
      "date_started": null,
      "date_stopped": null
    }
  ],
  "changelog": [
    {
      "timestamp": "2025-09-08T16:29:18.578054",
      "text": "Task created"
    },
    {
      "timestamp": "2025-09-08T16:35:00.000000",
      "text": "Completed initial setup"
    }
  ],
  "decisions": [
    "Use Python for implementation",
    "Follow Cage specification exactly"
  ],
  "lessons_learned": [],
  "issues_risks": [
    "Complex requirements may need additional time"
  ],
  "next_steps": [
    "Implement core functionality",
    "Add comprehensive tests"
  ],
  "references": [
    "memory-bank/context/spec/cage/100_SPLIT/005-data-models.md"
  ],
  "prompts": [],
  "locks": [],
  "migration": {
    "migrated": false,
    "source_path": null,
    "method": null,
    "migrated_at": null
  },
  "metadata": {
    "phase": 1,
    "complexity": "medium",
    "estimated_effort": "4-6 hours"
  }
}
```

## Features

### Automatic Progress Calculation
The system automatically calculates progress percentage based on todo items:
- **0%**: No todo items or all not-started
- **50%**: Half of todo items completed
- **100%**: All todo items completed

### Schema Validation
All task files are validated against the JSON schema to ensure:
- Required fields are present
- Data types are correct
- Format constraints are met (e.g., task ID pattern)
- Enum values are valid

### Status Tracking
The system maintains a status tracker (`tasks/_status.json`) that provides:
- Active tasks (planned, in-progress, blocked, review)
- Recently completed tasks (done status)
- Quick overview of project status

### Multi-Agent Collaboration
The task system supports multi-agent collaboration through:
- **File locks**: Cooperative locking mechanism for concurrent access
- **Changelog**: Complete audit trail of all changes
- **Prompt tracking**: User interaction history
- **Migration tracking**: Version control and migration history

### Error Handling
Comprehensive error handling includes:
- Validation errors with detailed messages
- File system errors (permissions, disk space)
- Network errors (API connectivity)
- Graceful degradation when possible

## Integration

### With Cage Specification
The Task Manager implements the core task file system specified in:
- `memory-bank/context/spec/cage/100_SPLIT/005-data-models.md`
- `memory-bank/context/spec/cage/100_SPLIT/016-acceptance-criteria-mvp.md`

### With Other Cage Features
- **Editor Tool**: Tasks can reference files being edited
- **Git Integration**: Tasks track commit history and changes
- **CrewAI Integration**: Tasks provide context for AI agents
- **RAG System**: Tasks are indexed for search and retrieval

## Usage Examples

### Creating a Development Task
```bash
# Create a feature development task
python -m src.cli.main task-create 2025-09-08-implement-editor-tool \
  "Implement Editor Tool" \
  --summary "Build the Editor Tool for structured file operations" \
  --tags "feature,editor-tool,phase2" \
  --owner "developer"

# Add success criteria and acceptance checks
python -m src.cli.main task-update 2025-09-08-implement-editor-tool \
  --status in-progress
```

### Tracking Progress
```bash
# Check current status
python -m src.cli.main task-list --status in-progress

# Update progress
python -m src.cli.main task-update 2025-09-08-implement-editor-tool \
  --progress 75 \
  --status review
```

### Team Collaboration
```bash
# List all active tasks for team review
python -m src.cli.main task-list --status in-progress,review

# Show detailed task for discussion
python -m src.cli.main task-show 2025-09-08-implement-editor-tool
```

## Configuration

### Environment Variables
- `POD_TOKEN`: Authentication token for API access
- `REPO_PATH`: Repository path for file operations
- `POD_ID`: Pod identifier for multi-pod environments

### Dependencies
- `fastapi`: Web framework for API endpoints
- `uvicorn`: ASGI server for running the API
- `typer`: CLI framework for command-line tools
- `pydantic`: Data validation and serialization
- `jsonschema`: JSON schema validation

## Future Enhancements

### Planned Features
- **Task Templates**: Predefined task templates for common workflows
- **Task Dependencies**: Support for task dependencies and prerequisites
- **Time Tracking**: Built-in time tracking for todo items
- **Notifications**: Real-time notifications for task updates
- **Export/Import**: Bulk task export and import capabilities
- **Advanced Filtering**: More sophisticated filtering and search options

### Integration Roadmap
- **Calendar Integration**: Sync with external calendar systems
- **Project Management**: Integration with external PM tools
- **Reporting**: Advanced reporting and analytics
- **Mobile Support**: Mobile-optimized interfaces

## Troubleshooting

### Common Issues

#### Validation Errors
```
Error: 2 validation errors for TaskFile
status
  Field required [type=missing, input_value=...]
progress_percent
  Field required [type=missing, input_value=...]
```
**Solution**: Ensure all required fields are provided when creating tasks.

#### Import Errors
```
ModuleNotFoundError: No module named 'cage'
```
**Solution**: Ensure you're running from the project root and the virtual environment is activated.

#### Permission Errors
```
PermissionError: [Errno 13] Permission denied: 'tasks/example-task.json'
```
**Solution**: Check file permissions and ensure the tasks directory is writable.

### Debug Mode
Enable debug logging by setting the log level:
```bash
export LOG_LEVEL=DEBUG
python -m src.cli.main task-list
```

## Contributing

### Adding New Features
1. Update the data models in `src/cage/task_models.py`
2. Add API endpoints in `src/api/main.py`
3. Add CLI commands in `src/cli/main.py`
4. Update the JSON schema in `tasks/_schema.json`
5. Add tests and documentation

### Code Style
- Follow PEP 8 for Python code
- Use type hints for all function parameters and return values
- Add docstrings for all public functions and classes
- Use meaningful variable and function names

## License

This task manager system is part of the Cage project and follows the same licensing terms.
