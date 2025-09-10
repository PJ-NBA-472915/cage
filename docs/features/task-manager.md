# Phase 1: Task Management - Feature Documentation

## Overview

Phase 1 implements the foundational task management system that serves as the core of the Cage Pod architecture. This system provides comprehensive task lifecycle management, JSON-based task storage, status tracking, and integration points for all other system components.

## Architecture

The Task Management system consists of:

- **TaskManager Class**: Core task operations and lifecycle management
- **TaskFile Model**: Structured task data representation
- **JSON Storage**: File-based task persistence
- **Status Tracking**: Real-time task status monitoring
- **REST API**: HTTP endpoints for task operations
- **CLI Commands**: Command-line interface for task management

## Core Components

### 1. TaskManager Class

Located in `src/cage/task_models.py`, provides all task operations.

**Key Methods:**
- `create_task(task_data)` - Create new task
- `load_task(task_id)` - Load task by ID
- `update_task(task_id, updates)` - Update task fields
- `list_tasks()` - List all tasks
- `delete_task(task_id)` - Delete task
- `rebuild_status()` - Rebuild status tracker
- `update_task_provenance(task_id, commit_data)` - Update task provenance

### 2. TaskFile Model

Comprehensive task data structure:

```python
class TaskFile(BaseModel):
    id: str                    # Unique task identifier
    title: str                 # Task title
    owner: str                 # Task owner
    status: str                # Current status
    created_at: str            # Creation timestamp
    updated_at: str            # Last update timestamp
    progress_percent: int      # Completion percentage
    summary: str               # Task summary
    tags: List[str]            # Task tags
    success_criteria: List[CriteriaItem]  # Success criteria
    acceptance_checks: List[CriteriaItem] # Acceptance checks
    subtasks: List[str]        # Subtask descriptions
    todo: List[TodoItem]       # Todo items with status
    changelog: List[LogEntry]  # Change history
    decisions: List[str]       # Decision records
    issues_risks: List[str]    # Issues and risks
    next_steps: List[str]      # Next steps
    references: List[str]      # Reference links
    provenance: ProvenanceData # Git and operation tracking
    metadata: Dict             # Additional metadata
```

### 3. Task Status System

**Status Values:**
- `planned` - Task is planned but not started
- `in-progress` - Task is actively being worked on
- `blocked` - Task is blocked by dependencies
- `review` - Task is under review
- `done` - Task is completed
- `abandoned` - Task was abandoned

**Progress Tracking:**
- Percentage-based progress (0-100%)
- Automatic progress calculation from todo items
- Real-time status updates

### 4. Provenance Tracking

Comprehensive tracking of task-related operations:

```json
{
  "provenance": {
    "commits": [
      {
        "sha": "abc123def456",
        "title": "feat: implement user authentication",
        "files_changed": ["src/auth.py", "tests/test_auth.py"],
        "insertions": 150,
        "deletions": 0,
        "timestamp": "2025-09-10T16:30:00Z"
      }
    ],
    "artefacts": [
      ".cage/runs/run-123/plan.yaml",
      ".cage/runs/run-123/report.md"
    ],
    "blobs_indexed": ["sha256:abc123...", "sha256:def456..."]
  }
}
```

## API Endpoints

### POST /tasks/confirm

Create or update a task.

**Request:**
```json
{
  "task_id": "2025-09-10-example-task",
  "status": "confirmed"
}
```

**Response:**
```json
{
  "status": "success",
  "task_id": "2025-09-10-example-task",
  "action": "created"
}
```

### PATCH /tasks/{task_id}

Update task fields.

**Request:**
```json
{
  "status": "in-progress",
  "progress_percent": 50,
  "logs": ["Started implementation", "Completed first milestone"]
}
```

**Response:**
```json
{
  "status": "success",
  "task_id": "2025-09-10-example-task",
  "updated_fields": ["status", "progress_percent", "logs"]
}
```

### GET /tasks/{task_id}

Get full task JSON.

**Response:**
```json
{
  "id": "2025-09-10-example-task",
  "title": "Example Task",
  "owner": "developer@example.com",
  "status": "in-progress",
  "progress_percent": 50,
  "created_at": "2025-09-10T10:00:00Z",
  "updated_at": "2025-09-10T16:30:00Z",
  "summary": "A comprehensive example task",
  "tags": ["example", "documentation"],
  "success_criteria": [
    {"text": "All tests pass", "checked": true},
    {"text": "Documentation updated", "checked": false}
  ],
  "acceptance_checks": [
    {"text": "Code review completed", "checked": true},
    {"text": "Deployment successful", "checked": false}
  ],
  "todo": [
    {
      "text": "Write implementation",
      "status": "done",
      "date_started": "2025-09-10T10:00:00Z",
      "date_stopped": "2025-09-10T14:00:00Z"
    },
    {
      "text": "Write tests",
      "status": "in-progress",
      "date_started": "2025-09-10T14:00:00Z",
      "date_stopped": null
    }
  ],
  "changelog": [
    {
      "timestamp": "2025-09-10T10:00:00Z",
      "text": "Task created"
    },
    {
      "timestamp": "2025-09-10T14:00:00Z",
      "text": "Implementation completed"
    }
  ],
  "provenance": {
    "commits": [],
    "artefacts": [],
    "blobs_indexed": []
  }
}
```

### GET /tasks

List all tasks.

**Response:**
```json
{
  "status": "success",
  "tasks": [
    {
      "id": "2025-09-10-example-task",
      "title": "Example Task",
      "status": "in-progress",
      "progress_percent": 50
    }
  ],
  "count": 1
}
```

### POST /tracker/rebuild

Rebuild the task status tracker.

**Response:**
```json
{
  "status": "success",
  "message": "Tracker rebuilt successfully",
  "active_tasks": 5,
  "recently_completed": 3
}
```

## CLI Commands

### Task Creation

```bash
# Create basic task
cage task create 2025-09-10-example "Example Task"

# Create task with details
cage task create 2025-09-10-example "Example Task" \
  --owner "developer@example.com" \
  --summary "A comprehensive example task" \
  --tags "example,documentation,testing"
```

### Task Management

```bash
# List all tasks
cage task list

# List tasks by status
cage task list --status in-progress

# List limited number of tasks
cage task list --limit 10

# Show detailed task information
cage task show 2025-09-10-example
```

### Task Updates

```bash
# Update task status
cage task update 2025-09-10-example --status in-progress

# Update progress
cage task update 2025-09-10-example --progress 75

# Update title
cage task update 2025-09-10-example --title "Updated Task Title"

# Update summary
cage task update 2025-09-10-example --summary "Updated task summary"
```

### Status Management

```bash
# Rebuild task tracker
cage tracker rebuild
```

## Usage Examples

### Basic Task Workflow

1. **Create Task**
   ```bash
   cage task create 2025-09-10-auth "Implement user authentication" \
     --summary "Add JWT-based authentication system" \
     --tags "security,backend,api"
   ```

2. **Update Progress**
   ```bash
   cage task update 2025-09-10-auth --status in-progress --progress 25
   ```

3. **Add Success Criteria**
   ```bash
   # Edit task file directly or use API
   cage task update 2025-09-10-auth --add-criteria "JWT tokens implemented"
   ```

4. **Track Todo Items**
   ```bash
   # Add todo items through API or direct file editing
   # Todo items are automatically tracked with timestamps
   ```

5. **Complete Task**
   ```bash
   cage task update 2025-09-10-auth --status done --progress 100
   ```

### Advanced Task Management

1. **Create Complex Task**
   ```bash
   cage task create 2025-09-10-refactor "Refactor authentication module" \
     --owner "senior-dev@example.com" \
     --summary "Improve code structure, add tests, and update documentation" \
     --tags "refactoring,testing,documentation,security"
   ```

2. **Define Success Criteria**
   ```json
   {
     "success_criteria": [
       {"text": "All existing tests pass", "checked": false},
       {"text": "Code coverage > 90%", "checked": false},
       {"text": "Security review completed", "checked": false},
       {"text": "Documentation updated", "checked": false}
     ]
   }
   ```

3. **Plan Subtasks**
   ```json
   {
     "subtasks": [
       "Analyze current authentication code",
       "Design improved architecture",
       "Implement new authentication service",
       "Write comprehensive tests",
       "Update API documentation",
       "Perform security review"
     ]
   }
   ```

4. **Track Progress**
   ```bash
   # Update progress as work is completed
   cage task update 2025-09-10-refactor --progress 20
   cage task update 2025-09-10-refactor --progress 40
   cage task update 2025-09-10-refactor --progress 60
   cage task update 2025-09-10-refactor --progress 80
   cage task update 2025-09-10-refactor --progress 100 --status done
   ```

### Team Collaboration

1. **Assign Tasks**
   ```bash
   cage task create 2025-09-10-frontend "Implement login UI" \
     --owner "frontend-dev@example.com"
   ```

2. **Track Dependencies**
   ```json
   {
     "references": [
       "2025-09-10-auth",  // Depends on authentication implementation
       "https://design-system.example.com"  // Design system reference
     ]
   }
   ```

3. **Document Decisions**
   ```json
   {
     "decisions": [
       "Use JWT tokens instead of session-based auth",
       "Implement OAuth2 for third-party authentication",
       "Use bcrypt for password hashing"
     ]
   }
   ```

4. **Track Issues and Risks**
   ```json
   {
     "issues_risks": [
       "Potential security vulnerability in token validation",
       "Performance impact of encryption on large user base",
       "Migration complexity for existing users"
     ]
   }
   ```

## Integration Points

### With Phase 2 (Editor Tool)
- File operations tracked in task provenance
- Task-based change management
- Progress tracking through file modifications

### With Phase 3 (Git Integration)
- Commit information stored in task provenance
- Task-based commit tracking
- Change history integration

### With Phase 4 (CrewAI Integration)
- AI agents can create and manage tasks
- Task-based AI workflow planning
- Automated task progress updates

## Configuration

### Environment Variables

```bash
# Task management settings
export TASK_DIR="/path/to/tasks"
export TASK_SCHEMA_PATH="/path/to/schema.json"
export TASK_BACKUP_ENABLED=true

# Repository settings
export REPO_PATH="/path/to/repository"
```

### Task Schema

Tasks must conform to the schema defined in `tasks/_schema.json`:

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}-[a-z0-9-]+$"},
    "title": {"type": "string", "minLength": 1},
    "owner": {"type": "string"},
    "status": {"type": "string", "enum": ["planned", "in-progress", "blocked", "review", "done", "abandoned"]},
    "progress_percent": {"type": "integer", "minimum": 0, "maximum": 100}
  },
  "required": ["id", "title", "owner", "status"]
}
```

## Error Handling

### Common Error Scenarios

1. **Invalid Task ID**
   ```
   Error: Task ID must match pattern YYYY-MM-DD-task-slug
   Solution: Use proper task ID format
   ```

2. **Task Not Found**
   ```
   Error: Task 2025-09-10-nonexistent not found
   Solution: Check task ID or create task first
   ```

3. **Schema Validation Error**
   ```
   Error: Task data does not match schema
   Solution: Check required fields and data types
   ```

4. **File System Error**
   ```
   Error: Cannot write to tasks directory
   Solution: Check directory permissions and disk space
   ```

### Error Recovery

- Automatic backup of task files
- Validation before saving changes
- Detailed error messages for debugging
- Rollback capability for failed operations

## Performance Considerations

### File System Performance
- Efficient JSON file operations
- Minimal memory usage for large task lists
- Optimized file I/O operations

### Status Tracking
- Incremental status updates
- Efficient status rebuilding
- Minimal overhead for status queries

### Scalability
- Support for thousands of tasks
- Efficient task filtering and searching
- Optimized API responses

## Testing

### Unit Tests

```bash
# Run task management tests
python -m pytest tests/unit/test_task_models.py -v

# Run specific test
python -m pytest tests/unit/test_task_models.py::TestTaskManager::test_create_task -v
```

### Integration Tests

```bash
# Run task API tests
python -m pytest tests/api/test_api_endpoints.py -v

# Run CLI tests
python -m pytest tests/cli/test_cli_commands.py -v
```

## Security Considerations

### File Access Control
- Repository-based access control
- Task file permissions
- Secure task data handling

### Data Validation
- Schema validation for all task data
- Input sanitization
- Prevention of malicious content

### Audit Trail
- Complete change history
- Author tracking for all modifications
- Timestamp logging for all operations

## Troubleshooting

### Debug Mode

Enable verbose logging:

```bash
# Set environment variable
export TASK_DEBUG=1

# Or use debug flag
cage task show 2025-09-10-example --debug
```

### Common Issues

1. **Tasks Not Loading**
   - Check file permissions
   - Verify task directory exists
   - Check JSON file validity

2. **Status Not Updating**
   - Rebuild status tracker
   - Check for file system errors
   - Verify task file format

3. **Performance Issues**
   - Check task directory size
   - Review task file complexity
   - Consider task cleanup

## Future Enhancements

### Planned Features
- Advanced task filtering and search
- Task templates and workflows
- Integration with external project management tools
- Enhanced collaboration features

### Extension Points
- Custom task fields
- Plugin system for task types
- Integration with external APIs
- Advanced reporting and analytics