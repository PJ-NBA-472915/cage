# Lock API Service Dockerfile with Golang support
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8004
ENV GO_VERSION=1.21.5
ENV GOPATH=/go
ENV GOROOT=/usr/local/go
ENV PATH=$GOROOT/bin:$GOPATH/bin:$PATH

# Create non-root user
RUN groupadd -r worker && useradd -r -g worker worker

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Golang
RUN wget -O go.tar.gz "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz

# Verify Go installation
RUN go version

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/generated /app/templates /go/src /go/bin /go/pkg && \
    chown -R worker:worker /app /go

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["python", "-m", "src.services.lock_api.main"]
