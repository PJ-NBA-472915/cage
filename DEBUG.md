# Debug Playbook: Isolate and Fix Service Issues

This guide provides step-by-step instructions for debugging individual services in the Cage microservices architecture.

## Service Overview

The Cage system is split into four main API services:

- **files-api** (port 8001): File operations, content management, file locking
- **git-api** (port 8002): Git operations, version control, repository management  
- **rag-api** (port 8003): Retrieval-Augmented Generation, document search, knowledge base
- **lock-api** (port 8004): Code generation, application building, Golang development

## Quick Start Commands

### Start Individual Services

```bash
# Start a single service with its dependencies
docker compose --profile dev up files-api
docker compose --profile dev up git-api
docker compose --profile dev up rag-api
docker compose --profile dev up lock-api

# Start all services
docker compose --profile dev up

# Start legacy monolithic API
docker compose --profile legacy up api
```

### Health Checks

```bash
# Check service health
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8001/health
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8002/health
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8003/health
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8004/health
```

## Debugging Workflow

### 1. Identify the Problem

**Symptoms to look for:**
- Service won't start
- Health check failures
- 500 errors on endpoints
- Slow response times
- Memory/CPU issues

**Quick diagnosis:**
```bash
# Check service status
docker compose ps

# Check logs for errors
docker compose logs <service-name>

# Check resource usage
docker stats
```

### 2. Isolate the Service

**Start only the problematic service:**
```bash
# Example: Debug files-api
docker compose --profile dev up files-api

# Check if it starts cleanly
docker compose logs files-api --follow
```

**Verify dependencies:**
```bash
# Check if required services are healthy
docker compose ps postgres redis

# Test database connectivity
docker compose exec postgres psql -U postgres -d cage -c "SELECT 1;"

# Test Redis connectivity  
docker compose exec redis redis-cli ping
```

### 3. Inspect Service Health

**Check health endpoint:**
```bash
# Test health endpoint
curl -v -H "Authorization: Bearer $POD_TOKEN" http://localhost:8001/health

# Expected response:
{
  "status": "success",
  "service": "files-api",
  "date": "2025-09-27 09:10:00",
  "version": "1.0.0"
}
```

**Check OpenAPI documentation:**
```bash
# View service API docs
open http://localhost:8001/docs  # files-api
open http://localhost:8002/docs  # git-api
open http://localhost:8003/docs  # rag-api
open http://localhost:8004/docs  # lock-api
```

### 4. Test Basic Endpoints

**Files API:**
```bash
# Test file operations
curl -X POST -H "Authorization: Bearer $POD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"operation": "INSERT", "path": "test.txt", "payload": {"content": "test"}}' \
  http://localhost:8001/files/edit
```

**Git API:**
```bash
# Test git status
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8002/git/status
```

**RAG API:**
```bash
# Test RAG query
curl -X POST -H "Authorization: Bearer $POD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}' \
  http://localhost:8003/rag/query
```

**Lock API:**
```bash
# Test Golang version
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8004/lock/go-version

# Test template listing
curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8004/lock/templates
```

### 5. Debug Common Issues

#### Service Won't Start

**Check logs:**
```bash
docker compose logs <service-name> --tail 50
```

**Common causes:**
- Missing environment variables (POD_TOKEN, DATABASE_URL, etc.)
- Port conflicts
- Missing dependencies
- Permission issues
- Invalid configuration

**Solutions:**
```bash
# Check environment variables
docker compose config

# Rebuild service
docker compose build <service-name>

# Start with debug logging
RELOAD=true docker compose --profile dev up <service-name>
```

#### Health Check Failures

**Check health check configuration:**
```bash
# View health check status
docker inspect <container-name> | grep -A 10 Health

# Test health check manually
docker compose exec <service-name> curl -f http://localhost:<port>/health
```

**Common fixes:**
- Increase health check timeout
- Fix health endpoint implementation
- Ensure service is actually ready

#### Database Connection Issues

**Test database connectivity:**
```bash
# Check PostgreSQL
docker compose exec postgres pg_isready -U postgres

# Test connection from service
docker compose exec <service-name> python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@postgres:5432/cage')
    result = await conn.fetchval('SELECT 1')
    print(f'Database test: {result}')
    await conn.close()
asyncio.run(test())
"
```

#### Redis Connection Issues

**Test Redis connectivity:**
```bash
# Check Redis
docker compose exec redis redis-cli ping

# Test connection from service
docker compose exec <service-name> python -c "
import redis
r = redis.from_url('redis://redis:6379')
print(f'Redis test: {r.ping()}')
"
```

### 6. Performance Debugging

**Monitor resource usage:**
```bash
# Real-time stats
docker stats

# Check specific service
docker stats <container-name>

# Monitor logs for performance issues
docker compose logs <service-name> --follow | grep -E "(slow|timeout|error)"
```

**Profile endpoints:**
```bash
# Test endpoint performance
time curl -H "Authorization: Bearer $POD_TOKEN" http://localhost:8001/health

# Use Apache Bench for load testing
ab -n 100 -c 10 -H "Authorization: Bearer $POD_TOKEN" http://localhost:8001/health
```

### 7. Golang Development (Lock API)

**Test Golang toolchain:**
```bash
# Check Go installation
docker compose exec lock-api go version

# Test Go build
docker compose exec lock-api bash -c "
cd /tmp && \
echo 'package main; import \"fmt\"; func main() { fmt.Println(\"Hello\") }' > main.go && \
go mod init test && \
go build main.go && \
./main
"
```

**Debug Go code generation:**
```bash
# Test template generation
curl -X POST -H "Authorization: Bearer $POD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "web-server", "name": "test-app", "variables": {"port": "8080"}}' \
  http://localhost:8004/lock/generate
```

### 8. Log Analysis

**Structured logging:**
```bash
# Follow logs with timestamps
docker compose logs <service-name> --follow --timestamps

# Filter for errors
docker compose logs <service-name> | grep -i error

# Filter for specific requests
docker compose logs <service-name> | grep "correlation_id"
```

**Log aggregation:**
```bash
# Check Loki logs (if logging stack is running)
curl http://localhost:3100/loki/api/v1/query?query={service="<service-name>"}
```

### 9. Recovery Procedures

**Service restart:**
```bash
# Restart specific service
docker compose restart <service-name>

# Force recreate
docker compose up --force-recreate <service-name>

# Clean restart
docker compose down <service-name>
docker compose up <service-name>
```

**Data recovery:**
```bash
# Backup database
docker compose exec postgres pg_dump -U postgres cage > backup.sql

# Restore database
docker compose exec -T postgres psql -U postgres cage < backup.sql
```

### 10. Development Mode

**Enable development features:**
```bash
# Start with code reload
RELOAD=true docker compose --profile dev up

# Start with debugger
DEBUGPY_ENABLED=1 docker compose --profile dev up

# Start with verbose logging
LOG_LEVEL=DEBUG docker compose --profile dev up
```

**Hot reload testing:**
```bash
# Make code changes and verify reload
echo "# Test change" >> src/services/files_api/main.py
# Check logs for reload message
docker compose logs files-api --follow
```

## Troubleshooting Checklist

- [ ] Service starts without errors
- [ ] Health endpoint returns 200
- [ ] Dependencies are healthy
- [ ] Environment variables are set
- [ ] Ports are not conflicted
- [ ] Authentication works
- [ ] Basic endpoints respond
- [ ] Logs show no errors
- [ ] Resource usage is normal
- [ ] Database/Redis connections work

## Emergency Procedures

**Complete system restart:**
```bash
docker compose down
docker compose --profile dev up
```

**Reset to clean state:**
```bash
docker compose down -v
docker system prune -f
docker compose --profile dev up
```

**Access service shell:**
```bash
docker compose exec <service-name> bash
```

## Service-Specific Notes

### Files API
- Depends on: PostgreSQL
- Key endpoints: `/files/edit`, `/files/commit`, `/files/sha`, `/diff`
- Common issues: File permission problems, Git integration

### Git API  
- Depends on: PostgreSQL
- Key endpoints: `/git/status`, `/git/commit`, `/git/push`, `/git/history`
- Common issues: Git repository corruption, authentication problems

### RAG API
- Depends on: PostgreSQL, Redis, OpenAI API
- Key endpoints: `/rag/query`, `/rag/reindex`, `/rag/blobs/{sha}`
- Common issues: Database connection, embedding service failures

### Lock API
- Depends on: PostgreSQL, Golang toolchain
- Key endpoints: `/lock/generate`, `/lock/build`, `/lock/templates`
- Common issues: Go installation, template compilation, build failures

## Getting Help

1. Check service logs first
2. Verify health endpoints
3. Test basic functionality
4. Check dependencies
5. Review this playbook
6. Check GitHub issues
7. Contact the development team
