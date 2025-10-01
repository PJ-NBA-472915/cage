# Dockerfiles Directory

This directory contains Docker configuration files for the Cage project services.

## Naming Convention

Each service has its own subdirectory with a `Dockerfile`:

```
dockerfiles/
├── api/           # Main API service
│   └── Dockerfile
├── files-api/     # File operations service
│   └── Dockerfile
├── git-api/       # Git operations service
│   └── Dockerfile
├── lock-api/      # Code generation service
│   └── Dockerfile
├── mcp/           # MCP server
│   └── Dockerfile
└── rag-api/       # RAG service
    └── Dockerfile
```

## Why This Structure?

- **Clear organization**: Each service has its own directory
- **No confusion**: Files are clearly named `Dockerfile` instead of ambiguous names like `api` or `mcp`
- **Consistent**: All services follow the same pattern
- **Extensible**: Easy to add additional files (like `.dockerignore`) per service

## Adding New Services

When adding a new service:

1. Create a new directory: `dockerfiles/new-service/`
2. Add a `Dockerfile` inside: `dockerfiles/new-service/Dockerfile`
3. Update `docker-compose.yml` to reference: `dockerfile: dockerfiles/new-service/Dockerfile`

## Docker Compose References

Services reference their Dockerfiles like this:

```yaml
services:
  my-service:
    build:
      context: .
      dockerfile: dockerfiles/my-service/Dockerfile
```
