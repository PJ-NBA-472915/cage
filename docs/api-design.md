# Cage Repository Service API Design

## Overview

The Cage Repository Service provides a REST API for programmatic access to repository operations. The service runs alongside a specific repository directory and exposes endpoints for common Git operations.

## Service Architecture

- **Single Repository Focus**: Each service instance is tied to one repository directory
- **REST API**: HTTP-based API with JSON request/response format
- **Service Startup**: `cage serve /path/to/repository` starts the service for that specific repository
- **Port**: Default port 8000 (configurable)

## Base URL

```
http://localhost:8000
```

## Authentication

V1 does not implement authentication. The service runs with the same permissions as the user who starts it.

## API Endpoints

### Health Check

#### GET /health
Check service health and repository status.

**Response:**
```json
{
  "status": "success",
  "date": "2025-09-07T16:25:00Z",
  "repository": {
    "path": "/path/to/repository",
    "branch": "main",
    "commit": "abc123...",
    "status": "clean"
  }
}
```

### Repository Information

#### GET /repository/info
Get information about the current repository.

**Response:**
```json
{
  "path": "/path/to/repository",
  "branch": "main",
  "commit": "abc123...",
  "status": "clean",
  "remotes": [
    {
      "name": "origin",
      "url": "https://github.com/user/repo.git"
    }
  ],
  "last_modified": "2025-09-07T16:20:00Z"
}
```

#### GET /repository/status
Get detailed Git status information.

**Response:**
```json
{
  "branch": "main",
  "commit": "abc123...",
  "status": "clean",
  "staged_files": [],
  "unstaged_files": [],
  "untracked_files": [],
  "ahead": 0,
  "behind": 0
}
```

### Branch Operations

#### GET /branches
List all branches (local and remote).

**Query Parameters:**
- `remote` (optional): Include remote branches (default: true)

**Response:**
```json
{
  "local": [
    {
      "name": "main",
      "commit": "abc123...",
      "is_current": true
    },
    {
      "name": "feature/new-feature",
      "commit": "def456...",
      "is_current": false
    }
  ],
  "remote": [
    {
      "name": "origin/main",
      "commit": "abc123...",
      "tracking": "main"
    }
  ]
}
```

#### POST /branches
Create a new branch.

**Request Body:**
```json
{
  "name": "feature/new-feature",
  "from": "main",
  "checkout": true
}
```

**Response:**
```json
{
  "status": "success",
  "branch": "feature/new-feature",
  "commit": "def456...",
  "message": "Branch created successfully"
}
```

#### DELETE /branches/{branch_name}
Delete a branch.

**Path Parameters:**
- `branch_name`: Name of the branch to delete

**Query Parameters:**
- `force` (optional): Force delete even if not merged (default: false)

**Response:**
```json
{
  "status": "success",
  "message": "Branch deleted successfully"
}
```

### Commit Operations

#### POST /commits
Create a new commit.

**Request Body:**
```json
{
  "message": "Add new feature",
  "files": ["src/new_file.py", "docs/README.md"],
  "all": false,
  "signoff": false,
  "no_verify": false
}
```

**Response:**
```json
{
  "status": "success",
  "commit": "def456...",
  "message": "Commit created successfully",
  "files_changed": 2
}
```

#### GET /commits
List recent commits.

**Query Parameters:**
- `limit` (optional): Number of commits to return (default: 10)
- `branch` (optional): Branch to list commits from (default: current)

**Response:**
```json
{
  "commits": [
    {
      "hash": "def456...",
      "message": "Add new feature",
      "author": "User <user@example.com>",
      "date": "2025-09-07T16:20:00Z",
      "files_changed": 2
    }
  ]
}
```

### Push/Pull Operations

#### POST /push
Push changes to remote.

**Request Body:**
```json
{
  "remote": "origin",
  "branch": "main",
  "force": false,
  "tags": false
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Pushed successfully",
  "remote": "origin",
  "branch": "main"
}
```

#### POST /pull
Pull changes from remote.

**Request Body:**
```json
{
  "remote": "origin",
  "branch": "main",
  "rebase": false
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Pulled successfully",
  "remote": "origin",
  "branch": "main",
  "commits_ahead": 0,
  "commits_behind": 0
}
```

### Merge Operations

#### POST /merge
Merge branches.

**Request Body:**
```json
{
  "source": "feature/new-feature",
  "target": "main",
  "no_ff": false,
  "message": "Merge feature branch"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Merge completed successfully",
  "merge_commit": "ghi789...",
  "conflicts": []
}
```

### File Operations

#### GET /files
List files in the repository.

**Query Parameters:**
- `path` (optional): Subdirectory to list (default: root)
- `status` (optional): Filter by Git status (staged, unstaged, untracked)

**Response:**
```json
{
  "files": [
    {
      "name": "src/main.py",
      "path": "src/main.py",
      "status": "modified",
      "size": 1024,
      "last_modified": "2025-09-07T16:20:00Z"
    }
  ]
}
```

#### GET /files/{file_path}
Get file content.

**Path Parameters:**
- `file_path`: Path to the file (URL encoded)

**Response:**
```json
{
  "content": "file content here...",
  "encoding": "utf-8",
  "size": 1024,
  "last_modified": "2025-09-07T16:20:00Z"
}
```

#### PUT /files/{file_path}
Update file content.

**Path Parameters:**
- `file_path`: Path to the file (URL encoded)

**Request Body:**
```json
{
  "content": "new file content...",
  "encoding": "utf-8",
  "message": "Update file content"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "File updated successfully",
  "file": "src/main.py",
  "size": 2048
}
```

### Clone Operations (Legacy Support)

#### POST /clone
Clone a repository (maintains existing functionality).

**Request Body:**
```json
{
  "origin": "https://github.com/user/repo.git",
  "branch": "main",
  "shallow": true,
  "agent_id": "agent-123"
}
```

**Response:**
```json
{
  "status": "success",
  "agent_id": "agent-123",
  "temp_dir": "/tmp/agent-repo-agent-123-xyz",
  "branch": "agent/feature-123",
  "commit": "abc123...",
  "created_at": "2025-09-07T16:25:00Z"
}
```

#### POST /clone/close
Close a cloned repository (maintains existing functionality).

**Request Body:**
```json
{
  "path": "/tmp/agent-repo-agent-123-xyz",
  "message": "Complete feature implementation",
  "agent_id": "agent-123",
  "merge": true,
  "target_branch": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Repository closed successfully",
  "merged": true,
  "merge_commit": "def456..."
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `409 Conflict`: Git operation conflict (merge conflicts, etc.)
- `500 Internal Server Error`: Server error

Error responses include a JSON body with error details:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "additional error details"
  }
}
```

## Rate Limiting

V1 does not implement rate limiting. Future versions may add rate limiting for API protection.

## Logging

All API requests are logged with:
- Timestamp
- HTTP method and path
- Request parameters
- Response status
- Processing time

Logs are written to `logs/api.log` in JSON format.

## Examples

### Starting the Service

```bash
# Start service for a specific repository
cage serve /path/to/my-repository

# Service starts on http://localhost:8000
```

### Basic Usage

```bash
# Check service health
curl http://localhost:8000/health

# Get repository information
curl http://localhost:8000/repository/info

# Create a new branch
curl -X POST http://localhost:8000/branches \
  -H "Content-Type: application/json" \
  -d '{"name": "feature/new-feature", "from": "main", "checkout": true}'

# Make a commit
curl -X POST http://localhost:8000/commits \
  -H "Content-Type: application/json" \
  -d '{"message": "Add new feature", "all": true}'

# Push changes
curl -X POST http://localhost:8000/push \
  -H "Content-Type: application/json" \
  -d '{"remote": "origin", "branch": "feature/new-feature"}'
```

## Future Enhancements

- Authentication and authorization
- Webhook support for repository events
- Real-time collaboration features
- Advanced Git operations (rebase, cherry-pick)
- Repository analytics and insights
- Multi-repository management

