#!/bin/bash
set -euo pipefail

echo "=== Testing Cursor CLI Integration ==="

# Check if CURSOR_API_KEY is set
if [ -z "${CURSOR_API_KEY:-}" ]; then
    echo "Error: CURSOR_API_KEY environment variable is required"
    echo "Please set it with: export CURSOR_API_KEY='your-api-key-here'"
    exit 1
fi

echo "✓ CURSOR_API_KEY is set"

# Test 1: Basic container with Cursor CLI
echo -e "\n1. Testing Cursor CLI installation..."
podman run --rm agent-test /bin/bash -c "
echo 'Cursor CLI version:' && cursor --version
echo 'Cursor CLI path:' && which cursor
"

# Test 2: Container with arguments (dry run)
echo -e "\n2. Testing argument parsing..."
podman run --rm agent-test /usr/local/bin/pod-entrypoint.sh /test/repo "test request" || echo "Expected error: repo path doesn't exist"

# Test 3: Container with mounted repo and actual request
echo -e "\n3. Testing with actual repo and Cursor CLI request..."
echo "Creating test repo with poem.txt..."
mkdir -p .scatchpad/test-1
echo "Old poem content" > .scatchpad/test-1/poem.txt

echo "Running container with repo path and CLI request..."
podman run --rm \
  -e CURSOR_API_KEY="$CURSOR_API_KEY" \
  -v "$(pwd)/.scatchpad/test-1:/app/repo:rw" \
  agent-test \
  /usr/local/bin/pod-entrypoint.sh /app/repo "please adjust poem.txt to contain a poem about pancakes"

echo -e "\n4. Checking results..."
echo "Poem.txt content after Cursor CLI processing:"
cat .scatchpad/test-1/poem.txt

echo -e "\n=== Test Complete ==="
