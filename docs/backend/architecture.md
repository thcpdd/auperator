# 后端架构设计

## 系统架构

```mermaid
flowchart TB
    subgraph Input["日志输入"]
        DC[Docker Containers]
        W[Web UI]
    end

    subgraph Collection["日志采集"]
        V[Vector]
    end

    subgraph Processing["日志处理"]
        API[HTTP API<br/>/vector/ingest]
        D3[Drain3<br/>模板提取去重]
        RL[Redis List<br/>logs:main]
    end

    subgraph Core["事件中枢"]
        EC[Event Center]
        RS[Redis Streams]
    end

    subgraph Engine["Agent 引擎"]
        AW[Agent Worker]
        Q[Qdrant]
        DT[Daytona]
        GH[GitHub]
        TG[Telegram]
    end

    DC --> V --> API --> D3 --> RL --> AW
    W --> EC --> AW
    AW --> EC --> RS --> W
    AW --> Q & DT & TG
    DT --> GH
```

## 核心组件

### 1. 日志采集层（Vector）

- **Source**: 从 Docker 容器捕获日志
- **Transform**:
  - `merged_logs`: 多行聚合（Python Traceback、Java Stack Trace）
  - `error_only_filter`: 错误关键词过滤
- **Sink**: 发送到 HTTP API

### 2. 日志处理层

#### HTTP API（FastAPI）

- `/vector/ingest` - 接收 Vector 日志
- `/chat/*` - 聊天对话接口
- `/events/*` - SSE 事件流
- `/memory/*` - 记忆管理

#### Drain3 服务

- 在线学习日志模板
- 智能去重（相同模板只处理一次）
- 状态持久化到 `drain3.json`

### 3. 事件中枢（Event Center）

基于 Redis Streams 的事件驱动核心：

```python
# 事件类型
class EventType(Enum):
    USER = "USER"      # 用户消息
    AGENT = "AGENT"    # Agent 响应
    ERROR = "ERROR"     # 错误事件
    STATUS = "STATUS"   # 状态更新
```

- **Stream**: `auperator:events:all`
- **Consumer Groups**:
  - `web-ui` - Web UI SSE 推送
  - `agent-worker` - Agent 任务处理

### 4. Agent 引擎

参见 [DeepAgents 架构](deepagents.md)

## 数据流

### CLI 模式（自动修复）

```mermaid
sequenceDiagram
    participant DC as Docker
    participant V as Vector
    participant API as API
    participant D3 as Drain3
    participant RL as Redis
    participant AW as Agent
    participant DT as Daytona

    DC->>V: 日志
    V->>API: JSON
    API->>D3: 提取模板
    D3->>RL: 新模板
    RL->>AW: 消费
    AW->>DT: 执行修复
```

### Web UI 模式（交互式）

```mermaid
sequenceDiagram
    participant W as Web UI
    participant CA as Chat API
    participant EC as Event Center
    participant AW as Agent
    participant DB as SQLite

    W->>CA: POST /chat/messages
    CA->>DB: 创建对话
    CA->>EC: 发布 USER 事件
    EC->>AW: 分发任务
    AW->>EC: 发布 AGENT 事件
    EC-->>W: SSE 推送
```

## 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| API 框架 | FastAPI | 高性能异步框架 |
| 消息队列 | Redis List + Streams | 日志队列 + 事件流 |
| 日志处理 | Drain3 | 模板提取去重 |
| Agent 编排 | LangGraph | 状态机编排 |
| 代码沙箱 | Daytona | 安全代码执行 |
| 持久化 | SQLite + Qdrant | 对话 + 向量记忆 |
| 状态持久化 | AsyncSqliteSaver | Agent 检查点 |

## 扩展性

### 添加新的日志源

编辑 `vector.yaml`：

```yaml
sources:
  - type: docker_logs
    # ...
  - type: file
    include_patterns:
      - /var/log/**/*.log
```

### 添加新的处理器

继承 `BaseLogHandler`：

```python
from auperator.collector.handlers.base import BaseLogHandler

class CustomHandler(BaseLogHandler):
    async def handle(self, entry: LogEntry):
        # 自定义处理逻辑
        pass
```

### 添加新的 API 端点

在 `routes/` 目录创建新路由文件：

```python
# routes/custom.py
from fastapi import APIRouter

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/action")
async def custom_action():
    return {"result": "ok"}
```

然后在 `server.py` 中注册：

```python
app.include_router(custom_router)
```
