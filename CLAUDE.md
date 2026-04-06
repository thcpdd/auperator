# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auperator (Automation Operator) is an intelligent AIOps Agent that automatically monitors web applications, collects logs, performs intelligent analysis, and fixes issues through PR submission.

**Architecture**: Vector → HTTP API → Drain3 → Redis List → Agent Handler → Agent

**Dual Interface**:
- **CLI**: Command-line interface for log consumption and auto-fix
- **Web UI**: Next.js-based chat interface at [http://localhost:3000](http://localhost:3000)

## Build & Development Commands

### Backend (Python)

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

### Frontend (Next.js)

```bash
# Navigate to web directory
cd src/web

# Install dependencies
npm install
# or: pnpm install

# Start development server
npm run dev
# or: pnpm dev

# Build for production
npm run build
# or: pnpm build

# Start production server
npm start
# or: pnpm start

# Run linter
npm run lint
```

The Web UI provides:
- **Real-time chat interface** with the Agent
- **Conversation history management** with create, rename, delete
- **SSE-based event streaming** for real-time updates
- **Modern UI** with shadcn/ui components
- **Multiple pages**:
  - `/` - Main chat interface
  - `/chat` - Dedicated chat page
  - `/config` - Configuration management
  - `/status` - System status monitoring
  - `/logs` - Log viewing and analysis

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

**CLI Mode (Auto-fix)**:
1. **Vector** captures Docker logs and performs multiline aggregation
2. **Vector** filters errors based on keywords (error, exception, traceback, 5xx)
3. **Vector** sends structured JSON to HTTP API `/vector/ingest`
4. **HTTP API** uses Drain3 to extract log templates and deduplicate
5. **API** pushes only new templates to Redis List
6. **Agent Handler** consumes from Redis List and invokes Agent to fix issues

**Web UI Mode (Interactive)**:
1. User sends message via Web UI
2. Frontend calls `POST /chat/messages`
3. Backend creates conversation in SQLite
4. Backend publishes USER event to Redis Stream
5. AgentWorker consumes event and invokes Agent
6. Agent publishes AGENT events to Redis Stream
7. Frontend receives events via SSE endpoint `/events/web-ui`
8. Frontend displays agent responses in real-time

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
  - `/chat/*` - Chat API for conversational interface
  - `/events/*` - SSE event streaming for web UI
  - `/memory/*` - Memory management endpoints
- Lifecycle management via `lifespan()` context manager
- Services managed in `GlobalState`:
  - `Drain3Service` - Log template extraction and deduplication
  - `Redis client` - Async Redis operations
  - `DaytonaService` - Sandbox management
  - `EventCenter` - Event publishing and consumption
  - `AgentWorker` - Background agent task processing

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

**Event Handler** (`src/auperator/collector/handlers/event.py`):

- Processes logs and publishes events to EventCenter
- Creates conversation records in SQLite database
- Generates user events for web UI consumption
- Builds structured prompts from log entries
- Integrates with the event-driven architecture

**Dependencies** (`src/auperator/dependencies.py`):

- FastAPI dependency injection for `Drain3Service`, `Redis client`, `EventCenter`, and `AgentWorker`
- `get_drain3_service()` - Returns Drain3Service from GlobalState
- `get_redis_client()` - Returns async Redis client from GlobalState
- `get_event_center()` - Returns EventCenter from GlobalState
- `get_agent_worker()` - Returns AgentWorker from GlobalState
- Used in route handlers via `Depends()`

**Event Center** (`src/auperator/events/event_center.py`):

- Manages event publishing to Redis Streams
- Provides async event consumption with consumer groups
- Supports multiple consumer types (web-ui, agent-worker, etc.)
- Handles connection management and health checks
- Event types: USER, AGENT, ERROR, STATUS

**Database** (`src/auperator/database/`):

- SQLite-based persistence for conversations
- Async SQLAlchemy ORM with `Conversation` model
- Thread-based conversation tracking
- Supports conversation renaming and history

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
│   │   ├── console.py      # Console handler (debug)
│   │   └── event.py        # Event handler (publishes to EventCenter)
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
│   ├── log.py              # Log entry models (LogEntry, LogLevel)
│   ├── event.py            # Event models
│   ├── conversation.py     # Chat/conversation models
│   └── memory.py           # Memory models
│
├── services/               # Business services
│   ├── drain3_service.py   # Drain3 wrapper
│   └── daytona_service.py  # Daytona sandbox service
│
├── events/                 # Event system
│   ├── event_center.py     # Event publishing and consumption
│   └── __init__.py
│
├── database/               # Database layer
│   ├── db.py               # Database session management
│   ├── models.py           # SQLAlchemy models
│   └── base.py             # Base database classes
│
└── routes/                 # FastAPI routes
    ├── vector.py           # Vector log ingestion
    ├── daytona.py          # Sandbox management
    ├── chat.py             # Chat API
    ├── events.py           # SSE event streaming
    └── memory.py           # Memory management

src/web/                    # Next.js Web UI
├── app/                    # Next.js app directory
│   ├── page.tsx            # Main page
│   ├── layout.tsx          # Root layout
│   ├── globals.css         # Global styles
│   └── api/                # API routes
├── components/             # React components
├── lib/                    # Utility libraries
└── package.json            # Frontend dependencies
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

### Embedding Configuration

- `EMBEDDING_API_BASE_URL`: Embedding API base URL (default: https://api.openai.com/v1)
- `EMBEDDING_API_KEY`: Embedding API key
- `EMBEDDING_MODEL`: Embedding model name (default: text-embedding-3-small)
- `EMBEDDING_VECTOR_SIZE`: Vector dimension size (must match model, default: 1536)

### SQLite Configuration

- `SQLITE_DB_FILE`: SQLite database file name (default: auperator.db.sqlite3)

### Consumer Configuration

- `CONSUMER_BATCH_SIZE`: Batch size for consuming messages (default: 1)
- `CONSUMER_BLOCK_TIMEOUT`: Blocking timeout in seconds (default: 5)

### Qdrant Configuration

- `QDRANT_URL`: Qdrant service URL (default: http://localhost:6333)
- `QDRANT_API_KEY`: Qdrant API key (optional)
- `QDRANT_COLLECTION`: Collection name (default: auperator_memories)

### Event Stream Configuration

- `REDIS_EVENT_STREAM`: Redis stream name for events (default: events:all)

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

## Event System Architecture

### Redis Streams

The event system uses Redis Streams for real-time event distribution:

**Stream Key**: `auperator:events:all`

**Event Types**:
- `USER` - User input/messages
- `AGENT` - Agent responses/actions
- `ERROR` - Error events
- `STATUS` - Status updates

**Event Structure**:
```json
{
  "event_id": "uuid",
  "thread_id": "conversation_uuid",
  "event_type": "USER|AGENT|ERROR|STATUS",
  "content": "event content",
  "agent_name": "agent_identifier",
  "metadata": {},
  "timestamp": "2026-03-17T14:30:00Z"
}
```

**Agent Name Tracking**: Events support agent name tracking for multi-agent scenarios, allowing identification of which agent generated specific events.

**Consumer Groups**:
- `web-ui` - Web UI SSE stream
- `agent-worker` - Background agent processing

### SSE Endpoint

**Route**: `POST /events/web-ui`

**Request Body**:
```json
{
  "thread_id": "optional-filter-thread-id"
}
```

**Response**: Server-Sent Events stream with event data

### Event Flow

1. **EventHandler** receives log from Redis List
2. Creates conversation in SQLite database
3. Publishes USER event to Redis Stream
4. **AgentWorker** consumes event
5. Invokes Agent to process
6. Publishes AGENT events with responses
7. **Web UI** consumes events via SSE

## Extending the System

**Add a new Vector source**: Edit `vector.yaml` and add new sources/transforms

**Add a new handler**: Inherit `BaseLogHandler` from `collector/handlers/base.py` and implement `handle(entry)`

**Add a new service**: Create in `services/` and initialize in `GlobalState.initialize_all()`

**Add a new Agent tool**:
1. Create a function decorated with `@tool` in `deepagents/tools/`
2. Register in `ToolRegistry` in `deepagents/tools/registry.py`
3. Add to appropriate sub-agent's tool list in `create_auperator()`

**Add a new sub-agent**:
1. Create prompt in `deepagents/prompts/your_agent.py`
2. Add sub-agent spec in `create_auperator()` function:
   ```python
   {
       "name": "your_agent",
       "description": "What this agent does",
       "system_prompt": YOUR_AGENT_PROMPT,
       "model": model,
       "tools": ToolRegistry.get("tool_group"),
   }
   ```

**Add a new API route**: Create in `routes/` and register in `server.py`

**Add a new event type**: Add to `EventType` enum in `schemas/event.py`

**Add web UI components**:
- React components go in `src/web/components/`
- Pages go in `src/web/app/`
- API routes go in `src/web/app/api/`
- Uses shadcn/ui for component library

## DeepAgents Architecture

The Agent system is built on a custom **Multi-Agent DeepAgents architecture** (`deepagents/`), providing:

### Architecture Overview

Auperator uses a **multi-agent orchestration system** with specialized sub-agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Agent (Orchestrator)                 │
│  - Coordinates task delegation                              │
│  - Manages conversation flow                                 │
│  - Routes to specialized sub-agents                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ log_analysis │  │     fix      │  │ validation   │
│              │  │              │  │              │
│ - Analyze    │  │ - Fix code   │  │ - Run tests  │
│ - Classify   │  │ - Edit files │  │ - Verify     │
│ - Report     │  │ - Document   │  │ - Check      │
└──────────────┘  └──────────────┘  └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │      pr      │
                                        │              │
                                        │ - Create PR  │
                                        │ - Describe   │
                                        └──────────────┘
```

### Core Components

**Builder** (`deepagents/builder.py`):
- `create_auperator()` - Creates the multi-agent system
- Returns a LangGraph `CompiledStateGraph`
- Configurable model, tools, middleware, skills, and subagents
- Uses `CompositeBackend` by default (Daytona sandbox + local Shell)

**Multi-Agent System** (`deepagents/builder.py`):

The `create_auperator()` function creates a specialized multi-agent system with:

1. **Main Agent (Orchestrator)**
   - Coordinates all sub-agents
   - Manages conversation flow
   - Routes tasks to appropriate specialists
   - Uses `EventAutoSendMiddleware` for real-time event streaming

2. **Specialized Sub-Agents**
   - **log_analysis** - Log analysis expert
     - Queries historical memory for similar issues
     - Collects context and classifies errors
     - Assesses severity and impact
     - Generates structured analysis reports
     - Tools: `memory_tools`, `docker_tools`

   - **fix** - Code fixing expert
     - Locates problematic code based on analysis
     - Implements safe, effective fixes
     - Generates fix documentation
     - Tools: Filesystem tools (`read`, `edit`, `write`, `grep`, `glob`)

   - **validation** - Validation expert
     - Runs test suites
     - Verifies fix effectiveness
     - Detects regressions
     - Assesses fix quality

   - **pr** - PR management expert
     - Generates PR descriptions
     - Creates meaningful PR titles
     - Submits Pull Requests
     - Tools: `pr_tools`

3. **General-Purpose Sub-Agent**
   - `general-purpose` - Handles general tasks
   - Has access to all tools like the main agent
   - Useful for isolating context and token usage

**Backends** (`deepagents/backends/`):
- `CompositeBackend` - Default backend routing to:
  - **DaytonaSandbox** (default) - Safe code execution in sandbox
  - **LocalShellBackend** (`/local` route) - Local filesystem access
- `StateBackend` - For in-memory state during invoke
- `StoreBackend` - For persistent storage
- `FilesystemBackend` - For filesystem operations
- All backends implement `BackendProtocol` for filesystem and execution

**Middleware** (`deepagents/middleware/`):
- `EventAutoSendMiddleware` - Automatically sends agent events (tool calls, outputs) to EventCenter
- `TodoListMiddleware` - Built-in todo list management
- `FilesystemMiddleware` - File operation tools (ls, read, write, edit, glob, grep)
- `SubAgentMiddleware` - Spawns and manages specialized subagents
- `SkillsMiddleware` - Loads skill files from directories
- `MemoryMiddleware` - Loads memory files (AGENTS.md)
- `SummarizationMiddleware` - Summarizes large outputs
- `PatchToolCallsMiddleware` - Patches tool call responses

**State Management** (`deepagents/state.py`):
- `AuperatorState` - Main agent state with subagent message tracking
- `SubAgentExecution` - Records subagent execution history
  - `tool_call_id` - Links to main agent messages
  - `subagent_name` - Identifies which subagent was called
  - `messages` - Intermediate messages from subagent execution
- All state is persisted via checkpointer (SQLite)

**Tools** (`deepagents/tools/`):
- `docker_tools.py` - Docker container inspection and management
  - `get_container_info`, `get_container_logs`, `restart_container`
  - `get_container_stats`, `list_containers`, `get_container_processes`
- `pr_tools.py` - GitHub PR creation
- `memory_tools.py` - Memory storage and retrieval for agent knowledge
  - `save_memory` - Save problem/solution pairs to vector store
  - `retrieve_memories` - Search historical memories by semantic similarity
- `registry.py` - Tool registry system for managing available tools

**Prompts** (`deepagents/prompts/`):
- `system.py` - Base system prompt for main agent
- `log_analysis.py` - Log analysis expert prompt with memory integration
- `fix.py` - Code fixing expert prompt
- `validation.py` - Validation expert prompt
- `pr.py` - PR management expert prompt

**Skills** (`deepagents/skills/`):
- `daytona/` - Daytona sandbox management skills
- Skills are loaded dynamically by `SkillsMiddleware`

### Multi-Agent Workflow

**Typical Error Resolution Flow**:

1. **Error Detection** → Log received from Vector
2. **Log Analysis Agent**:
   - Queries memory for similar historical issues
   - Collects context (logs, container info, system state)
   - Classifies error type and severity
   - Generates analysis report
3. **Fix Agent**:
   - Reads analysis report
   - Locates problematic code
   - Implements safe fixes
   - Documents changes
4. **Validation Agent**:
   - Runs test suite
   - Verifies fix effectiveness
   - Checks for regressions
5. **PR Agent**:
   - Generates PR description
   - Creates Pull Request
6. **Main Agent**:
   - Orchestrates the entire process
   - Sends real-time events via EventCenter
   - Updates conversation state

### Agent Creation Pattern

```python
from auperator.deepagents import create_auperator

# Create the multi-agent system
agent = create_auperator(
    model="gpt-4",  # or any model
    checkpointer=checkpointer,  # Optional: for state persistence
    store=store,  # Optional: for persistent storage
    debug=False,  # Enable debug mode
)

# Invoke the agent
async for chunk in agent.astream({"messages": [HumanMessage("Fix the error")]}):
    pass
```

The `create_auperator()` function automatically:
- Creates the main orchestrator agent
- Initializes all 4 specialized sub-agents
- Adds the general-purpose sub-agent
- Configures CompositeBackend (Daytona + LocalShell)
- Sets up EventAutoSendMiddleware for real-time events
- Configures tool registry with all available tools

### Agent Middleware Stack

**Main Agent Middleware** (in order):
1. `TodoListMiddleware` - Todo management
2. `EventAutoSendMiddleware` - Automatic event sending
3. `MemoryMiddleware` (if memory specified) - Load AGENTS.md files
4. `SkillsMiddleware` (if skills specified) - Load skill files
5. `FilesystemMiddleware` - File operations
6. `SubAgentMiddleware` - Subagent spawning
7. `SummarizationMiddleware` - Output summarization
8. `PatchToolCallsMiddleware` - Tool call patching

**Sub-Agent Middleware** (in order):
1. `TodoListMiddleware` - Todo management
2. `FilesystemMiddleware` - File operations
3. `SummarizationMiddleware` - Output summarization
4. `PatchToolCallsMiddleware` - Tool call patching
5. `EventAutoSendMiddleware` - Automatic event sending
6. `SkillsMiddleware` (if skills specified) - Load skill files
7. User-provided middleware (if any)

### Configuration for Agent

The agent uses these settings from `config.py`:
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - API base URL (default: https://api.openai.com/v1)
- `OPENAI_MODEL` - Model name (default: gpt-4)
- `MONITORED_CONTAINER` - Container name for log analysis agent
- `EMBEDDING_*` - Embedding settings for memory system
- `QDRANT_*` - Qdrant settings for vector storage

### Subagent System

DeepAgents supports specialized subagents:
- Each subagent has its own tools, model, and middleware
- Main agent spawns subagents via the `task` tool
- General-purpose subagent is created automatically with default middleware
- **Sub-agent execution tracking**:
  - All intermediate messages captured
  - Execution history stored in `subagent_messages` state
  - Linked to main agent via `tool_call_id`
  - Persisted across restarts via checkpointer

**Memory-Enabled Sub-agents**:
- The `log_analysis` sub-agent has access to memory tools
- Can query historical solutions for similar errors
- Can save new experiences to vector store (Qdrant)
- Accumulates knowledge over time for better error analysis

### Agent Worker

**AgentWorker** (`deepagents/worker.py`):
- Background task processor for multi-agent execution
- Listens to Redis Streams for USER events
- Manages agent lifecycle and checkpointer
- Provides conversation history retrieval
- Streams sub-agent execution details via EventCenter
- Langfuse integration for tracing

**Key Features**:
- AsyncSqliteSaver for checkpoint persistence
- Thread-based conversation management
- Real-time event streaming (including sub-agent messages)
- Error handling and recovery
- Automatic state persistence (including subagent_messages)

### Event Flow

**Multi-Agent Event Streaming**:

1. **User sends message** → USER event published
2. **Main Agent processes** → Sends AGENT events with tool calls
3. **Sub-Agent invoked** → Intermediate messages captured
4. **Sub-Agent completes** → Final result returned to main agent
5. **Main Agent responds** → AGENT events with final output

All events include `agent_name` field for tracking which agent generated them.

### Checkpointer & State Management

- Uses **LangGraph AsyncSqliteSaver** for state persistence
- Checkpoint file: `auperator.db.sqlite3`
- Maintains conversation state across restarts
- **Sub-agent execution history** persisted in `subagent_messages` field
- Thread-based conversation isolation
- Supports conversation history retrieval with full sub-agent details

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

## Development Workflows

### Full Stack Development

To run both backend and frontend:

```bash
# Terminal 1: Start API server
auperator server

# Terminal 2: Start Vector (for log collection)
vector --config vector.yaml

# Terminal 3: Start Web UI
cd src/web && npm run dev
```

### Debugging Event Flow

```bash
# View Redis Stream events
redis-cli XRANGE auperator:events:all - +

# View consumer groups
redis-cli XINFO GROUPS auperator:events:all

# View consumers in a group
redis-cli XINFO CONSUMERS auperator:events:all agent-worker

# View conversation history in SQLite
sqlite3 auperator.db.sqlite3 "SELECT id, thread_id, title, created_at FROM conversations;"
```

### Testing Web UI Integration

1. Start all services (API, Vector, Web UI)
2. Open http://localhost:3000
3. Send a message through the chat interface
4. Monitor events:
   - Check browser Network tab for SSE connection
   - Check backend logs for event publishing
   - Verify Redis Stream receives events

### Monitoring Agent Execution

```bash
# Enable Langfuse tracing
auperator start --enable-langfuse

# View agent checkpoints
sqlite3 auperator.db.sqlite3 "SELECT * FROM checkpoints;"

# Monitor event stream
redis-cli XREAD STREAMS auperator:events:all $
```

## Frontend Development

### Tech Stack

- **Framework**: Next.js 16 with App Router
- **UI Library**: shadcn/ui + Radix UI + Base UI
- **Styling**: Tailwind CSS 4 with tw-animate-css
- **State Management**: React hooks + SSE for real-time updates
- **Markdown**: react-markdown with rehyp-highlight and remark-gfm
- **Icons**: lucide-react
- **Components**: Custom components in `src/web/components/`

### Key Components

- **ChatView**: Main chat interface with streaming responses
- **ConversationList**: Sidebar with conversation history and filtering
- **ConfigView**: Configuration management interface
- **StatusView**: System status and health monitoring
- **Event Streaming**: SSE-based real-time updates with agent name tracking
- **Markdown Rendering**: React Markdown with syntax highlighting (highlight.js)

### Adding New Features

1. **New API Route**: Create in `src/web/app/api/`
2. **New Page**: Create in `src/web/app/`
3. **New Component**: Create in `src/web/components/`
4. **Styling**: Use Tailwind CSS utility classes
5. **UI Components**: Use shadcn/ui components

