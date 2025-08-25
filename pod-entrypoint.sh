#!/usr/bin/env bash
set -euo pipefail

# Show Cursor CLI status if installed
if command -v cursor-agent >/dev/null 2>&1; then
  echo "[entrypoint] Cursor CLI version: $(cursor-agent --version || true)"
else
  echo "[entrypoint][WARN] Cursor CLI not found on PATH"
fi

# Optional repo/pod specific setup
if [[ -f "/app/pod-setup.sh" ]]; then
  echo "[entrypoint] Running pod-setup.sh ..."
  # Try to make executable, but don't fail if it's read-only
  chmod +x /app/pod-setup.sh 2>/dev/null || echo "[entrypoint] Note: pod-setup.sh is read-only (expected for mounted volumes)"
  /app/pod-setup.sh
else
  echo "[entrypoint] No pod-setup.sh found. Skipping runtime setup."
fi

# Start supervisor to manage background processes
echo "[entrypoint] Starting supervisor to manage background processes..."
exec /app/venv/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
