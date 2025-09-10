# Editor Tool System

The Editor Tool is a comprehensive file manipulation system designed for structured file operations with built-in locking mechanisms for multi-agent collaboration. It provides a unified interface for reading, writing, updating, and deleting file content with precise control over what portions of files are affected.

## Overview

The Editor Tool system provides:
- **Structured file operations** (GET, INSERT, UPDATE, DELETE) with selector-based targeting
- **File locking mechanism** for safe concurrent access by multiple agents
- **REST API endpoints** for programmatic access
- **CLI tools** for interactive file operations
- **Task system integration** for operation tracking and audit trails
- **Conflict detection** and stale preimage checking
- **Diff generation** for change tracking

## Architecture

### Core Components

1. **EditorTool** (`src/cage/editor_tool.py` - main class)
   - Central orchestrator for all file operations
   - Integrates with locking system and task management
   - Handles operation execution and result formatting

2. **FileLockManager** (`src/cage/editor_tool.py` - FileLockManager class)
   - In-memory lock management for Phase 2
   - TTL-based lock expiration
   - Thread-safe lock operations

3. **Data Models** (`src/cage/editor_tool.py`)
   - FileOperation: Operation request structure
   - FileOperationResult: Operation result structure
   - FileLock: Lock information and metadata
   - OperationType: Supported operations enum
   - SelectorMode: Selector types enum

4. **REST API** (`src/api/main.py`)
   - FastAPI endpoints for file operations
   - Authentication with POD_TOKEN
   - Error handling and validation

5. **CLI Tools** (`src/cli/editor_cli.py`)
   - Command-line interface for file operations
   - Support for all operation types
   - Dry-run and verbose output options

## Data Models

### FileOperation

The core operation request model:

```python
@dataclass
class FileOperation:
    operation: OperationType        # GET, INSERT, UPDATE, DELETE
    path: str                      # File path (relative to repo root)
    selector: Optional[Dict[str, Any]] = None    # Content selector
    payload: Optional[Dict[str, Any]] = None     # Operation payload
    intent: str = ""               # Human-readable intent
    dry_run: bool = False          # Preview mode
    author: str = ""               # Operation author
    correlation_id: str = ""       # Task correlation ID
```

### FileOperationResult

Result structure for all operations:

```python
@dataclass
class FileOperationResult:
    ok: bool                       # Success status
    file: str                      # File path
    operation: str                 # Operation type
    lock_id: Optional[str] = None  # Lock identifier
    pre_hash: Optional[str] = None # Content hash before operation
    post_hash: Optional[str] = None # Content hash after operation
    diff: Optional[str] = None     # Diff output
    warnings: List[str] = None     # Warning messages
    conflicts: List[str] = None    # Conflict messages
    error: Optional[str] = None    # Error message if failed
```

### FileLock

Lock information for concurrent access control:

```python
@dataclass
class FileLock:
    file_path: str                 # File being locked
    lock_id: str                   # Unique lock identifier
    agent: str                     # Agent holding the lock
    started_at: str                # Lock start timestamp
    expires_at: str                # Lock expiration timestamp
    ranges: List[Dict[str, int]]   # Locked line ranges
    description: str               # Lock description
```

### Selectors

Content targeting system for precise file operations:

#### Region Selector
```python
{
    "mode": "region",
    "start": 10,    # Start line (1-based)
    "end": 20       # End line (inclusive) or -1 for end of file
}
```

#### Regex Selector
```python
{
    "mode": "regex",
    "pattern": r"def\s+\w+\s*\(",  # Regex pattern
    "flags": 0                     # Regex flags (re.IGNORECASE, etc.)
}
```

## API Endpoints

### File Operations

#### Edit File
```http
POST /files/edit
Authorization: Bearer <POD_TOKEN>
Content-Type: application/json

{
  "operation": "UPDATE",
  "path": "src/example.py",
  "selector": {
    "mode": "region",
    "start": 10,
    "end": 20
  },
  "payload": {
    "content": "def new_function():\n    pass\n"
  },
  "intent": "Add new function",
  "dry_run": false,
  "author": "agent-1",
  "correlation_id": "task-123-update"
}
```

**Response:**
```json
{
  "ok": true,
  "file": "src/example.py",
  "operation": "UPDATE",
  "lock_id": "lock:file:src/example.py:1691234567",
  "pre_hash": "abc123...",
  "post_hash": "def456...",
  "diff": "@@ -10,5 +10,7 @@\n-def old_function():\n-    pass\n+def new_function():\n+    pass\n",
  "warnings": [],
  "conflicts": []
}
```

#### Error Response
```json
{
  "ok": false,
  "file": "src/example.py",
  "operation": "UPDATE",
  "error": "File is locked by another process",
  "warnings": [],
  "conflicts": []
}
```

### Operation Types

#### GET Operation
Read file content with optional selector:
```json
{
  "operation": "GET",
  "path": "src/example.py",
  "selector": {
    "mode": "region",
    "start": 1,
    "end": 10
  }
}
```

#### INSERT Operation
Insert content at specified location:
```json
{
  "operation": "INSERT",
  "path": "src/example.py",
  "selector": {
    "mode": "region",
    "start": 10,
    "end": 10
  },
  "payload": {
    "content": "def new_function():\n    pass\n"
  }
}
```

#### UPDATE Operation
Replace content in specified region:
```json
{
  "operation": "UPDATE",
  "path": "src/example.py",
  "selector": {
    "mode": "regex",
    "pattern": "def\\s+old_function"
  },
  "payload": {
    "content": "def updated_function",
    "pre_hash": "expected_hash_for_conflict_detection"
  }
}
```

#### DELETE Operation
Delete content or entire file:
```json
{
  "operation": "DELETE",
  "path": "src/example.py",
  "selector": {
    "mode": "region",
    "start": 10,
    "end": 15
  }
}
```

## CLI Commands

### Basic Usage

#### Read File Content
```bash
# Read entire file
python -m src.cli.editor_cli get src/example.py

# Read specific lines
python -m src.cli.editor_cli get src/example.py --selector "10:20"

# Read with regex selector
python -m src.cli.editor_cli get src/example.py --selector '{"mode": "regex", "pattern": "def\\s+\\w+"}'
```

#### Insert Content
```bash
# Insert at end of file
python -m src.cli.editor_cli insert src/example.py --content "print('Hello World')"

# Insert at specific location
python -m src.cli.editor_cli insert src/example.py \
  --selector "10:10" \
  --content "def new_function():\n    pass\n"

# Insert from file
python -m src.cli.editor_cli insert src/example.py \
  --content-file new_function.py \
  --selector "10:10"
```

#### Update Content
```bash
# Update entire file
python -m src.cli.editor_cli update src/example.py --content-file new_content.py

# Update specific lines
python -m src.cli.editor_cli update src/example.py \
  --selector "10:20" \
  --content "def updated_function():\n    pass\n"

# Update with conflict detection
python -m src.cli.editor_cli update src/example.py \
  --selector "10:20" \
  --content "new content" \
  --pre-hash "expected_hash"
```

#### Delete Content
```bash
# Delete specific lines
python -m src.cli.editor_cli delete src/example.py --selector "10:20"

# Delete entire file
python -m src.cli.editor_cli delete src/example.py

# Dry run to preview
python -m src.cli.editor_cli delete src/example.py --selector "10:20" --dry-run
```

### Advanced Options

#### Dry Run Mode
Preview changes without applying them:
```bash
python -m src.cli.editor_cli update src/example.py \
  --content "new content" \
  --dry-run \
  --verbose
```

#### Verbose Output
Get detailed information about operations:
```bash
python -m src.cli.editor_cli update src/example.py \
  --content "new content" \
  --verbose
```

**Output:**
```
Operation: UPDATE
File: src/example.py
Lock ID: lock:file:src/example.py:1691234567
Pre-hash: abc123def456...
Post-hash: def456ghi789...
Diff:
@@ -10,5 +10,7 @@
-def old_function():
-    pass
+def new_function():
+    pass
```

#### Author and Correlation Tracking
```bash
python -m src.cli.editor_cli update src/example.py \
  --content "new content" \
  --author "developer-1" \
  --correlation-id "task-123-update"
```

## File Locking System

### Lock Acquisition

Locks are automatically acquired for non-dry-run operations:
- **Region-based locks**: When using region selectors
- **Full-file locks**: For regex selectors or whole-file operations
- **TTL-based expiration**: Default 5-minute lock lifetime
- **Thread-safe**: Supports concurrent operations

### Lock Management

```python
# Acquire lock
lock_id = editor.lock_manager.acquire_lock(
    file_path="src/example.py",
    agent="agent-1",
    ranges=[{"start": 10, "end": 20}],
    description="Update function"
)

# Release lock
success = editor.lock_manager.release_lock(lock_id)

# Check if file is locked
is_locked = editor.lock_manager.is_locked("src/example.py")
```

### Lock Expiration

- **Automatic cleanup**: Expired locks are removed on next access
- **Manual cleanup**: `editor.lock_manager.cleanup_expired_locks()`
- **Configurable TTL**: Default 300 seconds (5 minutes)

## Integration

### With Task Management System

The Editor Tool integrates with the task management system for:
- **Operation logging**: All operations are logged to task changelog
- **Correlation tracking**: Operations linked to specific tasks
- **Audit trails**: Complete history of file changes

```python
# Operations are automatically logged when correlation_id is provided
operation = FileOperation(
    operation=OperationType.UPDATE,
    path="src/example.py",
    correlation_id="task-123-update",
    # ... other parameters
)
```

### With Multi-Agent Systems

- **Cooperative locking**: Agents wait for locks to be released
- **Conflict detection**: Stale preimage checking prevents conflicts
- **Fail-fast**: Operations fail immediately if file is locked

### With Version Control

- **Content hashing**: SHA256 hashes for change detection
- **Diff generation**: Unified diff format for changes
- **Stale detection**: Pre-image hash validation

## Usage Examples

### Basic File Operations

#### Creating a New File
```python
from src.cage.editor_tool import EditorTool, FileOperation, OperationType

editor = EditorTool(Path("/path/to/repo"))

# Create new file
operation = FileOperation(
    operation=OperationType.INSERT,
    path="new_file.py",
    payload={"content": "print('Hello World')\n"},
    intent="Create new Python file",
    author="agent-1"
)

result = editor.execute_operation(operation)
```

#### Reading File Content
```python
# Read entire file
operation = FileOperation(
    operation=OperationType.GET,
    path="src/example.py"
)
result = editor.execute_operation(operation)
print(result.diff)  # File content

# Read specific lines
operation = FileOperation(
    operation=OperationType.GET,
    path="src/example.py",
    selector={"mode": "region", "start": 10, "end": 20}
)
result = editor.execute_operation(operation)
```

#### Updating Specific Lines
```python
# Update lines 10-20
operation = FileOperation(
    operation=OperationType.UPDATE,
    path="src/example.py",
    selector={"mode": "region", "start": 10, "end": 20},
    payload={"content": "def updated_function():\n    pass\n"},
    intent="Update function implementation",
    author="agent-1"
)
result = editor.execute_operation(operation)
```

#### Using Regex Selectors
```python
# Update all function definitions
operation = FileOperation(
    operation=OperationType.UPDATE,
    path="src/example.py",
    selector={
        "mode": "regex",
        "pattern": r"def\s+old_(\w+)",
        "flags": 0
    },
    payload={"content": "def new_\\1", "pre_hash": "expected_hash"},
    intent="Rename functions with old_ prefix",
    author="agent-1"
)
result = editor.execute_operation(operation)
```

### Multi-Agent Collaboration

#### Safe Concurrent Updates
```python
# Agent 1: Update file
operation1 = FileOperation(
    operation=OperationType.UPDATE,
    path="shared_file.py",
    selector={"mode": "region", "start": 1, "end": 10},
    payload={"content": "updated content"},
    author="agent-1"
)
result1 = editor.execute_operation(operation1)

# Agent 2: Try to update same lines (will fail if locks enabled)
operation2 = FileOperation(
    operation=OperationType.UPDATE,
    path="shared_file.py",
    selector={"mode": "region", "start": 1, "end": 10},
    payload={"content": "conflicting content"},
    author="agent-2"
)
result2 = editor.execute_operation(operation2)
# Will fail with "File is locked by another process"
```

### Error Handling

#### Handling Lock Conflicts
```python
result = editor.execute_operation(operation)
if not result.ok:
    if "locked by another process" in result.error:
        print("File is busy, retrying later...")
    else:
        print(f"Operation failed: {result.error}")
```

#### Handling Stale Preimages
```python
# Check for stale preimage conflicts
if not result.ok and "Stale preimage detected" in result.error:
    # Re-read file and retry with updated hash
    read_op = FileOperation(operation=OperationType.GET, path=operation.path)
    read_result = editor.execute_operation(read_op)
    # Use new hash for retry
    operation.payload["pre_hash"] = read_result.pre_hash
    result = editor.execute_operation(operation)
```

## Configuration

### Environment Variables
- `REPO_PATH`: Repository root path for file operations
- `POD_TOKEN`: Authentication token for API access
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Lock Manager Configuration
```python
# Custom lock TTL (default: 300 seconds)
lock_manager = FileLockManager(lock_ttl=600)  # 10 minutes
editor = EditorTool(repo_path, lock_manager)
```

### Repository Path
```python
# Set repository root
editor = EditorTool(Path("/path/to/repo"))

# Or use current directory
editor = EditorTool(Path.cwd())
```

## Features

### Selector System

The Editor Tool supports multiple ways to target content:

#### Region Selectors
- **Line-based**: Target specific line ranges
- **1-based indexing**: User-friendly line numbers
- **End-of-file support**: Use -1 for end of file
- **Overflow protection**: Automatically clamped to file bounds

#### Regex Selectors
- **Pattern matching**: Regular expression support
- **Flag support**: Case sensitivity, multiline, etc.
- **Multiple matches**: All matches are processed
- **Capture groups**: Support for replacement patterns

### Content Validation

- **Hash verification**: SHA256 content hashing
- **Stale detection**: Pre-image validation
- **Change tracking**: Before/after content comparison
- **Diff generation**: Unified diff format

### Multi-Agent Safety

- **Cooperative locking**: Agents respect existing locks
- **Lock expiration**: Automatic cleanup of stale locks
- **Conflict detection**: Stale preimage checking
- **Fail-fast**: Immediate failure on conflicts

### Audit Trail

- **Operation logging**: Complete history in task system
- **Author tracking**: Who made changes
- **Intent documentation**: Human-readable operation purpose
- **Correlation IDs**: Link operations to tasks

## Future Enhancements

### Planned Features

#### Advanced Selectors
- **AST selectors**: Parse and target code structures
- **Semantic selectors**: Target by meaning, not syntax
- **Multi-file selectors**: Cross-file operations
- **Template selectors**: Reusable selector patterns

#### Enhanced Locking
- **Distributed locks**: Redis-based locking for multi-pod environments
- **Lock priorities**: Priority-based lock acquisition
- **Lock inheritance**: Sub-operation lock sharing
- **Deadlock detection**: Automatic deadlock resolution

#### Improved Collaboration
- **Real-time updates**: WebSocket-based notifications
- **Conflict resolution**: Automatic merge capabilities
- **Branch awareness**: Git branch-aware operations
- **Change suggestions**: Collaborative editing features

#### Performance Optimization
- **Caching**: Content caching for repeated operations
- **Batch operations**: Multiple operations in single transaction
- **Async operations**: Non-blocking file operations
- **Streaming**: Large file streaming support

### Integration Roadmap

#### Git Integration (Phase 3)
- **Commit tracking**: Automatic commit on changes
- **Branch operations**: Branch-aware file operations
- **Merge integration**: Conflict resolution during merges
- **History integration**: Git history in audit trails

#### CrewAI Integration (Phase 4)
- **Agent workflows**: Automated file operations
- **Planning integration**: Task-based operation planning
- **Execution tracking**: Agent operation monitoring
- **Coordination**: Multi-agent operation coordination

#### RAG System Integration (Phase 5)
- **Content indexing**: File content for semantic search
- **Context-aware operations**: AI-informed file changes
- **Knowledge integration**: Documentation-aware editing
- **Search integration**: Find files by content similarity

## Troubleshooting

### Common Issues

#### Lock Timeout Errors
```
Error: File is locked by another process
```
**Solution**: Wait for lock to expire or release the lock manually.

#### Stale Preimage Errors
```
Error: Stale preimage detected - file was modified by another process
```
**Solution**: Re-read file content and retry with updated hash.

#### Selector Errors
```
Error: Invalid selector format
```
**Solution**: Ensure selector follows correct JSON format or use region syntax.

#### Permission Errors
```
Error: Permission denied
```
**Solution**: Check file permissions and repository access rights.

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.cli.editor_cli get src/example.py --verbose
```

### Lock Management

List active locks:
```bash
python -m src.cli.editor_cli locks
```

Clean up expired locks:
```python
editor.lock_manager.cleanup_expired_locks()
```

## Contributing

### Adding New Features
1. Update data models in `src/cage/editor_tool.py`
2. Add API endpoints in `src/api/main.py`
3. Add CLI commands in `src/cli/editor_cli.py`
4. Add comprehensive tests
5. Update documentation

### Code Style
- Follow PEP 8 for Python code
- Use type hints for all functions
- Add docstrings for all public methods
- Include comprehensive error handling

## License

This Editor Tool system is part of the Cage project and follows the same licensing terms.
