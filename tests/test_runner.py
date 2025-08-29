import pytest
import os
from pathlib import Path
from tools.mcp.actor_server.runner import run_shell, ToolError

def test_echo_happy_path(tmp_path: Path):
    """Test a simple echo command in a temporary directory."""
    instruction = "echo hello world"
    result = run_shell(str(tmp_path), instruction)
    assert result.strip() == "hello world"

def test_command_failure(tmp_path: Path):
    """Test that a non-zero exit code raises a ToolError."""
    instruction = "false"
    with pytest.raises(ToolError) as exc_info:
        run_shell(str(tmp_path), instruction)
    assert "Command failed with exit code" in str(exc_info.value)
    assert exc_info.value.exit_code == 1

def test_command_timeout(tmp_path: Path):
    """Test that a command exceeding the timeout raises a ToolError."""
    instruction = "sleep 2"
    with pytest.raises(ToolError) as exc_info:
        run_shell(str(tmp_path), instruction, timeout=1)
    assert "Command timed out after 1 seconds" in str(exc_info.value)
    assert exc_info.value.exit_code is None # Timeout doesn't have an exit code directly

def test_command_in_correct_directory(tmp_path: Path):
    """Test that the command is executed in the specified directory."""
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "test_file.txt").write_text("content")

    instruction = "ls"
    result = run_shell(str(sub_dir), instruction)
    assert "test_file.txt" in result

    # Verify it doesn't see files outside its cwd
    (tmp_path / "other_file.txt").write_text("other content")
    result_in_sub = run_shell(str(sub_dir), instruction)
    assert "other_file.txt" not in result_in_sub

def test_invalid_path(tmp_path: Path):
    """Test that an invalid path raises a ToolError."""
    invalid_path = tmp_path / "non_existent_dir"
    instruction = "echo hello"
    with pytest.raises(ToolError) as exc_info:
        run_shell(str(invalid_path), instruction)
    assert f"Path '{invalid_path}' is not a valid directory." in str(exc_info.value)

def test_stderr_capture(tmp_path: Path):
    """Test that stderr is captured on command failure."""
    instruction = "bash -c 'echo \"error output\" >&2 && exit 1'"
    with pytest.raises(ToolError) as exc_info:
        run_shell(str(tmp_path), instruction)
    assert "error output" in exc_info.value.stderr

def test_stdout_capture_on_failure(tmp_path: Path):
    """Test that stdout is captured on command failure."""
    instruction = "bash -c 'echo \"stdout output\" && exit 1'"
    with pytest.raises(ToolError) as exc_info:
        run_shell(str(tmp_path), instruction)
    assert "stdout output" in exc_info.value.stdout
