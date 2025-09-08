FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV REPO_PATH=/work/repo
ENV POD_ID=dev-pod
ENV POD_TOKEN=dev-token

# Create work directory
RUN mkdir -p /work/repo

# Expose port
EXPOSE 8000

# Run the API service
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]