# syntax=docker/dockerfile:1.4
# Consolidated multi-stage Dockerfile for Cage microservices
# Uses BuildKit features for improved caching and build performance

# ==============================================================================
# Base Python Stage - Common system dependencies and UV installation
# ==============================================================================
FROM python:3.12-slim AS base-python

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV for dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# ==============================================================================
# Builder Stage - Install Python dependencies with cache mounts
# ==============================================================================
FROM base-python AS builder

# Copy dependency files for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies with BuildKit cache mount for uv cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# ==============================================================================
# Runtime Base - Runtime environment with debug tools
# ==============================================================================
FROM base-python AS runtime-base

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src ./src
COPY scripts ./scripts
COPY README.md ./

# Install debug tools (debugpy for remote debugging)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install debugpy

# Create cage group and users with proper permissions
RUN groupadd -r cage && \
    useradd -r -g cage worker && \
    useradd -r -g cage system && \
    mkdir -p /app/logs /work/repo /home/worker/.cache/uv /home/system/.cache/uv && \
    chown -R worker:cage /work/repo /home/worker && \
    chown -R system:cage /home/system && \
    chgrp cage /app/logs && \
    chmod 775 /app/logs && \
    chmod 750 /work/repo && \
    # Make app directory writable by cage group for uv operations \
    chgrp -R cage /app && \
    chmod -R g+w /app

# ==============================================================================
# Files API Service
# ==============================================================================
FROM runtime-base AS files-api

# Files API runs as worker user (has repo write access)
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.apps.files_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Git API Service
# ==============================================================================
FROM runtime-base AS git-api

# Configure Git for the container
ARG GIT_EMAIL=cage-agent@example.com
ARG GIT_NAME="Cage Agent"
RUN git config --global user.email "${GIT_EMAIL}" && \
    git config --global user.name "${GIT_NAME}"

# Git API runs as worker user (has repo write access)
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.apps.git_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# RAG API Service
# ==============================================================================
FROM runtime-base AS rag-api

# RAG API runs as worker user (has repo write access)
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.apps.rag_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Lock API Service (with Golang support)
# ==============================================================================
FROM runtime-base AS lock-api

# Install Golang
ENV GO_VERSION=1.21.5 \
    GOPATH=/go \
    GOROOT=/usr/local/go \
    PATH=/usr/local/go/bin:/go/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && wget -O go.tar.gz "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz \
    && rm -rf /var/lib/apt/lists/*

# Configure Go
RUN go version && \
    go env -w GO111MODULE=on && \
    go env -w GOPROXY=https://proxy.golang.org,direct && \
    go env -w GOSUMDB=sum.golang.org

# Create Go directories and set permissions
RUN mkdir -p /app/logs /app/generated /app/templates /go/src /go/bin /go/pkg && \
    chown -R worker:cage /app /go

# Lock API runs as worker user (has repo write access)
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.apps.lock_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Crew API Service
# ==============================================================================
FROM runtime-base AS crew-api

# Install PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Configure Git for the container
ARG GIT_EMAIL=cage-agent@example.com
ARG GIT_NAME="Cage Agent"
RUN git config --global user.email "${GIT_EMAIL}" && \
    git config --global user.name "${GIT_NAME}"

# Crew API runs as worker user (has repo write access)
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.apps.crew_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# MCP Server Service
# ==============================================================================
FROM runtime-base AS mcp

# Ensure entrypoint script is executable
RUN chmod +x ./scripts/start-mcp.sh

# MCP service runs as system user (read-only access to /app, no repo access)
USER system

EXPOSE 8765 5679

CMD ["/app/scripts/start-mcp.sh"]
