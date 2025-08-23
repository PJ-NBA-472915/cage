#!/usr/bin/env python3
"""
Agent Daemon for Agent-Net

This daemon implements the basic agent functionality as specified in the product specification:
- Communicates with the coordinator via Redis Streams
- Maintains heartbeat for health monitoring
- Processes tasks by executing CLI commands
- Reports results back to the coordinator
- Accepts repo path and CLI request arguments
- Uses Cursor CLI for file modifications
"""

import asyncio
import argparse
import json
import logging
import os
import signal
import sys
import time
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import redis.asyncio as redis
from loguru import logger

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AGENT_ID = os.getenv("AGENT_ID", f"agent-{uuid.uuid4().hex[:8]}")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")

class AgentDaemon:
    def __init__(self, repo_path: str, cli_request: str):
        self.repo_path = Path(repo_path)
        self.cli_request = cli_request
        self.redis_client = None
        self.running = False
        
        # Validate repo path
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        # Validate Cursor API key
        if not CURSOR_API_KEY:
            raise ValueError("CURSOR_API_KEY environment variable is required")
    
    async def start(self):
        """Start the agent daemon"""
        logger.info(f"Starting agent {AGENT_ID} for repo: {self.repo_path}")
        logger.info(f"CLI request: {self.cli_request}")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            # Initialize Redis connection
            await self._init_redis()
            
            # Start heartbeat
            asyncio.create_task(self._heartbeat_loop())
            
            # Process the CLI request
            await self._process_cli_request()
            
            # Keep running for heartbeat
            self.running = True
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Agent daemon failed: {e}")
            raise
        finally:
            await self._cleanup()
    
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
    
    async def _heartbeat_loop(self):
        """Send heartbeat to Redis"""
        while self.running:
            try:
                if self.redis_client:
                    heartbeat_data = {
                        "agent_id": AGENT_ID,
                        "timestamp": time.time(),
                        "repo_path": str(self.repo_path),
                        "status": "active"
                    }
                    await self.redis_client.xadd("agent_heartbeats", heartbeat_data)
                    logger.debug("Heartbeat sent")
            except Exception as e:
                logger.warning(f"Failed to send heartbeat: {e}")
            
            await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    async def _process_cli_request(self):
        """Process the CLI request using Cursor CLI"""
        logger.info(f"Processing CLI request: {self.cli_request}")
        
        try:
            # Change to repo directory
            os.chdir(self.repo_path)
            logger.info(f"Changed to directory: {os.getcwd()}")
            
            # Execute Cursor CLI command
            result = await self._execute_cursor_command(self.cli_request)
            
            if result["success"]:
                logger.info("CLI request processed successfully")
                logger.info(f"Output: {result['output']}")
                
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
                "cursor", "-a", CURSOR_API_KEY, "-p",
                request
            ]
            
            logger.info(f"Executing Cursor CLI command: {' '.join(cmd)}")
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.repo_path
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
                "repo_path": str(self.repo_path),
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
    parser.add_argument("repo_path", help="Path to the repository to work with")
    parser.add_argument("cli_request", help="CLI request to execute")
    
    args = parser.parse_args()
    
    try:
        daemon = AgentDaemon(args.repo_path, args.cli_request)
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
