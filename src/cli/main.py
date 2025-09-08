import typer
import subprocess
import sys
import os
import uvicorn
from pathlib import Path

app = typer.Typer()

def check_podman():
    """Checks if podman is running and connected."""
    try:
        subprocess.run(["podman", "system", "connection", "list"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Cannot connect to Podman. Please verify your connection to the Linux system using `podman system connection list`, or try `podman machine init` and `podman machine start` to manage a new Linux VM", file=sys.stderr)
        sys.exit(1)

@app.command()
def start():
    """Builds and starts the API service container."""
    check_podman()
    try:
        # Build the container
        subprocess.run(["podman", "build", "-t", "cage-pod", "-f", "Containerfile", "."], check=True)
        # Run the container
        subprocess.run(["podman", "run", "-d", "--name", "cage-pod", "-p", "8000:8000", "cage-pod"], check=True)
        print("Container cage-pod started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def stop():
    """Stops and removes the API service container."""
    try:
        subprocess.run(["podman", "stop", "cage-pod"], check=True)
        subprocess.run(["podman", "rm", "cage-pod"], check=True)
        print("Container cage-pod stopped and removed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def status():
    """Checks the status of the API service container."""
    try:
        subprocess.run(["podman", "ps", "-f", "name=cage-pod"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error checking container status: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def serve(
    repository_path: str = typer.Argument(..., help="Path to the repository directory"),
    port: int = typer.Option(8000, help="Port to run the service on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the service to")
):
    """Start the Cage service for a specific repository directory."""
    # Validate repository path
    repo_path = Path(repository_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repository_path}", file=sys.stderr)
        sys.exit(1)
    
    if not (repo_path / ".git").is_dir():
        print(f"Error: Not a Git repository: {repository_path}", file=sys.stderr)
        sys.exit(1)
    
    # Set environment variables for the new Cage specification
    os.environ["REPO_PATH"] = str(repo_path)
    os.environ["POD_ID"] = os.environ.get("POD_ID", "dev-pod")
    os.environ["POD_TOKEN"] = os.environ.get("POD_TOKEN", "dev-token")
    
    print(f"Starting Cage service for repository: {repo_path}")
    print(f"Service will be available at: http://{host}:{port}")
    print("Press Ctrl+C to stop the service")
    
    try:
        # Import and run the API service
        from api.main import app
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        print("\nService stopped.")
    except Exception as e:
        print(f"Error starting service: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    app()