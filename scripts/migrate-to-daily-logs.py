#!/usr/bin/env python3
"""
Migration script to move from single log files to daily log structure.

This script:
1. Moves existing single log files to their respective component directories
2. Renames them to follow the daily naming convention
3. Updates the directory structure to match the new format
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def migrate_logs():
    """Migrate existing log files to the new daily structure."""
    
    logs_dir = Path("logs")
    
    # Define the migration mapping
    migrations = [
        {
            "old_path": logs_dir / "api.log",
            "new_dir": logs_dir / "api",
            "new_name": "api.log"
        },
        {
            "old_path": logs_dir / "manage.log", 
            "new_dir": logs_dir / "manage",
            "new_name": "manage.log"
        },
        {
            "old_path": logs_dir / "mcp" / "mcp.log",
            "new_dir": logs_dir / "mcp",
            "new_name": "mcp.log"
        }
        # crewai is already in the correct structure
    ]
    
    print("Starting log migration to daily structure...")
    
    for migration in migrations:
        old_path = migration["old_path"]
        new_dir = migration["new_dir"]
        new_name = migration["new_name"]
        new_path = new_dir / new_name
        
        if old_path.exists():
            print(f"Migrating {old_path} -> {new_path}")
            
            # Create new directory if it doesn't exist
            new_dir.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(old_path), str(new_path))
            print(f"  ✓ Moved {old_path} to {new_path}")
        else:
            print(f"  - {old_path} does not exist, skipping")
    
    # Ensure all component directories exist
    components = ["api", "crewai", "manage", "mcp"]
    for component in components:
        component_dir = logs_dir / component
        component_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = component_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*.log\n")
            print(f"  ✓ Created {gitignore_path}")
    
    print("\nMigration completed!")
    print("\nNew structure:")
    for component in components:
        component_dir = logs_dir / component
        if component_dir.exists():
            files = list(component_dir.glob("*.log"))
            print(f"  {component}/: {len(files)} log files")
            for file in files:
                print(f"    - {file.name}")


if __name__ == "__main__":
    migrate_logs()
