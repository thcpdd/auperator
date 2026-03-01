# Redis 消息队列

Auperator 使用 Redis Streams 作为消息队列，实现采集器和 Agent 之间的解耦。

## 为什么选择 Redis Streams?

| 特性 | Redis Streams | Kafka | RabbitMQ |
|------|---------------|-------|----------|
| 部署复杂度 | 低 | 高 | 中 |
| 性能 | 高 | 极高 | 中 |
| 持久化 | 支持 | 支持 | 支持 |
| 消费者组 | 支持 | 支持 | 支持 |
| 回溯消费 | 支持 | 支持 | 有限 |
| 适用场景 | 日志/事件 | 大数据 | 消息任务 |

**优势:**
- 轻量级，无需额外组件
- 支持持久化 (AOF/RDB)
- 天然支持消费者组
- 支持消息确认机制
- 可回溯消费历史消息

---

## 架构设计

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   采集器         │      │   Redis         │      │   Agent         │
│   (Producer)    │      │   Streams       │      │   (Consumer)    │
│                 │      │                 │      │                 │
│  Sender ──XADD─▶│─────▶│  logs:main      │─────▶│  Consumer ──▶   │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Stream 结构

```
Stream: logs:main

Entry:
  - id: 1709251200000-0
  - data: {"timestamp": "...", "level": "ERROR", "message": "..."}

消费者组：auperator-group
消费者：agent-1, agent-2, ...
```

---

## 使用示例

### 发送日志 (Producer)

```python
from auperator.collector import RedisSender, LogEntry, LogLevel

sender = RedisSender(
    redis_url="redis://localhost:6379",
    stream_name="logs:main",
)

await sender.connect()

# 发送单条
entry = LogEntry(message="Error occurred", level=LogLevel.ERROR)
message_id = await sender.send(entry)

# 批量发送
entries = [entry1, entry2, entry3]
success, failed = await sender.send_batch(entries)

await sender.close()
```

### 消费日志 (Consumer)

```python
from auperator.collector import RedisConsumer, LogEntry

consumer = RedisConsumer(
    redis_url="redis://localhost:6379",
    stream_name="logs:main",
    group_name="auperator-group",
    consumer_name="agent-1",
)

async def handler(entry: LogEntry):
    print(f"[{entry.level}] {entry.message}")

# 持续消费
await consumer.consume(handler)
```

---

## CLI 命令

```bash
# 发送日志到 Redis
auperator-collector docker my-app -r redis://localhost:6379

# 从 Redis 消费日志
auperator-collector consume -g auperator-group -n agent-1

# 查看 Stream 信息
auperator-collector redis-info
```

---

## 高级特性

### 消费者组模式

多个消费者实例负载均衡：

```bash
# 启动 3 个消费者
auperator-collector consume -n agent-1 &
auperator-collector consume -n agent-2 &
auperator-collector consume -n agent-3 &
```

每条日志只会被一个消费者处理。

### 消息确认

```python
# 消费者自动确认消息 (XACK)
async def consume(self, handler):
    for message_id, fields in messages:
        entry = self._parse(fields)
        await handler(entry)
        await self._redis.xack(stream, group, message_id)
```

### 待处理消息

```python
# 查看待处理消息
pending = await consumer.read_pending()

# 认领超时未处理的消息
claimed = await consumer.claim_pending(min_idle_time=30000)
```

---

## 配置选项

### RedisSender 配置

```python
RedisSender(
    redis_url="redis://localhost:6379",   # Redis 连接
    stream_name="logs:main",               # Stream 名称
    max_retries=3,                         # 最大重试次数
    retry_delay=1.0,                       # 重试延迟 (秒)
)
```

### RedisConsumer 配置

```python
RedisConsumer(
    redis_url="redis://localhost:6379",    # Redis 连接
    stream_name="logs:main",               # Stream 名称
    group_name="auperator-group",          # 消费者组
    consumer_name="agent-1",               # 消费者名称
    batch_size=100,                        # 批量大小
    block_timeout=5000,                    # 阻塞超时 (毫秒)
)
```

---

## Redis 配置

### 安装 Redis

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7 --appendonly yes
```

### 持久化配置

```bash
# redis.conf
appendonly yes
appendfsync everysec
```

### 内存管理

```bash
# 设置最大内存
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

## Stream 管理

### 创建消费者组

```python
await sender.create_consumer_group("auperator-group")
```

### 查看 Stream 信息

```python
info = await sender.get_stream_info()
print(f"消息数量：{info['length']}")
print(f"消费者组数：{info['groups']}")
```

### 清理 Stream

```python
# 删除所有消息
count = await sender.clear()

# 修剪旧消息 (保留最近 1000 条)
await redis.xtrim("logs:main", maxlen=1000)
```

---

## 监控指标

建议监控以下指标：

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| Stream 长度 | 待处理消息数量 | > 10000 |
| 消费延迟 | 消息产生到消费的时间 | > 60s |
| 待处理消息 | 已分配未确认的消息 | > 1000 |
| 错误率 | 发送/消费失败率 | > 1% |

---

## 故障排查

### Stream 不存在

```bash
# 创建 Stream
redis-cli XGROUP CREATE logs:main auperator-group 0 MKSTREAM
```

### 消息堆积

```bash
# 查看 Stream 长度
redis-cli XLEN logs:main

# 查看待处理消息
redis-cli XPENDING logs:main auperator-group
```

### 消费者离线

```bash
# 查看消费者组信息
redis-cli XINFO GROUPS logs:main

# 认领离线消费者的消息
redis-cli XAUTOCLAIM logs:main auperator-group agent-1 30000 0-0
```

---

## 文档导航

- [采集器概述](collector/overview.md) - 功能概览
- [架构设计](collector/architecture.md) - 架构详解
- [CLI 参考](collector/cli-reference.md) - 命令行接口
