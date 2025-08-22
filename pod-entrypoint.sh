#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting agent container..."

# Optional repo/pod specific setup
if [[ -f "/app/pod-setup.sh" ]]; then
  echo "[entrypoint] Running pod-setup.sh ..."
  # Try to make executable, but don't fail if it's read-only
  chmod +x /app/pod-setup.sh 2>/dev/null || echo "[entrypoint] Note: pod-setup.sh is read-only (expected for mounted volumes)"
  /app/pod-setup.sh
else
  echo "[entrypoint] No pod-setup.sh found. Skipping runtime setup."
fi

# Start the agent daemon
echo "[entrypoint] Starting agent daemon..."
exec python3 /app/agent_daemon.py
