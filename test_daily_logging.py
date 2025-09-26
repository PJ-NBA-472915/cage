#!/usr/bin/env python3
"""
Test script for daily logging functionality.
"""

import sys
import os
sys.path.append('src')

from cage.utils.daily_logger import setup_daily_logger
import time

def test_daily_logging():
    """Test the daily logging functionality."""
    
    print("Testing daily logging functionality...")
    
    # Test API logger
    api_logger = setup_daily_logger("api")
    api_logger.info("Test API log entry", extra={"json_data": {"test": "daily_logging"}})
    
    # Test CrewAI logger
    crewai_logger = setup_daily_logger("crewai")
    crewai_logger.info("Test CrewAI log entry", extra={"json_data": {"test": "daily_logging"}})
    
    # Test MCP logger
    mcp_logger = setup_daily_logger("mcp")
    mcp_logger.info("Test MCP log entry", extra={"json_data": {"test": "daily_logging"}})
    
    # Test Management logger
    manage_logger = setup_daily_logger("manage")
    manage_logger.info("Test Management log entry", extra={"json_data": {"test": "daily_logging"}})
    
    print("✓ Daily logging test completed")
    print("\nCheck the following log files:")
    print("  - logs/api/api.log")
    print("  - logs/crewai/crewai.log") 
    print("  - logs/mcp/mcp.log")
    print("  - logs/manage/manage.log")

if __name__ == "__main__":
    test_daily_logging()
