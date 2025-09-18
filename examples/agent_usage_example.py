#!/usr/bin/env python3
"""
Example: Using the Modular Agent System

This example demonstrates how to use the new modular agent system
for creating crews dynamically and testing individual agents.
"""

import sys
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cage.agents import (
    AgentRegistry, AgentFactory, CrewBuilder, AgentType
)
from cage.agents.planner import PlannerAgent, planner_config
from cage.agents.implementer import ImplementerAgent, implementer_config
from cage.agents.reviewer import ReviewerAgent, reviewer_config
from cage.agents.committer import CommitterAgent, committer_config
from cage.agents.config import AgentConfigManager


def setup_logging():
    """Set up logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_individual_agents():
    """Test each agent individually."""
    print("=== Testing Individual Agents ===")
    
    # Test Planner Agent
    print("\n1. Testing Planner Agent:")
    planner = PlannerAgent(planner_config)
    planner.initialize()
    
    test_input = "Create a plan for adding a new API endpoint"
    result = planner.test_agent(test_input)
    print(f"   Success: {result['success']}")
    print(f"   Output: {result['output'][:100]}...")
    
    # Test Implementer Agent
    print("\n2. Testing Implementer Agent:")
    implementer = ImplementerAgent(implementer_config)
    implementer.initialize()
    
    test_input = "Create a new Python file with a simple function"
    result = implementer.test_agent(test_input)
    print(f"   Success: {result['success']}")
    print(f"   Output: {result['output'][:100]}...")
    
    # Test Reviewer Agent
    print("\n3. Testing Reviewer Agent:")
    reviewer = ReviewerAgent(reviewer_config)
    reviewer.initialize()
    
    test_input = "Review the code changes for quality and compliance"
    result = reviewer.test_agent(test_input)
    print(f"   Success: {result['success']}")
    print(f"   Output: {result['output'][:100]}...")
    
    # Test Committer Agent
    print("\n4. Testing Committer Agent:")
    committer = CommitterAgent(committer_config)
    committer.initialize()
    
    test_input = "Commit the changes with a meaningful message"
    result = committer.test_agent(test_input)
    print(f"   Success: {result['success']}")
    print(f"   Output: {result['output'][:100]}...")


def demonstrate_agent_registry():
    """Demonstrate the agent registry system."""
    print("\n=== Agent Registry Demonstration ===")
    
    # Create registry and register agents
    registry = AgentRegistry()
    
    # Register all agents
    registry.register_agent(PlannerAgent, planner_config, "planner")
    registry.register_agent(ImplementerAgent, implementer_config, "implementer")
    registry.register_agent(ReviewerAgent, reviewer_config, "reviewer")
    registry.register_agent(CommitterAgent, committer_config, "committer")
    
    print(f"Registered {len(registry)} agents:")
    for agent_name in registry.list_agents():
        info = registry.get_agent_info(agent_name)
        print(f"  - {agent_name}: {info['role']} ({info['agent_type']})")
    
    # List agents by type
    print(f"\nPlanner agents: {registry.list_agents_by_type(AgentType.PLANNER)}")
    print(f"Implementer agents: {registry.list_agents_by_type(AgentType.IMPLEMENTER)}")


def demonstrate_agent_factory():
    """Demonstrate the agent factory system."""
    print("\n=== Agent Factory Demonstration ===")
    
    # Create factory with registry
    registry = AgentRegistry()
    registry.register_agent(PlannerAgent, planner_config, "planner")
    registry.register_agent(ImplementerAgent, implementer_config, "implementer")
    
    factory = AgentFactory(registry)
    
    # Create agents by name
    planner = factory.create_agent("planner")
    print(f"Created planner agent: {planner}")
    
    # Create agent with configuration overrides
    custom_implementer = factory.create_agent_with_config_override(
        "implementer", 
        {"verbose": False, "allow_delegation": True}
    )
    print(f"Created custom implementer: verbose={custom_implementer.config.verbose}")
    
    # Create agents by type
    planners = factory.create_agents_by_type(AgentType.PLANNER, count=2)
    print(f"Created {len(planners)} planner agents by type")


def demonstrate_crew_builder():
    """Demonstrate the crew builder system."""
    print("\n=== Crew Builder Demonstration ===")
    
    # Set up factory and registry
    registry = AgentRegistry()
    registry.register_agent(PlannerAgent, planner_config, "planner")
    registry.register_agent(ImplementerAgent, implementer_config, "implementer")
    registry.register_agent(ReviewerAgent, reviewer_config, "reviewer")
    registry.register_agent(CommitterAgent, committer_config, "committer")
    
    factory = AgentFactory(registry)
    builder = CrewBuilder(factory)
    
    # Build a planning crew
    print("Building planning crew...")
    planning_crew = (builder
                    .reset()
                    .add_agent("planner")
                    .set_verbose(True)
                    .build())
    
    print(f"Planning crew created with {len(planning_crew.agents)} agents")
    
    # Build a full execution crew
    print("\nBuilding execution crew...")
    execution_crew = (builder
                     .reset()
                     .add_agent("implementer")
                     .add_agent("reviewer")
                     .add_agent("committer")
                     .set_process(Process.sequential)
                     .set_verbose(True)
                     .build())
    
    print(f"Execution crew created with {len(execution_crew.agents)} agents")
    
    # Build a custom crew
    print("\nBuilding custom crew...")
    custom_crew = (builder
                  .reset()
                  .add_agents_by_type(AgentType.PLANNER, count=1)
                  .add_agents_by_type(AgentType.IMPLEMENTER, count=2)
                  .set_verbose(False)
                  .build())
    
    print(f"Custom crew created with {len(custom_crew.agents)} agents")


def demonstrate_configuration_management():
    """Demonstrate configuration management."""
    print("\n=== Configuration Management Demonstration ===")
    
    config_manager = AgentConfigManager()
    
    # List available configurations
    configs = config_manager.list_available_configs()
    print(f"Available configurations: {configs}")
    
    # Get default configurations
    planner_config = config_manager.get_default_config("planner")
    print(f"Planner config role: {planner_config.role}")
    
    # Create configuration template
    template_created = config_manager.create_config_template("custom_agent")
    print(f"Configuration template created: {template_created}")


def demonstrate_adding_new_agent():
    """Demonstrate how to add a new custom agent."""
    print("\n=== Adding New Agent Demonstration ===")
    
    from cage.agents.base import BaseAgent, AgentConfig, AgentType
    
    # Define a custom agent
    class CustomAgent(BaseAgent):
        def _get_agent_type(self):
            return AgentType.CUSTOM
        
        def _get_tools(self):
            return []
    
    # Create configuration for custom agent
    custom_config = AgentConfig(
        role="Custom Agent",
        goal="Perform custom operations",
        backstory="A custom agent for demonstration purposes",
        metadata={"specialization": "custom_operations"}
    )
    
    # Register and use the custom agent
    registry = AgentRegistry()
    registry.register_agent(CustomAgent, custom_config, "custom")
    
    factory = AgentFactory(registry)
    custom_agent = factory.create_agent("custom")
    
    print(f"Created custom agent: {custom_agent}")
    print(f"Agent type: {custom_agent.agent_type.value}")
    print(f"Agent role: {custom_agent.config.role}")
    
    # Test the custom agent
    result = custom_agent.test_agent("Perform a custom operation")
    print(f"Custom agent test result: {result['success']}")


def main():
    """Main function to run all demonstrations."""
    setup_logging()
    
    print("Modular Agent System Demonstration")
    print("=" * 50)
    
    try:
        # Test individual agents
        test_individual_agents()
        
        # Demonstrate registry system
        demonstrate_agent_registry()
        
        # Demonstrate factory system
        demonstrate_agent_factory()
        
        # Demonstrate crew builder
        demonstrate_crew_builder()
        
        # Demonstrate configuration management
        demonstrate_configuration_management()
        
        # Demonstrate adding new agents
        demonstrate_adding_new_agent()
        
        print("\n" + "=" * 50)
        print("All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
