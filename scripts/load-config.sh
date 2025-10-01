#!/bin/bash
# Configuration loader script for Cage Pod
# Loads environment-specific configuration files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
CONFIG_DIR="config"
VERBOSE=false
VALIDATE=false

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Configuration loader for Cage Pod"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment (development, testing, production)"
    echo "  -c, --config-dir DIR     Configuration directory (default: config)"
    echo "  -v, --verbose            Verbose output"
    echo "  --validate               Validate configuration only"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Load development config"
    echo "  $0 -e production                     # Load production config"
    echo "  $0 -e testing --validate             # Validate testing config"
    echo "  $0 -v -e production                  # Load production config with verbose output"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --validate)
            VALIDATE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Check if config directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${RED}Error: Configuration directory '$CONFIG_DIR' not found${NC}"
    exit 1
fi

# Check if environment config file exists
CONFIG_FILE="$CONFIG_DIR/$ENVIRONMENT.env"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file '$CONFIG_FILE' not found${NC}"
    echo "Available environments:"
    ls -1 "$CONFIG_DIR"/*.env 2>/dev/null | sed 's/.*\///' | sed 's/\.env$//' || echo "  No .env files found"
    exit 1
fi

echo -e "${BLUE}🔧 Cage Configuration Loader${NC}"
echo "================================"

if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Configuration:${NC}"
    echo "  Environment: $ENVIRONMENT"
    echo "  Config Directory: $CONFIG_DIR"
    echo "  Config File: $CONFIG_FILE"
    echo "  Validate Only: $VALIDATE"
    echo ""
fi

# Load environment variables from config file
echo -e "${BLUE}📁 Loading configuration from $CONFIG_FILE...${NC}"

# Export environment variables from config file
set -a  # automatically export all variables
source "$CONFIG_FILE"
set +a  # stop automatically exporting

# Set environment variable for the application
export ENVIRONMENT="$ENVIRONMENT"

if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Environment variables loaded:${NC}"
    grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | while read -r line; do
        if [[ $line == *"="* ]]; then
            key=$(echo "$line" | cut -d'=' -f1)
            echo "  $key=${!key}"
        fi
    done
    echo ""
fi

if [ "$VALIDATE" = true ]; then
    echo -e "${BLUE}🔍 Validating configuration...${NC}"

    # Check if uv is available
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Error: uv is not installed. Please install uv first:${NC}"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Validate using Python
    if uv run python -c "
import sys
sys.path.insert(0, 'src')
from cage.config import get_config_manager

try:
    manager = get_config_manager('$ENVIRONMENT')
    manager.validate_config()
    print('✅ Configuration is valid')
except Exception as e:
    print(f'❌ Configuration validation failed: {e}')
    sys.exit(1)
"; then
        echo -e "${GREEN}✅ Configuration validation passed!${NC}"
    else
        echo -e "${RED}❌ Configuration validation failed!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Configuration loaded successfully!${NC}"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Repository Path: ${REPO_PATH:-'Not set'}"
    echo "Pod Token: ${POD_TOKEN:0:10}..."  # Show only first 10 chars for security
    echo ""
    echo "To use this configuration in your application:"
    echo "  export ENVIRONMENT=$ENVIRONMENT"
    echo "  # Or run your application with the loaded environment"
fi
