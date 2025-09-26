#!/usr/bin/env python3
"""
Test script to manually trigger log rotation and verify [area]-[date].log format.
"""

import sys
import os
import time
from datetime import datetime
sys.path.append('src')

from cage.utils.daily_logger import DailyLogHandler
from pathlib import Path

def test_manual_rotation():
    """Test manual log rotation to verify naming format."""
    
    print("Testing manual log rotation with [area]-[date].log format...")
    
    # Create a test handler
    handler = DailyLogHandler("logs", "test", level=20)  # INFO level
    
    # Log some test messages
    handler.emit(type('LogRecord', (), {
        'getMessage': lambda: "Test message 1",
        'levelname': 'INFO',
        'filename': 'test.py',
        'lineno': 1,
        'created': time.time(),
        'msecs': 0,
        'json_data': {'test': 'rotation'}
    })())
    
    # Force rotation by calling doRollover
    print("Triggering manual rotation...")
    handler.doRollover()
    
    # Log another message to the new file
    handler.emit(type('LogRecord', (), {
        'getMessage': lambda: "Test message 2 after rotation",
        'levelname': 'INFO',
        'filename': 'test.py',
        'lineno': 2,
        'created': time.time(),
        'msecs': 0,
        'json_data': {'test': 'rotation_after'}
    })())
    
    # Check the files created
    test_dir = Path("logs/test")
    if test_dir.exists():
        files = list(test_dir.glob("*.log"))
        print(f"\nFiles created in logs/test/:")
        for file in files:
            print(f"  - {file.name}")
    
    print(f"\nExpected format: test-{datetime.now().strftime('%Y-%m-%d')}.log")
    
    # Clean up
    handler.close()

if __name__ == "__main__":
    test_manual_rotation()
