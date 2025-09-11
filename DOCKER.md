# Cage Docker Setup

This document describes how to run the Cage system using Docker containers.

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key (for RAG functionality)

## Quick Start

1. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Check service status:**
   ```bash
   docker-compose ps
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f cage-api
   ```

## Services

### PostgreSQL Database
- **Port:** 5432
- **Database:** cage
- **User:** postgres
- **Password:** password
- **Extensions:** pgvector for vector embeddings

### Redis Cache
- **Port:** 6379
- **Purpose:** Hot indexes and session management

### Cage API
- **Port:** 8000
- **Purpose:** Main API service with RAG functionality
- **Health Check:** http://localhost:8000/health

### Cage MCP Server
- **Purpose:** MCP server for external AI tool integration
- **Protocol:** Model Context Protocol (MCP)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key for embeddings |
| `DATABASE_URL` | postgresql://postgres:password@postgres:5432/cage | PostgreSQL connection string |
| `REDIS_URL` | redis://redis:6379 | Redis connection string |
| `POD_TOKEN` | dev-token | API authentication token |

## Testing

### Test RAG System
```bash
# Run inside the container
docker-compose exec cage-api python scripts/test-rag-system.py

# Or run locally (requires local PostgreSQL and Redis)
python scripts/test-rag-system.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# RAG query (requires authentication)
curl -X POST http://localhost:8000/rag/query \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world function", "top_k": 5}'

# Reindex repository
curl -X POST http://localhost:8000/rag/reindex \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"scope": "all"}'
```

## Development

### Rebuild containers
```bash
docker-compose build --no-cache
docker-compose up -d
```

### View database
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d cage

# List tables
\dt

# Check embeddings
SELECT COUNT(*) FROM embeddings;
```

### View Redis
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# List keys
KEYS *

# Check pending blobs
SMEMBERS rag:pending_blobs
```

## Troubleshooting

### Common Issues

1. **Database connection failed:**
   - Check if PostgreSQL container is running: `docker-compose ps`
   - Check logs: `docker-compose logs postgres`

2. **Redis connection failed:**
   - Check if Redis container is running: `docker-compose ps`
   - Check logs: `docker-compose logs redis`

3. **RAG service not available:**
   - Check if OPENAI_API_KEY is set
   - Check API logs: `docker-compose logs cage-api`

4. **MCP server not working:**
   - Check MCP server logs: `docker-compose logs cage-mcp`
   - Ensure database and Redis are healthy

### Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

## Production Considerations

For production deployment:

1. **Security:**
   - Change default passwords
   - Use proper secrets management
   - Configure proper CORS settings

2. **Performance:**
   - Adjust PostgreSQL connection pool settings
   - Configure Redis memory limits
   - Set up proper monitoring

3. **Persistence:**
   - Use named volumes for data persistence
   - Set up regular backups
   - Configure log rotation

4. **Scaling:**
   - Use external PostgreSQL and Redis services
   - Consider horizontal scaling for API service
   - Implement load balancing
