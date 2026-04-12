# API 参考

API 服务默认运行在 `http://localhost:7000`

## 健康检查

### GET /health

检查服务健康状态。

**响应**

```json
{
  "status": "healthy",
  "redis": "connected",
  "version": "1.0.0"
}
```

## 日志接入

### POST /vector/ingest

接收 Vector 发送的日志。

**请求体**

```json
{
  "message": "ERROR: Connection refused to 10.0.0.1:5432",
  "timestamp": "2026-04-12T10:30:00.123456Z",
  "host": "container-name",
  "container_name": "backend-1",
  "container_id": "abc123..."
}
```

**响应**

```json
{
  "status": "ok",
  "cluster_id": 42,
  "is_new_template": true
}
```

## 聊天接口

### POST /chat/conversations

创建新对话。

**请求体**

```json
{
  "title": "数据库连接问题"
}
```

**响应**

```json
{
  "id": "uuid-string",
  "title": "数据库连接问题",
  "created_at": "2026-04-12T10:30:00Z",
  "updated_at": "2026-04-12T10:30:00Z"
}
```

### GET /chat/conversations

获取对话列表。

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 返回数量（默认 50） |
| `offset` | int | 偏移量（默认 0） |
| `source` | string | 过滤来源（terminal/web-ui） |

**响应**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "title": "数据库连接问题",
      "source": "terminal",
      "created_at": "2026-04-12T10:30:00Z"
    }
  ],
  "total": 42
}
```

### GET /chat/conversations/{conversation_id}

获取对话详情。

**响应**

```json
{
  "id": "uuid-string",
  "title": "数据库连接问题",
  "source": "terminal",
  "created_at": "2026-04-12T10:30:00Z",
  "updated_at": "2026-04-12T10:35:00Z"
}
```

### PUT /chat/conversations/{conversation_id}

更新对话（重命名）。

**请求体**

```json
{
  "title": "新标题"
}
```

### DELETE /chat/conversations/{conversation_id}

删除对话。

**响应**

```json
{
  "status": "ok"
}
```

### POST /chat/messages

发送消息并触发 Agent 处理。

**请求体**

```json
{
  "conversation_id": "uuid-string",
  "content": "帮我分析这个错误",
  "metadata": {}
}
```

**响应**

```json
{
  "message_id": "uuid-string",
  "status": "queued"
}
```

### GET /chat/conversations/{conversation_id}/messages

获取对话消息列表。

**响应**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "role": "user",
      "content": "帮我分析这个错误",
      "created_at": "2026-04-12T10:30:00Z"
    },
    {
      "id": "uuid-string",
      "role": "assistant",
      "content": "让我来分析这个问题...",
      "created_at": "2026-04-12T10:30:05Z"
    }
  ]
}
```

## 事件流

### POST /events/web-ui

SSE 端点，接收 Web UI 实时事件。

**请求体**

```json
{
  "thread_id": "optional-conversation-id"
}
```

**响应类型**: `text/event-stream`

**事件格式**

```
event: agent
data: {"event_type": "AGENT", "content": "正在分析日志...", "agent_name": "main"}

event: agent
data: {"event_type": "AGENT", "content": "定位到问题代码...", "agent_name": "fix"}

event: agent
data: {"event_type": "AGENT", "content": "修复完成", "agent_name": "main"}
```

### POST /events/docker-logs

SSE 端点，实时推送 Docker 日志。

**响应类型**: `text/event-stream`

**事件格式**

```
event: log
data: {"container": "backend-1", "message": "ERROR: ...", "timestamp": "..."}
```

## 记忆管理

### GET /memory

获取记忆列表。

**响应**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "section": "problems",
      "content": "数据库连接超时问题...",
      "created_at": "2026-04-12T10:30:00Z"
    }
  ]
}
```

### POST /memory

添加新记忆。

**请求体**

```json
{
  "section": "problems",
  "content": "问题描述...",
  "metadata": {}
}
```

### GET /memory/search

搜索记忆。

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词 |
| `section` | string | 指定分区 |
| `limit` | int | 返回数量 |

**响应**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "content": "...",
      "score": 0.95
    }
  ]
}
```

## 沙箱管理（Daytona）

### GET /sandbox/workspaces

获取工作空间列表。

### POST /sandbox/workspaces

创建新工作空间。

### GET /sandbox/workspaces/{workspace_id}

获取工作空间详情。

### DELETE /sandbox/workspaces/{workspace_id}

删除工作空间。

### POST /sandbox/workspaces/{workspace_id}/execute

在沙箱中执行命令。

**请求体**

```json
{
  "command": "ls -la",
  "timeout": 30
}
```

## Telegram Webhook

### POST /telegram/webhook

Telegram Bot Webhook 端点。

### POST /telegram/set-webhook

设置 Webhook URL。

**请求体**

```json
{
  "url": "https://your-domain.com/telegram/webhook"
}
```

### GET /telegram/webhook-info

获取 Webhook 信息。
