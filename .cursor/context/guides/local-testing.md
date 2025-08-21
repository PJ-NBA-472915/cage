# Local Network Testing Guide

This guide explains how to test the agent pod network locally before deploying to Fly.io.

## 🎯 What We're Testing

The local network setup simulates the Fly.io per-user dev environments architecture:

- **Router Service**: Handles routing between agent pods (port 8080)
- **Agent Pods**: Individual agent instances (Alice on 8081, Bob on 8082)
- **Test Client**: Validates network connectivity between all services
- **Custom Network**: Isolated bridge network for inter-container communication

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Ensure you have docker-compose installed
docker-compose --version

# Set your Gemini API key (optional for local testing)
export GEMINI_API_KEY="your-actual-key-here"
```

### 2. Run Local Network Test

```bash
# Execute the automated test script
./test-local-network.sh
```

This script will:
- Build the agent base image
- Start all services (router, agent-alice, agent-bob)
- Run connectivity tests
- Display service logs
- Show service endpoints

### 3. Manual Testing

```bash
# Start services in background
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Test specific service
curl http://localhost:8080  # Router
curl http://localhost:8081  # Agent Alice
curl http://localhost:8082  # Agent Bob

# Stop services
docker-compose -f docker-compose.local.yml down
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Test Client   │    │   Router        │    │   Agent Alice   │
│                 │    │   (Port 8080)   │    │   (Port 8081)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Agent Bob     │
                    │   (Port 8082)   │
                    └─────────────────┘
```

## 🔧 Service Configuration

### Router Service
- **Purpose**: Central routing and service discovery
- **Port**: 8080 (external), 8080 (internal)
- **Setup**: Installs aiohttp, creates routing configuration
- **Function**: Maps subdomains to agent pod locations

### Agent Pods
- **Alice**: Port 8081 external, 8080 internal
- **Bob**: Port 8082 external, 8080 internal
- **Setup**: Uses example-pod-setup.sh for tooling
- **Function**: Run agent daemon with heartbeat

### Test Client
- **Purpose**: Validate network connectivity
- **Setup**: Installs testing tools, creates test scripts
- **Function**: Tests TCP and HTTP connectivity between all services

## 🧪 Testing Scenarios

### 1. Basic Connectivity
- ✅ All services start successfully
- ✅ Inter-container communication works
- ✅ External port mapping functions

### 2. Network Isolation
- ✅ Services can communicate within the custom network
- ✅ External access works through mapped ports
- ✅ No cross-talk between unrelated services

### 3. Service Discovery
- ✅ Router can locate agent pods
- ✅ Agent pods register with router
- ✅ Test client can discover all services

### 4. Health Monitoring
- ✅ Heartbeat logs from agent pods
- ✅ Router health status
- ✅ Network connectivity validation

## 📊 Expected Results

When running `./test-local-network.sh`, you should see:

```
🚀 Starting Local Agent Pod Network Testing
==========================================
🔑 Using API key: test-key...
🔨 Building agent base image...
🚀 Starting local agent pod network...
⏳ Waiting for services to be ready...
📋 Running containers:
🧪 Testing network connectivity...
✅ router: TCP connection successful to router:8080
✅ agent-alice: TCP connection successful to agent-alice:8080
✅ agent-bob: TCP connection successful to agent-bob:8080
✅ router: HTTP 200 - http://router:8080
✅ agent-alice: HTTP 200 - http://agent-alice:8080
✅ agent-bob: HTTP 200 - http://agent-bob:8080
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the ports
   lsof -i :8080,8081,8082
   
   # Kill conflicting processes
   docker-compose -f docker-compose.local.yml down
   ```

2. **Container Build Failures**
   ```bash
   # Clean build
   docker-compose -f docker-compose.local.yml build --no-cache
   ```

3. **Network Connectivity Issues**
   ```bash
   # Inspect network
   docker network ls
   docker network inspect cage_agent-network
   
   # Check container logs
   docker-compose -f docker-compose.local.yml logs
   ```

### Debug Commands

```bash
# Check container status
docker-compose -f docker-compose.local.yml ps

# View specific service logs
docker-compose -f docker-compose.local.yml logs router
docker-compose -f docker-compose.local.yml logs agent-alice
docker-compose -f docker-compose.local.yml logs agent-bob

# Execute commands in running containers
docker-compose -f docker-compose.local.yml exec router bash
docker-compose -f docker-compose.local.yml exec agent-alice bash

# Check network connectivity from within containers
docker-compose -f docker-compose.local.yml exec test-client python3 /app/test_network.py
```

## 🔄 Next Steps After Local Testing

Once local testing passes successfully:

1. **Validate all connectivity tests pass**
2. **Check service logs for any errors**
3. **Verify agent pod heartbeats are working**
4. **Test router service discovery**
5. **Proceed to Fly.io deployment**

## 📚 Related Files

- `docker-compose.local.yml` - Local network configuration
- `router-setup.sh` - Router service setup script
- `test-client-setup.sh` - Test client setup script
- `test-local-network.sh` - Automated testing script
- `example-pod-setup.sh` - Example agent pod setup
- `agent_daemon.py` - Agent daemon implementation

## 🎉 Success Criteria

Local testing is successful when:
- ✅ All services start without errors
- ✅ Network connectivity tests pass
- ✅ Agent pods show heartbeat logs
- ✅ Router can discover agent pods
- ✅ External port access works
- ✅ No network conflicts or errors
