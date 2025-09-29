# Files API Service Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8001

# Create dedicated user for files API with restricted access
RUN groupadd -r filesapi && useradd -r -g filesapi -s /bin/bash filesapi

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create restricted directory structure
RUN mkdir -p /work/repo /app/logs /app/data && \
    chown -R filesapi:filesapi /work /app && \
    chmod 755 /work && \
    chmod 755 /work/repo && \
    chmod 755 /app && \
    chmod 755 /app/logs

# Ensure the user can only access /work/repo and /app directories
RUN chown root:root / && \
    chmod 755 / && \
    chmod 755 /work

# Switch to restricted user
USER filesapi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["python", "-m", "src.services.files_api.main"]
