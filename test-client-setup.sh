#!/usr/bin/env bash
set -euo pipefail

echo "[test-client-setup] Installing test client tools..."

# Install additional tools for testing
pip3 install --no-cache-dir aiohttp asyncio requests

# Create test network script
cat > /app/test_network.py << 'EOF'
"""
Test client to verify network connectivity between agent pods.
"""
import asyncio
import aiohttp
import requests
import os
from loguru import logger

async def test_http_connectivity():
    """Test HTTP connectivity to all services."""
    services = [
        ("router", "http://router:8080"),
        ("agent-alice", "http://agent-alice:8080"), 
        ("agent-bob", "http://agent-bob:8080")
    ]
    
    async with aiohttp.ClientSession() as session:
        for name, url in services:
            try:
                async with session.get(url) as response:
                    logger.info(f"✅ {name}: HTTP {response.status} - {url}")
            except Exception as e:
                logger.error(f"❌ {name}: Failed to connect - {e}")

def test_tcp_connectivity():
    """Test TCP connectivity to all services."""
    import socket
    
    services = [
        ("router", "router", 8080),
        ("agent-alice", "agent-alice", 8080),
        ("agent-bob", "agent-bob", 8080)
    ]
    
    for name, host, port in services:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ {name}: TCP connection successful to {host}:{port}")
            else:
                logger.error(f"❌ {name}: TCP connection failed to {host}:{port}")
        except Exception as e:
            logger.error(f"❌ {name}: TCP test error - {e}")

async def main():
    """Run all connectivity tests."""
    logger.info("Starting network connectivity tests...")
    
    # Test TCP connectivity
    test_tcp_connectivity()
    
    # Test HTTP connectivity
    await test_http_connectivity()
    
    logger.info("Network connectivity tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
EOF

echo "[test-client-setup] Test network script created."
echo "[test-client-setup] Done."
