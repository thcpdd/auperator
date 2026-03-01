# Auperator

> **Automation Operator** - 智能运维 Agent

Auperator 是一个基于 DeepAgents 架构的智能运维系统，能够自动监控 Web 应用、收集日志、智能分析并修复问题，最终通过提交 PR 完成闭环修复。

## 概述

Auperator 致力于解决传统运维系统中的痛点：被动响应、依赖人工分析、修复周期长。通过引入 AI Agent 技术，实现从问题发现到修复的全自动化闭环。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Auperator 架构                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │
│   │  日志采集器   │───▶│  运维 Agent   │───▶│  配置与监控面板          │ │
│   │  Log Collector│    │  Core Agent  │    │  Dashboard               │ │
│   └──────────────┘    └──────────────┘    └──────────────────────────┘ │
│         │                   │                                              │
│         ▼                   ▼                                              │
│   ┌──────────────┐    ┌──────────────┐                                     │
│   │  任意日志源   │    │  代码沙箱    │                                     │
│   │  Any Logs   │    │  Sandbox     │                                     │
│   └──────────────┘    └──────────────┘                                     │
│                              │                                              │
│                              ▼                                              │
│                      ┌──────────────┐                                       │
│                      │  提交 PR      │                                       │
│                      │  Submit PR   │                                       │
│                      └──────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 日志采集器 (Log Collector)

日志采集器负责从任意 Web 应用中收集和标准化日志数据，支持多种部署环境。

#### 特性

- **适配器模式设计**：通过继承 + 重写的方式，轻松适配不同的日志格式和来源
- **多环境支持**：
  - 传统物理机/虚拟机部署
  - 容器化部署 (Docker, Kubernetes)
  - 云原生部署 (AWS, GCP, Azure)
  - Serverless 环境
- **结构化转换**：将非结构化日志转换为统一的 JSON 格式
- **实时流式处理**：支持日志的实时采集和推送
- **断点续传**：网络中断后自动恢复，不丢失日志

#### 支持的日志源

| 类型 | 支持项 |
|------|--------|
| Web 服务器 | Nginx, Apache, Caddy |
| 应用框架 | Spring Boot, Django, Flask, Express, FastAPI |
| 容器平台 | Docker, Kubernetes, OpenShift |
| 云服务 | CloudWatch, Stackdriver, Azure Monitor |
| 自定义 | 支持通过插件扩展 |

#### 输出格式

```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "level": "ERROR",
  "service": "user-service",
  "environment": "production",
  "message": "Database connection timeout",
  "stack_trace": "...",
  "context": {
    "request_id": "abc-123",
    "user_id": "user_456",
    "endpoint": "/api/users"
  },
  "metadata": {
    "host": "web-01",
    "pod": "user-service-xxx",
    "namespace": "default"
  }
}
```

### 2. 运维 Agent (Core Agent)

基于 DeepAgents 架构的核心智能体，负责问题分析、决策和执行。

#### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      DeepAgents 架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    感知层 (Perception)                   │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│  │  │ 日志分析  │  │ 指标监控  │  │ 链路追踪  │           │   │
│  │  └───────────┘  └───────────┘  └───────────┘           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     认知层 (Cognition)                   │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│  │  │ 问题诊断  │  │ 根因分析  │  │ 决策引擎  │           │   │
│  │  └───────────┘  └───────────┘  └───────────┘           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      执行层 (Action)                     │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│  │  │ 代码修复  │  │ 配置调整  │  │ PR 提交    │           │   │
│  │  └───────────┘  └───────────┘  └───────────┘           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心能力

| 能力 | 描述 |
|------|------|
| **Bug 定位** | 基于日志和上下文信息，精确定位问题根源 |
| **代码沙箱** | 内置隔离的代码运行环境，安全执行修复代码 |
| **自我进化** | 自动创建工具、积累 Skill、存储记忆 |
| **PR 提交** | 自动创建分支、提交代码、发起 Pull Request |
| **知识沉淀** | 将修复经验转化为可复用的解决方案 |

#### 工作流程

```
1. 日志接收 → 2. 异常检测 → 3. 根因分析 → 4. 方案生成
                                         ↓
7. 知识沉淀 ← 6. PR 提交 ← 5. 代码修复 ← 4. 方案验证
```

#### 工具集

- **代码分析工具**：AST 解析、依赖分析、代码搜索
- **调试工具**：断点调试、性能分析、内存分析
- **版本控制**：Git 操作、分支管理、冲突解决
- **CI/CD 集成**：触发流水线、查看构建结果
- **通信工具**：通知发送、状态更新

### 3. 配置与监控面板 (Dashboard)

可视化的管理和监控界面，提供完整的运维可视性。

#### 功能模块

##### 项目管理

- 添加/移除被监控项目
- 配置日志采集规则
- 设置告警阈值
- 定义 SLA 指标

##### Agent 状态监控

```
┌─────────────────────────────────────────────────────────────┐
│  Agent 状态概览                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ● 在线                                   运行时间：24h 30m │
│                                                             │
│  今日统计：                                                  │
│  ├─ 处理日志数：1,234,567 条                                │
│  ├─ 发现问题：12 个                                         │
│  ├─ 自动修复：9 个                                          │
│  ├─ 待人工介入：3 个                                        │
│  └─ 修复成功率：75%                                         │
│                                                             │
│  活跃任务：                                                 │
│  ├─ [RUNNING] 分析 user-service 异常日志                    │
│  ├─ [PENDING] 等待 CI 结果 - PR #123                        │
│  └─ [SLEEP] 监控中...                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

##### 修复历史

- 查看所有自动修复记录
- 修复详情和代码变更
- PR 状态追踪
- 回滚操作

##### 配置管理

- Agent 行为配置
- 工具权限管理
- API 密钥管理
- 通知渠道配置

## 快速开始

### 系统要求

- Python 3.11+
- Node.js 22+ (用于 Dashboard)
- Docker 20+ (可选，用于容器化部署)
- Redis 7+ (用于状态存储)
- PostgreSQL 15+ (用于数据持久化)

### 安装

#### 方式一：源码安装

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .

# 初始化配置
auperator init
```

#### 方式二：Docker 安装

```bash
# 使用 Docker Compose 启动
docker-compose up -d
```

### 配置

创建配置文件 `config.yaml`:

```yaml
# 基础配置
server:
  host: 0.0.0.0
  port: 8080

# 日志采集器配置
collector:
  enabled: true
  sources:
    - type: file
      path: /var/log/app/*.log
      format: nginx
    - type: docker
      container_name: my-app
    - type: kubernetes
      namespace: default
      labels:
        app: my-app

# Agent 配置
agent:
  model: deepseek-v3
  sandbox:
    enabled: true
    timeout: 300
  git:
    token: ${GIT_TOKEN}
    author_name: Auperator Bot
    author_email: bot@auperator.local
  auto_merge: false  # 是否自动合并 PR

# 存储配置
storage:
  redis:
    host: localhost
    port: 6379
    db: 0
  postgres:
    host: localhost
    port: 5432
    database: auperator
    user: auperator
    password: ${DB_PASSWORD}

# 通知配置
notification:
  channels:
    - type: slack
      webhook: ${SLACK_WEBHOOK}
    - type: email
      smtp_server: smtp.example.com
      from: auperator@example.com
      to: ops-team@example.com
```

### 启动

```bash
# 启动日志采集器
auperator collector start

# 启动 Agent
auperator agent start

# 启动 Dashboard
auperator dashboard start

# 或者使用一键启动
auperator start
```

## 项目结构

```
auperator/
├── README.md                    # 项目文档
├── pyproject.toml               # Python 项目配置
├── config.yaml                  # 配置文件模板
├── docker-compose.yml           # Docker Compose 配置
├── Dockerfile                   # Docker 镜像构建
│
├── src/
│   └── auperator/
│       ├── __init__.py
│       ├── cli.py               # 命令行接口
│       │
│       ├── collector/           # 日志采集器模块
│       │   ├── __init__.py
│       │   ├── base.py          # 基础采集器类
│       │   ├── adapters/        # 日志适配器
│       │   │   ├── nginx.py
│       │   │   ├── apache.py
│       │   │   ├── docker.py
│       │   │   └── kubernetes.py
│       │   ├── transformer.py   # 日志转换器
│       │   └── sender.py        # 数据发送器
│       │
│       ├── deepagents/               # 运维 Agent 模块
│       │   ├── __init__.py
│       │   ├── core.py          # Agent 核心逻辑
│       │   ├── perception/      # 感知层
│       │   │   ├── log_analyzer.py
│       │   │   └── metric_monitor.py
│       │   ├── cognition/       # 认知层
│       │   │   ├── diagnosis.py
│       │   │   ├── rca.py       # 根因分析
│       │   │   └── decision.py
│       │   ├── action/          # 执行层
│       │   │   ├── fixer.py     # 代码修复
│       │   │   ├── pr_manager.py
│       │   │   └── git_ops.py
│       │   ├── sandbox/         # 代码沙箱
│       │   │   ├── __init__.py
│       │   │   └── executor.py
│       │   └── tools/           # 工具集
│       │       ├── __init__.py
│       │       ├── code_tools.py
│       │       └── git_tools.py
│       │
│       ├── dashboard/           # 监控面板模块
│       │   ├── __init__.py
│       │   ├── app.py           # Web 应用入口
│       │   ├── api/             # REST API
│       │   ├── frontend/        # 前端资源
│       │   └── templates/       # 页面模板
│       │
│       ├── storage/             # 存储模块
│       │   ├── __init__.py
│       │   ├── redis_client.py
│       │   └── postgres_client.py
│       │
│       └── utils/               # 工具函数
│           ├── __init__.py
│           ├── logging.py
│           └── config.py
│
├── tests/                       # 测试用例
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/                        # 详细文档
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

## API 接口

### RESTful API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/projects` | 获取所有监控项目 |
| POST | `/api/v1/projects` | 添加监控项目 |
| GET | `/api/v1/projects/{id}` | 获取项目详情 |
| DELETE | `/api/v1/projects/{id}` | 移除监控项目 |
| GET | `/api/v1/agent/status` | 获取 Agent 状态 |
| POST | `/api/v1/agent/analyze` | 触发日志分析 |
| GET | `/api/v1/incidents` | 获取事件列表 |
| GET | `/api/v1/incidents/{id}` | 获取事件详情 |
| POST | `/api/v1/incidents/{id}/fix` | 触发自动修复 |
| GET | `/api/v1/prs` | 获取 PR 列表 |

### WebSocket

- `ws://localhost:8080/ws/logs` - 实时日志流
- `ws://localhost:8080/ws/events` - 实时事件流
- `ws://localhost:8080/ws/agent` - Agent 状态推送

## 扩展开发

### 自定义日志适配器

```python
from auperator.collector.base import BaseLogAdapter
from auperator.collector.transformer import LogEntry

class CustomLogAdapter(BaseLogAdapter):
    """自定义日志适配器示例"""

    def parse(self, log_line: str) -> LogEntry | None:
        """解析单行日志"""
        # 实现你的解析逻辑
        pass

    def collect(self) -> AsyncGenerator[LogEntry, None]:
        """收集日志"""
        # 实现你的收集逻辑
        pass
```

### 自定义 Agent 工具

```python
from auperator.agent.tools import BaseTool, tool

class CustomTool(BaseTool):
    """自定义工具示例"""

    name = "custom_tool"
    description = "执行自定义操作"

    @tool
    async def execute(self, param1: str) -> str:
        """执行工具逻辑"""
        return f"执行结果：{param1}"
```

## 安全考虑

- **沙箱隔离**：所有代码执行都在隔离的沙箱环境中进行
- **权限控制**：基于 RBAC 的细粒度权限管理
- **密钥管理**：敏感信息通过环境变量或密钥管理服务存储
- **审计日志**：所有操作都有完整的审计追踪
- **网络安全**：支持 TLS 加密通信

## 路线图

### v0.1.0 (当前版本)
- [x] 项目初始化
- [ ] 基础日志采集器实现
- [ ] Agent 基础框架
- [ ] Dashboard 基础界面

### v0.2.0
- [ ] 完整日志适配器生态
- [ ] Agent 自愈能力
- [ ] PR 自动提交
- [ ] 基础监控告警

### v0.3.0
- [ ] Agent 自我进化
- [ ] 知识库构建
- [ ] 多租户支持
- [ ] 高可用部署

### v1.0.0
- [ ] 生产就绪
- [ ] 完整文档
- [ ] 企业级功能

## 贡献指南

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 联系方式

- 项目主页：https://github.com/thcpdd/auperator
- 问题反馈：https://github.com/thcpdd/auperator/issues
- 邮件联系：1834763300@qq.com

---

<p align="center">Made with ❤️ by Auperator Team</p>
