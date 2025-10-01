#!/bin/bash
set -e

echo "Starting MCP server with PID $$"
echo "Environment:"
echo "  POD_TOKEN: ${POD_TOKEN}"
echo "  API_BASE_URL: ${API_BASE_URL}"
echo "  API_TIMEOUT_S: ${API_TIMEOUT_S}"

cd /app
echo "Current directory: $(pwd)"
echo "Python executable: $(which python)"
echo "Virtual env Python: $(ls -la .venv/bin/python)"
echo "About to run Python command..."

.venv/bin/python --version
echo "Python version check successful"

.venv/bin/python -c "print('Basic Python test successful')"
echo "Basic Python test successful"

.venv/bin/python -c "import sys; print('Python path:', sys.path)"
echo "Python path check successful"

.venv/bin/python -c "import src.cage.mcp; print('MCP package imported successfully')"
echo "MCP package import successful"

.venv/bin/python -c "import src.cage.mcp.settings; print('MCP settings imported successfully')"
echo "MCP settings import successful"

.venv/bin/python -c "import httpx; print('httpx imported successfully')"
echo "httpx import successful"

echo "Trying to install required dependencies with system pip..."
pip3 install pydantic fastapi starlette uvicorn httpx mcp
echo "Dependencies install completed"

python3 -c "import pydantic; print('pydantic imported successfully with system Python')"
echo "pydantic import successful with system Python"

python3 -c "import starlette; print('starlette imported successfully with system Python')"
echo "starlette import successful with system Python"

python3 -c "import fastapi; print('fastapi imported successfully with system Python')"
echo "fastapi import successful with system Python"

python3 -c "import mcp.server; print('mcp.server imported successfully with system Python')"
echo "mcp.server import successful with system Python"

python3 -c "import uvicorn; print('uvicorn imported successfully with system Python')"
echo "uvicorn import successful with system Python"

python3 -c "import src.cage.mcp.server; print('MCP server module imported successfully with system Python')"
echo "MCP server module import successful with system Python"

echo "About to start MCP server with system Python..."
exec python3 -m src.cage.mcp.server --host 0.0.0.0 --port 8765
