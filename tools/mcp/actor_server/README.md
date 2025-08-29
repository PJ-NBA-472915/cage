# Actor Server (MCP Tool)

## Purpose

The Actor Server is an MCP (Multi-Agent Communication Protocol) tool designed to execute shell commands within specified directories. This allows other agents or systems to remotely trigger arbitrary shell instructions in a controlled environment, typically a cloned repository.

## Tool: `actor.run`

This server exposes a single tool named `actor.run`.

### Parameters

The `actor.run` tool accepts the following JSON parameters:

-   `path` (string, **required**): The absolute or repository-relative directory in which the shell command should be executed. The server will `chdir` into this path before running the instruction.
-   `instruction` (string, **required**): The shell command to execute. This command will be run using POSIX shell semantics (e.g., `/bin/sh -lc`).

### Returns

On successful execution, the tool returns the `stdout` of the executed command as a string.

### Error Handling

If the command returns a non-zero exit code or times out, a `ToolError` will be raised, including `stderr` in the error diagnostics.

## Usage

### Running the Server

The server can be started as a persistent process or run for a single invocation (e.g., for testing).

To run persistently (e.g., in a `devbox` service or `supervisor`):

```bash
devbox run python -m tools.mcp.actor_server.server
```

### Smoke Test (using `Makefile`)

A `Makefile` target is provided for a quick smoke test:

```bash
make actor-smoke
```

This command will launch the MCP server in `--once` mode, execute a simple `echo hello` command in the current directory, and print the output. It should return `hello\n`.

### Running Tests

Unit tests for the `runner.py` module can be executed using the `Makefile`:

```bash
make test
```

## Implementation Details

-   **`runner.py`**: Contains the core logic for executing shell commands, handling `cwd`, `timeout`, and error conditions.
-   **`server.py`**: Implements the MCP server, registers the `actor.run` tool, and exposes the `runner.py` functionality.

## Dependencies

-   `modelcontextprotocol` SDK (expected to be available in the environment)
-   Standard Python `subprocess` module.
