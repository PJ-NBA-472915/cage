"""
CLI commands for CrewAI functionality.
"""

import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..cage.crew_tool import CrewTool
from ..cage.models import TaskManager

app = typer.Typer(name="crew", help="CrewAI workflow commands")
console = Console()


@app.command()
def plan(
    task_id: str = typer.Argument(..., help="Task ID to create plan for"),
    plan_file: Optional[Path] = typer.Option(None, "--plan-file", "-f", help="Path to plan JSON file"),
    repo_path: Path = typer.Option(Path("."), "--repo-path", "-r", help="Repository path")
):
    """Create a plan for a task using CrewAI."""
    try:
        # Initialize tools
        task_manager = TaskManager(repo_path / "tasks")
        crew_tool = CrewTool(repo_path, task_manager)
        
        # Load plan data if provided
        plan_data = {}
        if plan_file and plan_file.exists():
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
        
        # Create plan
        result = crew_tool.create_plan(task_id, plan_data)
        
        if result["status"] == "success":
            console.print(Panel(
                f"[green]✓ Plan created successfully![/green]\n\n"
                f"Task ID: {result['task_id']}\n"
                f"Run ID: {result['run_id']}\n"
                f"Plan: {result['plan']}",
                title="Plan Created",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]✗ Failed to create plan: {result['error']}[/red]",
                title="Plan Creation Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def apply(
    task_id: str = typer.Argument(..., help="Task ID to apply plan for"),
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help="Specific run ID to apply"),
    repo_path: Path = typer.Option(Path("."), "--repo-path", "-r", help="Repository path")
):
    """Apply a plan using CrewAI agents."""
    try:
        # Initialize tools
        task_manager = TaskManager(repo_path / "tasks")
        crew_tool = CrewTool(repo_path, task_manager)
        
        # Apply plan
        result = crew_tool.apply_plan(task_id, run_id)
        
        if result["status"] == "success":
            console.print(Panel(
                f"[green]✓ Plan applied successfully![/green]\n\n"
                f"Task ID: {result['task_id']}\n"
                f"Run ID: {result['run_id']}\n"
                f"Result: {result['result']}",
                title="Plan Applied",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]✗ Failed to apply plan: {result['error']}[/red]",
                title="Plan Application Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    run_id: str = typer.Argument(..., help="Run ID to get status for"),
    repo_path: Path = typer.Option(Path("."), "--repo-path", "-r", help="Repository path")
):
    """Get the status of a crew run."""
    try:
        # Initialize tools
        task_manager = TaskManager(repo_path / "tasks")
        crew_tool = CrewTool(repo_path, task_manager)
        
        # Get run status
        result = crew_tool.get_run_status(run_id)
        
        if result["status"] == "success":
            run_data = result["run_data"]
            
            # Create status table
            table = Table(title=f"Run Status: {run_id}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Run ID", run_data.get("run_id", "N/A"))
            table.add_row("Task ID", run_data.get("task_id", "N/A"))
            table.add_row("Status", run_data.get("status", "N/A"))
            table.add_row("Started At", run_data.get("started_at", "N/A"))
            table.add_row("Completed At", run_data.get("completed_at", "N/A"))
            
            if run_data.get("error"):
                table.add_row("Error", run_data["error"])
            
            console.print(table)
            
            # Show logs if available
            if run_data.get("logs"):
                console.print("\n[bold]Logs:[/bold]")
                for log in run_data["logs"]:
                    console.print(f"  • {log}")
            
            # Show artefacts if available
            if run_data.get("artefacts"):
                console.print("\n[bold]Artefacts:[/bold]")
                for artefact in run_data["artefacts"]:
                    console.print(f"  • {artefact}")
                    
        else:
            console.print(Panel(
                f"[red]✗ Failed to get run status: {result['error']}[/red]",
                title="Status Retrieval Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def upload(
    run_id: str = typer.Argument(..., help="Run ID to upload artefacts to"),
    files: str = typer.Argument(..., help="JSON string of files to upload (filename: content)"),
    repo_path: Path = typer.Option(Path("."), "--repo-path", "-r", help="Repository path")
):
    """Upload artefacts to a crew run."""
    try:
        # Parse files JSON
        try:
            files_dict = json.loads(files)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON format for files[/red]")
            raise typer.Exit(1)
        
        # Initialize tools
        task_manager = TaskManager(repo_path / "tasks")
        crew_tool = CrewTool(repo_path, task_manager)
        
        # Upload artefacts
        result = crew_tool.upload_artefacts(run_id, files_dict)
        
        if result["status"] == "success":
            console.print(Panel(
                f"[green]✓ Artefacts uploaded successfully![/green]\n\n"
                f"Run ID: {result['run_id']}\n"
                f"Uploaded Files: {len(result['uploaded_files'])}\n"
                f"Files: {', '.join(result['uploaded_files'])}",
                title="Artefacts Uploaded",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]✗ Failed to upload artefacts: {result['error']}[/red]",
                title="Artefact Upload Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_runs(
    repo_path: Path = typer.Option(Path("."), "--repo-path", "-r", help="Repository path")
):
    """List all crew runs."""
    try:
        runs_dir = repo_path / ".cage" / "runs"
        
        if not runs_dir.exists():
            console.print("[yellow]No runs directory found[/yellow]")
            return
        
        # Get all run directories
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        
        if not run_dirs:
            console.print("[yellow]No runs found[/yellow]")
            return
        
        # Create runs table
        table = Table(title="Crew Runs")
        table.add_column("Run ID", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Started At", style="dim")
        table.add_column("Completed At", style="dim")
        
        for run_dir in sorted(run_dirs, key=lambda x: x.name):
            status_file = run_dir / "status.json"
            
            if status_file.exists():
                with open(status_file, 'r') as f:
                    run_data = json.load(f)
                
                table.add_row(
                    run_data.get("run_id", run_dir.name),
                    run_data.get("status", "unknown"),
                    run_data.get("started_at", "N/A"),
                    run_data.get("completed_at", "N/A")
                )
            else:
                table.add_row(run_dir.name, "unknown", "N/A", "N/A")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
