# Modular Agent System

This module provides a modular system for defining and managing CrewAI agents with support for runtime crew construction and individual agent testing.

## Overview

The modular agent system transforms the previously hardcoded agent definitions into a flexible, extensible architecture that enables:

- **Individual Agent Testing**: Each agent can be tested in isolation
- **Runtime Crew Construction**: Build crews dynamically with different agent combinations
- **Easy Agent Addition**: Add new agents without modifying core logic
- **External Configuration**: Configure agents from files or environment variables
- **Agent Registry**: Centralized discovery and management of available agents

## Architecture

### Core Components

1. **Base Agent Classes** (`base.py`)
   - `BaseAgent`: Abstract base class for all agents
   - `AgentConfig`: Configuration dataclass for agent parameters
   - `AgentType`: Enumeration of available agent types

2. **Agent Registry** (`registry.py`)
   - `AgentRegistry`: Central registry for agent discovery and management
   - Supports agent registration, creation, and information retrieval

3. **Agent Factory** (`factory.py`)
   - `AgentFactory`: Factory for creating agent instances
   - `CrewBuilder`: Fluent interface for building crews dynamically

4. **Configuration Management** (`config.py`)
   - `AgentConfigManager`: Handles loading/saving agent configurations
   - Support for file-based and environment variable configurations

5. **Individual Agent Modules**
   - `planner.py`: Planner agent for creating execution plans
   - `implementer.py`: Implementer agent for file operations
   - `reviewer.py`: Reviewer agent for quality assurance
   - `committer.py`: Committer agent for Git operations

## Usage

### Basic Agent Usage

```python
from cage.agents import AgentRegistry, AgentFactory, CrewBuilder
from cage.agents.planner import PlannerAgent, planner_config

# Create registry and register agents
registry = AgentRegistry()
registry.register_agent(PlannerAgent, planner_config, "planner")

# Create factory and build agents
factory = AgentFactory(registry)
planner = factory.create_agent("planner")

# Test individual agent
result = planner.test_agent("Create a plan for adding a new feature")
print(f"Success: {result['success']}")
print(f"Output: {result['output']}")
```

### Dynamic Crew Construction

```python
from crewai import Task, Process

# Create crew builder
builder = CrewBuilder(factory)

# Build a planning crew
planning_crew = (builder
                .reset()
                .add_agent("planner")
                .set_verbose(True)
                .build())

# Build an execution crew
execution_crew = (builder
                 .reset()
                 .add_agent("implementer")
                 .add_agent("reviewer")
                 .add_agent("committer")
                 .set_process(Process.sequential)
                 .build())
```

### Individual Agent Testing

```python
# Test each agent individually
agents_to_test = ["planner", "implementer", "reviewer", "committer"]

for agent_name in agents_to_test:
    result = crew_tool.test_agent(agent_name, "Test input for this agent")
    print(f"{agent_name}: {result['success']}")
```

### Adding New Agents

```python
from cage.agents.base import BaseAgent, AgentConfig, AgentType

# Define custom agent
class CustomAgent(BaseAgent):
    def _get_agent_type(self):
        return AgentType.CUSTOM
    
    def _get_tools(self):
        return []  # Tools injected at runtime

# Create configuration
custom_config = AgentConfig(
    role="Custom Agent",
    goal="Perform custom operations",
    backstory="A custom agent for specific tasks"
)

# Register and use
registry.register_agent(CustomAgent, custom_config, "custom")
custom_agent = factory.create_agent("custom")
```

## Agent Types

### Planner Agent
- **Purpose**: Creates detailed execution plans using Cage-native API endpoints
- **Tools**: None (creates plans for other agents to execute)
- **Output**: JSON-formatted execution plans

### Implementer Agent
- **Purpose**: Executes file operations and code changes
- **Tools**: EditorToolWrapper for file operations
- **Specialization**: File creation, modification, and deletion

### Reviewer Agent
- **Purpose**: Reviews changes for quality and compliance
- **Tools**: EditorToolWrapper for file verification
- **Specialization**: Code quality, tool usage verification

### Committer Agent
- **Purpose**: Handles Git operations and commits
- **Tools**: GitToolWrapper for version control
- **Specialization**: Git staging, committing, and pushing

## Configuration

### File-based Configuration

Create configuration files in `config/agents/`:

```json
{
  "role": "Custom Planner",
  "goal": "Create custom plans",
  "backstory": "Specialized planner for specific domains",
  "verbose": true,
  "allow_delegation": false,
  "metadata": {
    "specialization": "domain_specific"
  }
}
```

### Environment Variables

Set agent-specific environment variables:

```bash
export CAGE_AGENT_PLANNER_ROLE="Custom Planner"
export CAGE_AGENT_PLANNER_GOAL="Create custom plans"
export CAGE_AGENT_PLANNER_VERBOSE="true"
```

### Configuration Loading

```python
from cage.agents.config import AgentConfigManager

config_manager = AgentConfigManager()

# Load from different sources
config = config_manager.get_config("planner", source="file")      # From file
config = config_manager.get_config("planner", source="env")       # From environment
config = config_manager.get_config("planner", source="auto")      # Auto-detect
```

## Testing

### Unit Tests

Run individual agent tests:

```bash
python -m pytest tests/unit/test_agents.py::TestPlannerAgent
python -m pytest tests/unit/test_agents.py::TestImplementerAgent
```

### Integration Tests

Test crew construction and execution:

```bash
python -m pytest tests/integration/test_crew_construction.py
```

### Individual Agent Testing

Test agents in isolation:

```python
# Test specific agent
result = crew_tool.test_agent("planner", "Create a plan for feature X")
assert result["success"] == True

# Test all agents
for agent_name in ["planner", "implementer", "reviewer", "committer"]:
    result = crew_tool.test_agent(agent_name, "Test input")
    print(f"{agent_name}: {result['success']}")
```

## Examples

See `examples/agent_usage_example.py` for comprehensive usage examples including:

- Individual agent testing
- Agent registry management
- Dynamic crew construction
- Configuration management
- Adding custom agents

## Migration from Legacy System

The modular system is designed to be backward compatible. To migrate:

1. **Use ModularCrewTool**: Replace `CrewTool` with `ModularCrewTool`
2. **Same API**: All existing methods work the same way
3. **Additional Features**: Access new features like individual testing
4. **Gradual Migration**: Can be adopted incrementally

```python
# Legacy usage (still works)
from cage.crew_tool import CrewTool

# New modular usage (recommended)
from cage.crew_tool_modular import ModularCrewTool

# Same API, additional features
crew_tool = ModularCrewTool(repo_path, task_manager)

# New: Individual agent testing
result = crew_tool.test_agent("planner", "Test input")
```

## Benefits

### For Development
- **Testability**: Each agent can be tested independently
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new agent types
- **Debugging**: Isolate issues to specific agents

### For Operations
- **Flexibility**: Build crews for different use cases
- **Configuration**: Externalize agent parameters
- **Monitoring**: Track individual agent performance
- **Scaling**: Add/remove agents as needed

### For Users
- **Reliability**: Better error isolation and handling
- **Customization**: Configure agents for specific needs
- **Transparency**: Clear understanding of agent roles
- **Control**: Fine-grained control over crew composition

## Future Enhancements

- **Agent Metrics**: Performance monitoring and analytics
- **Agent Chaining**: Complex agent workflows
- **Dynamic Tool Injection**: Runtime tool assignment
- **Agent Templates**: Pre-configured agent combinations
- **Distributed Agents**: Multi-instance agent execution

## Troubleshooting

### Common Issues

1. **Agent Not Found**: Ensure agent is registered in the registry
2. **Tool Injection**: Tools must be injected before agent initialization
3. **Configuration Errors**: Check configuration file format and environment variables
4. **Test Failures**: Verify agent initialization and tool availability

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific components
logging.getLogger("cage.agents").setLevel(logging.DEBUG)
```

### Support

For issues and questions:
- Check the test files for usage examples
- Review the example script for comprehensive demonstrations
- Examine the agent registry for available agents
- Use the configuration manager for setup issues
