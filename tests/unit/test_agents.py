"""
Unit Tests for Individual Agent Modules

This module provides comprehensive unit tests for testing each agent
individually in isolation, ensuring they can be tested independently.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from pathlib import Path

from src.cage.agents import (
    BaseAgent, AgentConfig, AgentType, AgentRegistry, AgentFactory, CrewBuilder
)
from src.cage.agents.planner import PlannerAgent, planner_config
from src.cage.agents.implementer import ImplementerAgent, implementer_config
from src.cage.agents.reviewer import ReviewerAgent, reviewer_config
from src.cage.agents.committer import CommitterAgent, committer_config
from src.cage.agents.config import AgentConfigManager


class TestBaseAgent:
    """Test cases for the BaseAgent class."""
    
    def test_agent_initialization(self):
        """Test agent initialization with configuration."""
        config = AgentConfig(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory"
        )
        
        agent = BaseAgent(config)
        assert agent.config == config
        assert agent.agent_type is None  # Abstract method not implemented
        assert not agent._initialized
        assert agent.crewai_agent is None
    
    def test_agent_configuration_update(self):
        """Test updating agent configuration."""
        config = AgentConfig(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory"
        )
        
        agent = BaseAgent(config)
        agent.update_config(verbose=False, allow_delegation=True)
        
        assert agent.config.verbose is False
        assert agent.config.allow_delegation is True
        assert not agent._initialized  # Should reset initialization
    
    def test_agent_representation(self):
        """Test string representation of agent."""
        config = AgentConfig(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory"
        )
        
        agent = BaseAgent(config)
        repr_str = repr(agent)
        assert "Test Agent" in repr_str
        assert "BaseAgent" in repr_str


class TestPlannerAgent:
    """Test cases for the PlannerAgent class."""
    
    def test_planner_agent_type(self):
        """Test planner agent type."""
        agent = PlannerAgent(planner_config)
        assert agent._get_agent_type() == AgentType.PLANNER
    
    def test_planner_agent_tools(self):
        """Test planner agent tools (should be empty)."""
        agent = PlannerAgent(planner_config)
        tools = agent._get_tools()
        assert tools == []
    
    def test_planner_agent_initialization(self):
        """Test planner agent initialization."""
        agent = PlannerAgent(planner_config)
        crewai_agent = agent.initialize()
        
        assert agent._initialized
        assert agent.crewai_agent is not None
        assert crewai_agent.role == "Planner"
        assert crewai_agent.goal == planner_config.goal
    
    def test_planner_agent_config(self):
        """Test planner agent configuration."""
        config = PlannerAgent.create_default_config()
        assert config.role == "Planner"
        assert "Cage-native API endpoints" in config.goal
        assert config.verbose is True
        assert config.allow_delegation is False
    
    def test_planner_agent_testing(self):
        """Test planner agent individual testing."""
        agent = PlannerAgent(planner_config)
        agent.initialize()
        
        test_input = "Create a plan for adding a new feature"
        result = agent.test_agent(test_input)
        
        assert result["success"] is True
        assert result["agent_type"] == "planner"
        assert result["role"] == "Planner"
        assert result["input"] == test_input
        assert result["output"] is not None
        assert result["error"] is None
    
    def test_planner_create_plan_task(self):
        """Test creating plan task description."""
        agent = PlannerAgent(planner_config)
        
        task_description = agent.create_plan_task(
            task_title="Test Task",
            task_summary="Test summary",
            success_criteria=["Criteria 1", "Criteria 2"],
            acceptance_checks=["Check 1", "Check 2"]
        )
        
        assert "Test Task" in task_description
        assert "Test summary" in task_description
        assert "Criteria 1" in task_description
        assert "Check 1" in task_description


class TestImplementerAgent:
    """Test cases for the ImplementerAgent class."""
    
    def test_implementer_agent_type(self):
        """Test implementer agent type."""
        agent = ImplementerAgent(implementer_config)
        assert agent._get_agent_type() == AgentType.IMPLEMENTER
    
    def test_implementer_agent_tools(self):
        """Test implementer agent tools."""
        agent = ImplementerAgent(implementer_config)
        tools = agent._get_tools()
        assert tools == []  # Tools injected at runtime
    
    def test_implementer_agent_initialization(self):
        """Test implementer agent initialization."""
        agent = ImplementerAgent(implementer_config)
        crewai_agent = agent.initialize()
        
        assert agent._initialized
        assert agent.crewai_agent is not None
        assert crewai_agent.role == "Implementer"
        assert crewai_agent.goal == implementer_config.goal
    
    def test_implementer_agent_config(self):
        """Test implementer agent configuration."""
        config = ImplementerAgent.create_default_config()
        assert config.role == "Implementer"
        assert "Editor Tool" in config.goal
        assert config.verbose is True
        assert config.allow_delegation is False
    
    def test_implementer_agent_testing(self):
        """Test implementer agent individual testing."""
        agent = ImplementerAgent(implementer_config)
        agent.initialize()
        
        test_input = "Create a new Python file with hello world"
        result = agent.test_agent(test_input)
        
        assert result["success"] is True
        assert result["agent_type"] == "implementer"
        assert result["role"] == "Implementer"
        assert result["input"] == test_input
        assert result["output"] is not None
        assert result["error"] is None
    
    def test_implementer_create_implementation_task(self):
        """Test creating implementation task description."""
        agent = ImplementerAgent(implementer_config)
        
        task_description = agent.create_implementation_task(
            task_title="Test Task",
            plan_content="Test plan content"
        )
        
        assert "Test Task" in task_description
        assert "Test plan content" in task_description
        assert "EditorTool" in task_description


class TestReviewerAgent:
    """Test cases for the ReviewerAgent class."""
    
    def test_reviewer_agent_type(self):
        """Test reviewer agent type."""
        agent = ReviewerAgent(reviewer_config)
        assert agent._get_agent_type() == AgentType.REVIEWER
    
    def test_reviewer_agent_tools(self):
        """Test reviewer agent tools."""
        agent = ReviewerAgent(reviewer_config)
        tools = agent._get_tools()
        assert tools == []  # Tools injected at runtime
    
    def test_reviewer_agent_initialization(self):
        """Test reviewer agent initialization."""
        agent = ReviewerAgent(reviewer_config)
        crewai_agent = agent.initialize()
        
        assert agent._initialized
        assert agent.crewai_agent is not None
        assert crewai_agent.role == "Reviewer"
        assert crewai_agent.goal == reviewer_config.goal
    
    def test_reviewer_agent_config(self):
        """Test reviewer agent configuration."""
        config = ReviewerAgent.create_default_config()
        assert config.role == "Reviewer"
        assert "quality" in config.goal.lower()
        assert config.verbose is True
        assert config.allow_delegation is False
    
    def test_reviewer_agent_testing(self):
        """Test reviewer agent individual testing."""
        agent = ReviewerAgent(reviewer_config)
        agent.initialize()
        
        test_input = "Review the changes made to the codebase"
        result = agent.test_agent(test_input)
        
        assert result["success"] is True
        assert result["agent_type"] == "reviewer"
        assert result["role"] == "Reviewer"
        assert result["input"] == test_input
        assert result["output"] is not None
        assert result["error"] is None
    
    def test_reviewer_create_review_task(self):
        """Test creating review task description."""
        agent = ReviewerAgent(reviewer_config)
        
        task_description = agent.create_review_task("Test Task")
        assert "Test Task" in task_description
        assert "EditorTool" in task_description
    
    def test_reviewer_quality_checklist(self):
        """Test quality checklist creation."""
        agent = ReviewerAgent(reviewer_config)
        checklist = agent.create_quality_checklist()
        
        assert isinstance(checklist, list)
        assert len(checklist) > 0
        assert "EditorTool was used" in checklist[0]


class TestCommitterAgent:
    """Test cases for the CommitterAgent class."""
    
    def test_committer_agent_type(self):
        """Test committer agent type."""
        agent = CommitterAgent(committer_config)
        assert agent._get_agent_type() == AgentType.COMMITTER
    
    def test_committer_agent_tools(self):
        """Test committer agent tools."""
        agent = CommitterAgent(committer_config)
        tools = agent._get_tools()
        assert tools == []  # Tools injected at runtime
    
    def test_committer_agent_initialization(self):
        """Test committer agent initialization."""
        agent = CommitterAgent(committer_config)
        crewai_agent = agent.initialize()
        
        assert agent._initialized
        assert agent.crewai_agent is not None
        assert crewai_agent.role == "Committer"
        assert crewai_agent.goal == committer_config.goal
    
    def test_committer_agent_config(self):
        """Test committer agent configuration."""
        config = CommitterAgent.create_default_config()
        assert config.role == "Committer"
        assert "Git operations" in config.goal
        assert config.verbose is True
        assert config.allow_delegation is False
    
    def test_committer_agent_testing(self):
        """Test committer agent individual testing."""
        agent = CommitterAgent(committer_config)
        agent.initialize()
        
        test_input = "Commit the changes with a meaningful message"
        result = agent.test_agent(test_input)
        
        assert result["success"] is True
        assert result["agent_type"] == "committer"
        assert result["role"] == "Committer"
        assert result["input"] == test_input
        assert result["output"] is not None
        assert result["error"] is None
    
    def test_committer_create_commit_task(self):
        """Test creating commit task description."""
        agent = CommitterAgent(committer_config)
        
        task_description = agent.create_commit_task("Test Task")
        assert "Test Task" in task_description
        assert "commit" in task_description.lower()
    
    def test_committer_create_commit_message(self):
        """Test commit message creation."""
        agent = CommitterAgent(committer_config)
        
        message = agent.create_commit_message(
            task_title="Fix bug in authentication",
            task_id="task-123",
            change_summary="Fixed login validation issue"
        )
        
        assert "fix:" in message
        assert "Fixed login validation issue" in message
        assert "task-123" in message
    
    def test_committer_git_workflow_steps(self):
        """Test Git workflow steps."""
        agent = CommitterAgent(committer_config)
        steps = agent.get_git_workflow_steps()
        
        assert isinstance(steps, list)
        assert len(steps) > 0
        assert "Check git status" in steps[0]


class TestAgentRegistry:
    """Test cases for the AgentRegistry class."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        assert len(registry) == 0
        assert registry.list_agents() == []
    
    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        config = AgentConfig(role="Test", goal="Test goal", backstory="Test backstory")
        
        name = registry.register_agent(PlannerAgent, config)
        assert name == "test"
        assert len(registry) == 1
        assert "test" in registry
    
    def test_get_agent_class(self):
        """Test getting agent class by name."""
        registry = AgentRegistry()
        config = AgentConfig(role="Test", goal="Test goal", backstory="Test backstory")
        
        registry.register_agent(PlannerAgent, config)
        agent_class = registry.get_agent_class("test")
        assert agent_class == PlannerAgent
    
    def test_create_agent(self):
        """Test creating agent instance."""
        registry = AgentRegistry()
        config = AgentConfig(role="Test", goal="Test goal", backstory="Test backstory")
        
        registry.register_agent(PlannerAgent, config)
        agent = registry.create_agent("test")
        
        assert agent is not None
        assert isinstance(agent, PlannerAgent)
        assert agent.config.role == "Test"
    
    def test_list_agents_by_type(self):
        """Test listing agents by type."""
        registry = AgentRegistry()
        
        # Register different agent types
        registry.register_agent(PlannerAgent, planner_config)
        registry.register_agent(ImplementerAgent, implementer_config)
        
        planner_agents = registry.list_agents_by_type(AgentType.PLANNER)
        assert len(planner_agents) == 1
        assert "planner" in planner_agents
    
    def test_agent_info(self):
        """Test getting agent information."""
        registry = AgentRegistry()
        registry.register_agent(PlannerAgent, planner_config)
        
        info = registry.get_agent_info("planner")
        assert info is not None
        assert info["name"] == "planner"
        assert info["role"] == "Planner"
        assert info["agent_type"] == "planner"


class TestAgentFactory:
    """Test cases for the AgentFactory class."""
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = AgentFactory()
        assert factory.registry is not None
    
    def test_create_agent_by_name(self):
        """Test creating agent by name."""
        factory = AgentFactory()
        factory.registry.register_agent(PlannerAgent, planner_config)
        
        agent = factory.create_agent("planner")
        assert agent is not None
        assert isinstance(agent, PlannerAgent)
    
    def test_create_agent_with_config_override(self):
        """Test creating agent with configuration overrides."""
        factory = AgentFactory()
        factory.registry.register_agent(PlannerAgent, planner_config)
        
        overrides = {"verbose": False, "allow_delegation": True}
        agent = factory.create_agent_with_config_override("planner", overrides)
        
        assert agent is not None
        assert agent.config.verbose is False
        assert agent.config.allow_delegation is True
    
    def test_create_agents_by_type(self):
        """Test creating agents by type."""
        factory = AgentFactory()
        factory.registry.register_agent(PlannerAgent, planner_config)
        factory.registry.register_agent(ImplementerAgent, implementer_config)
        
        planners = factory.create_agents_by_type(AgentType.PLANNER, count=2)
        assert len(planners) == 1  # Only one planner registered
        assert all(isinstance(agent, PlannerAgent) for agent in planners)


class TestCrewBuilder:
    """Test cases for the CrewBuilder class."""
    
    def test_crew_builder_initialization(self):
        """Test crew builder initialization."""
        builder = CrewBuilder()
        assert len(builder) == 0
        assert builder._agents == []
        assert builder._tasks == []
    
    def test_add_agent_by_name(self):
        """Test adding agent by name."""
        factory = AgentFactory()
        factory.registry.register_agent(PlannerAgent, planner_config)
        
        builder = CrewBuilder(factory)
        builder.add_agent("planner")
        
        assert len(builder) == 1
        assert builder._agents[0].config.role == "Planner"
    
    def test_add_agent_instance(self):
        """Test adding agent instance."""
        agent = PlannerAgent(planner_config)
        builder = CrewBuilder()
        builder.add_agent(agent)
        
        assert len(builder) == 1
        assert builder._agents[0] == agent
    
    def test_add_agents_by_type(self):
        """Test adding agents by type."""
        factory = AgentFactory()
        factory.registry.register_agent(PlannerAgent, planner_config)
        
        builder = CrewBuilder(factory)
        builder.add_agents_by_type(AgentType.PLANNER, count=1)
        
        assert len(builder) == 1
        assert builder._agents[0].config.role == "Planner"
    
    def test_set_process(self):
        """Test setting crew process."""
        builder = CrewBuilder()
        from crewai import Process
        
        builder.set_process(Process.hierarchical)
        assert builder._process == Process.hierarchical
    
    def test_build_crew(self):
        """Test building a crew."""
        agent = PlannerAgent(planner_config)
        agent.initialize()
        
        builder = CrewBuilder()
        builder.add_agent(agent)
        
        # Create a simple task
        from crewai import Task
        task = Task(
            description="Test task",
            agent=agent.get_agent(),
            expected_output="Test output"
        )
        builder.add_task(task)
        
        crew = builder.build()
        assert crew is not None
        assert len(crew.agents) == 1
        assert len(crew.tasks) == 1
    
    def test_reset_builder(self):
        """Test resetting the builder."""
        agent = PlannerAgent(planner_config)
        builder = CrewBuilder()
        builder.add_agent(agent)
        
        assert len(builder) == 1
        builder.reset()
        assert len(builder) == 0
        assert builder._agents == []
        assert builder._tasks == []


class TestAgentConfigManager:
    """Test cases for the AgentConfigManager class."""
    
    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        manager = AgentConfigManager()
        assert manager.config_dir is not None
        assert len(manager._default_configs) == 4  # 4 default agents
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        manager = AgentConfigManager()
        
        config = manager.get_default_config("planner")
        assert config is not None
        assert config.role == "Planner"
        
        config = manager.get_default_config("nonexistent")
        assert config is None
    
    def test_list_available_configs(self):
        """Test listing available configurations."""
        manager = AgentConfigManager()
        configs = manager.list_available_configs()
        
        assert "planner" in configs
        assert "implementer" in configs
        assert "reviewer" in configs
        assert "committer" in configs


if __name__ == "__main__":
    pytest.main([__file__])
