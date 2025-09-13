"""
CrewAI Integration Tool for Cage Pod

This module implements the CrewAI integration for AI agent workflows,
including planning, execution, and run management.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel

from .editor_tool import EditorTool, FileOperation, OperationType
from .git_tool import GitTool
from .task_models import TaskManager


@dataclass
class RunStatus:
    """Status of a crew run."""
    run_id: str
    task_id: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    logs: List[str] = None
    artefacts: List[str] = None


class CrewTool:
    """CrewAI integration tool for Cage Pod."""
    
    def __init__(self, repo_path: Path, task_manager: TaskManager):
        self.repo_path = repo_path
        self.task_manager = task_manager
        self.editor_tool = EditorTool(repo_path, task_manager=task_manager)
        self.git_tool = GitTool(repo_path)
        self.runs_dir = repo_path / ".cage" / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize CrewAI agents
        self._setup_agents()
    
    def _setup_agents(self):
        """Set up CrewAI agents for different roles."""
        
        # Planner Agent - Creates detailed plans for task execution
        self.planner_agent = Agent(
            role="Planner",
            goal="Create detailed, actionable plans for task execution",
            backstory="""You are an expert software architect and project planner. 
            You analyze tasks and create comprehensive, step-by-step plans that break down 
            complex work into manageable, executable steps. You consider dependencies, 
            risks, and best practices in your planning.""",
            verbose=True,
            allow_delegation=False,
            tools=[]
        )
        
        # Implementer Agent - Executes file operations and code changes
        self.implementer_agent = Agent(
            role="Implementer", 
            goal="Execute file operations and implement code changes according to plans",
            backstory="""You are an expert software developer with deep knowledge of 
            code structure, best practices, and implementation patterns. You carefully 
            execute file operations, making precise changes while maintaining code quality 
            and following established patterns.""",
            verbose=True,
            allow_delegation=False,
            tools=[EditorToolWrapper(self.editor_tool)]
        )
        
        # Reviewer Agent - Reviews changes and enforces policies
        self.reviewer_agent = Agent(
            role="Reviewer",
            goal="Review changes for quality, compliance, and policy adherence",
            backstory="""You are an expert code reviewer and quality assurance specialist. 
            You carefully review all changes for correctness, adherence to coding standards, 
            security best practices, and policy compliance. You ensure that all changes 
            meet the required quality standards before they are committed.""",
            verbose=True,
            allow_delegation=False,
            tools=[EditorToolWrapper(self.editor_tool)]
        )
        
        # Committer Agent - Handles Git operations and final commits
        self.committer_agent = Agent(
            role="Committer",
            goal="Handle Git operations and create proper commits with meaningful messages",
            backstory="""You are an expert in version control and Git workflows. You handle 
            all Git operations including staging, committing, and pushing changes. You create 
            clear, descriptive commit messages that follow best practices and provide good 
            audit trails.""",
            verbose=True,
            allow_delegation=False,
            tools=[GitToolWrapper(self.git_tool)]
        )
    
    def create_plan(self, task_id: str, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed plan for task execution."""
        try:
            # Load the task
            task = self.task_manager.load_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Create run ID
            run_id = str(uuid.uuid4())
            
            # Create run directory
            run_dir = self.runs_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            
            # Create plan using planner agent
            plan_task = Task(
                description=f"""Create a detailed execution plan for task: {task.title}
                
                Task Summary: {task.summary}
                Success Criteria: {[c.text for c in task.success_criteria]}
                Acceptance Checks: {[c.text for c in task.acceptance_checks]}
                
                Create a step-by-step plan that breaks down the work into manageable chunks.
                Include specific file operations, code changes, and validation steps.
                Consider dependencies and potential risks.""",
                agent=self.planner_agent,
                expected_output="A detailed JSON plan with steps, file operations, and validation criteria"
            )
            
            # Execute planning
            crew = Crew(
                agents=[self.planner_agent],
                tasks=[plan_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            
            # Convert CrewOutput to serializable format
            plan_content = str(result.raw) if hasattr(result, 'raw') else str(result)
            
            # Save plan to run directory
            plan_file = run_dir / "plan.json"
            with open(plan_file, 'w') as f:
                json.dump({
                    "run_id": run_id,
                    "task_id": task_id,
                    "created_at": datetime.now().isoformat(),
                    "plan": plan_content,
                    "raw_plan_data": plan_data
                }, f, indent=2)
            
            # Update task with plan
            task_data = task.model_dump()
            task_data["plan"] = {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "plan": plan_content
            }
            
            self.task_manager.update_task(task_id, task_data)
            
            self.logger.info(f"Created plan for task {task_id}, run {run_id}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "plan": plan_content
            }
            
        except Exception as e:
            self.logger.error(f"Error creating plan for task {task_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def apply_plan(self, task_id: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a plan using the crew of agents."""
        try:
            # Load the task
            task = self.task_manager.load_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Get run ID
            if not run_id:
                if hasattr(task, 'plan') and task.plan:
                    run_id = task.plan.get('run_id')
                else:
                    raise ValueError("No run_id provided and no plan found in task")
            
            # Load plan
            run_dir = self.runs_dir / run_id
            plan_file = run_dir / "plan.json"
            
            if not plan_file.exists():
                raise ValueError(f"Plan file not found for run {run_id}")
            
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
            
            # Create run status
            run_status = RunStatus(
                run_id=run_id,
                task_id=task_id,
                status="running",
                started_at=datetime.now(),
                logs=[],
                artefacts=[]
            )
            
            # Save initial run status
            self._save_run_status(run_status)
            
            # Create execution tasks
            implement_task = Task(
                description=f"""Execute the implementation plan for task: {task.title}
                
                Plan: {plan_data.get('plan', '')}
                
                Use the Editor Tool to make the necessary file changes according to the plan.
                Be precise and follow the plan exactly.""",
                agent=self.implementer_agent,
                expected_output="Confirmation of successful file operations and changes made"
            )
            
            review_task = Task(
                description=f"""Review the changes made for task: {task.title}
                
                Verify that all changes are correct, follow coding standards, and meet 
                the task requirements. Check for any issues or improvements needed.""",
                agent=self.reviewer_agent,
                expected_output="Review report with approval or specific issues found"
            )
            
            commit_task = Task(
                description=f"""Commit the changes for task: {task.title}
                
                Stage all changes and create a proper commit with a meaningful message.
                Update task provenance with commit information.""",
                agent=self.committer_agent,
                expected_output="Confirmation of successful commit with commit SHA"
            )
            
            # Execute the crew workflow
            crew = Crew(
                agents=[self.implementer_agent, self.reviewer_agent, self.committer_agent],
                tasks=[implement_task, review_task, commit_task],
                process=Process.sequential,
                verbose=True
            )
            
            # Execute the crew
            result = crew.kickoff()
            
            # Update run status
            run_status.status = "completed"
            run_status.completed_at = datetime.now()
            run_status.logs.append(f"Crew execution completed: {result}")
            
            self._save_run_status(run_status)
            
            # Update task progress
            task_data = task.model_dump()
            task_data["status"] = "in-progress"
            task_data["progress_percent"] = 75  # After implementation
            task_data["changelog"].append({
                "timestamp": datetime.now().isoformat(),
                "text": f"Crew execution completed for run {run_id}"
            })
            
            self.task_manager.update_task(task_id, task_data)
            
            self.logger.info(f"Successfully executed plan for task {task_id}, run {run_id}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"Error executing plan for task {task_id}: {e}")
            
            # Update run status with error
            if 'run_status' in locals():
                run_status.status = "failed"
                run_status.completed_at = datetime.now()
                run_status.error = str(e)
                self._save_run_status(run_status)
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of a crew run."""
        try:
            run_file = self.runs_dir / run_id / "status.json"
            
            if not run_file.exists():
                return {
                    "status": "error",
                    "error": f"Run {run_id} not found"
                }
            
            with open(run_file, 'r') as f:
                status_data = json.load(f)
            
            return {
                "status": "success",
                "run_data": status_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting run status for {run_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def upload_artefacts(self, run_id: str, files: Dict[str, str]) -> Dict[str, Any]:
        """Upload artefacts to a run directory."""
        try:
            run_dir = self.runs_dir / run_id
            artefacts_dir = run_dir / "artefacts"
            artefacts_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            
            for filename, content in files.items():
                file_path = artefacts_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                uploaded_files.append(str(file_path.relative_to(self.repo_path)))
            
            # Update run status with artefacts
            run_file = run_dir / "status.json"
            if run_file.exists():
                with open(run_file, 'r') as f:
                    status_data = json.load(f)
                
                if 'artefacts' not in status_data:
                    status_data['artefacts'] = []
                
                status_data['artefacts'].extend(uploaded_files)
                
                with open(run_file, 'w') as f:
                    json.dump(status_data, f, indent=2)
            
            self.logger.info(f"Uploaded {len(uploaded_files)} artefacts to run {run_id}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "uploaded_files": uploaded_files
            }
            
        except Exception as e:
            self.logger.error(f"Error uploading artefacts for run {run_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _save_run_status(self, run_status: RunStatus):
        """Save run status to file."""
        run_dir = self.runs_dir / run_status.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        status_file = run_dir / "status.json"
        status_data = {
            "run_id": run_status.run_id,
            "task_id": run_status.task_id,
            "status": run_status.status,
            "started_at": run_status.started_at.isoformat() if run_status.started_at else None,
            "completed_at": run_status.completed_at.isoformat() if run_status.completed_at else None,
            "error": run_status.error,
            "logs": run_status.logs or [],
            "artefacts": run_status.artefacts or []
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)


class EditorToolWrapper(BaseTool):
    """Wrapper for Editor Tool to be used by CrewAI agents."""
    
    name: str = "EditorTool"
    description: str = "Execute file operations through the Editor Tool. Valid operations: GET, INSERT, UPDATE, DELETE. For creating files, use INSERT with full content. Use JSON format: {\"operation\": \"INSERT\", \"path\": \"file.txt\", \"payload\": {\"content\": \"hello world\"}}"
    
    class EditorToolArgs(BaseModel):
        operation: str
        path: str
        selector: Optional[Dict] = None
        payload: Optional[Dict] = None
        intent: str = ""
        dry_run: bool = False
    
    args_schema = EditorToolArgs
    editor_tool: EditorTool
    
    def __init__(self, editor_tool: EditorTool):
        super().__init__(editor_tool=editor_tool)
    
    def _run(self, operation: str, path: str, selector: Dict = None, 
             payload: Dict = None, intent: str = "", dry_run: bool = False) -> str:
        """Execute a file operation through the Editor Tool."""
        try:
            # Map common operation names to valid enum values
            operation_mapping = {
                "CREATE": "INSERT",
                "create": "INSERT", 
                "WRITE": "INSERT",
                "write": "INSERT",
                "READ": "GET",
                "read": "GET",
                "MODIFY": "UPDATE",
                "modify": "UPDATE",
                "REMOVE": "DELETE",
                "remove": "DELETE"
            }
            
            # Use mapping if available, otherwise use the original operation
            mapped_operation = operation_mapping.get(operation, operation)
            
            # Convert operation string to enum
            operation_type = OperationType(mapped_operation)
            
            # Create file operation
            file_op = FileOperation(
                operation=operation_type,
                path=path,
                selector=selector,
                payload=payload,
                intent=intent,
                dry_run=dry_run,
                author="agent:implementer",
                correlation_id=str(uuid.uuid4())
            )
            
            # Execute operation
            result = self.editor_tool.execute_operation(file_op)
            
            if result.ok:
                return f"Successfully executed {operation} on {path}: {result.diff}"
            else:
                return f"Failed to execute {operation} on {path}: {result.error}"
                
        except Exception as e:
            return f"Error executing {operation} on {path}: {str(e)}"


class GitToolWrapper(BaseTool):
    """Wrapper for Git Tool to be used by CrewAI agents."""
    
    name: str = "GitTool"
    description: str = "Execute Git operations through the Git Tool. Use JSON format: {\"operation\": \"commit\", \"message\": \"commit message\"} or {\"operation\": \"add\"}"
    
    class GitToolArgs(BaseModel):
        operation: str
        message: Optional[str] = None
        remote: Optional[str] = "origin"
        branch: Optional[str] = None
    
    args_schema = GitToolArgs
    git_tool: GitTool
    
    def __init__(self, git_tool: GitTool):
        super().__init__(git_tool=git_tool)
    
    def _run(self, operation: str, message: str = None, remote: str = "origin", branch: str = None) -> str:
        """Execute a Git operation."""
        try:
            if operation == "add":
                result = self.git_tool.add_files()
            elif operation == "commit":
                commit_message = message or "AI agent commit"
                result = self.git_tool.commit(commit_message)
            elif operation == "push":
                result = self.git_tool.push(remote, branch)
            else:
                return f"Unknown Git operation: {operation}"
            
            if result.success:
                return f"Successfully executed Git {operation}: {result.data}"
            else:
                return f"Failed to execute Git {operation}: {result.error}"
                
        except Exception as e:
            return f"Error executing Git {operation}: {str(e)}"
