# Phase 2: Editor Tool - Feature Documentation

## Overview

Phase 2 implements a sophisticated Editor Tool that provides structured file operations with advanced locking mechanisms. This tool enables precise, atomic file modifications through a comprehensive API, supporting multiple operation types and selector modes for safe, concurrent file editing.

## Architecture

The Editor Tool consists of:

- **EditorTool Class**: Core file operations and locking management
- **FileOperation Model**: Structured operation definitions
- **Locking System**: In-memory file locking with conflict detection
- **Selector System**: Multiple ways to target specific file content
- **REST API Integration**: HTTP endpoints for file operations
- **CLI Commands**: Command-line interface for file operations

## Core Components

### 1. EditorTool Class

Located in `src/cage/editor_tool.py`, provides all file operations.

**Key Methods:**
- `execute_operation(operation)` - Execute a file operation
- `get_file_content(path)` - Read file content
- `insert_content(path, content, selector)` - Insert content at specific location
- `update_content(path, content, selector)` - Update existing content
- `delete_content(path, selector)` - Delete specific content
- `commit_changes(message, task_id, author)` - Commit all staged changes

### 2. FileOperation Model

Structured definition of file operations:

```python
class FileOperation(BaseModel):
    operation: OperationType  # GET, INSERT, UPDATE, DELETE
    path: str                 # File path
    selector: Dict            # Content selector
    payload: Dict             # Operation data
    intent: str               # Human-readable intent
    dry_run: bool             # Preview mode
    author: str               # Operation author
    correlation_id: str       # Unique operation ID
```

### 3. Operation Types

**GET**: Read file content
- Retrieve entire file or specific sections
- Support for different output formats
- Context-aware content extraction

**INSERT**: Add new content
- Insert at specific line/character positions
- Insert with context preservation
- Support for multiple insertion points

**UPDATE**: Modify existing content
- Replace specific content sections
- Preserve surrounding context
- Validate changes before applying

**DELETE**: Remove content
- Delete specific sections
- Clean up empty lines
- Preserve file structure

### 4. Selector System

**Region Selector**:
```json
{
  "mode": "region",
  "start": 120,
  "end": 145,
  "line_start": 10,
  "line_end": 15
}
```

**Regex Selector**:
```json
{
  "mode": "regex",
  "pattern": "def\\s+\\w+\\s*\\(",
  "flags": "MULTILINE"
}
```

**Context Selector**:
```json
{
  "mode": "context",
  "before": "class MyClass:",
  "after": "def my_method():",
  "include_before": 2,
  "include_after": 2
}
```

## API Endpoints

### POST /files/edit

Execute structured file operations.

**Request:**
```json
{
  "operation": "UPDATE",
  "path": "src/auth.py",
  "selector": {
    "mode": "region",
    "start": 120,
    "end": 145
  },
  "payload": {
    "content": "def authenticate_user(token):\n    return validate_token(token)\n",
    "before_context": 3,
    "after_context": 3
  },
  "intent": "refactor: improve authentication function",
  "dry_run": false,
  "author": "developer@example.com",
  "correlation_id": "op-12345"
}
```

**Response:**
```json
{
  "ok": true,
  "file": "src/auth.py",
  "operation": "UPDATE",
  "lock_id": "lock:file:src/auth.py",
  "pre_hash": "sha256:abc123...",
  "post_hash": "sha256:def456...",
  "diff": "@@ -120,10 +120,12 @@ def authenticate_user(token):\n     return validate_token(token)\n",
  "warnings": [],
  "conflicts": []
}
```

### POST /files/commit

Commit all staged file changes.

**Request:**
```json
{
  "message": "feat: improve authentication system",
  "task_id": "2025-09-10-auth-refactor",
  "author": "developer@example.com"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Changes committed successfully",
  "data": {
    "commit_sha": "abc123def456",
    "files_changed": ["src/auth.py", "tests/test_auth.py"],
    "insertions": 25,
    "deletions": 10
  }
}
```

## CLI Commands

### File Operations

```bash
# Read file content
cage files get src/auth.py

# Read specific region
cage files get src/auth.py --region 10:20

# Insert content
cage files insert src/auth.py --line 15 --content "import logging"

# Update content
cage files update src/auth.py --region 10:20 --content "new content"

# Delete content
cage files delete src/auth.py --region 15:20
```

### Advanced Operations

```bash
# Dry run (preview changes)
cage files update src/auth.py --region 10:20 --content "new content" --dry-run

# Use regex selector
cage files update src/auth.py --regex "def\\s+\\w+" --content "def new_function()"

# Use context selector
cage files insert src/auth.py --before "class Auth:" --after "def login():" --content "    def __init__(self):"
```

### Batch Operations

```bash
# Execute multiple operations
cage files batch operations.json

# Commit all changes
cage files commit "feat: implement new features"

# Commit with task tracking
cage files commit "refactor: improve code structure" --task-id 2025-09-10-refactor
```

## Usage Examples

### Basic File Editing

1. **Read File Content**
   ```bash
   cage files get src/auth.py
   ```

2. **Insert New Function**
   ```bash
   cage files insert src/auth.py \
     --line 25 \
     --content "def validate_token(token):\n    return token is not None"
   ```

3. **Update Existing Function**
   ```bash
   cage files update src/auth.py \
     --region 30:35 \
     --content "def authenticate_user(token):\n    if not validate_token(token):\n        raise AuthenticationError()\n    return True"
   ```

4. **Commit Changes**
   ```bash
   cage files commit "feat: add token validation"
   ```

### Advanced Editing with Selectors

1. **Regex-Based Updates**
   ```bash
   # Update all function definitions
   cage files update src/auth.py \
     --regex "def\\s+(\\w+)\\s*\\(" \
     --content "def $1(user_id, **kwargs):"
   ```

2. **Context-Based Insertions**
   ```bash
   # Insert after class definition
   cage files insert src/auth.py \
     --before "class AuthManager:" \
     --after "def __init__(self):" \
     --content "    def __init__(self, config):\n        self.config = config"
   ```

3. **Region-Based Updates**
   ```bash
   # Update specific lines
   cage files update src/auth.py \
     --region 50:60 \
     --content "    def login(self, username, password):\n        # Implementation here\n        pass"
   ```

### Batch Operations

1. **Create Operations File**
   ```json
   {
     "operations": [
       {
         "operation": "INSERT",
         "path": "src/auth.py",
         "selector": {"mode": "line", "line": 10},
         "payload": {"content": "import logging\n"},
         "intent": "add logging import"
       },
       {
         "operation": "UPDATE",
         "path": "src/auth.py",
         "selector": {"mode": "regex", "pattern": "print\\("},
         "payload": {"content": "logging.info("},
         "intent": "replace print with logging"
       }
     ]
   }
   ```

2. **Execute Batch Operations**
   ```bash
   cage files batch operations.json
   ```

3. **Commit All Changes**
   ```bash
   cage files commit "refactor: improve logging and error handling"
   ```

## Locking System

### File Locking

The Editor Tool implements a sophisticated locking system:

- **In-Memory Locks**: Fast, lightweight locking mechanism
- **Conflict Detection**: Prevents concurrent modifications
- **Automatic Cleanup**: Locks expire after timeout
- **Lock Validation**: Ensures operation consistency

### Lock Lifecycle

1. **Acquire Lock**: Operation requests file lock
2. **Validate Content**: Check file hasn't changed
3. **Execute Operation**: Perform the file modification
4. **Release Lock**: Free the lock for other operations

### Conflict Resolution

**Stale Preimage Detection**:
- Operations include file hash validation
- Conflicts detected if file changed during operation
- Automatic retry with updated content

**Lock Timeout**:
- Locks expire after 30 seconds (configurable)
- Prevents deadlocks from failed operations
- Automatic cleanup of stale locks

## Integration Points

### With Phase 1 (Task Management)
- Operations tracked in task provenance
- Task-based change management
- Progress tracking through file operations

### With Phase 3 (Git Integration)
- Automatic staging of changes
- Commit integration with file operations
- Change tracking and history

### With Phase 4 (CrewAI Integration)
- AI agents can perform file operations
- Structured operations for AI workflows
- Automated file modification capabilities

## Configuration

### Environment Variables

```bash
# File operation settings
export EDITOR_LOCK_TIMEOUT=30
export EDITOR_MAX_FILE_SIZE=10485760  # 10MB
export EDITOR_BACKUP_ENABLED=true

# Repository settings
export REPO_PATH="/path/to/repository"
export EDITOR_WORKSPACE="/path/to/workspace"
```

### Lock Configuration

```python
# In editor_tool.py
LOCK_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
```

## Error Handling

### Common Error Scenarios

1. **File Not Found**
   ```
   Error: File 'src/nonexistent.py' not found
   Solution: Check file path and ensure file exists
   ```

2. **Lock Conflict**
   ```
   Error: File is locked by another operation
   Solution: Wait for lock to be released or retry operation
   ```

3. **Stale Preimage**
   ```
   Error: File content has changed during operation
   Solution: Retry operation with updated content
   ```

4. **Invalid Selector**
   ```
   Error: Invalid selector mode 'invalid'
   Solution: Use supported selector modes: region, regex, context
   ```

### Error Recovery

- Automatic retry for transient errors
- Detailed error messages for debugging
- Operation rollback on failure
- Lock cleanup on errors

## Performance Considerations

### File Size Limits
- Maximum file size: 10MB (configurable)
- Large files processed in chunks
- Memory-efficient content handling

### Lock Performance
- In-memory locks for speed
- Minimal overhead for lock operations
- Efficient conflict detection

### Batch Operations
- Optimized for multiple operations
- Reduced lock acquisition overhead
- Atomic batch execution

## Testing

### Unit Tests

```bash
# Run Editor Tool tests
python -m pytest tests/unit/test_editor_tool.py -v

# Run specific test
python -m pytest tests/unit/test_editor_tool.py::TestEditorTool::test_insert_operation -v
```

### Integration Tests

```bash
# Run file operation integration tests
python -m pytest tests/integration/test_file_operations.py -v
```

## Security Considerations

### File Access Control
- Repository-based access control
- Path validation and sanitization
- Prevention of directory traversal

### Operation Validation
- Content validation before operations
- Malicious content detection
- Safe file path handling

### Audit Trail
- All operations logged with timestamps
- Author tracking for all changes
- Correlation ID for operation tracing

## Troubleshooting

### Debug Mode

Enable verbose logging:

```bash
# Set environment variable
export EDITOR_DEBUG=1

# Or use debug flag
cage files get src/auth.py --debug
```

### Common Issues

1. **Operations Failing**
   - Check file permissions
   - Verify file exists and is readable
   - Check for lock conflicts

2. **Poor Performance**
   - Monitor file sizes
   - Check for excessive lock contention
   - Review operation complexity

3. **Content Issues**
   - Validate selector syntax
   - Check file encoding
   - Verify content format

## Future Enhancements

### Planned Features
- AST-based selectors for code operations
- Advanced conflict resolution strategies
- Real-time collaboration support
- Enhanced batch operation capabilities

### Extension Points
- Custom selector types
- Plugin system for operation types
- Integration with external editors
- Advanced content validation rules