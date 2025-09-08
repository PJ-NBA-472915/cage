# Cage Repository Service Documentation

This directory contains documentation and testing resources for the Cage Repository Service API.

## Files

- `api-design.md` - Comprehensive API design documentation
- `cage-api-postman-collection.json` - Postman collection for API testing
- `README.md` - This file

## Quick Start

### 1. Start the Cage Service

```bash
# Using the CLI directly
cage serve /path/to/your/repository

# Using Make (recommended)
make serve REPO=/path/to/your/repository

# Service will be available at http://localhost:8000
```

### 2. Import Postman Collection

1. Open Postman
2. Click "Import" button
3. Select `cage-api-postman-collection.json`
4. The collection will be imported with all API endpoints

### 3. Configure Variables

Before using the collection, update the collection variables:

1. Open the collection in Postman
2. Go to "Variables" tab
3. Update the following variables:
   - `base_url`: Set to your service URL (default: `http://localhost:8000`)
   - `repository_path`: Set to your repository path (default: `/path/to/your/repository`)

## API Endpoints Overview

### Health & Status
- `GET /health` - Check service health and repository status
- `GET /repository/info` - Get repository information
- `GET /repository/status` - Get detailed Git status

### Branch Operations
- `GET /branches` - List all branches
- `POST /branches` - Create a new branch
- `DELETE /branches/{name}` - Delete a branch

### Commit Operations
- `POST /commits` - Create a new commit

### Push/Pull Operations
- `POST /push` - Push changes to remote
- `POST /pull` - Pull changes from remote

### Merge Operations
- `POST /merge` - Merge branches

### Legacy Clone Operations
- `GET /repos` - List open repositories
- `POST /repos` - Clone a repository
- `POST /repos/close` - Close a cloned repository

## Testing Workflows

### Basic Repository Operations

1. **Check Service Health**
   - Run "Health Check" request
   - Verify repository path and status

2. **Create and Work with Branches**
   - Run "Create Branch" to create a new feature branch
   - Run "List Branches" to see all branches
   - Make changes to files in your repository
   - Run "Create Commit" to commit changes
   - Run "Push Changes" to push to remote

3. **Merge Workflow**
   - Run "Merge Branch" to merge feature branch
   - Run "Delete Branch" to clean up

### Error Testing

1. **Repository Not Set**
   - Start service without repository path
   - Run any repository endpoint to see error

2. **Invalid Operations**
   - Try to delete non-existent branch
   - Try to merge with conflicts

## Make Commands

The project includes convenient Make commands for common operations:

```bash
# Show all available commands
make help

# Start service for a repository
make serve REPO=/path/to/repository

# Install dependencies
make install

# Run tests
make test

# Run end-to-end tests
make test-e2e

# Follow API logs
make tail-logs
```

## Environment Setup

### Prerequisites

- Git repository with at least one commit
- Cage service installed and running
- Postman (or compatible API client)

### Service Configuration

The service can be configured with environment variables:

```bash
# Set custom port
cage serve /path/to/repo --port 8080

# Set custom host
cage serve /path/to/repo --host 127.0.0.1
```

## Troubleshooting

### Common Issues

1. **"Repository path not set" error**
   - Make sure you started the service with `cage serve <path>`
   - Verify the path is a valid Git repository

2. **Git command failures**
   - Ensure Git is installed and accessible
   - Check repository permissions
   - Verify network connectivity for remote operations

3. **Port already in use**
   - Use a different port: `cage serve /path/to/repo --port 8080`
   - Stop other services using port 8000

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export CAGE_DEBUG=1
cage serve /path/to/repo
```

## API Response Examples

### Successful Health Check

```json
{
  "status": "success",
  "date": "2025-09-07T17:00:00Z",
  "repository": {
    "path": "/path/to/repository",
    "branch": "main",
    "commit": "abc123...",
    "status": "clean"
  }
}
```

### Repository Information

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
  "last_modified": "2025-09-07T17:00:00Z"
}
```

### Error Response

```json
{
  "error": "Repository path not set. Start the service with 'cage serve <path>'",
  "code": "REPOSITORY_NOT_SET",
  "details": {}
}
```

## Contributing

When adding new API endpoints:

1. Update `api-design.md` with endpoint documentation
2. Add corresponding requests to the Postman collection
3. Include example requests and responses
4. Test error scenarios

## License

This documentation is part of the Cage Repository Service project.
