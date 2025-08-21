#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Local Agent Pod Network Testing"
echo "=========================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install it first."
    exit 1
fi

# Set default API key if not provided
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "⚠️  GEMINI_API_KEY not set, using test-key for local testing"
    export GEMINI_API_KEY="test-key"
fi

echo "🔑 Using API key: ${GEMINI_API_KEY:0:10}..."

# Build the base image first
echo "🔨 Building agent base image..."
docker-compose -f docker-compose.local.yml build

# Start the services
echo "🚀 Starting local agent pod network..."
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Show running containers
echo "📋 Running containers:"
docker-compose -f docker-compose.local.yml ps

# Test network connectivity
echo "🧪 Testing network connectivity..."
docker-compose -f docker-compose.local.yml run --rm test-client

# Show logs from all services
echo "📝 Service logs:"
echo "--- Router Logs ---"
docker-compose -f docker-compose.local.yml logs router | tail -10

echo "--- Agent Alice Logs ---"
docker-compose -f docker-compose.local.yml logs agent-alice | tail -10

echo "--- Agent Bob Logs ---"
docker-compose -f docker-compose.local.yml logs agent-bob | tail -10

echo ""
echo "✅ Local network testing completed!"
echo ""
echo "🌐 Services available at:"
echo "   Router:    http://localhost:8080"
echo "   Agent Alice: http://localhost:8081"
echo "   Agent Bob:   http://localhost:8082"
echo ""
echo "📋 To view logs: docker-compose -f docker-compose.local.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.local.yml down"
