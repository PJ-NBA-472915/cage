import subprocess
import os
import sys

class ToolError(Exception):
    """Custom exception for errors during tool execution."""
    def __init__(self, message, stdout=None, stderr=None, exit_code=None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

def run_shell(path: str, instruction: str, timeout: int = 60) -> str:
    """
    Executes a shell command in the specified path.

    Args:
        path: The directory in which to run the command.
        instruction: The shell command to execute.
        timeout: The maximum time in seconds to wait for the command to complete.

    Returns:
        The stdout of the executed command.

    Raises:
        ToolError: If the command fails (non-zero exit code) or times out.
    """
    if not os.path.isdir(path):
        raise ToolError(f"Path '{path}' is not a valid directory.")

    try:
        process = subprocess.run(
            instruction,
            cwd=path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True # Raise CalledProcessError for non-zero exit codes
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        raise ToolError(
            f"Command failed with exit code {e.returncode}",
            stdout=e.stdout,
            stderr=e.stderr,
            exit_code=e.returncode
        ) from e
    except subprocess.TimeoutExpired as e:
        # For TimeoutExpired, stdout/stderr might be in the exception object
        raise ToolError(
            f"Command timed out after {timeout} seconds",
            stdout=e.stdout,
            stderr=e.stderr,
            exit_code=None # Timeout doesn't have an exit code directly
        ) from e
    except Exception as e:
        raise ToolError(f"An unexpected error occurred: {e}") from e
