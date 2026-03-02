# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auperator is an intelligent operations system based on the DeepAgents architecture. It automatically monitors web applications, collects logs, intelligently analyzes and fixes issues, and completes the closed-loop fix by submitting PRs.

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
uv sync

# Install the package in development mode
uv pip install -e .
```

### Running the Application
```bash
# Start log collector for Docker container
auperator-collector docker <container_name> -f

# Consume logs from Redis
auperator-collector consume -v

# List available Docker containers
auperator-collector list

# View Redis Stream information
auperator-collector redis-info

# Test log adapters
auperator-collector test -a json
```

### Building
```bash
# Build the package
uv build

# Install from built wheel
uv pip install dist/auperator-*.whl
```

## Architecture

### Core Components

```
Source (read logs) ──▶ Adapter (parse logs) ──▶ Sender (send to Redis) ──▶ Redis Streams
```

1. **Log Collector** ([src/auperator/collector/](src/auperator/collector/))
   - **Sources**: Read raw logs from specific origins (Docker, File, Kubernetes)
   - **Adapters**: Parse raw logs into standardized `LogEntry` format
   - **Sender**: Send logs to Redis Streams
   - **Consumer**: Consume logs from Redis for Agent processing

2. **Message Queue** (Redis Streams)
   - Decouples collector and Agent
   - Supports multiple consumers via consumer groups
   - Provides persistence and replay capability

3. **DeepAgents Agent** ([src/auperator/deepagents/](src/auperator/deepagents/))
   - Analyzes logs for bug detection
   - Performs root cause analysis
   - Generates fixes and submits PRs

### Design Patterns

- **Adapter Pattern**: Extensible log parsing via `BaseLogAdapter`
- **Source Pattern**: Extensible log collection via `BaseLogSource`
- **Async/Await**: All I/O operations are asynchronous

## Configuration

Configuration is managed through `pydantic-settings` and loaded from `.env` file. See [`.env.example`](.env.example) for all available options.

Key configuration files:
- [src/auperator/config.py](src/auperator/config.py) - Settings class with validation
- `.env` - Environment-specific configuration (not in git)

## Adding New Features

### Adding a New Log Source

1. Inherit from `BaseLogSource` in [src/auperator/collector/sources/base.py](src/auperator/collector/sources/base.py)
2. Implement `read()`, `start()`, `stop()`, and `name` property
3. Return an async iterator of raw log lines

### Adding a New Log Adapter

1. Inherit from `BaseLogAdapter` in [src/auperator/collector/adapters/base.py](src/auperator/collector/adapters/base.py)
2. Implement `parse()` to return a `LogEntry`
3. The adapter should handle various log formats and extract structured data

## Code Conventions

- Use async/await for all I/O operations
- Type hints are required (Python 3.11+)
- Use `pydantic` for data validation and models
- CLI commands use `typer` for argument parsing
- Configuration uses `pydantic-settings`

## Project Structure Notes

- No tests directory yet - tests should be added in a `tests/` directory
- Documentation is in [docs/](docs/) - architecture, implementation guides
- The main CLI entry point is `auperator` command
- The collector CLI is `auperator-collector` command
