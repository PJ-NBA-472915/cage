# Git API Service Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8002

# Create non-root user
RUN groupadd -r worker && useradd -r -g worker worker

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files for better caching
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies with UV
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/repos && \
    chown -R worker:worker /app

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["python", "-m", "src.apps.git_api.main"]
