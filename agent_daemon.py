#!/usr/bin/env python3
"""
Agent Daemon for Agent-Net

This daemon implements the basic agent functionality as specified in the product specification:
- Communicates with the coordinator via Redis Streams
- Maintains heartbeat for health monitoring
- Processes tasks by executing CLI commands
- Reports results back to the coordinator
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
from typing import Dict, Any, Optional

import redis.asyncio as redis
from loguru import logger

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AGENT_ID = os.getenv("AGENT_ID", f"agent-{uuid.uuid4().hex[:8]}")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "60"))

# Redis Stream names
TASKS_STREAM = "tasks"
RESULTS_STREAM = "results"
SIGNALS_STREAM = "signals"

class AgentDaemon:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.current_task: Optional[Dict[str, Any]] = None
        self.consumer_group = "agents_group"
        
        # Setup logging
        logger.remove()
        logger.add(sys.stderr, level="INFO", format="[AGENT] {time} | {level} | {message}")
        
    async def connect_redis(self):
        """Connect to Redis and setup consumer groups"""
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL}")
            
            # Setup consumer groups
            await self._setup_consumer_groups()
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def _setup_consumer_groups(self):
        """Setup Redis consumer groups for task processing"""
        try:
            # Create consumer group for tasks if it doesn't exist
            try:
                await self.redis_client.xgroup_create(TASKS_STREAM, self.consumer_group, id="0", mkstream=True)
                logger.info(f"Created consumer group {self.consumer_group} for tasks stream")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"Consumer group {self.consumer_group} already exists")
                else:
                    raise
            
            # Create consumer group for signals if it doesn't exist
            try:
                await self.redis_client.xgroup_create(SIGNALS_STREAM, self.consumer_group, id="0", mkstream=True)
                logger.info(f"Created consumer group {self.consumer_group} for signals stream")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"Consumer group {self.consumer_group} already exists")
                else:
                    raise
                
        except Exception as e:
            logger.error(f"Failed to setup consumer groups: {e}")
            raise
    
    async def start_heartbeat(self):
        """Start heartbeat monitoring"""
        while self.running:
            try:
                if self.redis_client:
                    heartbeat_key = f"agent:{AGENT_ID}:heartbeat"
                    await self.redis_client.setex(heartbeat_key, 30, "alive")
                    logger.debug(f"Heartbeat sent: {heartbeat_key}")
                
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    async def process_tasks(self):
        """Process tasks from the Redis stream"""
        while self.running:
            try:
                if not self.redis_client:
                    await asyncio.sleep(1)
                    continue
                
                # Read tasks from stream
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    AGENT_ID,
                    {TASKS_STREAM: ">"},
                    count=1,
                    block=1000
                )
                
                if messages:
                    for stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            await self._process_task(message_id, fields)
                            
            except Exception as e:
                logger.error(f"Task processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, message_id: str, fields: Dict[str, Any]):
        """Process a single task"""
        try:
            task_id = fields.get("task_id", "unknown")
            description = fields.get("description", "No description")
            repo_url = fields.get("repo_url", "")
            
            logger.info(f"Processing task {task_id}: {description}")
            
            # Mark task as started
            await self._report_task_event("TaskStarted", task_id, {
                "agent_id": AGENT_ID,
                "message": "Task execution started"
            })
            
            # Execute the task
            result = await self._execute_task(task_id, description, repo_url, fields)
            
            # Report completion
            if result["success"]:
                await self._report_task_event("TaskSucceeded", task_id, {
                    "agent_id": AGENT_ID,
                    "result": result
                })
            else:
                await self._report_task_event("TaskFailed", task_id, {
                    "agent_id": AGENT_ID,
                    "error": result["error"]
                })
            
            # Acknowledge the message
            await self.redis_client.xack(TASKS_STREAM, self.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            # Report failure
            task_id = fields.get("task_id", "unknown")
            await self._report_task_event("TaskFailed", task_id, {
                "agent_id": AGENT_ID,
                "error": str(e)
            })
    
    async def _execute_task(self, task_id: str, description: str, repo_url: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task by running CLI commands"""
        try:
            logger.info(f"Executing task {task_id}")
            
            # For now, implement basic task execution
            # In a real implementation, this would:
            # 1. Clone the repository
            # 2. Parse the task description
            # 3. Execute appropriate CLI commands
            # 4. Run tests
            # 5. Commit and push changes
            
            # Simulate task execution
            await asyncio.sleep(2)
            
            # Example: Run a simple command
            if "test" in description.lower():
                # Simulate running tests
                logger.info("Running tests...")
                await asyncio.sleep(1)
                return {
                    "success": True,
                    "message": "Tests completed successfully",
                    "files_changed": [],
                    "tests_passed": True
                }
            else:
                # Simulate code changes
                logger.info("Making code changes...")
                await asyncio.sleep(1)
                return {
                    "success": True,
                    "message": "Code changes completed",
                    "files_changed": ["example.py"],
                    "tests_passed": True
                }
                
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _report_task_event(self, event_type: str, task_id: str, data: Dict[str, Any]):
        """Report a task event to the results stream"""
        try:
            if self.redis_client:
                event_data = {
                    "event_type": event_type,
                    "task_id": task_id,
                    "agent_id": AGENT_ID,
                    "timestamp": int(time.time()),
                    **data
                }
                
                await self.redis_client.xadd(
                    RESULTS_STREAM,
                    event_data
                )
                logger.info(f"Reported {event_type} for task {task_id}")
                
        except Exception as e:
            logger.error(f"Failed to report event {event_type}: {e}")
    
    async def monitor_signals(self):
        """Monitor for control signals from coordinator"""
        while self.running:
            try:
                if not self.redis_client:
                    await asyncio.sleep(1)
                    continue
                
                # Read signals from stream
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    AGENT_ID,
                    {SIGNALS_STREAM: ">"},
                    count=1,
                    block=1000
                )
                
                if messages:
                    for stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            await self._handle_signal(message_id, fields)
                            
            except Exception as e:
                logger.error(f"Signal monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_signal(self, message_id: str, fields: Dict[str, Any]):
        """Handle control signals from coordinator"""
        try:
            signal_type = fields.get("signal", "")
            logger.info(f"Received signal: {signal_type}")
            
            if signal_type == "pause":
                # Pause taking new tasks
                logger.info("Pausing task processing")
                # Implementation: set a flag to stop processing new tasks
                
            elif signal_type == "drain":
                # Stop taking new tasks and exit when current task is done
                logger.info("Draining - will exit after current task")
                self.running = False
                
            elif signal_type == "shutdown":
                # Immediate shutdown
                logger.info("Shutdown signal received")
                self.running = False
                
            # Acknowledge the signal
            await self.redis_client.xack(SIGNALS_STREAM, self.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"Signal handling failed: {e}")
    
    async def run(self):
        """Main run loop"""
        try:
            await self.connect_redis()
            self.running = True
            
            logger.info(f"Agent {AGENT_ID} started successfully")
            
            # Start background tasks
            heartbeat_task = asyncio.create_task(self.start_heartbeat())
            task_task = asyncio.create_task(self.process_tasks())
            signal_task = asyncio.create_task(self.monitor_signals())
            
            # Wait for all tasks
            await asyncio.gather(
                heartbeat_task,
                task_task,
                signal_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            raise
        finally:
            self.running = False
            if self.redis_client:
                await self.redis_client.close()
    
    def stop(self):
        """Stop the agent"""
        logger.info("Stopping agent...")
        self.running = False

async def main():
    """Main entry point"""
    agent = AgentDaemon()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        agent.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
