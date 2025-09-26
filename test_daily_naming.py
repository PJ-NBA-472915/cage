#!/usr/bin/env python3
"""
Test script for daily logging with [area]-[date].log naming format.
"""

import sys
import os
import time
from datetime import datetime, timedelta
sys.path.append('src')

from cage.utils.daily_logger import setup_daily_logger

def test_daily_naming():
    """Test the daily logging naming format."""
    
    print("Testing daily logging with [area]-[date].log format...")
    
    # Test API logger
    api_logger = setup_daily_logger("api")
    api_logger.info("Test API log entry for naming format", extra={"json_data": {"test": "naming_format"}})
    
    # Test CrewAI logger
    crewai_logger = setup_daily_logger("crewai")
    crewai_logger.info("Test CrewAI log entry for naming format", extra={"json_data": {"test": "naming_format"}})
    
    # Test MCP logger
    mcp_logger = setup_daily_logger("mcp")
    mcp_logger.info("Test MCP log entry for naming format", extra={"json_data": {"test": "naming_format"}})
    
    # Test Management logger
    manage_logger = setup_daily_logger("manage")
    manage_logger.info("Test Management log entry for naming format", extra={"json_data": {"test": "naming_format"}})
    
    print("✓ Daily logging test completed")
    print("\nCurrent log files:")
    
    # Check current log files
    components = ["api", "crewai", "mcp", "manage"]
    for component in components:
        log_dir = f"logs/{component}"
        if os.path.exists(log_dir):
            files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            print(f"  {component}/: {files}")
    
    print(f"\nExpected format: [area]-[date].log")
    print(f"Example: api-2025-09-26.log")

if __name__ == "__main__":
    test_daily_naming()
