#!/usr/bin/env bash
set -euo pipefail

echo "[router-setup] Installing router-specific tools..."

# Install additional tools for routing
pip3 install --no-cache-dir aiohttp asyncio

# Create router configuration
cat > /app/router_config.py << 'EOF'
"""
Router configuration for local agent pod testing.
"""
import os
from typing import Dict, Optional

# Agent pod mappings (in production, this would come from a database)
AGENT_PODS = {
    "alice": {
        "host": "agent-alice",
        "port": 8080,
        "name": "Alice"
    },
    "bob": {
        "host": "agent-bob", 
        "port": 8080,
        "name": "Bob"
    }
}

def get_agent_pod(subdomain: str) -> Optional[Dict]:
    """Get agent pod configuration by subdomain."""
    return AGENT_PODS.get(subdomain)

def list_agent_pods() -> Dict:
    """List all available agent pods."""
    return AGENT_PODS
EOF

echo "[router-setup] Router configuration created."
echo "[router-setup] Done."
