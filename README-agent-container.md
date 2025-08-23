# Agent Container - Local Usage Guide

This document describes how to use the Agent-Net agent container locally for development and testing.

## Overview

The agent container is a minimal Ubuntu-based environment that provides:
- Python 3.13 runtime with virtual environment
- Common CLI tools (git, curl, build-essential)
- Agent daemon for Redis Streams communication
- Runtime customization via pod-setup.sh

## Quick Start

### 1. Build the Container

```bash
# Build the agent container
podman build -t agent-test .

# Verify the image was created
podman images agent-test
```

### 2. Test Basic Functionality

```bash
# Run the comprehensive test suite
./test-container.sh

# Or test individual components manually
podman run --rm agent-test /bin/bash -c "git --version && python3 --version"
```

### 3. Run the Container

```bash
# Interactive shell
podman run --rm -it agent-test /bin/bash

# With custom pod setup
podman run --rm -it -v $(pwd)/example-pod-setup.sh:/app/pod-setup.sh:ro agent-test
```

## Container Features

### ✅ **What's Included**
- **Base OS**: Ubuntu 24.04 (questing)
- **Python**: 3.13.6 with virtual environment
- **CLI Tools**: git, curl, build-essential, tini
- **Python Dependencies**: redis, httpx, loguru, pytest suite
- **Security**: Non-root user (app:10001), tini as PID 1

### 🔧 **Runtime Customization**
The container supports runtime customization via `pod-setup.sh`:
- Install additional Python packages
- Configure git settings
- Add system packages
- Set up project-specific tooling

### 📁 **Container Structure**
```
/app/
├── venv/                 # Python virtual environment
├── agent_daemon.py       # Main agent daemon
├── requirements.txt      # Python dependencies
└── pod-setup.sh         # Optional runtime setup (mounted)
```

## Development Workflow

### 1. **Local Development**
```bash
# Start interactive container
podman run --rm -it agent-test /bin/bash

# Activate Python environment
cd /app && source venv/bin/activate

# Install additional packages
pip install your-package

# Test your code
python3 your_script.py
```

### 2. **Testing with Pod Setup**
```bash
# Create custom pod-setup.sh
cat > my-pod-setup.sh << 'EOF'
#!/bin/bash
echo "Installing project-specific tools..."
pip install black ruff mypy
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
EOF

# Run container with custom setup
podman run --rm -it -v $(pwd)/my-pod-setup.sh:/app/pod-setup.sh:ro agent-test
```

### 3. **Testing Agent Daemon**
```bash
# Test daemon syntax (no Redis required)
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate
python3 -m py_compile agent_daemon.py
echo 'Syntax check passed!'
"

# Test daemon startup (will fail without Redis, which is expected)
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate
timeout 5 python3 agent_daemon.py || echo 'Expected timeout - no Redis connection'
"
```

## Environment Variables

The container supports these environment variables:

```bash
# Redis connection (default: redis://localhost:6379)
REDIS_URL=redis://your-redis-host:6379

# Agent identification (auto-generated if not set)
AGENT_ID=my-agent-001

# Heartbeat interval in seconds (default: 10)
HEARTBEAT_INTERVAL=15

# Task timeout in seconds (default: 60)
TASK_TIMEOUT=120
```

## Troubleshooting

### **Container Won't Start**
```bash
# Check container logs
podman logs <container-name>

# Verify image exists
podman images agent-test

# Check for port conflicts
podman ps -a
```

### **Python Import Errors**
```bash
# Verify virtual environment
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate && pip list
"

# Reinstall dependencies if needed
podman run --rm agent-test /bin/bash -c "
cd /app && source venv/bin/activate && pip install -r requirements.txt
"
```

### **Permission Issues**
```bash
# Check user permissions
podman run --rm agent-test /bin/bash -c "whoami && id"

# Verify app directory ownership
podman run --rm agent-test /bin/bash -c "ls -la /app"
```

## Performance Notes

- **Container Size**: ~1.67 GB (includes build tools and full Python environment)
- **Startup Time**: ~2-3 seconds for basic container, ~10-15 seconds with pod-setup.sh
- **Memory Usage**: ~100-200 MB when idle, varies with Python packages installed

## Next Steps

Once you're comfortable with local usage:

1. **Add Redis**: Set up a local Redis instance for full agent functionality
2. **Customize Pod Setup**: Create project-specific pod-setup.sh scripts
3. **Extend Agent**: Modify agent_daemon.py for your specific needs
4. **Production**: Consider Fly.io deployment for production use

## Support

For issues or questions:
1. Check the test output: `./test-container.sh`
2. Review container logs: `podman logs <container-name>`
3. Verify your pod-setup.sh syntax
4. Check Python dependency compatibility

---

**Note**: This container is designed for local development and testing. For production deployment, additional configuration and security measures may be required.
