# MCP Server Dockerfile
FROM python:3.12-slim

# Ensure python output is not buffered and bytecode isn't written to disk
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies required for builds and runtime
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files for reproducible installs
COPY pyproject.toml uv.lock README.md ./

# Create virtual environment with uv (honours uv.lock)
RUN uv sync --frozen

# Copy application source and scripts
COPY src ./src
COPY scripts ./scripts

# Ensure entrypoint script is executable
RUN chmod +x ./scripts/start-mcp.sh

# Expose MCP ports
EXPOSE 8765
EXPOSE 5679

# Entrypoint uses existing start script
CMD ["/app/scripts/start-mcp.sh"]
