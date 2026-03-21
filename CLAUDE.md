# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auperator (Automation Operator) is an intelligent AIOps Agent that automatically monitors web applications, collects logs, performs intelligent analysis, and fixes issues through PR submission.

**Architecture**: Vector → HTTP API → Drain3 → Redis List → Agent

## Build & Development Commands

```bash
# Install dependencies and package
uv pip install -e .

# Run the main CLI
auperator --help

# Start auto-fix mode (consumes logs and fixes issues)
auperator start

# View logs in terminal (debug mode)
auperator terminal-consume -v

# View Redis List info
auperator list-info

# Start the API server
auperator server

# Start Vector
vector --config vector.yaml
```

## Architecture

### High-Level Design

```
┌──────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  Docker      │───▶│    Vector    │───▶│  HTTP API   │───▶│   Drain3    │───▶│  Redis List  │
│  Containers  │    │  (Collection)│    │  /ingest)   │    │  (Dedup)    │    │  (logs:main)│
└──────────────┘    └──────────────┘    └─────────────┘    └─────────────┘    └──────────────┘
                                                                 │
                                                                 ▼
                                                        ┌──────────────────┐
                                                        │   Agent Handler  │
                                                        │      Consumer    │
                                                        └──────────────────┘
```

### Data Flow

1. **Vector** captures Docker logs and performs multiline aggregation
2. **Vector** filters errors based on keywords (error, exception, traceback, 5xx)
3. **Vector** sends structured JSON to HTTP API `/vector/ingest`
4. **HTTP API** uses Drain3 to extract log templates and deduplicate
5. **API** pushes only new templates to Redis List
6. **Agent Handler** consumes from Redis List and invokes Agent to fix issues

### Core Components

**Vector Integration** (`vector.yaml`):

- **Source**: `docker_logs` - Captures logs from Docker containers
- **Transforms**:
  - `merged_logs`: Multiline aggregation using `reduce` transform
  - `error_only_filter`: Filters logs containing error keywords
- **Sinks**:
  - `http_output`: Sends filtered logs to Auperator API
  - `console_output`: Debug output to console

**Auperator API** (`src/auperator/server.py`):

- FastAPI server listening on port 7000
- Routes:
  - `/vector/ingest` - Receives logs from Vector
  - `/sandbox/*` - Daytona sandbox management
  - `/health` - Health check
- Lifecycle management via `lifespan()` context manager
- Services managed in `GlobalState`:
  - `Drain3Service` - Log template extraction and deduplication
  - `Redis client` - Async Redis operations
  - `DaytonaService` - Sandbox management

**Drain3 Service** (`src/auperator/services/drain3_service.py`):

- Extracts log templates using Drain3 algorithm
- Identifies new templates and template changes
- Maintains learned templates in `drain3_state.json`
- Configuration:
  - `DRAIN3_STATE_FILE`: Path to state file (default: drain3.json)
  - `DRAIN3_DEPTH`, `DRAIN3_MAX_CLUSTERS`, `DRAIN3_SIM_TH`: Drain3 parameters

**Agent Handler** (`src/auperator/collector/handlers/agent.py`):

- Consumes logs from Redis List via `VectorRedisConsumer`
- Invokes LangGraph Agent to analyze and fix errors
- Uses Daytona sandbox for safe code execution
- Langfuse integration for tracing (configurable via `--enable-langfuse`)
- Builds prompts from error logs with context (container, timestamp, error message)
- Streams agent output with `astream()` for real-time feedback

**Dependencies** (`src/auperator/dependencies.py`):

- FastAPI dependency injection for `Drain3Service` and `Redis client`
- `get_drain3_service()` - Returns Drain3Service from GlobalState
- `get_redis_client()` - Returns async Redis client from GlobalState
- Used in route handlers via `Depends()`

### Project Structure

```
src/auperator/
├── cli.py                  # Main CLI entry point
├── config.py               # Configuration management
├── server.py               # FastAPI application
├── state.py                # Global state management
├── dependencies.py         # Dependency injection
│
├── collector/              # Log collection and consumption
│   ├── handlers/           # Log handlers
│   │   ├── base.py         # Base handler interface
│   │   ├── agent.py        # Agent handler (calls LangGraph)
│   │   └── console.py      # Console handler (debug)
│   └── vector_consumer.py  # Redis List consumer
│
├── deepagents/             # Agent architecture
│   ├── builder.py          # Agent creation factory
│   ├── backends/           # Backend implementations
│   │   ├── protocol.py     # Backend protocol definition
│   │   ├── local_shell.py  # Local shell backend (default)
│   │   ├── sandbox.py      # Daytona sandbox backend
│   │   ├── state.py        # In-memory state backend
│   │   ├── filesystem.py   # Filesystem backend
│   │   └── store.py        # Persistent store backend
│   ├── middleware/         # Agent middleware
│   │   ├── filesystem.py   # File operation tools
│   │   ├── memory.py       # Memory file loading
│   │   ├── skills.py       # Skill loading
│   │   ├── subagents.py    # Subagent spawning
│   │   ├── summarization.py # Output summarization
│   │   └── patch_tool_calls.py # Tool call patching
│   ├── tools/              # Agent tools
│   │   ├── docker_tools.py # Docker operations
│   │   └── pull_request.py # GitHub PR creation
│   ├── skills/             # Skill files
│   │   └── daytona/        # Daytona sandbox skills
│   └── prompts/            # System prompts
│       └── system.py       # Base system prompt
│
├── schemas/                # Data models
│   ├── vector.py           # Vector log models
│   ├── daytona.py          # Daytona models
│   └── log.py              # Log entry models (LogEntry, LogLevel)
│
├── services/               # Business services
│   ├── drain3_service.py   # Drain3 wrapper
│   └── daytona_service.py  # Daytona sandbox service
│
└── routes/                 # FastAPI routes
    ├── vector.py           # Vector log ingestion
    └── daytona.py          # Sandbox management
```

## Configuration

Configuration is loaded from `.env` file. Key options:

### API Configuration

- `API_HOST`: API server host (default: 127.0.0.1)
- `API_PORT`: API server port (default: 7000)
- `API_RELOAD`: Auto-reload on code changes (default: false)
- `API_WORKERS`: Number of worker processes (default: 1)

### Redis Configuration

- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_PASSWORD`: Redis password (optional)
- `REDIS_DB`: Redis database (default: 0)
- `REDIS_KEY_PREFIX`: Key prefix for Redis keys (default: auperator:)
- `REDIS_LIST_NAME`: List name for logs (default: logs:main)

### Drain3 Configuration

- `DRAIN3_STATE_FILE`: State file path (default: drain3.json)
- `DRAIN3_DEPTH`: Drain tree depth (default: 4)
- `DRAIN3_MAX_CLUSTERS`: Max clusters (default: 1000)
- `DRAIN3_MAX_CHILDREN`: Max children per node (default: 100)
- `DRAIN3_SIM_TH`: Similarity threshold (default: 0.4)

### OpenAI Configuration

- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_BASE_URL`: API base URL
- `OPENAI_MODEL`: Model name

### LangFuse Configuration

- `LANGFUSE_PUBLIC_KEY`: LangFuse public key
- `LANGFUSE_SECRET_KEY`: LangFuse secret key
- `LANGFUSE_HOST`: LangFuse host URL

### Daytona Configuration

- `DAYTONA_API_KEY`: Daytona API key
- `DAYTONA_API_URL`: Daytona API URL

### Git Configuration

- `REMOTE_REPO_URL`: Remote repository URL
- `GITHUB_TOKEN`: GitHub token for PR creation

## Vector Configuration

**Key features in** **`vector.yaml`**:

- **Multiline aggregation**: 1000ms window, groups by container\_id
- **Error filtering**: Keywords (error, exception, traceback, critical, fatal) + 5xx HTTP codes
- **HTTP sink**: Sends to `http://172.17.0.1:7000/vector/ingest` (Docker gateway IP)

**Note**: If Vector runs in Docker, use `172.17.0.1` to access host services. If running on host, use `127.0.0.1`.

## Redis Data Format

### Redis List Structure

Key: `auperator:logs:main`

Each item is a JSON string:

```json
{
  "message": "Connection refused to <*:<:NUM:>>",
  "timestamp": "2026-03-17T14:30:00.123456Z",
  "cluster_id": 1,
  "host": "6f29d7e9cc5b",
  "source_type": "docker"
}
```

### Drain3 Output

When Drain3 processes a log:

```json
{
  "change_type": "cluster_created" | "cluster_template_changed" | "none",
  "cluster_id": 1,
  "cluster_size": 10,
  "cluster_count": 3,
  "template_mined": "Connection refused to <*:<:NUM:>>",
  "is_new_template": true
}
```

Only logs with `is_new_template: true` are pushed to Redis List.

## Extending the System

**Add a new Vector source**: Edit `vector.yaml` and add new sources/transforms

**Add a new handler**: Inherit `BaseLogHandler` from `collector/handlers/base.py` and implement `handle(entry)`

**Add a new service**: Create in `services/` and initialize in `GlobalState.initialize_all()`

**Add a new Agent tool**: Create a function decorated with `@tool` in `deepagents/tools/` and include it in the `get_tools()` function

## DeepAgents Architecture

The Agent system is built on a custom DeepAgents architecture (`deepagents/`), providing:

### Core Components

**Builder** (`deepagents/builder.py`):
- `create_auperator()` - Main entry point for creating agents
- Returns a LangGraph `CompiledStateGraph`
- Configurable model, tools, middleware, skills, and subagents

**Backends** (`deepagents/backends/`):
- `LocalShellBackend` - Default backend for filesystem and shell access
- `SandboxBackend` - For Daytona sandbox integration
- `StateBackend` - For in-memory state during invoke
- Backends implement `BackendProtocol` for filesystem and execution

**Middleware** (`deepagents/middleware/`):
- `TodoListMiddleware` - Built-in todo list management
- `FilesystemMiddleware` - File operation tools (ls, read, write, edit, glob, grep)
- `SubAgentMiddleware` - Spawns specialized subagents
- `SkillsMiddleware` - Loads skill files from directories
- `MemoryMiddleware` - Loads memory files (AGENTS.md)
- `SummarizationMiddleware` - Summarizes large outputs
- `PatchToolCallsMiddleware` - Patches tool call responses

**Tools** (`deepagents/tools/`):
- `docker_tools.py` - Docker container inspection and management
  - `get_container_info`, `get_container_logs`, `restart_container`
  - `get_container_stats`, `list_containers`, `get_container_processes`
- `pull_request.py` - GitHub PR creation

**Skills** (`deepagents/skills/`):
- `daytona/` - Daytona sandbox management skills
- Skills are loaded dynamically by `SkillsMiddleware`

### Agent Creation Pattern

```python
from auperator.deepagents import create_auperator
from auperator.deepagents.tools.docker_tools import get_tools as docker_tools
from auperator.deepagents.tools.pull_request import get_tools as pr_tools

# Create agent with tools and skills
tools = docker_tools() + pr_tools()
agent = create_auperator(
    skills=["./src/auperator/deepagents/skills"],
    tools=tools,
)

# Invoke the agent
async for chunk in agent.astream({"messages": [HumanMessage("Fix the error")]}):
    pass
```

### Agent Middleware Stack

The agent middleware is applied in this order:
1. `TodoListMiddleware` - Todo management
2. `MemoryMiddleware` (if memory specified) - Load AGENTS.md files
3. `SkillsMiddleware` (if skills specified) - Load skill files
4. `FilesystemMiddleware` - File operations
5. `SubAgentMiddleware` - Subagent spawning
6. `SummarizationMiddleware` - Output summarization
7. `PatchToolCallsMiddleware` - Tool call patching

### Configuration for Agent

The agent uses these settings from `config.py`:
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - API base URL (default: https://api.openai.com/v1)
- `OPENAI_MODEL` - Model name (default: gpt-4)

### Subagent System

DeepAgents supports specialized subagents:
- Each subagent has its own tools, model, and middleware
- Main agent can spawn subagents via the `task` tool
- General-purpose subagent is created automatically with default middleware

## 配置文件修改

如果你需要修改配置文件，那么你通常需要修改两个文件：

- `.env.example` - 样例配置文件
- `.env` - 实际配置文件

样例文件和正式文件的**配置项需要统一**（指的是配置项统一，而不是配置的值统一）。

## 常用命令

```bash
# 启动API服务
auperator server

# 启动自动修复模式
auperator start

# 终端消费模式（调试）
auperator terminal-consume -v

# 查看Redis List信息
auperator list-info

# 启动Vector
vector --config vector.yaml

# 查看Redis List中的日志数量
redis-cli LLEN auperator:logs:main

# 查看Drain3学习到的模板
cat drain3.json | jq '.clusters[] | {cluster_id, template}'
```

