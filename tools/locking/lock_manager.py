import argparse
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import fcntl # For flock, if available and needed

# --- Configuration ---
COORDINATION_DIR = Path(os.environ.get("LOCK_COORDINATION_DIR", "coordination")).resolve()
CONFIG_FILE = COORDINATION_DIR / "config.json"
ACTIVE_REGISTRY = COORDINATION_DIR / "active_work_registry.json"
COMPLETED_LOG = COORDINATION_DIR / "completed_work_log.json"
PLANNED_QUEUE = COORDINATION_DIR / "planned_work_queue.json"
AGENT_LOCKS_DIR = COORDINATION_DIR / "agent_locks"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
RELEASED_LOCKS_DIR = COORDINATION_DIR / "released_locks"

DEFAULT_CONFIG = {
    "lock_ttl_minutes": 90,
    "stale_grace_minutes": 30,
    "max_paths_per_claim": 25,
    "allow_topic_claims": True,
    "advisory_only": False,
    "use_flock_when_available": True,
}

def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# --- Utility Functions ---
def get_current_utc_timestamp():
    return datetime.now(timezone.utc).isoformat()

def generate_agent_id():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:4]
    return f"agent_{timestamp}_{random_suffix}"

def normalize_path(path_str):
    """Normalizes a path, ensuring it's relative to the project root and resolves '..'."""
    # Ensure path is relative to current working directory (project root)
    # and resolve any '..' components.
    # This assumes the script is run from the project root.
    return Path(path_str).resolve().relative_to(Path.cwd()).as_posix()

def is_path_ancestor(ancestor, descendant):
    """Checks if ancestor path is a parent directory of descendant path."""
    try:
        Path(descendant).relative_to(Path(ancestor))
        return True
    except ValueError:
        return False

def atomic_write_json(file_path, data):
    """Writes data to a JSON file atomically."""
    temp_file = Path(str(file_path) + ".tmp." + uuid.uuid4().hex)
    try:
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.rename(temp_file, file_path)
    except Exception as e:
        print(f"Error during atomic write to {file_path}: {e}", file=sys.stderr)
        if temp_file.exists():
            temp_file.unlink() # Clean up temp file on error
        raise
    finally:
        if temp_file.exists(): # Ensure temp file is removed if rename failed for some reason
            temp_file.unlink()

def read_json_file(file_path, default_value=None):
    """Reads a JSON file, returning default_value if file doesn't exist or is empty."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return default_value if default_value is not None else {}
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {file_path} is not valid JSON. Returning empty data.", file=sys.stderr)
        return default_value if default_value is not None else {}
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return default_value if default_value is not None else {}

class LockManager:
    def __init__(self):
        self.config = load_config()
        self._ensure_dirs()

    def _ensure_dirs(self):
        COORDINATION_DIR.mkdir(exist_ok=True)
        AGENT_LOCKS_DIR.mkdir(exist_ok=True)
        HEARTBEATS_DIR.mkdir(exist_ok=True)
        RELEASED_LOCKS_DIR.mkdir(exist_ok=True)

    def _get_active_claims(self):
        return read_json_file(ACTIVE_REGISTRY, default_value={})

    def _update_active_claims(self, claims):
        atomic_write_json(ACTIVE_REGISTRY, claims)

    def _append_to_completed_log(self, entry):
        log = read_json_file(COMPLETED_LOG, default_value=[])
        log.append(entry)
        atomic_write_json(COMPLETED_LOG, log)

    def _get_claim_file_path(self, claim_id):
        return AGENT_LOCKS_DIR / f"{claim_id}.json"

    def _create_heartbeat(self, agent_id):
        heartbeat_file = HEARTBEATS_DIR / f"{agent_id}.heartbeat"
        heartbeat_file.touch(exist_ok=True)
        # Update modification time
        os.utime(heartbeat_file, None)

    def _check_path_overlap(self, new_paths, existing_claim_paths):
        for new_p in new_paths:
            new_path_obj = Path(new_p)
            for existing_p in existing_claim_paths:
                existing_path_obj = Path(existing_p)

                # Check if new_path is a directory and existing_path is inside it
                if new_path_obj.is_dir() and is_path_ancestor(new_path_obj, existing_path_obj):
                    return True
                # Check if existing_path is a directory and new_path is inside it
                if existing_path_obj.is_dir() and is_path_ancestor(existing_path_obj, new_path_obj):
                    return True
                # Check for exact match
                if new_path_obj == existing_path_obj:
                    return True
        return False

    def claim(self, agent_id, paths, topics, intent, issue_pr, reason, scope):
        if not agent_id:
            agent_id = generate_agent_id()

        if not paths and not topics:
            print("Error: Must specify at least one path or topic to claim.", file=sys.stderr)
            return False

        normalized_paths = [normalize_path(p) for p in paths]
        if len(normalized_paths) > self.config["max_paths_per_claim"]:
            print(f"Error: Too many paths. Max allowed: {self.config['max_paths_per_claim']}", file=sys.stderr)
            return False

        if topics and not self.config["allow_topic_claims"]:
            print("Error: Topic claims are not allowed by configuration.", file=sys.stderr)
            return False

        active_claims = self._get_active_claims()
        for claim_id, claim_data in active_claims.items():
            # Check for path conflicts
            if normalized_paths and claim_data.get("paths"):
                if self._check_path_overlap(normalized_paths, claim_data["paths"]):
                    print(f"Conflict: Paths {normalized_paths} overlap with existing claim {claim_id} by agent {claim_data['agent_id']}.", file=sys.stderr)
                    return False
            # Check for topic conflicts
            if topics and claim_data.get("topics"):
                if any(t in claim_data["topics"] for t in topics):
                    print(f"Conflict: Topics {topics} overlap with existing claim {claim_id} by agent {claim_data['agent_id']}.", file=sys.stderr)
                    return False

        claim_id = f"claim_{uuid.uuid4().hex}"
        created_at = get_current_utc_timestamp()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=self.config["lock_ttl_minutes"])).isoformat()

        claim_data = {
            "claim_id": claim_id,
            "agent_id": agent_id,
            "created_at": created_at,
            "expires_at": expires_at,
            "paths": normalized_paths,
            "topics": topics,
            "intent": intent,
            "issue_pr": issue_pr,
            "reason": reason,
            "scope": scope,
            "host": os.uname().nodename,
            "pid": os.getpid(),
        }

        # Atomically write the claim file
        atomic_write_json(self._get_claim_file_path(claim_id), claim_data)

        # Update active registry
        active_claims[claim_id] = claim_data
        self._update_active_claims(active_claims)

        self._create_heartbeat(agent_id)

        print(f"Claim {claim_id} successfully created by agent {agent_id}.")
        return True

    def release(self, agent_id, claim_id):
        active_claims = self._get_active_claims()
        if claim_id not in active_claims:
            print(f"Error: Claim {claim_id} not found in active registry.", file=sys.stderr)
            return False

        claim_data = active_claims[claim_id]
        if claim_data["agent_id"] != agent_id:
            print(f"Error: Agent {agent_id} does not own claim {claim_id}.", file=sys.stderr)
            return False

        # Remove from active registry
        del active_claims[claim_id]
        self._update_active_claims(active_claims)

        # Move claim file to released_locks
        claim_file = self._get_claim_file_path(claim_id)
        if claim_file.exists():
            os.rename(claim_file, RELEASED_LOCKS_DIR / claim_file.name)

        # Log completion
        completed_entry = {
            "action": "released",
            "timestamp": get_current_utc_timestamp(),
            "agent_id": agent_id,
            "claim_id": claim_id,
            "claim_data": claim_data,
        }
        self._append_to_completed_log(completed_entry)

        print(f"Claim {claim_id} successfully released by agent {agent_id}.")
        return True

    def renew(self, agent_id, claim_id):
        active_claims = self._get_active_claims()
        if claim_id not in active_claims:
            print(f"Error: Claim {claim_id} not found in active registry.", file=sys.stderr)
            return False

        claim_data = active_claims[claim_id]
        if claim_data["agent_id"] != agent_id:
            print(f"Error: Agent {agent_id} does not own claim {claim_id}.", file=sys.stderr)
            return False

        new_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=self.config["lock_ttl_minutes"])).isoformat()
        claim_data["expires_at"] = new_expires_at
        claim_data["renewed_at"] = get_current_utc_timestamp() # Add renewed_at for audit

        # Update claim file
        atomic_write_json(self._get_claim_file_path(claim_id), claim_data)

        # Update active registry
        active_claims[claim_id] = claim_data
        self._update_active_claims(active_claims)

        self._create_heartbeat(agent_id)

        print(f"Claim {claim_id} successfully renewed by agent {agent_id}. New expiry: {new_expires_at}")
        return True

    def status(self, output_json=False):
        active_claims = self._get_active_claims()
        completed_log = read_json_file(COMPLETED_LOG, default_value=[])

        if output_json:
            print(json.dumps({"active_claims": active_claims, "completed_log": completed_log}, indent=2))
            return

        print("\n--- Active Claims ---")
        if not active_claims:
            print("No active claims.")
        else:
            for claim_id, data in active_claims.items():
                expires_dt = datetime.fromisoformat(data["expires_at"])
                now_dt = datetime.now(timezone.utc)
                is_stale_candidate = now_dt > expires_dt
                status = "STALE CANDIDATE" if is_stale_candidate else "ACTIVE"
                print(f"  Claim ID: {claim_id} ({status})")
                print(f"    Agent: {data['agent_id']} (Host: {data.get('host')}, PID: {data.get('pid')})")
                print(f"    Created: {data['created_at']}")
                print(f"    Expires: {data['expires_at']}")
                print(f"    Intent: {data.get('intent', 'N/A')}")
                if data.get('paths'):
                    print(f"    Paths: {', '.join(data['paths'])}")
                if data.get('topics'):
                    print(f"    Topics: {', '.join(data['topics'])}")
                print("-" * 30)

        print("\n--- Last 5 Completed Actions ---")
        if not completed_log:
            print("No completed actions logged.")
        else:
            for entry in completed_log[-5:]:
                print(f"  Action: {entry['action']} at {entry['timestamp']}")
                print(f"    Claim ID: {entry['claim_id']} by Agent: {entry['agent_id']}")
                print("-" * 30)

    def reap_stale(self, reaper_id=None, output_json=False):
        if not reaper_id:
            reaper_id = generate_agent_id() + "_reaper"

        active_claims = self._get_active_claims()
        reaped_claims = {}
        now_dt = datetime.now(timezone.utc)
        stale_grace_period = timedelta(minutes=self.config["stale_grace_minutes"])

        for claim_id, claim_data in list(active_claims.items()): # Iterate over a copy
            expires_dt = datetime.fromisoformat(claim_data["expires_at"])
            if now_dt > expires_dt + stale_grace_period:
                print(f"Reaping stale claim {claim_id} (expired at {claim_data['expires_at']}).", file=sys.stderr)
                reaped_claims[claim_id] = claim_data
                del active_claims[claim_id]

                # Move claim file to released_locks
                claim_file = self._get_claim_file_path(claim_id)
                if claim_file.exists():
                    os.rename(claim_file, RELEASED_LOCKS_DIR / claim_file.name)

                # Log reaping
                completed_entry = {
                    "action": "reaped",
                    "timestamp": get_current_utc_timestamp(),
                    "reaper_id": reaper_id,
                    "claim_id": claim_id,
                    "claim_data": claim_data,
                    "reason": f"Expired and past grace period ({stale_grace_period})."
                }
                self._append_to_completed_log(completed_entry)

        if reaped_claims:
            self._update_active_claims(active_claims)
            if output_json:
                print(json.dumps({"reaped_claims": reaped_claims}, indent=2))
            else:
                print(f"Successfully reaped {len(reaped_claims)} stale claims.")
        else:
            print("No stale claims to reap.")
        return True

    def validate(self):
        print("\n--- Lock System Validation ---")
        # Check coordination directory writability
        if not COORDINATION_DIR.is_dir() or not os.access(COORDINATION_DIR, os.W_OK):
            print(f"Error: Coordination directory '{COORDINATION_DIR}' does not exist or is not writable.", file=sys.stderr)
            return False
        print(f"  Coordination directory '{COORDINATION_DIR}' is writable. [OK]")

        # Check atomic file operations (os.rename is atomic on POSIX for same filesystem)
        # We assume POSIX compliance for now.
        print("  Atomic file operations (os.rename) are assumed to be available and atomic on this POSIX-like system. [OK]")

        # Check git clean state (optional, as per prompt, can be a separate check)
        # For now, just a placeholder. This would require running a git command.
        # print("  Git clean state check (not implemented in this tool). [SKIPPED]")

        print("Validation complete. Basic checks passed.")
        return True

def main():
    parser = argparse.ArgumentParser(description="Repo-local locking mechanism for autonomous agents.")
    parser.add_argument("--coordination-dir", type=str, default="coordination",
                        help="Path to the coordination directory (default: coordination)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Claim parser
    claim_parser = subparsers.add_parser("claim", help="Claim one or more paths/topics.")
    claim_parser.add_argument("--agent", type=str, help="Agent ID (will be generated if not provided).")
    claim_parser.add_argument("--paths", type=str, help="Comma-separated list of paths to claim.")
    claim_parser.add_argument("--topics", type=str, help="Comma-separated list of topics to claim.")
    claim_parser.add_argument("--intent", type=str, required=True, help="Brief description of the agent's intent/plan.")
    claim_parser.add_argument("--issue-pr", type=str, help="Related issue or PR identifier.")
    claim_parser.add_argument("--reason", type=str, help="Reason for the claim.")
    claim_parser.add_argument("--scope", type=str, help="Scope of the claim (e.g., 'refactor', 'feature').")

    # Release parser
    release_parser = subparsers.add_parser("release", help="Release a claim.")
    release_parser.add_argument("--agent", type=str, required=True, help="Agent ID that owns the claim.")
    release_parser.add_argument("--claim-id", type=str, required=True, help="ID of the claim to release.")

    # Renew parser
    renew_parser = subparsers.add_parser("renew", help="Renew a claim's TTL.")
    renew_parser.add_argument("--agent", type=str, required=True, help="Agent ID that owns the claim.")
    renew_parser.add_argument("--claim-id", type=str, required=True, help="ID of the claim to renew.")

    # Status parser
    status_parser = subparsers.add_parser("status", help="Display current lock status.")
    status_parser.add_argument("--json", action="store_true", help="Output status in JSON format.")

    # Reap stale parser
    reap_parser = subparsers.add_parser("reap-stale", help="Detect and clean up stale locks.")
    reap_parser.add_argument("--reaper-id", type=str, help="ID of the agent performing the reaping (will be generated if not provided).")
    reap_parser.add_argument("--json", action="store_true", help="Output reaped claims in JSON format.")

    # Validate parser
    validate_parser = subparsers.add_parser("validate", help="Run preflight checks on the locking system.")

    args = parser.parse_args()

    # Set COORDINATION_DIR based on argument if provided
    global COORDINATION_DIR, CONFIG_FILE, ACTIVE_REGISTRY, COMPLETED_LOG, PLANNED_QUEUE, AGENT_LOCKS_DIR, HEARTBEATS_DIR, RELEASED_LOCKS_DIR
    if args.coordination_dir != "coordination":
        COORDINATION_DIR = Path(args.coordination_dir).resolve()
        CONFIG_FILE = COORDINATION_DIR / "config.json"
        ACTIVE_REGISTRY = COORDINATION_DIR / "active_work_registry.json"
        COMPLETED_LOG = COORDINATION_DIR / "completed_work_log.json"
        PLANNED_QUEUE = COORDINATION_DIR / "planned_work_queue.json"
        AGENT_LOCKS_DIR = COORDINATION_DIR / "agent_locks"
        HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
        RELEASED_LOCKS_DIR = COORDINATION_DIR / "released_locks"

    manager = LockManager()

    if args.command == "claim":
        paths = args.paths.split(',') if args.paths else []
        topics = args.topics.split(',') if args.topics else []
        manager.claim(args.agent, paths, topics, args.intent, args.issue_pr, args.reason, args.scope)
    elif args.command == "release":
        manager.release(args.agent, args.claim_id)
    elif args.command == "renew":
        manager.renew(args.agent, args.claim_id)
    elif args.command == "status":
        manager.status(args.json)
    elif args.command == "reap-stale":
        manager.reap_stale(args.reaper_id, args.json)
    elif args.command == "validate":
        manager.validate()

if __name__ == "__main__":
    import sys
    main()
