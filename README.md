# Auperator

> **Automation Operator** - 智能运维 Agent

Auperator 是一个基于 DeepAgents 架构的智能运维系统，能够自动监控 Web 应用、收集日志、智能分析并修复问题，最终通过提交 PR 完成闭环修复。

## 概述

Auperator 致力于解决传统运维系统中的痛点：被动响应、依赖人工分析、修复周期长。通过引入 AI Agent 技术，实现从问题发现到修复的全自动化闭环。

## 核心功能

### 1. 日志采集（集成 Vector.dev）

使用专业的日志处理工具 **Vector.dev** 进行日志采集和处理。

#### 特性

- **多行日志聚合**：自动合并多行错误日志（如 Python Traceback、Java Stack Trace）
- **智能过滤**：基于关键词和模式的错误日志过滤
- **实时处理**：流式处理，低延迟
- **结构化输出**：统一的 JSON 格式输出

### 2. 智能去重（集成 Drain3）

使用 **Drain3** 算法进行日志模板提取和去重：

- **在线学习**：持续学习新的日志模板
- **模板提取**：自动识别日志中的变量部分
- **智能去重**：相同模板的日志只处理一次
- **状态持久化**：学习的模板持久化保存，重启不丢失

### 3. 自动修复（AI Agent）

基于 DeepAgents 架构的核心智能体，负责问题分析、决策和执行。

#### 核心能力

| 能力 | 描述 |
|------|------|
| **问题分析** | 基于日志模板，分析错误根因 |
| **代码沙箱** | 内置隔离的代码运行环境，安全执行修复代码 |
| **自动修复** | 在沙箱中定位问题、实施修复、运行测试 |
| **PR 提交** | 自动创建分支、提交代码、发起 Pull Request |

## 架构

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

### 数据流

1. **Vector** 采集 Docker 容器日志
2. **Vector** 过滤错误日志（error、exception、traceback、5xx）
3. **Vector** 发送到 Auperator API `/vector/ingest`
4. **API** 使用 Drain3 提取日志模板并去重
5. **API** 只推送新模板到 Redis List
6. **Agent Handler** 消费日志并调用 Agent 修复

## 快速开始

### 系统要求

- Python 3.11+
- Vector 0.40+
- Redis 7+
- Docker（用于日志采集）

### 安装

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 安装依赖
uv pip install -e .
```

### 配置

编辑 `.env` 文件：

```bash
# API 配置
API_HOST=127.0.0.1
API_PORT=7000

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_KEY_PREFIX=auperator:
REDIS_LIST_NAME=logs:main

# Drain3 配置
DRAIN3_STATE_FILE=drain3.json
DRAIN3_DEPTH=4
DRAIN3_SIM_TH=0.4

# OpenAI 配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# LangFuse 配置（可选）
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

# Daytona 配置
DAYTONA_API_KEY=
DAYTONA_API_URL=https://app.daytona.io/api

# Git 配置
REMOTE_REPO_URL=git@github.com:username/repo.git
GITHUB_TOKEN=your-github-token
```

### 启动服务

```bash
# 1. 启动 Auperator API 服务
auperator server

# 2. 启动 Vector（另一个终端）
vector --config vector.yaml

# 3. 启动自动修复模式（第三个终端）
auperator start
```

## CLI 命令

### 主命令

```bash
# 启动 API 服务
auperator server

# 启动自动修复模式
auperator start

# 终端消费模式（调试）
auperator terminal-consume -v

# 查看 Redis List 信息
auperator list-info
```

### 命令选项

```bash
# server 命令选项
auperator server [OPTIONS]

选项：
  -h, --host TEXT     API server host (default: 127.0.0.1)
  -p, --port INT      API server port (default: 7000)
  --reload            Enable auto-reload on code changes

# start 命令选项
auperator start [OPTIONS]

选项：
  -r, --redis TEXT         Redis 连接 URL
  -e, --enable-langfuse    启用 Langfuse 追踪

# terminal-consume 命令选项
auperator terminal-consume [OPTIONS]

选项：
  -r, --redis TEXT     Redis 连接 URL
  -l, --list TEXT      List 名称
  -v, --verbose        详细输出模式

# list-info 命令选项
auperator list-info [OPTIONS]

选项：
  -r, --redis TEXT     Redis 连接 URL
  -l, --list TEXT      List 名称
```

## 项目结构

```
auperator/
├── README.md               # 项目文档
├── CLAUDE.md               # Claude Code 开发指南
├── pyproject.toml          # Python 项目配置
├── .env                    # 环境变量配置
├── .env.example            # 环境变量配置示例
├── vector.yaml             # Vector 配置
├── drain3.json             # Drain3 状态文件（自动生成）
│
├── src/
│   └── auperator/
│       ├── cli.py               # 主命令行接口
│       ├── server.py            # FastAPI 应用入口
│       ├── config.py            # 配置管理
│       ├── state.py             # 全局状态管理
│       ├── dependencies.py      # 依赖注入
│       │
│       ├── collector/           # 日志采集和消费
│       │   ├── handlers/        # 日志处理器
│       │   │   ├── agent.py      # Agent 处理器（调用 LangGraph）
│       │   │   └── console.py    # 控制台处理器（调试）
│       │   └── vector_consumer.py # Redis List 消费者
│       │
│       ├── schemas/             # 数据模型
│       │   ├── vector.py         # Vector 日志模型
│       │   ├── daytona.py        # Daytona 模型
│       │   └── log.py            # 日志数据模型
│       │
│       ├── services/            # 业务服务
│       │   ├── drain3_service.py # Drain3 服务
│       │   └── daytona_service.py # Daytona 沙箱服务
│       │
│       └── routes/              # FastAPI 路由
│           ├── vector.py         # Vector 日志接收
│           └── daytona.py        # 沙箱管理
│
└── tests/                      # 测试用例
```

## Vector 配置

### vector.yaml

```yaml
sources:
  docker_logs:
    type: "docker_logs"
    include_containers: ["container_name"]  # 指定容器名称

transforms:
  # 多行日志聚合
  merged_logs:
    type: "reduce"
    inputs: ["docker_logs"]
    group_by: ["container_id"]
    merge_strategies:
      message: "concat"
    starts_when: |
      msg = to_string(.message) ?? ""
      match(msg, r'^(\d{4}|\[|\d{2}:\d{2}|INFO|DEBUG|WARN|ERROR|CRITICAL)')
    expire_after_ms: 1000

  # 错误过滤
  error_only_filter:
    type: "filter"
    inputs: ["merged_logs"]
    condition: |
      msg = downcase(to_string(.message) ?? "")
      contains(msg, "error") ||
      contains(msg, "exception") ||
      contains(msg, "traceback") ||
      contains(msg, "critical") ||
      contains(msg, "fatal") ||
      match(msg, r' (5\d{2}) ')

sinks:
  # HTTP sink - 发送到 Auperator API
  http_output:
    type: "http"
    inputs: ["error_only_filter"]
    uri: "http://172.17.0.1:7000/vector/ingest"  # Docker 网关 IP
    encoding:
      codec: "json"
    batch:
      max_events: 10
      timeout_secs: 5
    request:
      timeout_secs: 10
      retry_attempts: 3

  # 控制台输出（调试用）
  console_output:
    type: "console"
    inputs: ["error_only_filter"]
    encoding:
      codec: "json"
```

**注意**：
- 如果 Vector 在 Docker 中运行，使用 `172.17.0.1` 访问宿主机服务
- 如果 Vector 在宿主机运行，使用 `127.0.0.1`

## 工作流程示例

### 1. 错误日志产生

```
ERROR: Connection refused to 10.0.0.1:5432
```

### 2. Vector 采集并发送

```json
{
  "message": "ERROR: Connection refused to 10.0.0.1:5432",
  "timestamp": "2026-03-17T14:30:00Z",
  "container_name": "backend-1",
  "host": "server-01"
}
```

### 3. Drain3 提取模板

```json
{
  "template_mined": "ERROR: Connection refused to <*:<:NUM:>>",
  "cluster_id": 1,
  "is_new_template": true
}
```

### 4. 推送到 Redis

```json
{
  "message": "ERROR: Connection refused to <*:<:NUM:>>",
  "cluster_id": 1,
  "timestamp": "2026-03-17T14:30:00Z"
}
```

### 5. Agent 处理

- 分析错误原因（数据库连接失败）
- 在 Daytona 沙箱中克隆代码
- 定位问题代码（缺少数据库配置）
- 实施修复（添加配置文件）
- 运行测试验证
- 提交 PR

## 故障排查

### Vector 无法连接 API

如果看到 `Connection refused` 错误：

1. 确认 API 服务已启动：`curl http://127.0.0.1:7000/health`
2. 如果 Vector 在 Docker 中，使用 `172.17.0.1` 代替 `127.0.0.1`
3. 检查防火墙设置

### Drain3 状态丢失

- Drain3 状态保存在 `drain3.json` 中
- 重启 API 服务会自动加载之前学习的模板
- 确保 `drain3.json` 文件可写

### Agent 处理失败

1. 检查 OpenAI API 配置
2. 查看 Langfuse 追踪日志（如果启用）
3. 启用详细日志：`LOG_LEVEL=DEBUG`

## 贡献指南

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 文档

- [CLAUDE.md](CLAUDE.md) - Claude Code 开发指南
- [.env.example](.env.example) - 环境变量配置示例

## 联系方式

- 项目主页：https://github.com/thcpdd/auperator
- 问题反馈：https://github.com/thcpdd/auperator/issues
- 邮件联系：1834763300@qq.com

---

<p align="center">Made with ❤️ by Auperator Team</p>
