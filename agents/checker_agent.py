"""
Checker Agent for Progress Monitoring

This agent is responsible for monitoring task progress and can terminate
stalled tasks. It runs on a schedule to ensure continuous monitoring.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from loguru import logger


class ProgressMonitoringTool:
    """Tool for monitoring task progress and detecting stalls."""
    
    def __init__(self):
        self.name = "progress_monitor"
        self.description = "Monitor task progress and detect stalled tasks"
        self.active_tasks = {}  # Track active tasks and their progress
    
    def __call__(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Monitor task progress or perform monitoring actions.
        
        Args:
            action: Action to perform (start_monitoring, check_progress, stop_monitoring)
            
        Returns:
            Monitoring results
        """
        try:
            if action == "start_monitoring":
                return self._start_monitoring(**kwargs)
            elif action == "check_progress":
                return self._check_progress(**kwargs)
            elif action == "stop_monitoring":
                return self._stop_monitoring(**kwargs)
            elif action == "get_all_progress":
                return self._get_all_progress()
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            error_msg = f"Exception during progress monitoring: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _start_monitoring(self, task_id: str, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Start monitoring a new task."""
        if task_id in self.active_tasks:
            return {
                "success": False,
                "error": f"Task {task_id} is already being monitored"
            }
        
        # Initialize task monitoring
        self.active_tasks[task_id] = {
            "task_info": task_info,
            "start_time": datetime.now(),
            "last_activity": datetime.now(),
            "progress_updates": [],
            "status": "active",
            "stall_detected": False
        }
        
        logger.info(f"Started monitoring task: {task_id}")
        return {
            "success": True,
            "message": f"Started monitoring task {task_id}",
            "task_id": task_id
        }
    
    def _check_progress(self, task_id: str) -> Dict[str, Any]:
        """Check progress of a specific task."""
        if task_id not in self.active_tasks:
            return {
                "success": False,
                "error": f"Task {task_id} is not being monitored"
            }
        
        task = self.active_tasks[task_id]
        current_time = datetime.now()
        
        # Check for stalls (no activity for more than 10 minutes)
        time_since_last_activity = current_time - task["last_activity"]
        stall_threshold = timedelta(minutes=10)
        
        if time_since_last_activity > stall_threshold and not task["stall_detected"]:
            task["stall_detected"] = True
            task["status"] = "stalled"
            logger.warning(f"Task {task_id} appears to be stalled")
        
        # Calculate progress metrics
        total_time = current_time - task["start_time"]
        progress_metrics = {
            "task_id": task_id,
            "status": task["status"],
            "total_time": str(total_time),
            "time_since_last_activity": str(time_since_last_activity),
            "stall_detected": task["stall_detected"],
            "progress_updates_count": len(task["progress_updates"]),
            "last_activity": task["last_activity"].isoformat()
        }
        
        return {
            "success": True,
            "progress": progress_metrics
        }
    
    def _stop_monitoring(self, task_id: str) -> Dict[str, Any]:
        """Stop monitoring a task."""
        if task_id not in self.active_tasks:
            return {
                "success": False,
                "error": f"Task {task_id} is not being monitored"
            }
        
        task = self.active_tasks.pop(task_id)
        logger.info(f"Stopped monitoring task: {task_id}")
        
        return {
            "success": True,
            "message": f"Stopped monitoring task {task_id}",
            "final_status": task["status"]
        }
    
    def _get_all_progress(self) -> Dict[str, Any]:
        """Get progress for all monitored tasks."""
        all_progress = {}
        
        for task_id, task in self.active_tasks.items():
            progress = self._check_progress(task_id)
            if progress["success"]:
                all_progress[task_id] = progress["progress"]
        
        return {
            "success": True,
            "monitored_tasks_count": len(self.active_tasks),
            "all_progress": all_progress
        }
    
    def update_progress(self, task_id: str, progress_info: Dict[str, Any]):
        """Update progress for a monitored task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task["last_activity"] = datetime.now()
            task["progress_updates"].append({
                "timestamp": datetime.now().isoformat(),
                "info": progress_info
            })
            
            # Keep only last 10 progress updates
            if len(task["progress_updates"]) > 10:
                task["progress_updates"] = task["progress_updates"][-10:]
            
            logger.debug(f"Updated progress for task {task_id}: {progress_info}")


class TaskTerminationTool:
    """Tool for terminating stalled or problematic tasks."""
    
    def __init__(self):
        self.name = "task_terminator"
        self.description = "Terminate stalled or problematic tasks"
    
    def __call__(self, task_id: str, reason: str) -> Dict[str, Any]:
        """
        Terminate a task.
        
        Args:
            task_id: ID of the task to terminate
            reason: Reason for termination
            
        Returns:
            Termination results
        """
        try:
            logger.warning(f"Terminating task {task_id} for reason: {reason}")
            
            # In a real implementation, this would communicate with the task manager
            # to actually stop the task execution
            termination_result = {
                "success": True,
                "task_id": task_id,
                "termination_reason": reason,
                "termination_timestamp": datetime.now().isoformat(),
                "action_taken": "Task termination requested"
            }
            
            logger.info(f"Task {task_id} termination completed: {reason}")
            return termination_result
            
        except Exception as e:
            error_msg = f"Exception during task termination: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "task_id": task_id
            }


class CheckerAgent(BaseAgent):
    """Agent responsible for monitoring task progress and terminating stalled tasks."""
    
    def __init__(self, check_interval_minutes: int = 10):
        super().__init__(
            name="ProgressChecker",
            role="Progress Monitoring Specialist",
            goal="Monitor task progress and terminate stalled tasks to maintain system efficiency",
            backstory="""You are an expert progress monitor with keen attention to detail. 
            You continuously watch over active tasks, detect stalls, and take action to 
            maintain system productivity."""
        )
        
        # Add monitoring and termination tools
        self.progress_tool = ProgressMonitoringTool()
        self.termination_tool = TaskTerminationTool()
        self.add_tool(self.progress_tool)
        self.add_tool(self.termination_tool)
        
        # Monitoring configuration
        self.check_interval_minutes = check_interval_minutes
        self.monitoring_active = False
        self.monitoring_thread = None
        
        logger.info(f"Checker Agent initialized with {check_interval_minutes}-minute monitoring interval")
    
    def start_monitoring(self) -> Dict[str, Any]:
        """Start the continuous monitoring process."""
        if self.monitoring_active:
            return {
                "success": False,
                "error": "Monitoring is already active"
            }
        
        try:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Started continuous monitoring process")
            return {
                "success": True,
                "message": "Continuous monitoring started",
                "check_interval_minutes": self.check_interval_minutes
            }
            
        except Exception as e:
            self.monitoring_active = False
            error_msg = f"Failed to start monitoring: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop the continuous monitoring process."""
        if not self.monitoring_active:
            return {
                "success": False,
                "error": "Monitoring is not active"
            }
        
        try:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            
            logger.info("Stopped continuous monitoring process")
            return {
                "success": True,
                "message": "Continuous monitoring stopped"
            }
            
        except Exception as e:
            error_msg = f"Failed to stop monitoring: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs continuously."""
        logger.info("Monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Check all monitored tasks
                progress_result = self.progress_tool("get_all_progress")
                
                if progress_result["success"]:
                    for task_id, progress in progress_result["all_progress"].items():
                        if progress.get("stall_detected", False):
                            logger.warning(f"Stall detected in task {task_id}, initiating termination")
                            
                            # Terminate stalled task
                            termination_result = self.termination_tool(
                                task_id, 
                                "Task stalled - no activity detected for 10+ minutes"
                            )
                            
                            if termination_result["success"]:
                                logger.info(f"Successfully terminated stalled task {task_id}")
                            else:
                                logger.error(f"Failed to terminate stalled task {task_id}")
                
                # Wait for next check interval
                time.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Monitoring loop stopped")
    
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a monitoring task.
        
        Args:
            task_input: Task definition and parameters
            
        Returns:
            Task execution results
        """
        try:
            logger.info(f"Checker Agent executing task: {task_input.get('action', 'Unknown')}")
            
            action = task_input.get('action', '')
            
            if action == 'start_monitoring':
                return self.start_monitoring()
            elif action == 'stop_monitoring':
                return self.stop_monitoring()
            elif action == 'check_progress':
                task_id = task_input.get('task_id', '')
                if task_id:
                    return self.progress_tool("check_progress", task_id=task_id)
                else:
                    return self.progress_tool("get_all_progress")
            elif action == 'terminate_task':
                task_id = task_input.get('task_id', '')
                reason = task_input.get('reason', 'Manual termination')
                if task_id:
                    return self.termination_tool(task_id, reason)
                else:
                    return {
                        "success": False,
                        "error": "No task_id provided for termination"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            error_msg = f"Exception during checker task execution: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "task_input": task_input
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the checker agent."""
        base_status = super().get_status()
        base_status.update({
            "monitoring_active": self.monitoring_active,
            "check_interval_minutes": self.check_interval_minutes,
            "progress_tool_available": hasattr(self, 'progress_tool'),
            "termination_tool_available": hasattr(self, 'termination_tool')
        })
        return base_status
