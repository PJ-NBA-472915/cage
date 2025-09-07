
import os
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

REGISTRY_PATH = Path("coordination/runtime_registry.json")


def init(origin: str, *, agent_id: str | None = None, branch: str | None = None, shallow: bool = True, task_slug: str | None = None) -> dict:
    """
    Initialise a working copy from a local path or Git URL into a unique temporary directory.
    A new agent-specific branch is always created.

    Returns a metadata dict including temp_dir, origin, branch, commit (if resolvable),
    agent_id, and timestamps.

    Parameters:
      origin: Local filesystem path OR Git URL (https/ssh/file).
      agent_id: Optional caller-provided agent identifier; generate a UUIDv4 if omitted.
      branch: Optional branch to checkout after clone; default: provider's default.
      shallow: If true, use a depth-1 clone when cloning remotes.
      task_slug: Optional slug for the task, used to create a new agent-specific branch. If not provided, a unique slug will be generated.

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

        if not task_slug:
            task_slug = str(uuid.uuid4())[:8]
        
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
        "status": "initialized",
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

def _update_runtime_registry(agent_id: str, temp_dir: str, update_data: dict, remove: bool = False) -> None:
    """Atomically update or remove an entry in the runtime registry."""
    REGISTRY_PATH.parent.mkdir(exist_ok=True)

    entries = []
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r") as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError:
                pass
    
    if remove:
        entries = [
            entry
            for entry in entries
            if not (entry.get("agent_id") == agent_id and entry.get("temp_dir") == temp_dir)
        ]
    else:
        updated = False
        for entry in entries:
            if entry.get("agent_id") == agent_id and entry.get("temp_dir") == temp_dir:
                entry.update(update_data)
                updated = True
                break
        
        if not updated:
            entries.append(update_data)


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


def _read_runtime_registry() -> list:
    """Reads the runtime registry file."""
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def get_open_repositories(status_filter: list[str] | None = None) -> list:
    """
    Returns a list of open repositories from the runtime registry,
    optionally filtered by status.
    By default, it shows 'initialized', 'in progress', and 'conflicted' repositories.
    """
    entries = _read_runtime_registry()
    
    if status_filter is None:
        # Default filter: show initialized, in progress, and conflicted
        default_statuses = ["initialized", "in progress", "conflicted"]
        return [
            entry
            for entry in entries
            if entry.get("status") in default_statuses
        ]
    else:
        # Filter by provided statuses
        return [
            entry
            for entry in entries
            if entry.get("status") in status_filter
        ]


def _now_iso() -> str:
    """Return the current time in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()


def close(path: str, *, message: str, agent_id: str | None = None, task_id: str | None = None, remote: str = "origin", allow_empty: bool = False, require_changes: bool = False, signoff: bool = False, no_verify: bool = False, merge: bool = False, target_branch: str = "main") -> None:
    """
    Finalise a clone's work, commit, and push.
    """
    if not path:
        raise ValueError("A repository path must be provided.")
    repo_path = Path(path).resolve()
    if not (repo_path / ".git").is_dir():
        raise ValueError(f"Not a git repository: {repo_path}")

    # Check for changes
    status_result = subprocess.run(["git", "-C", str(repo_path), "status", "--porcelain"], capture_output=True, text=True)
    if not status_result.stdout.strip() and not allow_empty:
        if require_changes:
            raise RuntimeError("No changes to commit.")
        print("No changes to commit.")
        return

    # Stage all changes
    subprocess.run(["git", "-C", str(repo_path), "add", "-A"], check=True)

    # Commit
    commit_cmd = ["git", "-C", str(repo_path), "commit", "-m", message]
    if allow_empty:
        commit_cmd.append("--allow-empty")
    if signoff:
        commit_cmd.append("--signoff")
    if no_verify:
        commit_cmd.append("--no-verify")
    
    commit_message = f"[agent:{agent_id}] close: {message}"
    if task_id:
        commit_message += f"\n\nTask-ID: {task_id}"
    
    commit_cmd.extend(["-m", commit_message])

    subprocess.run(commit_cmd, check=True)

    # Push
    current_branch = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()
    
    push_cmd = ["git", "-C", str(repo_path), "push", remote, current_branch]
    if no_verify:
        push_cmd.append("--no-verify")
    
    try:
        subprocess.run(push_cmd, check=True)
    except subprocess.CalledProcessError as e:
        # Update registry with failure reason
        failure_metadata = {
            "status": "failed",
            "failure_reason": "push_failed",
            "error_message": f"Failed to push to remote: {e.stderr}"
        }
        _update_runtime_registry(agent_id, str(repo_path), failure_metadata)
        raise RuntimeError(f"Failed to push to remote: {e.stderr}")

    # Update registry with initial close status
    commit_sha = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    close_metadata = {
        "commit_sha": commit_sha,
        "branch": current_branch,
        "remote": remote,
        "closed_at": _now_iso(),
        "status": "closed",
    }
    _update_runtime_registry(agent_id, str(repo_path), close_metadata)

    if merge:
        merge_status = "merged"
        merge_commit_sha = None
        conflict_files = []
        failure_reason = None

        try:
            # Fetch the latest from the remote
            subprocess.run(["git", "-C", str(repo_path), "fetch", remote], check=True)

            # Check if target branch exists remotely
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "ls-remote", "--heads", remote, target_branch],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                raise RuntimeError(f"Target branch '{target_branch}' does not exist on remote '{remote}'")

            # Check if target branch is protected (simple check: if it's main/master and not explicitly allowed)
            # This is a placeholder for a more robust protection mechanism.
            # For now, we'll allow main but protect master
            if target_branch == "master": # master is protected
                raise RuntimeError(f"Target branch '{target_branch}' is protected. Merge aborted.")

            # Check out the default branch locally
            subprocess.run(["git", "-C", str(repo_path), "checkout", target_branch], check=True)
            subprocess.run(["git", "-C", str(repo_path), "pull", remote, target_branch], check=True)

            # Attempt to merge the agent's branch into the default branch
            agent_branch_name = current_branch # The branch the agent was working on
            
            # Try fast-forward merge first
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "merge", "--ff-only", agent_branch_name],
                    check=True,
                    capture_output=True,
                    text=True
                )
                merge_commit_sha = subprocess.run(
                    ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
            except subprocess.CalledProcessError:
                # If fast-forward not possible, create a merge commit
                merge_message = f"Merge branch '{agent_branch_name}' into {target_branch}\n\n[agent:{agent_id}] merged after close of task {task_id}"
                try:
                    subprocess.run(
                        ["git", "-C", str(repo_path), "merge", "--no-ff", "-m", merge_message, agent_branch_name],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    merge_commit_sha = subprocess.run(
                        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True
                    ).stdout.strip()
                except subprocess.CalledProcessError as e:
                    # Merge conflicts occurred
                    # Get conflicting files before aborting the merge
                    try:
                        conflict_result = subprocess.run(
                            ["git", "-C", str(repo_path), "diff", "--name-only", "--diff-filter=U"],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        conflict_files = conflict_result.stdout.strip().splitlines()
                    except subprocess.CalledProcessError:
                        # If we can't get conflict files, use a default
                        conflict_files = ["unknown_conflict"]
                    
                    # Now abort the merge
                    subprocess.run(["git", "-C", str(repo_path), "merge", "--abort"], check=True)
                    
                    # Checkout back to the agent branch
                    subprocess.run(["git", "-C", str(repo_path), "checkout", agent_branch_name], check=True)
                    
                    merge_status = "conflict"
                    failure_reason = "merge_conflict"
                    raise RuntimeError(f"Merge conflict: {e.stderr}")

            # Push the merged branch
            try:
                subprocess.run(["git", "-C", str(repo_path), "push", remote, target_branch], check=True)
            except subprocess.CalledProcessError as e:
                # Check if push was denied due to branch protection
                if "protected" in e.stderr.lower() or "denied" in e.stderr.lower():
                    merge_status = "blocked"
                    failure_reason = "protected_branch"
                    raise RuntimeError(f"Push to protected branch '{target_branch}' was denied: {e.stderr}")
                else:
                    merge_status = "failed"
                    failure_reason = "push_failed"
                    raise RuntimeError(f"Failed to push merged branch: {e.stderr}")

        except RuntimeError as e:
            if "protected" in str(e).lower():
                merge_status = "blocked"
                failure_reason = "protected_branch"
            elif "conflict" in str(e).lower():
                merge_status = "conflict"
                failure_reason = "merge_conflict"
            else:
                merge_status = "failed"
                failure_reason = str(e)
            print(f"Merge failed: {e}", file=sys.stderr)
            raise e
        except subprocess.CalledProcessError as e:
            merge_status = "failed"
            failure_reason = f"Git command failed: {e.stderr}"
            print(f"Merge failed: {e.stderr}", file=sys.stderr)
            raise RuntimeError(f"Merge failed: {e.stderr}")
        finally:
            # Update registry with merge results
            merge_metadata = {
                "status": merge_status,
                "merged": merge_status == "merged",
                "merged_into": target_branch if merge_status == "merged" else None,
                "merge_commit_sha": merge_commit_sha if merge_status == "merged" else None,
                "merged_at": _now_iso() if merge_status == "merged" else None,
                "conflict_files": conflict_files if merge_status == "conflict" else None,
                "failure_reason": failure_reason,
            }
            _update_runtime_registry(agent_id, str(repo_path), merge_metadata)
            
            # Clean up the repository only if merge was successful or not attempted
            if merge_status == "merged" or not merge:
                shutil.rmtree(repo_path)
                _update_runtime_registry(agent_id, str(repo_path), {}, remove=True)
            else:
                print(f"Repository at {repo_path} not removed due to merge issues. Please resolve manually.", file=sys.stderr)
    else:
        # If no merge, just clean up the repository and remove from registry
        shutil.rmtree(repo_path)
        _update_runtime_registry(agent_id, str(repo_path), {}, remove=True)


