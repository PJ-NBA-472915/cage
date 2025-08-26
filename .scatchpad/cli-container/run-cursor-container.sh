#!/bin/bash
#
# Debug script for running cursor-agent CLI in container
#
# Usage: ./run-cursor-container.sh [API_KEY] [QUESTION_FILE]
#
# Example: ./run-cursor-container.sh "your-api-key" ./test.txt
#

set -e

API_KEY="${1:-}"
QUESTION_FILE="${2:-./test.txt}"

if [[ -z "$API_KEY" ]]; then
    echo "Error: API key required as first argument"
    echo "Usage: $0 <api-key> [question-file]"
    echo ""
    echo "To get an API key:"
    echo "1. Sign up at https://cursor.com/"
    echo "2. Go to account settings to generate API key"
    exit 1
fi

if [[ ! -f "$QUESTION_FILE" ]]; then
    echo "Error: Question file '$QUESTION_FILE' not found"
    exit 1
fi

echo "Building cursor debug container..."
cd ../.. && docker build --load -f .scatchpad/cli-container/Dockerfile -t cursor-debug . && cd .scatchpad/cli-container

echo ""
echo "Running cursor-agent CLI with question file: $QUESTION_FILE"
echo "Question: $(cat "$QUESTION_FILE")"
echo ""
echo "Cursor response:"
echo "=================="

# Run the container with API key and mounted file
docker run --rm \
    -v "$(realpath "$QUESTION_FILE"):/app/test.txt" \
    cursor-debug \
    cursor-agent \
    -a "$API_KEY" \
    -p \
    "Please read the file /app/test.txt and answer the question it contains."

echo "=================="
echo "Container test complete!"