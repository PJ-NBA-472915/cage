#!/bin/bash
# Pull bge-code-v1 model for Ollama

set -e

MODEL="${OLLAMA_MODEL:-mahonzhan/bge-code-v1}"
OLLAMA_SERVICE="${OLLAMA_SERVICE:-ollama}"

echo "Pulling Ollama model: $MODEL"
docker compose exec "$OLLAMA_SERVICE" ollama pull "$MODEL"

if [ $? -eq 0 ]; then
    echo "✓ Model $MODEL pulled successfully"
    echo "Restart rag-api service to use the new model:"
    echo "  docker compose restart rag-api"
else
    echo "✗ Failed to pull model $MODEL"
    exit 1
fi
