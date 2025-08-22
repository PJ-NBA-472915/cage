#!/bin/bash
set -euo pipefail

echo "🧪 Running Cage Platform Tests with Pytest"
echo "=========================================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing testing dependencies..."
    pip install -r requirements.txt
fi

# Set default environment for testing
export GEMINI_API_KEY="${GEMINI_API_KEY:-test-key-for-testing}"
export PYTHONPATH="${PYTHONPATH:-.}:${PYTHONPATH:-}"

echo "🔑 Using API key: ${GEMINI_API_KEY:0:10}..."
echo "🐍 Python path: ${PYTHONPATH}"

# Function to run tests with different configurations
run_test_suite() {
    local suite_name="$1"
    local pytest_args="$2"
    
    echo ""
    echo "🚀 Running $suite_name tests..."
    echo "Command: pytest $pytest_args"
    echo "----------------------------------------"
    
    if pytest $pytest_args; then
        echo "✅ $suite_name tests passed!"
    else
        echo "❌ $suite_name tests failed!"
        return 1
    fi
}

# Run different test suites
echo ""
echo "📋 Available test suites:"
echo "1. Unit tests (fast, isolated)"
echo "2. Integration tests (component interactions)"
echo "3. Functional tests (end-to-end)"
echo "4. All tests with coverage"
echo "5. Quick smoke test"

read -p "Select test suite (1-5) or press Enter for all tests: " choice

case $choice in
    1)
        run_test_suite "Unit" "-m unit -v"
        ;;
    2)
        run_test_suite "Integration" "-m integration -v"
        ;;
    3)
        run_test_suite "Functional" "-m functional -v"
        ;;
    4)
        run_test_suite "All with Coverage" "--cov=. --cov-report=term-missing --cov-report=html -v"
        ;;
    5)
        run_test_suite "Smoke Test" "-m "not slow" --tb=short -v"
        ;;
    *)
        echo ""
        echo "🚀 Running all tests..."
        echo "----------------------------------------"
        
        # Run all tests with coverage
        if pytest --cov=. --cov-report=term-missing --cov-report=html -v; then
            echo ""
            echo "✅ All tests passed!"
            echo ""
            echo "📊 Coverage report generated:"
            echo "   - Terminal: Coverage summary above"
            echo "   - HTML: htmlcov/index.html"
            echo "   - XML: coverage.xml"
        else
            echo ""
            echo "❌ Some tests failed!"
            exit 1
        fi
        ;;
esac

echo ""
echo "🎉 Testing completed!"
echo ""
echo "💡 Tips:"
echo "   - Run 'pytest --help' for more options"
echo "   - Use 'pytest -m unit' for fast unit tests only"
echo "   - Use 'pytest -m "not slow"' to exclude slow tests"
echo "   - Use 'pytest --pdb' to debug failing tests"
echo "   - Use 'pytest -n auto' for parallel test execution"
