#!/bin/bash
# Start Cage service with isolated repository

if [ $# -eq 0 ]; then
    echo "Usage: $0 <repository-path>"
    echo "Example: $0 .scratchpad/note-app-test"
    exit 1
fi

REPO_PATH="$1"
FULL_REPO_PATH="$(pwd)/$REPO_PATH"

# Validate repository exists and is a git repo
if [ ! -d "$FULL_REPO_PATH" ]; then
    echo "Error: Repository path does not exist: $FULL_REPO_PATH"
    exit 1
fi

if [ ! -d "$FULL_REPO_PATH/.git" ]; then
    echo "Error: Not a Git repository: $FULL_REPO_PATH"
    exit 1
fi

echo "Starting Cage service with isolated repository: $FULL_REPO_PATH"

# Set environment variables for isolated repository
export REPO_PATH="$FULL_REPO_PATH"
export POD_TOKEN="EQmjYQJJRRF4TQo3QgXn8CyQMAYrEhbz"
export POD_ID="isolated-test"

# Start the API service
cd /Users/mother/Git/nebula/cage
source venv/bin/activate
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
