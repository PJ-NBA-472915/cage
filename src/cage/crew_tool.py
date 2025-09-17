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
        
        # Initialize comprehensive logging
        self.logger = logging.getLogger(__name__)
        self._setup_crewai_logging()
        
        # Initialize CrewAI agents
        self._setup_agents()
    
    def _setup_crewai_logging(self):
        """Set up comprehensive logging for CrewAI operations."""
        # Create crewai-specific logger
        self.crewai_logger = logging.getLogger(f"{__name__}.crewai")
        
        # Create logs directory for crewai
        logs_dir = Path("logs") / "crewai"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up file handler for crewai logs
        crewai_log_file = logs_dir / "crewai.log"
        file_handler = logging.FileHandler(crewai_log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "component": "crewai", "message": "%(message)s", "file": "%(filename)s", "line": %(lineno)d}'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.crewai_logger.addHandler(file_handler)
        self.crewai_logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate logs
        self.crewai_logger.propagate = False
        
        self.logger.info(f"CrewAI logging initialized. Log file: {crewai_log_file}")
    
    def _log_agent_activity(self, agent_name: str, activity: str, details: Dict[str, Any] = None):
        """Log agent activity with structured details."""
        log_data = {
            "agent": agent_name,
            "activity": activity,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.crewai_logger.info(f"Agent Activity: {json.dumps(log_data)}")
    
    def _log_tool_usage(self, agent_name: str, tool_name: str, operation: str, result: str, success: bool):
        """Log tool usage with detailed information."""
        log_data = {
            "agent": agent_name,
            "tool": tool_name,
            "operation": operation,
            "success": success,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        self.crewai_logger.info(f"Tool Usage: {json.dumps(log_data)}")
    
    def _log_crew_execution(self, crew_name: str, task_name: str, status: str, details: Dict[str, Any] = None):
        """Log crew execution details."""
        log_data = {
            "crew": crew_name,
            "task": task_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.crewai_logger.info(f"Crew Execution: {json.dumps(log_data)}")
    
    def _setup_agents(self):
        """Set up CrewAI agents for different roles."""
        self.logger.info("Setting up CrewAI agents...")
        
        # Planner Agent - Creates detailed plans for task execution
        self.planner_agent = Agent(
            role="Planner",
            goal="Create detailed, actionable plans for task execution using Cage-native API endpoints",
            backstory="""You are an expert software architect and project planner. 
            You analyze tasks and create comprehensive, step-by-step plans that break down 
            complex work into manageable, executable steps. You consider dependencies, 
            risks, and best practices in your planning.
            
            CRITICAL: All plans MUST use Cage-native API endpoints only:
            - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
            - Use GET /files/sha for content validation
            - Use GET /diff for change validation
            - Use POST /git/revert for rollback operations
            - Use POST /runner/exec for optional execution checks
            - Use POST /git/open_pr for pull request creation
            - Use POST /tasks/update for task updates
            
            NEVER include terminal commands like 'touch', 'mkdir', 'echo', etc.
            Always include validation steps and rollback paths.
            Include branch names and task-linked commit messages.
            
            Output format must be EXACTLY this JSON structure (no markdown, no code blocks):
            {
              "taskName": "Task Title",
              "taskId": "task-id",
              "goal": "Clear goal description",
              "branch": "chore/task-name-YYYY-MM-DD",
              "steps": [
                {
                  "name": "Step description",
                  "request": {
                    "method": "POST",
                    "path": "/files/edit",
                    "body": {
                      "operation": "INSERT",
                      "path": "file.py",
                      "payload": {"content": "file content"},
                      "intent": "Create file",
                      "author": "planner",
                      "correlation_id": "task-id"
                    }
                  },
                  "validate": [
                    "GET /files/sha?path=file.py -> returns non-empty sha",
                    "GET /diff?branch=chore/task-name-YYYY-MM-DD -> shows added file"
                  ],
                  "onFailure": {
                    "action": "abort",
                    "rollback": {
                      "method": "POST",
                      "path": "/git/revert",
                      "body": {"branch": "chore/task-name-YYYY-MM-DD", "to": "HEAD~1"}
                    }
                  }
                }
              ]
            }
            
            CRITICAL: Return ONLY the JSON object, no markdown formatting, no code blocks, no additional text.
            """,
            verbose=True,
            allow_delegation=False,
            tools=[]
        )
        self._log_agent_activity("Planner", "Agent Created", {"role": "Planner", "tools": []})
        
        # Implementer Agent - Executes file operations and code changes
        self.implementer_agent = Agent(
            role="Implementer", 
            goal="Execute file operations and implement code changes using the Cage Editor Tool",
            backstory="""You are an expert software developer with deep knowledge of 
            code structure, best practices, and implementation patterns. You MUST use the 
            EditorTool for ALL file operations - creating, reading, updating, and deleting files.
            
            CRITICAL RULES:
            1. NEVER use terminal commands like 'touch', 'mkdir', 'echo', 'cat', etc.
            2. ALWAYS use the EditorTool for file operations
            3. If a file you need to modify does not exist, create it with INSERT (include full content)
            4. For creating new files, use INSERT operation with full content
            5. For directories, create files with paths like 'subdir/file.txt'
            6. Always provide meaningful intent descriptions
            7. Use proper file extensions (.py, .md, .txt, etc.)
            
            You carefully execute file operations, making precise changes while maintaining 
            code quality and following established patterns.""",
            verbose=True,
            allow_delegation=False,
            tools=[EditorToolWrapper(self.editor_tool)]
        )
        self._log_agent_activity("Implementer", "Agent Created", {"role": "Implementer", "tools": ["EditorToolWrapper"]})
        
        # Reviewer Agent - Reviews changes and enforces policies
        self.reviewer_agent = Agent(
            role="Reviewer",
            goal="Review changes for quality, compliance, and proper tool usage",
            backstory="""You are an expert code reviewer and quality assurance specialist. 
            You carefully review all changes for correctness, adherence to coding standards, 
            security best practices, and policy compliance. You also verify that the 
            Implementer used the EditorTool correctly for all file operations.
            
            CRITICAL RULES:
            1. Verify that EditorTool was used for all file operations
            2. Check that no terminal commands were used inappropriately
            3. Ensure file content is correct and complete
            4. Validate that file paths and extensions are appropriate
            5. Confirm that intent descriptions are meaningful
            
            You ensure that all changes meet the required quality standards before they are committed.""",
            verbose=True,
            allow_delegation=False,
            tools=[EditorToolWrapper(self.editor_tool)]
        )
        self._log_agent_activity("Reviewer", "Agent Created", {"role": "Reviewer", "tools": ["EditorToolWrapper"]})
        
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
        self._log_agent_activity("Committer", "Agent Created", {"role": "Committer", "tools": ["GitToolWrapper"]})
        
        self.logger.info("All CrewAI agents created successfully")
    
    def create_plan(self, task_id: str, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed plan for task execution."""
        self.logger.info(f"Starting plan creation for task {task_id}")
        self._log_agent_activity("Planner", "Plan Creation Started", {
            "task_id": task_id,
            "plan_data": plan_data
        })
        
        try:
            # Load the task
            self.logger.debug(f"Loading task {task_id}")
            task = self.task_manager.load_task(task_id)
            if not task:
                error_msg = f"Task {task_id} not found"
                self.logger.error(error_msg)
                self._log_agent_activity("Planner", "Plan Creation Failed", {
                    "task_id": task_id,
                    "error": error_msg
                })
                raise ValueError(error_msg)
            
            # Create run ID
            run_id = str(uuid.uuid4())
            self.logger.info(f"Created run ID: {run_id}")
            
            # Create run directory
            run_dir = self.runs_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created run directory: {run_dir}")
            
            # Create plan using planner agent
            self.logger.info("Creating plan task for planner agent")
            plan_task = Task(
                description=f"""Create a detailed execution plan for task: {task.title}
                
                Task Summary: {task.summary}
                Success Criteria: {[c.text for c in task.success_criteria]}
                Acceptance Checks: {[c.text for c in task.acceptance_checks]}
                
                Create a Cage-native execution plan that uses only API endpoints:
                - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
                - Use GET /files/sha for content validation
                - Use GET /diff for change validation
                - Use POST /git/revert for rollback operations
                - Use POST /runner/exec for optional execution checks
                - Use POST /git/open_pr for pull request creation
                - Use POST /tasks/update for task updates
                
                Include:
                1. Branch name following convention: chore/task-name-YYYY-MM-DD
                2. Task-linked commit messages with format: "type: description (links: task {task_id})"
                3. Validation steps for each operation
                4. Rollback paths for failure scenarios
                5. Idempotent operations that can be re-run safely
                
                Output must be valid JSON following the Cage-native plan schema.""",
                agent=self.planner_agent,
                expected_output="A detailed JSON plan with Cage-native API calls, validation steps, and rollback paths"
            )
            
            # Execute planning
            self.logger.info("Executing planning crew with planner agent")
            self._log_crew_execution("Planning Crew", task.title, "Started", {
                "run_id": run_id,
                "task_id": task_id,
                "agents": ["Planner"]
            })
            
            crew = Crew(
                agents=[self.planner_agent],
                tasks=[plan_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            self.logger.info("Planning crew execution completed")
            self._log_crew_execution("Planning Crew", task.title, "Completed", {
                "run_id": run_id,
                "result_type": type(result).__name__
            })
            
            # Convert CrewOutput to serializable format
            plan_content = str(result.raw) if hasattr(result, 'raw') else str(result)
            self.logger.debug(f"Plan content length: {len(plan_content)} characters")
            
            # Save plan to run directory
            plan_file = run_dir / "plan.json"
            plan_data_to_save = {
                "run_id": run_id,
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "plan": plan_content,
                "raw_plan_data": plan_data
            }
            
            with open(plan_file, 'w') as f:
                json.dump(plan_data_to_save, f, indent=2)
            
            self.logger.info(f"Plan saved to: {plan_file}")
            
            # Update task with plan
            task_data = task.model_dump()
            task_data["plan"] = {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "plan": plan_content
            }
            
            self.task_manager.update_task(task_id, task_data)
            self.logger.info(f"Task {task_id} updated with plan information")
            
            self._log_agent_activity("Planner", "Plan Creation Completed", {
                "task_id": task_id,
                "run_id": run_id,
                "plan_length": len(plan_content),
                "plan_file": str(plan_file)
            })
            
            self.logger.info(f"Successfully created plan for task {task_id}, run {run_id}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "plan": plan_content
            }
            
        except Exception as e:
            error_msg = f"Error creating plan for task {task_id}: {e}"
            self.logger.error(error_msg)
            self._log_agent_activity("Planner", "Plan Creation Failed", {
                "task_id": task_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return {
                "status": "error",
                "error": str(e)
            }
    
    def apply_plan(self, task_id: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a plan using the crew of agents."""
        self.logger.info(f"Starting plan application for task {task_id}, run {run_id}")
        self._log_agent_activity("Crew", "Plan Application Started", {
            "task_id": task_id,
            "run_id": run_id
        })
        
        try:
            # Load the task
            self.logger.debug(f"Loading task {task_id}")
            task = self.task_manager.load_task(task_id)
            if not task:
                error_msg = f"Task {task_id} not found"
                self.logger.error(error_msg)
                self._log_agent_activity("Crew", "Plan Application Failed", {
                    "task_id": task_id,
                    "error": error_msg
                })
                raise ValueError(error_msg)
            
            # Get run ID
            if not run_id:
                if hasattr(task, 'plan') and task.plan:
                    run_id = task.plan.get('run_id')
                    self.logger.info(f"Using run_id from task plan: {run_id}")
                else:
                    error_msg = "No run_id provided and no plan found in task"
                    self.logger.error(error_msg)
                    self._log_agent_activity("Crew", "Plan Application Failed", {
                        "task_id": task_id,
                        "error": error_msg
                    })
                    raise ValueError(error_msg)
            
            # Load plan
            run_dir = self.runs_dir / run_id
            plan_file = run_dir / "plan.json"
            
            if not plan_file.exists():
                error_msg = f"Plan file not found for run {run_id}"
                self.logger.error(error_msg)
                self._log_agent_activity("Crew", "Plan Application Failed", {
                    "task_id": task_id,
                    "run_id": run_id,
                    "error": error_msg
                })
                raise ValueError(error_msg)
            
            self.logger.info(f"Loading plan from: {plan_file}")
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
            self.logger.debug(f"Plan data loaded successfully, plan length: {len(plan_data.get('plan', ''))}")
            
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
            self.logger.info(f"Run status created and saved for run {run_id}")
            
            # Create execution tasks
            implement_task = Task(
                description=f"""Execute the implementation plan for task: {task.title}
                
                Plan: {plan_data.get('plan', '')}
                
                CRITICAL INSTRUCTIONS:
                1. Use ONLY the EditorTool for all file operations
                2. Do NOT use terminal commands like 'touch', 'mkdir', 'echo', etc.
                3. For creating files, use INSERT operation with full content
                4. For reading files, use GET operation
                5. For updating files, use UPDATE operation
                6. For deleting files, use DELETE operation
                7. Always provide meaningful intent descriptions
                8. Use proper file extensions (.py, .md, .txt, etc.)
                
                Be precise and follow the plan exactly using the EditorTool.""",
                agent=self.implementer_agent,
                expected_output="Confirmation of successful file operations using EditorTool and changes made"
            )
            
            review_task = Task(
                description=f"""Review the changes made for task: {task.title}
                
                CRITICAL REVIEW CHECKLIST:
                1. Verify that EditorTool was used for ALL file operations
                2. Check that no terminal commands were used inappropriately
                3. Ensure file content is correct and complete
                4. Validate that file paths and extensions are appropriate
                5. Confirm that intent descriptions are meaningful
                6. Verify that all changes follow coding standards
                7. Check that task requirements are met
                
                Use the EditorTool to read and verify the created/modified files.""",
                agent=self.reviewer_agent,
                expected_output="Review report confirming EditorTool usage and file quality, with approval or specific issues found"
            )
            
            commit_task = Task(
                description=f"""Commit the changes for task: {task.title}
                
                Stage all changes and create a proper commit with a meaningful message.
                Check the working tree status first; if there are no changes, respond with a
                summary indicating nothing needed to be committed instead of forcing a commit.
                Update task provenance with commit information.""",
                agent=self.committer_agent,
                expected_output="Confirmation of successful commit with commit SHA"
            )
            
            # Execute the crew workflow
            self.logger.info("Creating execution crew with Implementer, Reviewer, and Committer agents")
            self._log_crew_execution("Execution Crew", task.title, "Started", {
                "run_id": run_id,
                "task_id": task_id,
                "agents": ["Implementer", "Reviewer", "Committer"],
                "tasks": ["implement_task", "review_task", "commit_task"]
            })
            
            crew = Crew(
                agents=[self.implementer_agent, self.reviewer_agent, self.committer_agent],
                tasks=[implement_task, review_task, commit_task],
                process=Process.sequential,
                verbose=True
            )
            
            # Execute the crew
            self.logger.info("Starting crew execution...")
            result = crew.kickoff()
            self.logger.info("Crew execution completed")
            self._log_crew_execution("Execution Crew", task.title, "Completed", {
                "run_id": run_id,
                "result_type": type(result).__name__,
                "result_length": len(str(result)) if result else 0
            })
            
            # Update run status
            run_status.status = "completed"
            run_status.completed_at = datetime.now()
            run_status.logs.append(f"Crew execution completed: {result}")
            
            self._save_run_status(run_status)
            self.logger.info(f"Run status updated to completed for run {run_id}")
            
            # Update task progress
            task_data = task.model_dump()
            task_data["status"] = "in-progress"
            task_data["progress_percent"] = 75  # After implementation
            task_data["changelog"].append({
                "timestamp": datetime.now().isoformat(),
                "text": f"Crew execution completed for run {run_id}"
            })
            
            self.task_manager.update_task(task_id, task_data)
            self.logger.info(f"Task {task_id} updated with execution results")
            
            self._log_agent_activity("Crew", "Plan Application Completed", {
                "task_id": task_id,
                "run_id": run_id,
                "status": "success",
                "result_type": type(result).__name__
            })
            
            self.logger.info(f"Successfully executed plan for task {task_id}, run {run_id}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "result": result
            }
            
        except Exception as e:
            error_msg = f"Error executing plan for task {task_id}: {e}"
            self.logger.error(error_msg)
            
            self._log_agent_activity("Crew", "Plan Application Failed", {
                "task_id": task_id,
                "run_id": run_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            
            # Update run status with error
            if 'run_status' in locals():
                run_status.status = "failed"
                run_status.completed_at = datetime.now()
                run_status.error = str(e)
                self._save_run_status(run_status)
                self.logger.info(f"Run status updated to failed for run {run_id}")
            
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
    description: str = """Execute file operations through the Cage Editor Tool. 
    
    IMPORTANT: This is the ONLY way to create, read, update, or delete files in this system.
    Do NOT use terminal commands like 'touch', 'mkdir', 'echo', etc. Use this tool instead.
    
    Operations:
    - INSERT: Create new files or insert content into existing files
    - GET: Read file content
    - UPDATE: Modify existing file content
    - DELETE: Remove files
    
    For creating new files, use INSERT with the full file content in the payload.
    
    Example for creating a Python file:
    {
        "operation": "INSERT",
        "path": "hello.py", 
        "payload": {"content": "#!/usr/bin/env python3\\nprint('Hello, World!')"},
        "intent": "Create Hello World Python script"
    }
    
    Example for creating a directory structure:
    {
        "operation": "INSERT",
        "path": "subdir/file.txt",
        "payload": {"content": "File content here"},
        "intent": "Create file in subdirectory"
    }
    """
    
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
        # Get the crew tool logger for detailed logging
        crew_tool_logger = logging.getLogger(f"{__name__}.crewai")
        
        crew_tool_logger.info(f"EditorToolWrapper called: operation={operation}, path={path}, intent={intent}")
        
        try:
            # Map common operation names to valid enum values
            operation_mapping = {
                "CREATE": "INSERT",
                "create": "INSERT", 
                "WRITE": "INSERT",
                "write": "INSERT",
                "MAKE": "INSERT",
                "make": "INSERT",
                "NEW": "INSERT",
                "new": "INSERT",
                "READ": "GET",
                "read": "GET",
                "VIEW": "GET",
                "view": "GET",
                "MODIFY": "UPDATE",
                "modify": "UPDATE",
                "EDIT": "UPDATE",
                "edit": "UPDATE",
                "CHANGE": "UPDATE",
                "change": "UPDATE",
                "REMOVE": "DELETE",
                "remove": "DELETE",
                "DELETE": "DELETE",
                "delete": "DELETE"
            }
            
            # Use mapping if available, otherwise use the original operation
            mapped_operation = operation_mapping.get(operation, operation)
            crew_tool_logger.debug(f"Operation mapping: {operation} -> {mapped_operation}")
            
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
            
            crew_tool_logger.info(f"Executing file operation: {operation_type.value} on {path}")
            
            # Execute operation
            result = self.editor_tool.execute_operation(file_op)

            # If update failed because the file is missing, retry as insert to create it.
            if (
                not result.ok
                and operation_type == OperationType.UPDATE
                and result.error
                and "File not found" in result.error
            ):
                crew_tool_logger.info(
                    f"Update failed due to missing file {path}; retrying as INSERT"
                )
                file_op.operation = OperationType.INSERT
                result = self.editor_tool.execute_operation(file_op)

            if result.ok:
                executed_operation = file_op.operation.value if file_op else operation_type.value
                success_msg = (
                    f"✅ Successfully executed {executed_operation} on {path}\nDiff: {result.diff}"
                )
                crew_tool_logger.info(
                    f"File operation successful: {executed_operation} on {path}"
                )
                return success_msg
            else:
                error_msg = f"❌ Failed to execute {operation} on {path}: {result.error}"
                crew_tool_logger.error(f"File operation failed: {operation} on {path} - {result.error}")
                return error_msg
                
        except Exception as e:
            error_msg = f"❌ Error executing {operation} on {path}: {str(e)}"
            crew_tool_logger.error(f"File operation exception: {operation} on {path} - {str(e)}")
            return error_msg


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
        # Get the crew tool logger for detailed logging
        crew_tool_logger = logging.getLogger(f"{__name__}.crewai")
        
        crew_tool_logger.info(f"GitToolWrapper called: operation={operation}, message={message}, remote={remote}, branch={branch}")
        
        try:
            if operation == "add":
                crew_tool_logger.info("Executing Git add operation")
                result = self.git_tool.add_files()
            elif operation == "commit":
                commit_message = message or "AI agent commit"
                status_check = self.git_tool.get_status()
                if status_check.success and status_check.data.get("is_clean", False):
                    crew_tool_logger.info("Working tree clean - skipping commit request")
                    return "No changes detected. Skipping git commit."

                crew_tool_logger.info(f"Executing Git commit operation with message: {commit_message}")
                result = self.git_tool.commit(commit_message)
            elif operation == "push":
                crew_tool_logger.info(f"Executing Git push operation to {remote}/{branch}")
                result = self.git_tool.push(remote, branch)
            elif operation == "status":
                crew_tool_logger.info("Retrieving Git status")
                result = self.git_tool.get_status()
                if result.success:
                    status_data = result.data
                    return json.dumps({
                        "current_branch": status_data.get("current_branch"),
                        "staged_files": status_data.get("staged_files", []),
                        "unstaged_files": status_data.get("unstaged_files", []),
                        "untracked_files": status_data.get("untracked_files", []),
                        "is_clean": status_data.get("is_clean", False)
                    })
            else:
                error_msg = f"Unknown Git operation: {operation}"
                crew_tool_logger.error(error_msg)
                return error_msg

            if result.success:
                success_msg = f"Successfully executed Git {operation}: {result.data}"
                crew_tool_logger.info(f"Git operation successful: {operation}")
                return success_msg
            else:
                error_msg = f"Failed to execute Git {operation}: {result.error}"
                crew_tool_logger.error(f"Git operation failed: {operation} - {result.error}")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error executing Git {operation}: {str(e)}"
            crew_tool_logger.error(f"Git operation exception: {operation} - {str(e)}")
            return error_msg
