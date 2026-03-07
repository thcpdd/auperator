# Auperator

> **Automation Operator** - 智能运维 Agent

Auperator 是一个基于 DeepAgents 架构的智能运维系统，能够自动监控 Web 应用、收集日志、智能分析并修复问题，最终通过提交 PR 完成闭环修复。

## 概述

Auperator 致力于解决传统运维系统中的痛点：被动响应、依赖人工分析、修复周期长。通过引入 AI Agent 技术，实现从问题发现到修复的全自动化闭环。

## 核心功能

### 1. 日志采集器（集成 Vector.dev）

使用专业的日志处理工具 **Vector.dev** 进行日志采集和处理。

#### 特性

- **多行日志聚合**：自动合并多行错误日志（如 Python Traceback、Java Stack Trace）
- **智能过滤**：基于关键词和模式的错误日志过滤
- **实时处理**：流式处理，低延迟
- **结构化输出**：统一的 JSON 格式输出

#### 架构

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Log Source  │───▶│    Vector    │───▶│  Redis List      │───▶│   Consumer   │
│  (Docker)    │    │  (Collection)│    │  (logs:main)     │    │   (Agent)    │
└──────────────┘    └──────────────┘    └──────────────────┘    └──────────────┘
                          │
                          ├─ Multiline aggregation
                          ├─ Error filtering
                          └─ Structured JSON output
```

#### Vector 输出示例

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
  "timestamp": "2026-03-07T02:29:19.941390846Z"
}
```

### 2. 日志消费者

从 Redis List 消费 Vector 处理后的日志并转换为标准格式。

```bash
# 消费日志
auperator-collector consume -v

# 查看 List 信息
auperator-collector list-info
```

### 3. 运维 Agent (Core Agent)

基于 DeepAgents 架构的核心智能体，负责问题分析、决策和执行。

#### 核心能力

| 能力 | 描述 |
|------|------|
| **Bug 定位** | 基于日志和上下文信息，精确定位问题根源 |
| **代码沙箱** | 内置隔离的代码运行环境，安全执行修复代码 |
| **自我进化** | 自动创建工具、积累 Skill、存储记忆 |
| **PR 提交** | 自动创建分支、提交代码、发起 Pull Request |

## 快速开始

### 系统要求

- Python 3.11+
- Vector 0.40+
- Redis 7+

### 安装

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 配置

编辑 `.env` 文件：

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_KEY_PREFIX=auperator:
REDIS_LIST_NAME=logs:main

# 消费者配置
CONSUMER_BATCH_SIZE=1
CONSUMER_BLOCK_TIMEOUT=5

# 通用配置
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 启动 Vector

编辑 `vector.yaml` 配置文件，然后启动：

```bash
vector --config vector.yaml
```

### 消费日志

```bash
# 消费 Vector 发送的日志
auperator-collector consume -v

# 查看 Redis List 信息
auperator-collector list-info
```

## 项目结构

```
auperator/
├── README.md                    # 项目文档
├── CLAUDE.md                    # Claude Code 开发指南
├── pyproject.toml               # Python 项目配置
├── .env                         # 环境变量配置
├── vector.yaml                  # Vector 配置
│
├── src/
│   └── auperator/
│       ├── __init__.py
│       ├── cli.py               # 主命令行接口
│       ├── config.py            # 配置管理
│       │
│       └── collector/           # 日志采集器模块
│           ├── __init__.py
│           ├── cli.py           # 采集器 CLI
│           ├── models.py        # 数据模型
│           ├── adapters/        # 日志适配器
│           │   ├── __init__.py
│           │   ├── base.py
│           │   └── vector_adapter.py  # Vector JSON 适配器
│           ├── handlers/        # 日志处理器
│           │   ├── __init__.py
│           │   ├── base.py
│           │   └── console.py    # 控制台输出
│           ├── sources/         # 日志源（保留用于扩展）
│           │   ├── __init__.py
│           │   └── base.py
│           └── vector_consumer.py    # Vector Redis 消费者
│
└── tests/                       # 测试用例
```

## CLI 命令

### 采集器命令

```bash
# 消费日志
auperator-collector consume [OPTIONS]

# 查看 List 信息
auperator-collector list-info [OPTIONS]

# 选项：
#   -r, --redis TEXT         Redis 连接 URL
#   -l, --list TEXT          List 名称
#   -v, --verbose            详细输出模式
```

## 扩展开发

### 自定义日志适配器

```python
from auperator.collector.adapters.base import BaseLogAdapter
from auperator.collector.models import LogEntry

class CustomLogAdapter(BaseLogAdapter):
    """自定义日志适配器"""

    def parse(self, raw_line: str) -> LogEntry:
        """解析原始日志"""
        # 实现解析逻辑
        pass
```

### 自定义日志处理器

```python
from auperator.collector.handlers.base import BaseLogHandler

class CustomHandler(BaseLogHandler):
    """自定义日志处理器"""

    async def handle(self, entry: LogEntry) -> None:
        """处理日志条目"""
        # 实现处理逻辑
        pass
```

## 配置文件

### Vector 配置 (vector.yaml)

```yaml
sources:
  docker_logs:
    type: "docker_logs"
    include_containers: ["container_name"]

transforms:
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

  error_only_filter:
    type: "filter"
    inputs: ["merged_logs"]
    condition: |
      msg = downcase(to_string(.message) ?? "")
      contains(msg, "error") || contains(msg, "exception")

sinks:
  redis_output:
    type: "redis"
    inputs: ["error_only_filter"]
    endpoint: "redis://localhost:6379"
    key: "auperator:logs:main"
    request:
      timeout_secs: 60
    batch:
      max_events: 1
      timeout_secs: 10
```

## 故障排查

### Vector 连接 Redis 超时

如果遇到远程 Redis 连接超时，可以尝试：

1. 增加超时时间：`request.timeout_secs: 120`
2. 减小批量大小：`batch.max_events: 1`
3. 检查网络连接质量
4. 考虑使用本地 Redis + 转发

### 日志没有被过滤

检查 Vector 的过滤条件，可以通过启用 `console_output` sink 调试。

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
