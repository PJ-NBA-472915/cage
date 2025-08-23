#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting agent container..."

# Check if required arguments are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <repo_path> <cli_request>"
    echo "Example: $0 /app/repo 'please adjust poem.txt to contain a poem about pancakes'"
    exit 1
fi

REPO_PATH="$1"
CLI_REQUEST="$2"

echo "[entrypoint] Repository path: $REPO_PATH"
echo "[entrypoint] CLI request: $CLI_REQUEST"

# Optional repo/pod specific setup
if [[ -f "/app/pod-setup.sh" ]]; then
  echo "[entrypoint] Running pod-setup.sh ..."
  # Try to make executable, but don't fail if it's read-only
  chmod +x /app/pod-setup.sh 2>/dev/null || echo "[entrypoint] Note: pod-setup.sh is read-only (expected for mounted volumes)"
  /app/pod-setup.sh
else
  echo "[entrypoint] No pod-setup.sh found. Skipping runtime setup."
fi

# Start the agent daemon with arguments
echo "[entrypoint] Starting agent daemon..."
exec python3 /app/agent_daemon.py "$REPO_PATH" "$CLI_REQUEST"
