#!/usr/bin/env python3
import datetime
import json
import logging
import os
import sys
from modules import repo
from modules import platform_manager
import typer

app = typer.Typer()
repo_app = typer.Typer()
app.add_typer(repo_app, name="repo")

# Configure logging
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "manage.log")
os.makedirs(LOG_DIR, exist_ok=True)

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

@app.command()
def health():
    """Perform a health check."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = {"status": "success", "date": current_date}
    logger.info("Health check performed", extra={'json_data': response})
    print(json.dumps(response))

@repo_app.command("init")
def repo_init(
    origin: str = typer.Option(..., "--origin", help="Local filesystem path or Git URL."),
    agent_id: str = typer.Option(None, "--agent-id", help="Optional agent identifier."),
    branch: str = typer.Option(None, "--branch", help="Optional branch to checkout."),
    task_slug: str = typer.Option(None, "--task-slug", help="Optional task slug to create a new agent-specific branch."),
    no_shallow: bool = typer.Option(False, "--no-shallow", help="Disable shallow clone."),
):
    """Initialise a working copy of a repository."""
    try:
        metadata = repo.init(
            origin=origin,
            agent_id=agent_id,
            branch=branch,
            shallow=not no_shallow,
            task_slug=task_slug
        )
        print("Repository initialised successfully.")
        print(json.dumps(metadata, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

@repo_app.command("close")
def repo_close(
    path: str = typer.Option(..., "--path", help="Path to the repository to close."),
    message: str = typer.Option(..., "--message", help="Commit message."),
    agent_id: str = typer.Option(None, "--agent-id", help="Agent identifier."),
    task_id: str = typer.Option(None, "--task-id", help="Task identifier."),
    remote: str = typer.Option("origin", "--remote", help="The remote to push to."),
    allow_empty: bool = typer.Option(False, "--allow-empty", help="Allow an empty commit."),
    require_changes: bool = typer.Option(False, "--require-changes", help="Fail if there are no changes to commit."),
    signoff: bool = typer.Option(False, "--signoff", help="Add a Signed-off-by trailer to the commit message."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Bypass pre-commit and commit-msg hooks."),
    merge: bool = typer.Option(False, "--merge", help="Attempt to merge the agent's branch into the target branch after closing."),
    target_branch: str = typer.Option("main", "--target-branch", help="The branch to merge into if --merge is enabled."),
):
    """Finalise a clone's work, commit, and push."""
    try:
        repo.close(
            path=path,
            message=message,
            agent_id=agent_id,
            task_id=task_id,
            remote=remote,
            allow_empty=allow_empty,
            require_changes=require_changes,
            signoff=signoff,
            no_verify=no_verify,
            merge=merge,
            target_branch=target_branch
        )
        print("Repository closed successfully.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)



@app.command()
def manager(
    headless: bool = typer.Option(False, "--headless", help="Run in headless mode."),
    command: str = typer.Argument(None, help="The command to run in headless mode."),
):
    """Run the interactive platform manager."""
    if headless:
        if command == "init":
            repo_init()
        elif command == "close":
            repo_close()
        else:
            print(f"Error: Unknown command '{command}' for headless mode.", file=sys.stderr)
            sys.exit(1)
    else:
        platform_manager.main()

if __name__ == "__main__":
    app()
