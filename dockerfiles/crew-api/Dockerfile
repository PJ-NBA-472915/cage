# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Copy dependency files for better caching
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies with UV
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/

# Create logs directory
RUN mkdir -p logs

# Set build arguments for Git configuration
ARG GIT_EMAIL=cage-agent@example.com
ARG GIT_NAME="Cage Agent"

# Configure Git for the container using build arguments
RUN git config --global user.email "${GIT_EMAIL}" && \
    git config --global user.name "${GIT_NAME}"

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "src.apps.crew_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
