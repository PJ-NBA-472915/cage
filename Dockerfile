# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY tasks/ ./tasks/
COPY memory-bank/ ./memory-bank/

# Create logs directory
RUN mkdir -p logs

# Set build arguments for Git configuration
ARG GIT_EMAIL=cage-agent@example.com
ARG GIT_NAME="Cage Agent"

# Set environment variables
ENV PYTHONPATH=/app
ENV REPO_PATH=/app
ENV POD_TOKEN=dev-token
ENV DATABASE_URL=postgresql://postgres:password@postgres:5432/cage
ENV REDIS_URL=redis://redis:6379

# Configure Git for the container using build arguments
RUN git config --global user.email "${GIT_EMAIL}" && \
    git config --global user.name "${GIT_NAME}"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
