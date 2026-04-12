# API 客户端

## 概述

`lib/api.ts` 是前端统一的 API 客户端，封装了所有与后端的 HTTP 通信。

## 基础用法

```typescript
import { api } from '@/lib/api'

// 获取对话列表
const conversations = await api.getConversations()

// 发送消息
await api.sendMessage('conversation-id', 'Hello')
```

## API 方法

### 对话管理

#### getConversations

获取对话列表。

```typescript
const result = await api.getConversations(params?)

// 参数
interface ConversationsParams {
  limit?: number    // 返回数量，默认 50
  offset?: number    // 偏移量，默认 0
  source?: 'terminal' | 'web-ui'  // 过滤来源
}

// 返回
interface ConversationsResponse {
  items: Conversation[]
  total: number
}
```

#### getConversation

获取单个对话详情。

```typescript
const conversation = await api.getConversation(id: string)
```

#### createConversation

创建新对话。

```typescript
const conversation = await api.createConversation(title?: string)
```

#### updateConversation

更新对话（重命名）。

```typescript
await api.updateConversation(id: string, data: { title: string })
```

#### deleteConversation

删除对话。

```typescript
await api.deleteConversation(id: string)
```

### 消息

#### sendMessage

发送消息。

```typescript
await api.sendMessage(conversationId: string, content: string, metadata?: object)
```

#### getMessages

获取对话消息。

```typescript
const messages = await api.getMessages(conversationId: string)
```

### 记忆

#### searchMemories

搜索记忆。

```typescript
const memories = await api.searchMemories(query: string, params?)

// 参数
interface SearchParams {
  section?: string   // 记忆分区
  limit?: number     // 返回数量
}

// 返回
interface MemoriesResponse {
  items: Memory[]
}
```

#### saveMemory

保存记忆。

```typescript
await api.saveMemory(section: string, content: string, metadata?: object)
```

#### getMemories

获取记忆列表。

```typescript
const memories = await api.getMemories(params?)
```

### 事件流

#### createEventSource

创建 SSE 连接。

```typescript
const eventSource = api.createEventSource(threadId?: string)

// 监听事件
eventSource.addEventListener('agent', (e) => {
  const data = JSON.parse(e.data)
  console.log(data.content)
})

eventSource.addEventListener('error', (e) => {
  console.error('SSE Error:', e)
})

// 关闭连接
eventSource.close()
```

### 健康检查

#### healthCheck

检查服务健康状态。

```typescript
const status = await api.healthCheck()

// 返回
interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  redis: 'connected' | 'disconnected'
  version: string
}
```

## 类型定义

```typescript
// lib/types.ts

interface Conversation {
  id: string
  title: string
  source: 'terminal' | 'web-ui'
  created_at: string
  updated_at: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface Memory {
  id: string
  section: string
  content: string
  metadata?: Record<string, any>
  created_at: string
}

interface Event {
  event_id: string
  event_type: 'USER' | 'AGENT' | 'ERROR' | 'STATUS'
  content: string
  agent_name?: string
  thread_id: string
  metadata?: Record<string, any>
  timestamp: string
}
```

## 错误处理

API 客户端使用统一的错误处理：

```typescript
import { APIError, NetworkError } from '@/lib/api'

try {
  await api.sendMessage('id', 'content')
} catch (error) {
  if (error instanceof APIError) {
    // HTTP 错误
    console.error(`API Error: ${error.status} - ${error.message}`)
  } else if (error instanceof NetworkError) {
    // 网络错误
    console.error('Network Error:', error.message)
  }
}
```

## 请求拦截

API 客户端会自动添加：

```typescript
// 请求头
{
  'Content-Type': 'application/json',
}

// 可选认证头（如需要）
{
  'Authorization': `Bearer ${token}`,
}
```

## 自定义配置

可以通过环境变量配置 API 地址：

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:7000
```

## SSE 使用示例

### 聊天实时响应

```tsx
'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Event } from '@/lib/types'

export function ChatStream({ conversationId }: { conversationId: string }) {
  const [events, setEvents] = useState<Event[]>([])

  useEffect(() => {
    const es = api.createEventSource(conversationId)

    es.addEventListener('agent', (e) => {
      const data = JSON.parse(e.data)
      setEvents(prev => [...prev, data])
    })

    return () => es.close()
  }, [conversationId])

  return (
    <div>
      {events.map((event, i) => (
        <div key={i}>
          <span className="text-gray-500">[{event.agent_name}]</span>
          <span>{event.content}</span>
        </div>
      ))}
    </div>
  )
}
```

### Docker 日志流

```tsx
'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export function DockerLogs() {
  const [logs, setLogs] = useState<Log[]>([])

  useEffect(() => {
    const es = api.createDockerLogsEventSource()

    es.addEventListener('log', (e) => {
      const data = JSON.parse(e.data)
      setLogs(prev => [...prev.slice(-100), data]) // 保留最近 100 条
    })

    return () => es.close()
  }, [])

  return (
    <div className="font-mono text-sm">
      {logs.map((log, i) => (
        <div key={i}>
          <span className="text-gray-400">[{log.container}]</span>
          <span>{log.message}</span>
        </div>
      ))}
    </div>
  )
}
```
