# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auperator (Automation Operator) is an intelligent AIOps Agent that automatically monitors web applications, collects logs, performs intelligent analysis, and fixes issues through PR submission.

## Build & Development Commands

```bash
# Install dependencies and package
uv pip install -e .

# Run the main CLI
auperator --help

# Run the collector CLI
auperator-collector --help

# Collect Docker logs
auperator-collector docker <container> -n 100

# Consume logs from Redis
auperator-collector consume -v

# List available containers
auperator-collector list

# View Redis Stream info
auperator-collector redis-info

# Show/reset position for a log source
auperator-collector show-position <source-id>
auperator-collector reset-position <source-id> --confirm
```

## Architecture

### High-Level Design

The system uses a message-queue-based decoupled architecture:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│  Log Source  │───▶│   Collector  │───▶│  Redis Streams   │
│  (Docker)    │    │  (Source+Adapter) │  (logs:main)      │
└──────────────┘    └──────────────┘    └──────────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │    Consumer      │
                                          │  (Agent reads)   │
                                          └──────────────────┘
```

### Core Components

**Log Collector (`src/auperator/collector/`)**:
- **Sources** (`sources/`): Read raw logs from specific sources (Docker, File, Kubernetes)
- **Adapters** (`adapters/`): Parse raw logs into standardized `LogEntry` format
  - `JsonAdapter`: For JSON-structured logs
  - `GenericAdapter`: For unstructured logs with heuristic parsing
- **Handlers** (`handlers/`): Process parsed logs (Console, Redis)
- **Consumer** (`consumer.py`): Redis Streams consumer for Agent to read logs
- **Position Manager** (`position_manager.py`): Tracks collection progress and handles deduplication

**Configuration (`src/auperator/config.py`)**:
- Uses `pydantic-settings` to load config from `.env` file
- Key settings: Redis connection, collector batch size, Docker options, deduplication window/TTL

**CLI (`src/auperator/cli.py`, `src/auperator/collector/cli.py`)**:
- Built with `typer`
- Main commands: `auperator` (main CLI), `auperator-collector` (collector subcommands)

### Data Flow

1. **Source** reads raw log lines via `read()` async iterator
2. **Adapter** parses each line into `LogEntry` via `parse()`
3. **Handler** processes the entry (e.g., sends to Redis)
4. **Consumer** reads from Redis Stream using consumer groups
5. Agent processes logs and takes action

### Key Design Patterns

- **Adapter Pattern**: Easy to extend for new log formats by inheriting `BaseLogAdapter`
- **Strategy Pattern**: Different sources implement `BaseLogSource` interface
- **Consumer Groups**: Redis Streams consumer groups for load balancing and reliability

## Redis Key Prefix

All Redis keys are prefixed with `auperator:` (configurable via `REDIS_KEY_PREFIX`). Use `settings.redis.add_prefix(key)` to add prefix.

## Extending the System

**Add a new log source**: Inherit `BaseLogSource` and implement `read()`, `start()`, `stop()`, `name`

**Add a new adapter**: Inherit `BaseLogAdapter` and implement `parse(raw_line) -> LogEntry`

**Add a new handler**: Inherit `BaseLogHandler` and implement `handle(entry)`

## Configuration

Configuration is loaded from `.env` file. See `.env` for all available options including:
- Redis settings (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_KEY_PREFIX`)
- Collector settings (`COLLECTOR_BATCH_SIZE`, `COLLECTOR_BATCH_TIMEOUT`)
- Docker settings (`DOCKER_TAIL`, `DOCKER_FOLLOW`)
- Deduplication settings (`DEDUPLICATION_ENABLED`, `DEDUPLICATION_WINDOW`, `DEDUPLICATION_TTL`)
