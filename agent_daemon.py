#!/usr/bin/env python3
"""
Agent-Net Agent Daemon

A simple containerized agent that can:
- Accept repository path and CLI request arguments
- Execute Cursor CLI commands for code modifications
- Communicate with Redis for task coordination
- Run as a non-root user with proper signal handling
"""

import argparse
import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import redis.asyncio as redis
from loguru import logger

# Configuration
AGENT_ID = f"agent-{os.getpid():08x}"
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ORIGIN_BRANCH = os.getenv("ORIGIN_BRANCH", "main")
CURRENT_BRANCH = os.getenv("CURRENT_BRANCH", "agent-work")

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}")


class AgentDaemon:
    """Agent daemon for processing CLI requests and executing Cursor commands"""
    
    def __init__(self, cli_request: str):
        self.cli_request = cli_request
        self.origin_path = Path("/origin")
        self.workspace_path = Path("/app/workspace")
        self.redis_client = None
        self.running = False
        
        # Validate Cursor API key
        if not CURSOR_API_KEY:
            raise ValueError("CURSOR_API_KEY environment variable is required")
    
    async def start(self):
        """Start the agent daemon"""
        try:
            # Initialize Redis connection
            await self._init_redis()
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.running = True
            logger.info(f"Starting agent {AGENT_ID}")
            logger.info(f"CLI request: {self.cli_request}")
            
            # Set up workspace by cloning from origin
            await self._setup_workspace()
            
            # Process the CLI request
            await self._process_cli_request()
            
            # Keep running for potential future requests
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in agent daemon: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _setup_workspace(self):
        """Set up workspace by cloning from origin and creating a new branch"""
        try:
            logger.info("Setting up workspace...")
            
            # Ensure workspace directory exists
            self.workspace_path.mkdir(exist_ok=True)
            
            # Clone from origin to workspace
            if self.workspace_path.exists() and any(self.workspace_path.iterdir()):
                logger.info("Workspace already exists, cleaning up...")
                import shutil
                shutil.rmtree(self.workspace_path)
                self.workspace_path.mkdir()
            
            logger.info(f"Cloning from {self.origin_path} to {self.workspace_path}")
            
            # Clone the repository
            process = await asyncio.create_subprocess_exec(
                "git", "clone", str(self.origin_path), str(self.workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Failed to clone repository: {stderr.decode().strip()}")
            
            logger.info("Repository cloned successfully")
            
            # Checkout the origin branch and pull latest changes
            logger.info(f"Checking out origin branch: {ORIGIN_BRANCH}")
            process = await asyncio.create_subprocess_exec(
                "git", "checkout", ORIGIN_BRANCH,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"Failed to checkout origin branch {ORIGIN_BRANCH}: {stderr.decode().strip()}")
            else:
                logger.info(f"Checked out origin branch: {ORIGIN_BRANCH}")
                
                # Pull latest changes from origin
                logger.info("Pulling latest changes from origin")
                process = await asyncio.create_subprocess_exec(
                    "git", "pull", "origin", ORIGIN_BRANCH,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.workspace_path
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.warning(f"Failed to pull latest changes: {stderr.decode().strip()}")
                else:
                    logger.info("Pulled latest changes from origin")
            
            # Create and checkout the current branch for this agent's work
            logger.info(f"Creating and checking out current branch: {CURRENT_BRANCH}")
            process = await asyncio.create_subprocess_exec(
                "git", "checkout", "-b", CURRENT_BRANCH,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"Failed to create current branch {CURRENT_BRANCH}: {stderr.decode().strip()}")
            else:
                logger.info(f"Created and switched to current branch: {CURRENT_BRANCH}")
                
        except Exception as e:
            logger.error(f"Error setting up workspace: {e}")
            raise
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            logger.info("Continuing without Redis connection")
            self.redis_client = None
    
    async def _process_cli_request(self):
        """Process the CLI request using Cursor CLI"""
        try:
            logger.info(f"Processing CLI request: {self.cli_request}")
            
            # Change to the workspace directory
            os.chdir(self.workspace_path)
            logger.info(f"Changed to directory: {self.workspace_path}")
            
            # Execute the request using Cursor CLI
            result = await self._execute_cursor_command(self.cli_request)
            
            if result["success"]:
                logger.info(f"CLI request completed successfully: {result['output']}")
                
                # Report success to Redis if available
                if self.redis_client:
                    await self._report_result("success", result)
            else:
                logger.error(f"CLI request failed: {result['error']}")
                
                # Report failure to Redis if available
                if self.redis_client:
                    await self._report_result("failed", result)
                    
        except Exception as e:
            logger.error(f"Error processing CLI request: {e}")
            if self.redis_client:
                await self._report_result("error", {"error": str(e)})
    
    async def _execute_cursor_command(self, request: str) -> Dict[str, Any]:
        """Execute a command using Cursor CLI"""
        try:
            # Use Cursor CLI with -a for API key and -p for non-interactive mode
            cmd = [
                "cursor-agent", "-a", CURSOR_API_KEY, "-p",
                request
            ]
            
            logger.info(f"Executing Cursor CLI command: {' '.join(cmd)}")
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout.decode().strip(),
                    "stderr": stderr.decode().strip()
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode().strip(),
                    "stdout": stdout.decode().strip(),
                    "returncode": process.returncode
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _report_result(self, status: str, result: Dict[str, Any]):
        """Report result to Redis"""
        try:
            report_data = {
                "agent_id": AGENT_ID,
                "timestamp": time.time(),
                "workspace_path": str(self.workspace_path),
                "origin_path": str(self.origin_path),
                "origin_branch": ORIGIN_BRANCH,
                "current_branch": CURRENT_BRANCH,
                "status": status,
                "result": result
            }
            await self.redis_client.xadd("agent_results", report_data)
            logger.info(f"Result reported to Redis: {status}")
        except Exception as e:
            logger.warning(f"Failed to report result to Redis: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _cleanup(self):
        """Clean up resources"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Agent daemon shutdown complete")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Agent-Net Agent Daemon")
    parser.add_argument("cli_request", help="CLI request to execute")
    
    args = parser.parse_args()
    
    try:
        daemon = AgentDaemon(args.cli_request)
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
