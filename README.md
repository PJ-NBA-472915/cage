# Cage Pod

Pod-based Multi-Agent Repository Service

## Overview

Cage is a multi-agent repository service that provides file operations, Git management, RAG (Retrieval-Augmented Generation), and Golang code generation capabilities through a microservices architecture.

## Services

- **Files API** (Port 8001): File operations, content management, and file locking
- **Git API** (Port 8002): Git operations, version control, and repository management  
- **RAG API** (Port 8003): Retrieval-Augmented Generation, document search, and knowledge base operations
- **Lock API** (Port 8004): Code generation, application building, and Golang development

## Quick Start

```bash
# Start all services
make docker-up

# Start specific service
docker-compose up files-api

# Run tests
make test

# Development with hot reload
RELOAD=true docker-compose up files-api
```

## Development

The services are designed to run independently with proper health checks and failure isolation. Each service can be started individually for targeted debugging.

For more information, see the DEBUG.md file for troubleshooting and service-specific debugging procedures.
