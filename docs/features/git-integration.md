# Phase 3: Git Integration - Feature Documentation

## Overview

Phase 3 implements comprehensive Git integration with commit trail tracking, providing full version control capabilities for the Cage Pod system. This phase enables automated Git operations, commit provenance tracking, and seamless integration with the Editor Tool for complete workflow management.

## Architecture

The Git integration consists of:

- **GitTool Class**: Core Git operations and repository management
- **REST API Endpoints**: HTTP interface for Git operations
- **CLI Commands**: Command-line interface for Git functionality
- **Provenance Tracking**: Automatic commit tracking in task files
- **Event Emission**: System events for Git operations

## Core Components

### 1. GitTool Class

Located in `src/cage/git_tool.py`, provides all Git operations.

**Key Methods:**
- `get_status()` - Get repository status
- `get_branches()` - List all branches
- `create_branch(name)` - Create and switch to new branch
- `commit(message, task_id, author)` - Create commit with provenance tracking
- `push(remote, branch)` - Push changes to remote
- `pull(remote, branch)` - Pull changes from remote
- `merge_branch(source)` - Merge branch into current
- `get_commit_history(limit)` - Get commit history

### 2. Commit Provenance Tracking

Automatic tracking of commits in task files:

```json
{
  "provenance": {
    "commits": [
      {
        "sha": "abc123def456",
        "title": "feat: add authentication module",
        "files_changed": ["src/auth.py", "tests/test_auth.py"],
        "insertions": 150,
        "deletions": 0,
        "timestamp": "2025-09-10T16:30:00Z"
      }
    ]
  }
}
```

### 3. Event Emission

System events for Git operations:
- `cage.git.commit.created` - Emitted after successful commit
- Additional events for push, pull, merge operations

## API Endpoints

### GET /git/status

Get current repository status.

**Response:**
```json
{
  "status": "success",
  "data": {
    "current_branch": "main",
    "commit_count": 42,
    "is_clean": false,
    "staged_files": ["src/auth.py"],
    "unstaged_files": ["README.md"],
    "untracked_files": ["temp.txt"]
  }
}
```

### GET /git/branch

List all branches.

**Response:**
```json
{
  "status": "success",
  "data": {
    "branches": ["main", "feature/auth", "hotfix/security"],
    "current": "main"
  }
}
```

### POST /git/branch

Create a new branch.

**Request:**
```json
{
  "name": "feature/new-feature",
  "from_branch": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Created branch: feature/new-feature",
  "data": {
    "branch": "feature/new-feature",
    "from": "main"
  }
}
```

### POST /git/commit

Create a commit with optional task tracking.

**Request:**
```json
{
  "message": "feat: add user authentication",
  "include_audits": ["audit-123"],
  "coauthors": ["user@example.com"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Commit created successfully",
  "data": {
    "sha": "abc123def456789",
    "title": "feat: add user authentication",
    "files_changed": ["src/auth.py", "tests/test_auth.py"],
    "insertions": 150,
    "deletions": 0,
    "timestamp": "2025-09-10T16:30:00Z"
  }
}
```

### POST /git/push

Push changes to remote repository.

**Request:**
```json
{
  "remote": "origin",
  "branch": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Pushed to origin/main",
  "data": {
    "remote": "origin",
    "branch": "main",
    "commits_pushed": 3
  }
}
```

### POST /git/pull

Pull changes from remote repository.

**Request:**
```json
{
  "remote": "origin",
  "branch": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Pulled from origin/main",
  "data": {
    "remote": "origin",
    "branch": "main",
    "commits_pulled": 2
  }
}
```

### POST /git/merge

Merge a branch into current branch.

**Request:**
```json
{
  "source": "feature/auth",
  "target": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Merged branch: feature/auth",
  "data": {
    "source": "feature/auth",
    "target": "main",
    "merge_commit": "def456ghi789"
  }
}
```

### GET /git/history

Get commit history.

**Query Parameters:**
- `limit` (optional): Number of commits to return (default: 10)

**Response:**
```json
{
  "status": "success",
  "data": {
    "commits": [
      {
        "sha": "abc123def456",
        "title": "feat: add authentication module",
        "author": "developer@example.com",
        "date": "2025-09-10T16:30:00Z",
        "message": "feat: add authentication module\n\n- Implemented JWT authentication\n- Added user management\n- Created comprehensive tests"
      }
    ]
  }
}
```

## CLI Commands

### Repository Status

```bash
# Get current repository status
cage git status

# List all branches
cage git branches
```

### Branch Management

```bash
# Create and switch to new branch
cage git create-branch feature/new-feature

# Create branch from specific branch
cage git create-branch feature/hotfix main
```

### Commit Operations

```bash
# Create commit with message
cage git commit "feat: add new feature"

# Create commit with author
cage git commit "fix: resolve bug" --author "developer@example.com"

# Create commit with task tracking
cage git commit "refactor: improve code structure" --task-id 2025-09-10-refactor
```

### Remote Operations

```bash
# Push to remote
cage git push

# Push specific branch
cage git push --branch feature/new-feature

# Push to specific remote
cage git push --remote upstream

# Pull from remote
cage git pull

# Pull specific branch
cage git pull --branch feature/new-feature
```

### Merge Operations

```bash
# Merge branch into current
cage git merge feature/new-feature

# Merge with conflict resolution
cage git merge feature/complex-feature
```

### History and Logs

```bash
# Show commit history
cage git history

# Show last 20 commits
cage git history --limit 20
```

## Usage Examples

### Basic Workflow

1. **Check Repository Status**
   ```bash
   cage git status
   ```

2. **Create Feature Branch**
   ```bash
   cage git create-branch feature/user-auth
   ```

3. **Make Changes and Commit**
   ```bash
   # Make file changes using Editor Tool
   cage git commit "feat: implement user authentication" --task-id 2025-09-10-auth
   ```

4. **Push Changes**
   ```bash
   cage git push --branch feature/user-auth
   ```

5. **Merge to Main**
   ```bash
   cage git merge feature/user-auth
   cage git push
   ```

### Advanced Workflow with Task Integration

1. **Create Task**
   ```bash
   cage task create 2025-09-10-refactor "Refactor authentication module"
   ```

2. **Start Feature Branch**
   ```bash
   cage git create-branch feature/refactor-auth
   ```

3. **Make Changes with Task Tracking**
   ```bash
   # Each commit automatically updates task provenance
   cage git commit "refactor: extract auth service" --task-id 2025-09-10-refactor
   cage git commit "test: add auth service tests" --task-id 2025-09-10-refactor
   cage git commit "docs: update auth documentation" --task-id 2025-09-10-refactor
   ```

4. **Review Task Progress**
   ```bash
   cage task show 2025-09-10-refactor
   # Shows all commits in provenance.commits[]
   ```

5. **Complete and Merge**
   ```bash
   cage git push --branch feature/refactor-auth
   cage git merge feature/refactor-auth
   cage git push
   ```

### Collaborative Workflow

1. **Sync with Remote**
   ```bash
   cage git pull
   ```

2. **Create Personal Branch**
   ```bash
   cage git create-branch feature/my-contribution
   ```

3. **Work and Commit**
   ```bash
   cage git commit "feat: add my feature" --task-id 2025-09-10-my-task
   cage git push --branch feature/my-contribution
   ```

4. **Create Pull Request** (external process)
   - Use GitHub/GitLab interface
   - Review and approve changes

5. **Merge and Cleanup**
   ```bash
   cage git pull  # Get merged changes
   cage git create-branch cleanup  # Clean up old branches
   ```

## Integration Points

### With Phase 1 (Task Management)
- Automatic task provenance tracking
- Commit information stored in task files
- Task status updates based on Git operations

### With Phase 2 (Editor Tool)
- Seamless integration with file operations
- Automatic staging of changes
- Conflict detection and resolution

### With Phase 4 (CrewAI Integration)
- AI agents can perform Git operations
- Automated commit message generation
- Intelligent branch management

## Configuration

### Environment Variables

```bash
# Git configuration
export GIT_AUTHOR_NAME="Cage System"
export GIT_AUTHOR_EMAIL="cage@example.com"

# Repository settings
export REPO_PATH="/path/to/repository"
export DEFAULT_REMOTE="origin"
export DEFAULT_BRANCH="main"
```

### Git Configuration

The system respects existing Git configuration:

```bash
# Set global Git configuration
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Set repository-specific configuration
git config user.name "Cage System"
git config user.email "cage@example.com"
```

## Error Handling

### Common Error Scenarios

1. **Repository Not Found**
   ```
   Error: Not a git repository
   Solution: Initialize repository with 'git init' or check REPO_PATH
   ```

2. **Merge Conflicts**
   ```
   Error: Merge conflict in file.py
   Solution: Resolve conflicts manually and retry merge
   ```

3. **Remote Connection Failed**
   ```
   Error: Could not connect to remote repository
   Solution: Check remote URL and network connectivity
   ```

4. **Branch Already Exists**
   ```
   Error: Branch 'feature/existing' already exists
   Solution: Use different branch name or delete existing branch
   ```

### Error Recovery

- Failed operations preserve repository state
- Detailed error messages for troubleshooting
- Automatic rollback for failed operations
- Conflict resolution guidance

## Security Considerations

### Commit Signing

```bash
# Enable commit signing
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY
```

### Access Control

- Repository access controlled by Git permissions
- API endpoints require POD_TOKEN authentication
- CLI commands respect user permissions

### Audit Trail

- All operations logged with timestamps
- Commit provenance provides complete history
- Task integration enables change tracking

## Performance Considerations

### Large Repositories

- Optimized for repositories with thousands of commits
- Efficient branch listing and history retrieval
- Minimal memory usage for status operations

### Network Operations

- Push/pull operations optimized for large changes
- Progress indicators for long-running operations
- Retry mechanisms for network failures

## Testing

### Unit Tests

```bash
# Run Git integration tests
python -m pytest tests/unit/test_git_tool.py -v

# Run specific test
python -m pytest tests/unit/test_git_tool.py::TestGitTool::test_commit -v
```

### Integration Tests

```bash
# Run full integration tests
python -m pytest tests/integration/test_git_integration.py -v
```

## Troubleshooting

### Debug Mode

Enable verbose Git operations:

```bash
# Set environment variable
export GIT_VERBOSE=1

# Or use Git's built-in verbose mode
cage git status --verbose
```

### Common Issues

1. **Slow Operations**
   - Check repository size and history
   - Verify network connectivity for remote operations
   - Consider repository optimization

2. **Permission Errors**
   - Verify Git user configuration
   - Check repository permissions
   - Ensure proper authentication

3. **Merge Conflicts**
   - Use `git status` to identify conflicted files
   - Resolve conflicts manually
   - Complete merge with `git add` and `git commit`

## Future Enhancements

### Planned Features
- Advanced merge strategies
- Automated conflict resolution
- Integration with CI/CD systems
- Enhanced commit message templates
- Branch protection rules

### Extension Points
- Custom commit message generators
- Integration with external Git providers
- Advanced branch management strategies
- Custom merge conflict resolvers