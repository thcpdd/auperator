# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auperator (Automation Operator) is an intelligent AIOps Agent that automatically monitors web applications, collects logs, performs intelligent analysis, and fixes issues through PR submission.

**Architecture Change**: The system now uses Vector.dev for log collection, with Auperator focusing on log consumption and analysis.

## Build & Development Commands

```bash
# Install dependencies and package
uv pip install -e .

# Run the main CLI
auperator --help

# Run the Vector collector CLI
auperator-vector --help

# Consume Vector logs from Redis
auperator-vector consume -v

# View Redis Stream info
auperator-vector stream-info

# Start Vector (if configured locally)
vector --config vector.yaml
```

## Architecture

### High-Level Design

The system uses Vector.dev for log collection and Redis Streams for message delivery:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Log Source  │───▶│    Vector    │───▶│  Redis Streams   │───▶│   Consumer   │
│  (Docker)    │    │  (Collection)│    │  (logs:main)     │    │   (Agent)    │
└──────────────┘    └──────────────┘    └──────────────────┘    └──────────────┘
                          │
                          ├─ Multiline aggregation
                          ├─ Error filtering
                          └─ Structured JSON output
```

### Core Components

**Vector Integration** (`vector.yaml`):
- **Sources**: `docker_logs` - Captures logs from Docker containers
- **Transforms**:
  - `merged_logs`: Multiline aggregation using `reduce` transform
  - `error_only_filter`: Filters logs containing error keywords
- **Sinks**:
  - `redis_output`: Sends filtered logs to Redis Streams
  - `console_output`: Debug output to console

**Auperator Collector** (`src/auperator/collector/`):
- **Adapters** (`adapters/`):
  - `VectorAdapter`: Converts Vector JSON output to `LogEntry`
  - Legacy adapters (JsonAdapter, GenericAdapter) kept for backward compatibility
- **Consumer** (`vector_consumer.py`): `VectorRedisConsumer` - Reads Vector logs from Redis
- **Handlers** (`handlers/`): Process logs (Console, legacy Redis)
- **Models** (`models.py`): `LogEntry` - Standardized log entry format

**Legacy Components** (deprecated but kept for reference):
- **Sources** (`sources/`): Docker, File, Kubernetes sources (replaced by Vector)
- **Position Manager** (`position_manager.py`): Collection tracking (Vector handles this)

**Configuration (`src/auperator/config.py`)**:
- Uses `pydantic-settings` to load config from `.env` file
- Key settings: Redis connection, consumer batch size, Vector integration

### Data Flow

1. **Vector** captures Docker logs and performs multiline aggregation
2. **Vector** filters errors based on keywords (error, exception, traceback, 5xx)
3. **Vector** sends structured JSON to Redis Streams
4. **VectorRedisConsumer** reads from Redis Stream using consumer groups
5. **VectorAdapter** converts Vector JSON to `LogEntry`
6. Agent processes logs and takes action

### Vector Configuration

**Key features in `vector.yaml`**:
- **Multiline aggregation**: 1000ms window, groups by container_id
- **Error filtering**: Keywords (error, exception, traceback, critical, fatal) + 5xx HTTP codes
- **Redis sink**: Batch sending (10 events, 5s timeout)

**Modify Vector config** for:
- Different containers/log sources
- Custom filter rules
- Different Redis endpoints

### Key Design Patterns

- **Adapter Pattern**: `VectorAdapter` converts Vector JSON to internal `LogEntry` format
- **Consumer Groups**: Redis Streams consumer groups for load balancing
- **Separation of Concerns**: Vector handles collection, Auperator handles analysis

## Redis Key Prefix

All Redis keys are prefixed with `auperator:` (configurable via `REDIS_KEY_PREFIX`). Use `settings.redis.add_prefix(key)` to add prefix.

## Vector Log Format

Vector outputs structured JSON:

```json
{
  "container_created_at": "2026-03-02T12:50:21.602172058Z",
  "container_id": "6a0964310ac3...",
  "container_name": "bug-web-backend-1",
  "host": "6f29d7e9cc5b",
  "image": "bug-web-backend",
  "message": "INFO: 172.18.0.1:43532 - \"GET /api/stats HTTP/1.1\" 500 Internal Server Error",
  "source_type": "docker_logs",
  "stream": "stdout",
  "timestamp": "2026-03-07T02:29:19.941390846Z",
  "label": {
    "com.docker.compose.service": "backend"
  }
}
```

## Extending the System

**Add a new Vector source**: Edit `vector.yaml` and add new sources/transforms

**Add a new adapter**: Inherit `BaseLogAdapter` and implement `parse(raw_line) -> LogEntry`

**Add a new handler**: Inherit `BaseLogHandler` and implement `handle(entry)`

**Customize Vector filtering**: Modify the `error_only_filter` condition in `vector.yaml`

## Configuration

Configuration is loaded from `.env` file. Key options:
- Redis settings (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_KEY_PREFIX`)
- Consumer settings (`COLLECTOR_BATCH_SIZE`, `COLLECTOR_BATCH_TIMEOUT`)
- Vector config is in `vector.yaml`

## Legacy Components

The following components are kept for backward compatibility but are not used in the Vector-based architecture:
- `DockerSource`, `FileSource`, `KubernetesSource`
- `JsonAdapter`, `GenericAdapter` (except for custom sources)
- `RedisHandler` (Vector writes directly to Redis)
- `PositionManager` (Vector handles position tracking)
- Legacy CLI commands (`docker`, `list`, `show-position`, etc.)
