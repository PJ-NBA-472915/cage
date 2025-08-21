#!/usr/bin/env bash
set -euo pipefail

# Show Gemini CLI status if installed
if command -v gemini >/dev/null 2>&1; then
  echo "[entrypoint] Gemini CLI version: $(gemini --version || true)"
else
  echo "[entrypoint][WARN] Gemini CLI not found on PATH"
fi

# Optional repo/pod specific setup
if [[ -f "/app/pod-setup.sh" ]]; then
  echo "[entrypoint] Running pod-setup.sh ..."
  chmod +x /app/pod-setup.sh || true
  /app/pod-setup.sh
else
  echo "[entrypoint] No pod-setup.sh found. Skipping runtime setup."
fi

# Start the daemon
exec python3 /app/agent_daemon.py
