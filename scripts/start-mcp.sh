#!/bin/bash
set -euo pipefail

log() {
  printf '%s\n' "$*"
}

log "Starting MCP server with PID $$"
log "Environment:"
log "  POD_TOKEN: ${POD_TOKEN:-<unset>}"
log "  API_BASE_URL: ${API_BASE_URL:-<unset>}"
log "  API_TIMEOUT_S: ${API_TIMEOUT_S:-<unset>}"
log "  DEBUGPY_ENABLED: ${DEBUGPY_ENABLED:-0}"
log "  DEBUGPY_WAIT_FOR_CLIENT: ${DEBUGPY_WAIT_FOR_CLIENT:-0}"

cd /app
log "Current directory: $(pwd)"

# Use uv run instead of direct venv python to handle dependencies
log "Python executable: $(which python || echo 'python not set')"

uv run python --version
uv run python -c "print('Basic Python test successful')"
uv run python -c "import sys; print('Python path:', sys.path)"
uv run python -c "import src.cage.mcp; print('MCP package imported successfully')"
uv run python -c "import src.cage.mcp.settings; print('MCP settings imported successfully')"
uv run python -c "import httpx; print('httpx imported successfully')"

HOST=${MCP_HOST:-0.0.0.0}
PORT=${MCP_PORT:-8765}

if [[ "${DEBUGPY_ENABLED:-0}" == "1" ]]; then
  log "Starting under debugpy on 0.0.0.0:5679 (wait=${DEBUGPY_WAIT_FOR_CLIENT:-0})"
  if [[ "${DEBUGPY_WAIT_FOR_CLIENT:-0}" == "1" ]]; then
    exec uv run python -m debugpy --listen 0.0.0.0:5679 --wait-for-client -m src.cage.mcp.server --host "$HOST" --port "$PORT"
  else
    exec uv run python -m debugpy --listen 0.0.0.0:5679 -m src.cage.mcp.server --host "$HOST" --port "$PORT"
  fi
else
  log "About to start MCP server on ${HOST}:${PORT}"
  exec uv run python -m src.cage.mcp.server --host "$HOST" --port "$PORT"
fi
