"""
Daily logging utility for Cage application.

This module provides a daily logging handler that creates new log files
each day while maintaining the existing JSON format and structure.
"""

import os
import logging
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


class DailyJsonFormatter(logging.Formatter):
    """Custom JSON formatter for daily logs."""
    
    def __init__(self, component: str = None):
        super().__init__()
        self.component = component
    
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }
        
        # Add component if specified
        if self.component:
            log_record["component"] = self.component
            
        # Add any extra JSON data
        if hasattr(record, 'json_data'):
            log_record.update(record.json_data)
            
        return json.dumps(log_record)


class DailyLogHandler(TimedRotatingFileHandler):
    """Custom daily rotating file handler with JSON formatting."""
    
    def __init__(self, log_dir: str, component: str, level: int = logging.INFO):
        # Ensure log directory exists
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create log file path with component subdirectory
        component_dir = log_path / component
        component_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = component_dir / f"{component}.log"
        
        # Initialize TimedRotatingFileHandler for daily rotation
        super().__init__(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days of logs
            encoding='utf-8'
        )
        
        # Set up JSON formatter
        formatter = DailyJsonFormatter(component=component)
        self.setFormatter(formatter)
        self.setLevel(level)


def setup_daily_logger(component: str, log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a daily logger for a specific component.
    
    Args:
        component: Component name (e.g., 'api', 'crewai', 'mcp', 'manage')
        log_dir: Base log directory (default: 'logs')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"cage.{component}")
    logger.setLevel(level)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Add daily file handler
    file_handler = DailyLogHandler(log_dir, component, level)
    logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_daily_logger(component: str) -> logging.Logger:
    """
    Get an existing daily logger for a component.
    
    Args:
        component: Component name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"cage.{component}")


# Convenience functions for common components
def get_api_logger() -> logging.Logger:
    """Get the API daily logger."""
    return get_daily_logger("api")


def get_crewai_logger() -> logging.Logger:
    """Get the CrewAI daily logger."""
    return get_daily_logger("crewai")


def get_mcp_logger() -> logging.Logger:
    """Get the MCP daily logger."""
    return get_daily_logger("mcp")


def get_manage_logger() -> logging.Logger:
    """Get the management daily logger."""
    return get_daily_logger("manage")
