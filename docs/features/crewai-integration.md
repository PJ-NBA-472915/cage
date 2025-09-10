# Phase 4: CrewAI Integration - Feature Documentation

## Overview

Phase 4 implements intelligent AI agent workflows using CrewAI, enabling automated task planning, execution, and management. This phase adds the intelligent automation layer that can analyze tasks, create detailed execution plans, and coordinate file operations through specialized AI agents.

## Architecture

The CrewAI integration consists of four specialized agents working together:

- **Planner Agent**: Analyzes tasks and creates detailed execution plans
- **Implementer Agent**: Executes file operations and code changes
- **Reviewer Agent**: Reviews changes for quality and compliance
- **Committer Agent**: Handles Git operations and creates commits

## Core Components

### 1. CrewTool Class

The main orchestrator for AI workflows, located in `src/cage/crew_tool.py`.

**Key Methods:**
- `create_plan(task_id, plan_data)` - Creates detailed execution plans
- `apply_plan(task_id, run_id)` - Executes plans using AI agents
- `get_run_status(run_id)` - Retrieves run status and logs
- `upload_artefacts(run_id, files)` - Uploads files to run directories

### 2. Agent Wrappers

**EditorToolWrapper**: Enables AI agents to perform file operations
- Inherits from CrewAI BaseTool
- Provides structured file operations (GET, INSERT, UPDATE, DELETE)
- Integrates with existing Editor Tool functionality

**GitToolWrapper**: Enables AI agents to perform Git operations
- Inherits from CrewAI BaseTool
- Provides Git operations (add, commit, push, pull)
- Integrates with existing Git Tool functionality

### 3. Run Management System

**Directory Structure:**
```
.cage/runs/
├── {run_id}/
│   ├── plan.yaml          # Execution plan
│   ├── status.json        # Run status and metadata
│   └── artefacts/         # Uploaded files
│       ├── file1.txt
│       └── file2.txt
```

**Run Status Fields:**
- `run_id`: Unique identifier for the run
- `task_id`: Associated task identifier
- `status`: Current status (pending, running, completed, failed)
- `started_at`: Run start timestamp
- `completed_at`: Run completion timestamp
- `error`: Error message if failed
- `logs`: Array of log entries
- `artefacts`: Array of uploaded file paths

## API Endpoints

### POST /crew/plan

Creates a detailed execution plan for a task.

**Request:**
```json
{
  "task_id": "2025-09-10-example-task",
  "plan": {
    "description": "Additional plan context",
    "constraints": ["specific requirements"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "run_id": "uuid-1234-5678-9abc",
  "task_id": "2025-09-10-example-task",
  "plan": "Detailed execution plan created by AI agent"
}
```

### POST /crew/apply

Executes a plan using AI agents.

**Request:**
```json
{
  "task_id": "2025-09-10-example-task",
  "run_id": "uuid-1234-5678-9abc"
}
```

**Response:**
```json
{
  "status": "success",
  "run_id": "uuid-1234-5678-9abc",
  "task_id": "2025-09-10-example-task",
  "result": "Execution completed successfully"
}
```

### GET /crew/runs/{run_id}

Retrieves run status and metadata.

**Response:**
```json
{
  "status": "success",
  "run_data": {
    "run_id": "uuid-1234-5678-9abc",
    "task_id": "2025-09-10-example-task",
    "status": "completed",
    "started_at": "2025-09-10T16:00:00",
    "completed_at": "2025-09-10T16:30:00",
    "logs": ["Execution completed successfully"],
    "artefacts": [".cage/runs/uuid-1234-5678-9abc/artefacts/output.txt"]
  }
}
```

### POST /crew/runs/{run_id}/artefacts

Uploads files to a run directory.

**Request:**
```json
{
  "file1.txt": "File content 1",
  "file2.txt": "File content 2"
}
```

**Response:**
```json
{
  "status": "success",
  "run_id": "uuid-1234-5678-9abc",
  "uploaded_files": [
    ".cage/runs/uuid-1234-5678-9abc/artefacts/file1.txt",
    ".cage/runs/uuid-1234-5678-9abc/artefacts/file2.txt"
  ]
}
```

## CLI Commands

### Plan Creation

```bash
# Create a plan for a task
cage crew plan 2025-09-10-example-task

# Create a plan with custom plan data
cage crew plan 2025-09-10-example-task --plan-file plan.json

# Specify repository path
cage crew plan 2025-09-10-example-task --repo-path /path/to/repo
```

### Plan Execution

```bash
# Execute a plan for a task
cage crew apply 2025-09-10-example-task

# Execute a specific run
cage crew apply 2025-09-10-example-task --run-id uuid-1234-5678-9abc

# Specify repository path
cage crew apply 2025-09-10-example-task --repo-path /path/to/repo
```

### Run Management

```bash
# Check run status
cage crew status uuid-1234-5678-9abc

# List all runs
cage crew list-runs

# Upload artefacts
cage crew upload uuid-1234-5678-9abc '{"file.txt": "content"}'
```

## Usage Examples

### Basic Workflow

1. **Create a Task**
   ```bash
   cage task create 2025-09-10-refactor-code "Refactor authentication module" --summary "Improve code structure and add tests"
   ```

2. **Create a Plan**
   ```bash
   cage crew plan 2025-09-10-refactor-code
   ```

3. **Execute the Plan**
   ```bash
   cage crew apply 2025-09-10-refactor-code
   ```

4. **Check Status**
   ```bash
   cage crew status <run_id>
   ```

### Advanced Workflow with Custom Plan

1. **Create Custom Plan File**
   ```json
   {
     "description": "Refactor authentication module with focus on security",
     "constraints": [
       "Maintain backward compatibility",
       "Add comprehensive tests",
       "Follow OWASP guidelines"
     ],
     "steps": [
       "Analyze current authentication code",
       "Identify security vulnerabilities",
       "Refactor core authentication logic",
       "Add unit and integration tests",
       "Update documentation"
     ]
   }
   ```

2. **Create Plan with Custom Data**
   ```bash
   cage crew plan 2025-09-10-refactor-code --plan-file custom-plan.json
   ```

3. **Execute and Monitor**
   ```bash
   cage crew apply 2025-09-10-refactor-code
   cage crew list-runs
   cage crew status <run_id>
   ```

## Configuration

### Environment Variables

```bash
# Required for AI functionality
export OPENAI_API_KEY="your-openai-api-key"

# Optional configuration
export POD_ID="dev-pod"
export POD_TOKEN="dev-token"
export REPO_PATH="/path/to/repository"
```

### Agent Configuration

Agents can be configured by modifying the `_setup_agents()` method in `CrewTool`:

```python
# Example: Customize planner agent
self.planner_agent = Agent(
    role="Senior Software Architect",
    goal="Create comprehensive, production-ready execution plans",
    backstory="You are an expert software architect with 15+ years experience...",
    verbose=True,
    allow_delegation=False,
    tools=[]
)
```

## Error Handling

### Common Error Scenarios

1. **Missing API Key**
   ```
   Error: OpenAIException - The api_key client option must be set
   Solution: Set OPENAI_API_KEY environment variable
   ```

2. **Task Not Found**
   ```
   Error: Task 2025-09-10-example-task not found
   Solution: Ensure task exists before creating plan
   ```

3. **Run Not Found**
   ```
   Error: Run uuid-1234-5678-9abc not found
   Solution: Check run ID or create plan first
   ```

### Error Recovery

- Failed runs are marked with `status: "failed"` and include error details
- Partial execution results are preserved in run directories
- Logs provide detailed error information for debugging
- Artefacts are retained even for failed runs

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Run all CrewAI tests
python -m pytest tests/unit/test_crew_tool.py -v

# Run specific test
python -m pytest tests/unit/test_crew_tool.py::TestCrewTool::test_create_plan_success -v
```

### Test Coverage

The test suite covers:
- Agent initialization and configuration
- Plan creation and execution
- Run status management
- Artefact upload functionality
- Error handling scenarios

## Integration Points

### With Phase 1 (Task Management)
- Uses TaskManager for task loading and updates
- Updates task provenance with commit information
- Integrates with task status tracking

### With Phase 2 (Editor Tool)
- Uses EditorTool for all file operations
- Leverages structured file operations (GET, INSERT, UPDATE, DELETE)
- Maintains file locking and conflict detection

### With Phase 3 (Git Integration)
- Uses GitTool for commit operations
- Tracks commit history in task provenance
- Enables automated commit message generation

## Performance Considerations

### Resource Usage
- AI agents require OpenAI API calls (cost consideration)
- Run directories grow over time (cleanup recommended)
- Concurrent runs are supported but may impact performance

### Optimization Tips
- Use specific, focused task descriptions for better AI planning
- Monitor run directory size and clean up old runs periodically
- Consider rate limiting for high-volume usage

## Security Considerations

### API Key Management
- Store OpenAI API keys securely
- Use environment variables, not hardcoded keys
- Consider key rotation for production environments

### File Access
- AI agents have access to repository files through Editor Tool
- Review and validate AI-generated changes before committing
- Use reviewer agent to enforce security policies

## Troubleshooting

### Debug Mode

Enable verbose logging:

```python
# In crew_tool.py
self.planner_agent = Agent(
    # ... other config
    verbose=True  # Enable detailed logging
)
```

### Common Issues

1. **Plan Creation Fails**
   - Check task exists and is properly formatted
   - Verify OpenAI API key is set
   - Review task description for clarity

2. **Execution Hangs**
   - Check for file locking conflicts
   - Verify Git repository is in clean state
   - Review agent tool configurations

3. **Poor Plan Quality**
   - Provide more detailed task descriptions
   - Include specific requirements and constraints
   - Review agent backstories and goals

## Future Enhancements

### Planned Features
- Custom agent roles and specializations
- Advanced plan templates and patterns
- Integration with external tools and services
- Enhanced error recovery and retry mechanisms
- Performance monitoring and analytics

### Extension Points
- Custom tool wrappers for specialized operations
- Custom agent backstories and capabilities
- Integration with additional AI providers
- Custom run status and logging formats
