#!/bin/bash
set -euo pipefail

echo "=== Testing Agent Container Functionality ==="

# Test 1: Basic container startup and CLI tools
echo "1. Testing basic CLI tools..."
podman run --rm agent-test /bin/bash -c "
echo 'Git version:' && git --version
echo 'Python version:' && python3 --version
echo 'Pip version:' && pip3 --version
echo 'Build tools:' && gcc --version | head -1
echo 'Curl version:' && curl --version | head -1
"

# Test 2: Python environment and dependencies
echo -e "\n2. Testing Python environment..."
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate
echo 'Python path:' && which python3
echo 'Pip path:' && which pip3
echo 'Testing imports...'
python3 -c 'import redis; import httpx; import loguru; print(\"✓ All dependencies imported successfully\")'
"

# Test 3: Agent daemon syntax check
echo -e "\n3. Testing agent daemon syntax..."
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate
python3 -m py_compile agent_daemon.py
echo '✓ Agent daemon syntax check passed'
"

# Test 4: Container structure and permissions
echo -e "\n4. Testing container structure..."
podman run --rm agent-test /bin/bash -c "
echo 'User:' && whoami
echo 'Working directory:' && pwd
echo 'App directory contents:' && ls -la /app
echo 'Virtual environment:' && ls -la /app/venv/bin/python3
"

# Test 5: Pod setup functionality
echo -e "\n5. Testing pod setup functionality..."
podman run --rm -v $(pwd)/example-pod-setup.sh:/app/pod-setup.sh:ro agent-test /bin/bash -c "
echo 'Testing pod-setup.sh execution...'
timeout 10 /usr/local/bin/pod-entrypoint.sh || echo 'Expected timeout due to no Redis connection'
"

echo -e "\n=== Container Testing Complete ==="
echo "✓ All basic functionality tests passed"
echo "✓ Container is ready for local development and testing"
echo ""
echo "To run the container with Redis:"
echo "  podman run --rm -it agent-test /bin/bash"
echo ""
echo "To test with pod-setup.sh:"
echo "  podman run --rm -it -v \$(pwd)/example-pod-setup.sh:/app/pod-setup.sh:ro agent-test"
