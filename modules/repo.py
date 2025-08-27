
import os
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

REGISTRY_PATH = Path("coordination/runtime_registry.json")


def init(origin: str, *, agent_id: str | None = None, branch: str | None = None, shallow: bool = True, task_slug: str | None = None) -> dict:
    """
    Initialise a working copy from a local path or Git URL into a unique temporary directory.

    Returns a metadata dict including temp_dir, origin, branch, commit (if resolvable),
    agent_id, and timestamps.

    Parameters:
      origin: Local filesystem path OR Git URL (https/ssh/file).
      agent_id: Optional caller-provided agent identifier; generate a UUIDv4 if omitted.
      branch: Optional branch to checkout after clone; default: provider's default.
      shallow: If true, use a depth-1 clone when cloning remotes.
      task_slug: Optional slug for the task, used to create a new agent-specific branch.

    Returns:
      A dict with: { 'agent_id', 'origin', 'is_remote', 'temp_dir', 'branch', 'commit', 'created_at_iso' }.
    """
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    temp_dir = _unique_tempdir(prefix=f"agent-repo-{agent_id}-")
    is_remote = _is_git_url(origin)

    if is_remote:
        _clone_remote(origin, temp_dir, branch=branch, shallow=shallow)
    else:
        source_path = Path(origin).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Local origin not found: {origin}")
        _clone_local(source_path, temp_dir)

    commit_hash = None
    if (temp_dir / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "-C", str(temp_dir), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit_hash = None # Git not found or not a repo

        if task_slug:
            agent_branch = f"agent/{task_slug}"
            subprocess.run(
                ["git", "-C", str(temp_dir), "checkout", "-b", agent_branch],
                check=True,
                capture_output=True,
                text=True,
            )
            branch = agent_branch

    metadata = {
        "agent_id": agent_id,
        "origin": origin,
        "is_remote": is_remote,
        "temp_dir": str(temp_dir),
        "branch": branch,
        "commit": commit_hash,
        "created_at_iso": _now_iso(),
    }

    _write_runtime_registry(metadata)
    return metadata

def _is_git_url(value: str) -> bool:
    """Check if a string is a git URL."""
    return value.startswith(("https://", "http://", "ssh://", "git@"))

def _unique_tempdir(prefix: str = "agent-repo-") -> Path:
    """Create a unique temporary directory."""
    return Path(tempfile.mkdtemp(prefix=prefix))

def _clone_local(src: Path, dst: Path) -> None:
    """Clone a local directory, preserving .git if it exists."""
    if (src / ".git").is_dir():
        subprocess.run(["git", "clone", "--local", str(src), str(dst)], check=True)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)

def _clone_remote(url: str, dst: Path, *, branch: str | None, shallow: bool) -> None:
    """Clone a remote git repository."""
    cmd = ["git", "clone"]
    if shallow:
        cmd.append("--depth=1")
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, str(dst)])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("git command not found. Please ensure Git is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone remote repository: {e.stderr}")


def _write_runtime_registry(entry: dict) -> None:
    """Atomically append an entry to the runtime registry."""
    REGISTRY_PATH.parent.mkdir(exist_ok=True)

    entries = []
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r") as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError:
                # Handle corrupted or empty file
                pass
    
    entries.append(entry)

    temp_path = REGISTRY_PATH.with_suffix(f".json.tmp.{uuid.uuid4()}")
    with open(temp_path, "w") as f:
        json.dump(entries, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.rename(temp_path, REGISTRY_PATH)
    if os.name != 'nt':
        parent_fd = os.open(REGISTRY_PATH.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)


def _now_iso() -> str:
    """Return the current time in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()
