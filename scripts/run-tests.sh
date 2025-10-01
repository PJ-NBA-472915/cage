#!/bin/bash
# Test runner script for Cage project
# Provides different test execution modes and configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
PARALLEL=false
COVERAGE=true
VERBOSE=false
MARKERS=""
TIMEOUT=""
OUTPUT=""

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Test runner for Cage project"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: unit, integration, api, cli, smoke, e2e, all (default: all)"
    echo "  -p, --parallel         Run tests in parallel using pytest-xdist"
    echo "  -c, --no-coverage      Disable coverage reporting"
    echo "  -v, --verbose          Verbose output"
    echo "  -m, --markers MARKERS  Additional pytest markers to filter tests"
    echo "  --timeout SECONDS      Set test timeout (default: no timeout)"
    echo "  -o, --output FORMAT    Output format: html, xml, term (default: term)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests with coverage"
    echo "  $0 -t unit                           # Run only unit tests"
    echo "  $0 -t api -p                         # Run API tests in parallel"
    echo "  $0 -m 'not slow'                     # Run all tests except slow ones"
    echo "  $0 -t integration -c                 # Run integration tests without coverage"
    echo "  $0 -t smoke -o html                  # Run smoke tests with HTML coverage report"
    echo ""
    echo "Available test types:"
    echo "  unit        - Fast, isolated unit tests"
    echo "  integration - Tests requiring external services"
    echo "  api         - HTTP API endpoint tests"
    echo "  cli         - Command-line interface tests"
    echo "  smoke       - Basic functionality validation"
    echo "  e2e         - End-to-end workflow tests"
    echo "  all         - All tests (default)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -c|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
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

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed. Please install uv first:${NC}"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${BLUE}🧪 Cage Test Runner${NC}"
echo "=================="

# Build pytest command
PYTEST_CMD="uv run pytest"

# Add test type markers
case $TEST_TYPE in
    unit)
        MARKERS="unit"
        ;;
    integration)
        MARKERS="integration"
        ;;
    api)
        MARKERS="api"
        ;;
    cli)
        MARKERS="cli"
        ;;
    smoke)
        MARKERS="smoke"
        ;;
    e2e)
        MARKERS="e2e"
        ;;
    all)
        # No specific marker for all tests
        ;;
    *)
        echo -e "${RED}Error: Invalid test type '$TEST_TYPE'${NC}"
        echo "Valid types: unit, integration, api, cli, smoke, e2e, all"
        exit 1
        ;;
esac

# Add markers to command
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add coverage options
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing"

    # Add output format for coverage
    case $OUTPUT in
        html)
            PYTEST_CMD="$PYTEST_CMD --cov-report=html:htmlcov"
            ;;
        xml)
            PYTEST_CMD="$PYTEST_CMD --cov-report=xml:coverage.xml"
            ;;
        term|"")
            # Default term output already included
            ;;
        *)
            echo -e "${YELLOW}Warning: Unknown output format '$OUTPUT', using default${NC}"
            ;;
    esac
else
    PYTEST_CMD="$PYTEST_CMD --no-cov"
fi

# Add verbose output
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add timeout
if [ -n "$TIMEOUT" ]; then
    PYTEST_CMD="$PYTEST_CMD --timeout=$TIMEOUT"
fi

# Display configuration
echo -e "${BLUE}Configuration:${NC}"
echo "  Test Type: $TEST_TYPE"
echo "  Parallel: $PARALLEL"
echo "  Coverage: $COVERAGE"
echo "  Verbose: $VERBOSE"
if [ -n "$MARKERS" ]; then
    echo "  Markers: $MARKERS"
fi
if [ -n "$TIMEOUT" ]; then
    echo "  Timeout: ${TIMEOUT}s"
fi
if [ -n "$OUTPUT" ]; then
    echo "  Output: $OUTPUT"
fi
echo ""

# Install dependencies if needed
echo -e "${BLUE}📦 Installing dependencies...${NC}"
uv sync --extra dev

# Run tests
echo -e "${BLUE}🚀 Running tests...${NC}"
echo "Command: $PYTEST_CMD"
echo ""

# Execute the command
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"

    if [ "$COVERAGE" = true ] && [ "$OUTPUT" = "html" ]; then
        echo -e "${BLUE}📊 Coverage report generated: htmlcov/index.html${NC}"
    elif [ "$COVERAGE" = true ] && [ "$OUTPUT" = "xml" ]; then
        echo -e "${BLUE}📊 Coverage report generated: coverage.xml${NC}"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
