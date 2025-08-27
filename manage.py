#!/usr/bin/env python3
import argparse
import datetime
import json
import logging
import os
import sys
from modules import repo

# Configure logging
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "manage.log")

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }
        if hasattr(record, 'json_data'):
            log_record.update(record.json_data)
        return json.dumps(log_record)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

def health():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = {
        "status": "success",
        "date": current_date
    }
    logger.info("Health check performed", extra={'json_data': response})
    print(json.dumps(response))

def repo_init(args):
    """Handler for the 'repo:init' subcommand."""
    try:
        metadata = repo.init(
            origin=args.origin,
            agent_id=args.agent_id,
            branch=args.branch,
            shallow=not args.no_shallow,
            task_slug=args.task_slug
        )
        print("Repository initialised successfully.")
        print(json.dumps(metadata, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Management script for the Cage project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Health command
    parser_health = subparsers.add_parser("health", help="Perform a health check.")
    parser_health.set_defaults(func=lambda args: health())

    # Repo command
    parser_repo = subparsers.add_parser("repo", help="Repository management commands.")
    repo_subparsers = parser_repo.add_subparsers(dest="subcommand", required=True)

    # Repo:init command
    parser_repo_init = repo_subparsers.add_parser("init", help="Initialise a working copy of a repository.")
    parser_repo_init.add_argument("--origin", required=True, help="Local filesystem path or Git URL.")
    parser_repo_init.add_argument("--agent-id", help="Optional agent identifier.")
    parser_repo_init.add_argument("--branch", help="Optional branch to checkout.")
    parser_repo_init.add_argument("--task-slug", help="Optional task slug to create a new agent-specific branch.")
    parser_repo_init.add_argument("--no-shallow", action="store_true", help="Disable shallow clone.")
    parser_repo_init.set_defaults(func=repo_init)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()