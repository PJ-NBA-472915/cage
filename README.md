# Agent Base Dockerfile

A minimal, secure Ubuntu-based container image designed for Fly.io deployment with agent pod architecture. This base image ships with Python, the Gemini SDK, and the official Gemini CLI, providing a foundation for isolated development and execution environments.

## Features

- **Ubuntu 24.04 base** with minimal footprint
- **Python 3** with essential development tools
- **Gemini SDK** for AI-powered workflows
- **Gemini CLI** available globally for terminal operations
- **Non-root user** execution for security
- **Tini process manager** for proper signal handling
- **Runtime customization** via optional `pod-setup.sh` scripts
- **Fly.io ready** with health checks and deployment config

## Architecture

This image follows the [Fly.io Per-User Dev Environments](https://fly.io/docs/blueprints/per-user-dev-environments/) blueprint pattern:

- **Base Image**: Minimal Ubuntu with Python and Gemini tools
- **Runtime Setup**: Optional `pod-setup.sh` for repo-specific tooling
- **Daemon Service**: Lightweight Python daemon for agent pod lifecycle
- **Health Monitoring**: TCP health checks for Fly.io deployment

## Quick Start

### Local Development

```bash
# Build the image
podman build -t agent-base:dev .

# Run with Gemini API key
podman run --rm -e GEMINI_API_KEY=sk-... agent-base:dev

# Run with custom pod setup
podman run --rm -e GEMINI_API_KEY=sk-... \
  -v ./my-pod-setup.sh:/app/pod-setup.sh \
  agent-base:dev
```

### Fly.io Deployment

```bash
# Launch the app (creates fly.toml)
fly launch --no-deploy

# Set your Gemini API key
fly secrets set GEMINI_API_KEY=sk-...

# Deploy
fly deploy

# Check logs
fly logs
```

## Configuration

### Environment Variables

- `GEMINI_API_KEY` (required): Your Gemini API key for authentication
- `GEMINI_MODEL` (optional): Model to use (default: `gemini-2.5-pro`)

### Customization

Create a `pod-setup.sh` script in your deployment to install repo-specific tools:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Installing repo-specific tools..."
pip3 install --no-cache-dir black ruff mypy
npm install -g typescript
echo "Setup complete!"
```

## File Structure

```
.
├── Dockerfile              # Main container definition
├── requirements.txt        # Python dependencies
├── pod-entrypoint.sh      # Runtime entrypoint script
├── agent_daemon.py        # Python daemon service
├── fly.toml               # Fly.io deployment config
├── example-pod-setup.sh   # Example customization script
└── README.md              # This file
```

## Development

### Building Locally

```bash
# Using Podman (recommended)
podman build -t agent-base:dev .

# Using Docker
docker build -t agent-base:dev .
```

### Testing

The project uses pytest for comprehensive testing with the following test categories:

#### Test Structure
```
tests/
├── unit/           # Unit tests for individual functions/classes
├── integration/    # Integration tests for component interactions
└── functional/     # End-to-end functional tests
```

#### Running Tests

**Quick Start:**
```bash
# Run all tests
./run_tests.sh

# Or run directly with pytest
pytest
```

**Specific Test Categories:**
```bash
# Unit tests only (fastest)
pytest -m unit

# Integration tests
pytest -m integration

# Functional tests
pytest -m functional

# Exclude slow tests
pytest -m "not slow"
```

**With Coverage:**
```bash
# Run with coverage reporting
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Test Selection:**
```bash
# Run specific test file
pytest tests/unit/test_daemon.py

# Run specific test function
pytest tests/unit/test_daemon.py::test_init_gemini_with_valid_key

# Run tests in parallel
pytest -n auto
```

#### Test Configuration

- **`pytest.ini`**: Main pytest configuration with markers and options
- **`conftest.py`**: Shared fixtures and configuration for all tests
- **Custom markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.async`

#### Testing Standards

All tests follow the established pytest testing standards defined in `.cursor/rules/pytest-testing-standards.md`. Key principles:

- **Unit tests**: Fast, isolated tests for individual functions
- **Integration tests**: Component interaction tests
- **Functional tests**: End-to-end workflow tests
- **Async support**: Proper handling of async/await patterns
- **Mocking**: Comprehensive mocking of external dependencies
- **Coverage**: Minimum 80% code coverage requirement

#### Legacy Testing

For backward compatibility, existing shell-based test scripts continue to work:

```bash
# Test basic functionality
podman run --rm agent-base:dev

# Test with API key
podman run --rm -e GEMINI_API_KEY=test-key agent-base:dev

# Test with custom setup script
podman run --rm \
  -e GEMINI_API_KEY=test-key \
  -v ./example-pod-setup.sh:/app/pod-setup.sh \
  agent-base:dev
```

## Deployment

### Fly.io

1. **Install flyctl**: Follow the [official installation guide](https://fly.io/docs/hands-on/install-flyctl/)
2. **Authenticate**: `fly auth login`
3. **Launch app**: `fly launch --no-deploy`
4. **Configure secrets**: `fly secrets set GEMINI_API_KEY=your-key`
5. **Deploy**: `fly deploy`

### Health Checks

The container exposes port 8080 with TCP health checks. The daemon logs heartbeat messages every 10 seconds to confirm liveness.

### Scaling

Configure scaling in your `fly.toml`:

```toml
[env]
  SCALE_COUNT = "3"

[processes]
  app = "python3 /app/agent_daemon.py"
```

## Security Considerations

- **Non-root execution**: Container runs as non-privileged user
- **Minimal base**: Only essential packages installed
- **Secret management**: Use Fly.io secrets for sensitive data
- **Process isolation**: Tini manages process lifecycle

## Troubleshooting

### Common Issues

1. **Gemini CLI not found**: Ensure Node.js installation completed successfully
2. **Permission denied**: Check that `/app` directory is writable by the app user
3. **Health checks failing**: Verify the daemon is starting and logging heartbeats

### Debug Mode

Run with additional logging:

```bash
podman run --rm -e GEMINI_API_KEY=sk-... \
  -e LOG_LEVEL=DEBUG \
  agent-base:dev
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with Podman/Docker
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## References

- [Fly.io Per-User Dev Environments](https://fly.io/docs/blueprints/per-user-dev-environments/)
- [Fly.io Machines Documentation](https://fly.io/docs/machines/)
- [Google Generative AI Python SDK](https://ai.google.dev/docs/python_quickstart)
- [Gemini CLI Documentation](https://ai.google.dev/docs/gemini_cli)
