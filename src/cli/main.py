import typer
import subprocess
import sys

app = typer.Typer()

CONTAINER_NAME = "cage-api-service"

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
        subprocess.run(["podman", "build", "-t", CONTAINER_NAME, "-f", "Containerfile", "."], check=True)
        # Run the container
        subprocess.run(["podman", "run", "-d", "--name", CONTAINER_NAME, "-p", "8000:8000", CONTAINER_NAME], check=True)
        print(f"Container {CONTAINER_NAME} started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def stop():
    """Stops and removes the API service container."""
    try:
        subprocess.run(["podman", "stop", CONTAINER_NAME], check=True)
        subprocess.run(["podman", "rm", CONTAINER_NAME], check=True)
        print(f"Container {CONTAINER_NAME} stopped and removed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def status():
    """Checks the status of the API service container."""
    try:
        subprocess.run(["podman", "ps", "-f", f"name={CONTAINER_NAME}"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error checking container status: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    app()
