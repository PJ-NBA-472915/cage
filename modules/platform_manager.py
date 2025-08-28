
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import questionary
import sys
import json
from modules import repo

app = typer.Typer()
console = Console()

def _interactive_init():
    """Interactive repository initialization."""
    origin = questionary.text("Enter the repository URL or local path:").ask()
    agent_id = questionary.text("Enter the agent ID (optional):").ask()
    branch = questionary.text("Enter the branch to checkout (optional):").ask()
    task_slug = questionary.text("Enter the task slug (optional):").ask()
    shallow = questionary.confirm("Perform a shallow clone?").ask()

    try:
        metadata = repo.init(
            origin=origin,
            agent_id=agent_id if agent_id else None,
            branch=branch if branch else None,
            task_slug=task_slug if task_slug else None,
            shallow=shallow
        )
        console.print("[bold green]Repository initialised successfully![/bold green]")
        console.print(metadata)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

def _interactive_close():
    """Interactive repository closing."""
    path = questionary.text("Enter the path to the repository (or leave blank to select from a list):").ask()

    if not path:
        open_repos = repo.get_open_repositories()
        if not open_repos:
            console.print("[yellow]No open repositories found.[/yellow]")
            return

        choices = [
            f"{r.get('origin', 'N/A')} (in {r.get('temp_dir', 'N/A')})"
            for r in open_repos
        ]
        selection = questionary.select(
            "Select a repository to close:",
            choices=choices
        ).ask()

        if not selection:
            console.print("No repository selected.")
            return
        
        # Extract the path from the selection string
        path = selection.split('(in ')[1][:-1]

    message = questionary.text("Enter the commit message:").ask()
    if not message:
        console.print("[bold red]Error:[/bold red] A commit message is required.")
        return
        
    agent_id = questionary.text("Enter the agent ID (optional):").ask()
    task_id = questionary.text("Enter the task ID (optional):").ask()
    remote = questionary.text("Enter the remote to push to:", default="origin").ask()
    allow_empty = questionary.confirm("Allow empty commit?").ask()
    require_changes = questionary.confirm("Require changes?").ask()
    signoff = questionary.confirm("Sign off the commit?").ask()
    no_verify = questionary.confirm("Bypass git hooks?").ask()

    try:
        repo.close(
            path=path,
            message=message,
            agent_id=agent_id if agent_id else None,
            task_id=task_id if task_id else None,
            remote=remote,
            allow_empty=allow_empty,
            require_changes=require_changes,
            signoff=signoff,
            no_verify=no_verify
        )
        console.print("[bold green]Repository closed successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

def _view_clones():
    """Display a list of active repository clones."""
    if not repo.REGISTRY_PATH.exists():
        console.print("[yellow]No repository clones found.[/yellow]")
        return

    with open(repo.REGISTRY_PATH, "r") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError:
            console.print("[bold red]Error: Could not parse the runtime registry.[/bold red]")
            return

    if not entries:
        console.print("[yellow]No repository clones found.[/yellow]")
        return

    table = Table(title="Active Repository Clones")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Origin", style="magenta")
    table.add_column("Temp Dir", style="green")
    table.add_column("Branch", style="blue")
    table.add_column("Status", style="yellow")

    for entry in entries:
        table.add_row(
            entry.get("agent_id", "N/A"),
            entry.get("origin", "N/A"),
            entry.get("temp_dir", "N/A"),
            entry.get("branch", "N/A"),
            entry.get("status", "N/A"),
        )

    console.print(table)

@app.command()
def main():
    """
    Cage Platform Manager
    """
    if not sys.stdin.isatty():
        console.print("[bold red]Error:[/bold red] This is not a TTY. The interactive manager requires a terminal.")
        console.print("For headless operation, please use the appropriate subcommands and flags.")
        raise typer.Exit(1)

    console.print(Panel("Welcome to the Cage Platform Manager!", title="[bold green]Cage[/bold green]"))

    while True:
        menu_choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Initialise a new repository",
                "Close a repository",
                "View repository clones",
                "Exit"
            ]
        ).ask()

        if menu_choice == "Initialise a new repository":
            _interactive_init()
        elif menu_choice == "Close a repository":
            _interactive_close()
        elif menu_choice == "View repository clones":
            _view_clones()
        else:
            console.print("Exiting.")
            break

if __name__ == "__main__":
    app()
