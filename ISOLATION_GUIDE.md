# Cage Platform Isolation Guide

This guide explains how to use the isolated testing system to ensure CrewAI agents only work within designated repositories.

## Overview

The isolation system creates dedicated test repositories in `.scratchpad/` directory and ensures that:
- CrewAI agents can only access files within their assigned repository
- Each test gets a clean, isolated environment
- No accidental modifications to the main codebase
- Proper Git tracking for all changes

## Quick Start

### 1. Create a Test Repository

```bash
# Create a new isolated test repository
python manage-isolated-tests.py create --name "my-test" --description "Description of what this test does"
```

### 2. Start Cage Service with Isolation

```bash
# Start Cage service restricted to the test repository
python manage-isolated-tests.py start --name "my-test" --port 8000
```

### 3. Test the Isolation

```bash
# In another terminal, test that operations are restricted
python test-isolation.py
```

### 4. Clean Up

```bash
# Remove a specific test repository
python manage-isolated-tests.py cleanup --name "my-test"

# Remove all test repositories
python manage-isolated-tests.py cleanup-all
```

## Available Commands

### `manage-isolated-tests.py`

| Command | Description | Required Args |
|---------|-------------|---------------|
| `create` | Create new test repository | `--name` |
| `list` | List all test repositories | None |
| `start` | Start Cage service with isolation | `--name` |
| `cleanup` | Remove specific test repository | `--name` |
| `cleanup-all` | Remove all test repositories | None |

### Options

- `--name`: Name of the test repository
- `--description`: Description of the test (optional)
- `--port`: Port for Cage service (default: 8000)

## Example Workflow

### Testing a New Feature

1. **Create isolated environment:**
   ```bash
   python manage-isolated-tests.py create --name "feature-test" --description "Testing new feature X"
   ```

2. **Start isolated Cage service:**
   ```bash
   python manage-isolated-tests.py start --name "feature-test"
   ```

3. **Submit task to CrewAI:**
   ```bash
   curl -X POST http://localhost:8000/crew/plan \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer EQmjYQJJRRF4TQo3QgXn8CyQMAYrEhbz" \
     -d '{"task_id": "test-feature", "plan": {...}}'
   ```

4. **Verify isolation:**
   - Check that files are only created in `.scratchpad/feature-test/`
   - Verify no changes to main codebase
   - Test that API operations are restricted to the test directory

5. **Clean up:**
   ```bash
   python manage-isolated-tests.py cleanup --name "feature-test"
   ```

## Security Features

### Repository Isolation
- Each test gets its own Git repository
- Cage service is configured with `REPO_PATH` environment variable
- All file operations are restricted to the designated directory
- No access to parent directories or main codebase

### Environment Variables
- `REPO_PATH`: Absolute path to the isolated repository
- `POD_TOKEN`: Authentication token for API access
- `POD_ID`: Unique identifier for the test session

### File Operations
- All `/files/edit` operations are scoped to the isolated repository
- Git operations only affect the test repository
- No cross-contamination between tests

## Best Practices

### 1. Naming Conventions
- Use descriptive names: `feature-name-test`, `bug-fix-test`, `integration-test`
- Include date if needed: `2025-09-15-note-app-test`

### 2. Test Organization
- One test per repository
- Clear descriptions for each test
- Regular cleanup of old test repositories

### 3. Verification
- Always run `test-isolation.py` to verify isolation
- Check that files are created in the correct directory
- Verify no unintended changes to main codebase

### 4. Documentation
- Document what each test is supposed to do
- Keep test repositories small and focused
- Clean up after testing is complete

## Troubleshooting

### Common Issues

1. **"Repository path does not exist"**
   - Ensure the test repository was created successfully
   - Check the path in `.scratchpad/` directory

2. **"Not a Git repository"**
   - The directory exists but isn't a Git repository
   - Recreate the test repository

3. **API connection errors**
   - Ensure Cage service is running on the correct port
   - Check that the service started successfully

4. **File operations fail**
   - Verify the service is using the correct repository path
   - Check API authentication token

### Debug Commands

```bash
# List all test repositories
python manage-isolated-tests.py list

# Check repository structure
ls -la .scratchpad/

# Verify Git repository
cd .scratchpad/<test-name> && git status

# Test API connectivity
python test-isolation.py
```

## Integration with CrewAI

When using CrewAI agents with isolation:

1. **Always specify the test repository** when starting the service
2. **Use descriptive task names** that match the test purpose
3. **Verify agent operations** are restricted to the test directory
4. **Monitor file changes** to ensure isolation is working
5. **Clean up** test repositories after completion

## Example: Complete Test Session

```bash
# 1. Create test environment
python manage-isolated-tests.py create --name "note-app-v2" --description "Testing improved note app"

# 2. Start isolated service
python manage-isolated-tests.py start --name "note-app-v2" &
SERVICE_PID=$!

# 3. Wait for service to start
sleep 5

# 4. Test isolation
python test-isolation.py

# 5. Submit CrewAI task
curl -X POST http://localhost:8000/crew/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EQmjYQJJRRF4TQo3QgXn8CyQMAYrEhbz" \
  -d '{"task_id": "note-app-v2", "plan": {...}}'

# 6. Monitor and verify
# ... do testing ...

# 7. Clean up
kill $SERVICE_PID
python manage-isolated-tests.py cleanup --name "note-app-v2"
```

This isolation system ensures that all future CrewAI testing is properly contained and doesn't affect the main codebase.
