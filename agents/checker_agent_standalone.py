#!/usr/bin/env python3
"""
Standalone Checker Agent for Supervisor Management

This script runs the checker agent independently and can be managed by supervisor.
It includes a main loop that runs on a 10-minute schedule to monitor progress
and check for stalled tasks.
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Optional

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.checker_agent import CheckerAgent
from agents.crew_manager import CrewManager
from loguru import logger

# Configure logging - use local logs directory for development, /app/logs for container
import os
log_dir = os.environ.get('LOG_DIR', 'logs')
log_path = os.path.join(log_dir, 'checker-agent.log')

logger.add(
    log_path,
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

class StandaloneCheckerAgent:
    """Standalone checker agent that can run independently."""
    
    def __init__(self):
        self.running = True
        self.checker_agent: Optional[CheckerAgent] = None
        self.crew_manager: Optional[CrewManager] = None
        self.check_interval = 600  # 10 minutes in seconds
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Standalone Checker Agent initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def initialize(self):
        """Initialize the checker agent and crew manager."""
        try:
            # Initialize the checker agent
            self.checker_agent = CheckerAgent()
            logger.info("Checker agent initialized successfully")
            
            # Initialize the crew manager
            self.crew_manager = CrewManager()
            logger.info("Crew manager initialized successfully")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def run_check(self):
        """Run a single check cycle."""
        try:
            if not self.checker_agent or not self.crew_manager:
                logger.error("Agent or crew manager not initialized")
                return False
            
            logger.info("Starting progress check cycle...")
            
            # Check for stalled tasks
            stalled_tasks = self.checker_agent.check_for_stalled_tasks()
            if stalled_tasks:
                logger.warning(f"Found {len(stalled_tasks)} stalled tasks")
                for task in stalled_tasks:
                    logger.info(f"Stalled task: {task}")
                    
                    # Attempt to terminate stalled tasks
                    if self.checker_agent.terminate_stalled_task(task):
                        logger.info(f"Successfully terminated stalled task: {task}")
                    else:
                        logger.error(f"Failed to terminate stalled task: {task}")
            else:
                logger.info("No stalled tasks found")
            
            # Monitor overall progress
            progress_status = self.checker_agent.monitor_progress()
            logger.info(f"Progress status: {progress_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during check cycle: {e}")
            return False
    
    def run(self):
        """Main run loop with 10-minute intervals."""
        logger.info("Starting standalone checker agent...")
        
        if not self.initialize():
            logger.error("Failed to initialize, exiting")
            return 1
        
        logger.info(f"Checker agent running with {self.check_interval}s intervals")
        
        last_check = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time for the next check cycle
                if current_time - last_check >= self.check_interval:
                    logger.info("Running scheduled check cycle...")
                    
                    if self.run_check():
                        last_check = current_time
                        logger.info("Check cycle completed successfully")
                    else:
                        logger.warning("Check cycle failed, will retry on next interval")
                    
                    # Log next scheduled check
                    next_check = time.strftime(
                        "%Y-%m-%d %H:%M:%S", 
                        time.localtime(current_time + self.check_interval)
                    )
                    logger.info(f"Next check scheduled for: {next_check}")
                
                # Sleep for a short interval to avoid busy waiting
                time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(30)  # Wait before retrying
        
        logger.info("Standalone checker agent shutting down")
        return 0

def main():
    """Main entry point for the standalone checker agent."""
    try:
        agent = StandaloneCheckerAgent()
        return agent.run()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
