# Testing Guide for Cage System

This document provides comprehensive guidance for testing the Cage system, covering both Phase 1 (Task Manager) and Phase 2 (Editor Tool) components.

## Overview

The Cage system includes a comprehensive test suite built with pytest that covers:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component interaction testing
- **API Tests**: REST API endpoint testing
- **CLI Tests**: Command-line interface testing
- **Performance Tests**: System performance and scalability testing

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── run_tests.py                   # Test runner script
├── unit/                          # Unit tests
│   ├── test_task_models.py        # Task Manager unit tests
│   └── test_editor_tool.py        # Editor Tool unit tests
├── api/                           # API tests
│   └── test_api_endpoints.py      # REST API endpoint tests
├── cli/                           # CLI tests
│   └── test_cli_commands.py       # Command-line interface tests
└── integration/                   # Integration tests
    └── test_system_integration.py # Cross-component integration tests
```

## Quick Start

### Install Test Dependencies

```bash
# Install test dependencies
make test-deps

# Or manually
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Run all tests
make test

# Or with custom options
python tests/run_tests.py all -v --coverage
```

### Run Specific Test Types

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# API tests only
make test-api

# CLI tests only
make test-cli
```

## Test Categories

### Unit Tests

Unit tests focus on individual components and classes:

#### Task Manager Unit Tests (`tests/unit/test_task_models.py`)

- **TaskFile Model Tests**: Data model validation and serialization
- **TaskManager Tests**: CRUD operations, validation, status generation
- **Data Model Tests**: All supporting models (TaskCriteria, TaskTodoItem, etc.)

**Key Test Areas:**
- Model validation with valid and invalid data
- JSON serialization/deserialization
- Progress calculation from todo items
- Schema validation and error handling
- File operations (load, save, list)

#### Editor Tool Unit Tests (`tests/unit/test_editor_tool.py`)

- **FileOperation Tests**: Operation request model validation
- **FileLockManager Tests**: Lock acquisition, release, expiration
- **EditorTool Tests**: All file operations (GET, INSERT, UPDATE, DELETE)
- **Selector Tests**: Region and regex selector functionality

**Key Test Areas:**
- File operations with different selectors
- Lock management and concurrency
- Error handling and edge cases
- Content validation and diff generation
- Dry run functionality

### API Tests

API tests verify REST endpoint functionality:

#### API Endpoint Tests (`tests/api/test_api_endpoints.py`)

- **Health Endpoints**: System health checks
- **Task Endpoints**: Task CRUD operations via API
- **File Endpoints**: File operations via API
- **Git Endpoints**: Git integration endpoints
- **CrewAI Endpoints**: AI agent workflow endpoints

**Key Test Areas:**
- Authentication and authorization
- Request/response validation
- Error handling and status codes
- Data consistency across endpoints
- Integration with underlying services

### CLI Tests

CLI tests verify command-line interface functionality:

#### CLI Command Tests (`tests/cli/test_cli_commands.py`)

- **Task CLI**: Task management commands
- **Editor CLI**: File operation commands
- **Error Handling**: Invalid commands and arguments
- **Integration**: End-to-end CLI workflows

**Key Test Areas:**
- Command parsing and validation
- Input/output handling
- Error messages and help text
- File operations via CLI
- Workflow completion

### Integration Tests

Integration tests verify system-wide functionality:

#### System Integration Tests (`tests/integration/test_system_integration.py`)

- **Task-Editor Integration**: Cross-component workflows
- **API-CLI Consistency**: Consistent behavior across interfaces
- **Error Propagation**: System-wide error handling
- **Performance**: Concurrent operations and scalability
- **Data Consistency**: Cross-component data integrity

**Key Test Areas:**
- Multi-component workflows
- Concurrent operation handling
- Data consistency across components
- Performance under load
- Error recovery and resilience

## Test Fixtures

The test suite includes comprehensive fixtures in `conftest.py`:

### Core Fixtures

- **`temp_dir`**: Temporary directory for file operations
- **`temp_tasks_dir`**: Temporary tasks directory with schema
- **`task_manager`**: TaskManager instance for testing
- **`editor_tool`**: EditorTool instance for testing
- **`file_lock_manager`**: FileLockManager instance for testing

### Data Fixtures

- **`sample_task_data`**: Complete task data for testing
- **`sample_tasks`**: Multiple task samples with different statuses
- **`test_file_content`**: Sample file content for Editor Tool tests
- **`test_file`**: Created test file for operations

### API Fixtures

- **`api_client`**: FastAPI test client
- **`auth_headers`**: Authentication headers for API requests
- **`mock_pod_token`**: Mock authentication token
- **`mock_repo_path`**: Mock repository path

### Operation Fixtures

- **`sample_file_operation`**: Sample file operation requests
- **`sample_insert_operation`**: INSERT operation examples
- **`sample_update_operation`**: UPDATE operation examples
- **`sample_delete_operation`**: DELETE operation examples

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py all -v

# Run specific test type
python tests/run_tests.py unit -v
python tests/run_tests.py integration -v
python tests/run_tests.py api -v
python tests/run_tests.py cli -v
```

### Advanced Test Options

```bash
# Run with coverage report
python tests/run_tests.py all -v --coverage

# Run tests in parallel
python tests/run_tests.py all -v --parallel

# Run slow tests only
python tests/run_tests.py slow -v

# Run specific test file
python tests/run_tests.py unit/test_task_models.py -v
```

### Makefile Commands

```bash
# Basic test execution
make test

# Specific test types
make test-unit
make test-integration
make test-api
make test-cli

# Advanced options
make test-coverage
make test-parallel
make test-all
```

### Direct Pytest Execution

```bash
# Run all tests
pytest tests/

# Run with specific markers
pytest -m unit
pytest -m integration
pytest -m api
pytest -m cli

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run in parallel
pytest -n auto tests/
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
    -ra
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    cli: CLI tests
    slow: Slow running tests
    performance: Performance tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### Test Dependencies (`requirements-test.txt`)

```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.0
pytest-mock>=3.11.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
typer[all]>=0.9.0
coverage>=7.2.0
pytest-html>=3.2.0
pytest-json-report>=1.5.0
```

## Test Coverage

### Coverage Reports

The test suite generates comprehensive coverage reports:

```bash
# Generate HTML coverage report
python tests/run_tests.py all --coverage

# View coverage report
open htmlcov/index.html
```

### Coverage Targets

- **Overall Coverage**: > 90%
- **Core Components**: > 95%
- **API Endpoints**: > 90%
- **CLI Commands**: > 85%

### Coverage Exclusions

The following are excluded from coverage:
- Test files themselves
- Configuration files
- Main entry points
- Error handling paths that are difficult to trigger

## Test Data Management

### Temporary Data

All tests use temporary directories and files that are automatically cleaned up:

```python
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)  # Automatic cleanup
```

### Test Isolation

Each test is isolated and independent:
- No shared state between tests
- Fresh fixtures for each test
- Automatic cleanup after each test
- No external dependencies

### Mock Data

Tests use comprehensive mock data:
- Sample tasks with various statuses
- Test file content for Editor Tool operations
- Mock API responses
- Simulated user interactions

## Debugging Tests

### Verbose Output

```bash
# Run with verbose output
python tests/run_tests.py all -v

# Run specific test with maximum verbosity
pytest tests/unit/test_task_models.py::TestTaskFile::test_task_file_creation -vvv
```

### Debug Mode

```bash
# Run with debug output
pytest --pdb tests/

# Run specific test with debugger
pytest --pdb tests/unit/test_task_models.py::TestTaskFile::test_task_file_creation
```

### Test Logging

```bash
# Enable test logging
pytest --log-cli-level=DEBUG tests/

# Log to file
pytest --log-file=test.log --log-cli-level=DEBUG tests/
```

## Continuous Integration

### GitHub Actions

The test suite is designed to work with GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: make test-all
```

### Local CI Simulation

```bash
# Simulate CI environment
export CI=true
make test-all
```

## Performance Testing

### Load Testing

```bash
# Run performance tests
python tests/run_tests.py slow -v

# Run with performance profiling
pytest --profile tests/integration/test_system_integration.py::TestSystemPerformance
```

### Memory Testing

```bash
# Run with memory profiling
pytest --memray tests/
```

## Best Practices

### Writing Tests

1. **Test Naming**: Use descriptive test names that explain what is being tested
2. **Test Structure**: Follow Arrange-Act-Assert pattern
3. **Test Isolation**: Each test should be independent
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include tests for error conditions and edge cases

### Test Organization

1. **Group Related Tests**: Use test classes to group related functionality
2. **Use Fixtures**: Leverage pytest fixtures for common setup
3. **Parameterized Tests**: Use `@pytest.mark.parametrize` for testing multiple scenarios
4. **Test Markers**: Use markers to categorize tests

### Test Maintenance

1. **Keep Tests Updated**: Update tests when code changes
2. **Remove Obsolete Tests**: Clean up tests for removed functionality
3. **Monitor Test Performance**: Keep test execution time reasonable
4. **Review Test Coverage**: Regularly review and improve coverage

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python tests/run_tests.py
```

#### Permission Errors

```bash
# Ensure test files are executable
chmod +x tests/run_tests.py
```

#### Dependency Issues

```bash
# Reinstall test dependencies
pip install -r requirements-test.txt --force-reinstall
```

#### Test Failures

```bash
# Run specific failing test
pytest tests/unit/test_task_models.py::TestTaskFile::test_task_file_creation -v

# Run with debug output
pytest --pdb tests/unit/test_task_models.py::TestTaskFile::test_task_file_creation
```

### Getting Help

1. **Check Test Output**: Look for error messages in test output
2. **Use Debug Mode**: Run tests with `--pdb` for interactive debugging
3. **Check Logs**: Review test logs for additional information
4. **Verify Environment**: Ensure all dependencies are installed correctly

## Contributing

### Adding New Tests

1. **Follow Naming Conventions**: Use `test_` prefix for test functions
2. **Use Appropriate Markers**: Mark tests with appropriate categories
3. **Add Documentation**: Document complex test scenarios
4. **Update Fixtures**: Add new fixtures as needed

### Test Review Process

1. **Code Review**: All test changes require code review
2. **Coverage Check**: Ensure new code is covered by tests
3. **Performance Check**: Verify tests don't significantly impact performance
4. **Documentation Update**: Update this guide when adding new test categories

## Conclusion

The Cage test suite provides comprehensive coverage of all system components with a focus on reliability, maintainability, and performance. By following the guidelines in this document, developers can effectively test the system and contribute to its ongoing quality assurance.

