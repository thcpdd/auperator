# 日志采集器架构设计

本文档详细介绍日志采集器的架构设计。

## 设计原则

1. **单一职责**: 每个组件只负责一个功能
2. **开闭原则**: 对扩展开放，对修改关闭
3. **异步优先**: 全异步 IO，高并发处理
4. **可靠传输**: 基于 Redis Streams 保证不丢日志

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         日志采集器架构                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   日志源层 (Source Layer)                                           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│   │ DockerSource│  │  FileSource │  │  K8sSource  │               │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│          │                │                │                        │
│          └────────────────┼────────────────┘                        │
│                           │                                         │
│                           ▼                                         │
│   适配层 (Adapter Layer)                                          │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │              BaseLogAdapter                             │      │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │      │
│   │  │ JsonAdapter  │  │GenericAdapter│  │ NginxAdapter │  │      │
│   │  └──────────────┘  └──────────────┘  └──────────────┘  │      │
│   └─────────────────────────────────────────────────────────┘      │
│                           │                                         │
│                           ▼                                         │
│   发送层 (Sender Layer)                                             │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │                   RedisSender                           │      │
│   │  - 连接管理  - 批量发送  - 自动重试                     │      │
│   └─────────────────────────────────────────────────────────┘      │
│                           │                                         │
│                           ▼                                         │
│                   ┌───────────────┐                                │
│                   │ Redis Streams │                                │
│                   └───────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

## 组件详解

### 1. Source 层 - 日志源

**职责**: 从特定来源读取原始日志行，不关心内容格式。

**设计**:

```python
class BaseLogSource(ABC):
    """日志源抽象基类"""

    @abstractmethod
    async def read(self) -> AsyncIterator[str]:
        """持续读取原始日志行"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动日志源"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止日志源"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """日志源名称"""
        pass
```

**实现**:

```python
# DockerSource 示例
class DockerSource(BaseLogSource):
    def __init__(
        self,
        container_name: str,
        follow: bool = True,
        tail: int = 100,
    ):
        self.container_name = container_name
        self.follow = follow
        self.tail = tail

    async def read(self) -> AsyncIterator[str]:
        async for line in self._container.logs(stream=True):
            yield line.decode()
```

### 2. Adapter 层 - 适配器

**职责**: 将原始日志行解析为标准 `LogEntry` 格式。

**设计**:

```python
class BaseLogAdapter(ABC):
    """日志适配器抽象基类"""

    @abstractmethod
    def parse(self, raw_line: str) -> LogEntry:
        """解析原始日志行"""
        pass

    def parse_batch(self, lines: list[str]) -> list[LogEntry]:
        """批量解析"""
        return [self.parse(line) for line in lines]
```

**实现**:

```python
# JsonAdapter 示例
class JsonAdapter(BaseLogAdapter):
    def parse(self, raw_line: str) -> LogEntry:
        data = json.loads(raw_line)
        return LogEntry(
            message=data.get("msg", ""),
            level=LogLevel.from_string(data.get("level", "INFO")),
            timestamp=data.get("time"),
            context=data.get("context", {}),
        )
```

### 3. Sender 层 - 发送器

**职责**: 将解析后的日志发送到 Redis Stream。

**设计**:

```python
class RedisSender:
    def __init__(
        self,
        redis_url: str,
        stream_name: str,
        max_retries: int = 3,
    ):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.max_retries = max_retries

    async def send(self, entry: LogEntry) -> str:
        """发送单条日志"""
        data = json.dumps(entry.to_dict())
        return await self._redis.xadd(
            self.stream_name,
            {"data": data}
        )

    async def send_batch(self, entries: list[LogEntry]) -> tuple[int, int]:
        """批量发送"""
        pipe = self._redis.pipeline()
        for entry in entries:
            data = json.dumps(entry.to_dict())
            pipe.xadd(self.stream_name, {"data": data})
        results = await pipe.execute()
        return len(results), 0
```

### 4. Collector 层 - 采集器

**职责**: 组合 Source 和 Adapter，实现完整的采集流程。

**设计**:

```python
class LogCollector:
    def __init__(
        self,
        source: BaseLogSource,
        adapter: BaseLogAdapter,
    ):
        self.source = source
        self.adapter = adapter

    async def collect(self, handler: LogHandler) -> None:
        """开始采集"""
        await self.source.start()
        async for line in self.source.read():
            entry = self.adapter.parse(line)
            await handler.handle(entry)
```

## 设计模式

### 适配器模式

Source 和 Adapter 分离，实现正交扩展：

```
        Source (哪里读)          Adapter (怎么解析)
        ┌─────────────┐         ┌─────────────┐
        │ DockerSource│         │ JsonAdapter │
        │ FileSource  │    +    │ GenericAdapter
        │ K8sSource   │         │ NginxAdapter│
        └─────────────┘         └─────────────┘

        可以任意组合使用
```

### 策略模式

Adapter 作为可替换的策略：

```python
# 同一个 Source，可以使用不同的 Adapter
collector1 = LogCollector(
    source=DockerSource("my-app"),
    adapter=JsonAdapter()
)

collector2 = LogCollector(
    source=DockerSource("my-app"),
    adapter=GenericAdapter()
)
```

### 工厂模式

使用配置创建采集器：

```python
def create_collector(config: dict) -> LogCollector:
    source = SourceFactory.create(config["source"])
    adapter = AdapterFactory.create(config["adapter"])
    return LogCollector(source, adapter)
```

## 扩展性

### 添加新的日志源

```python
class CustomSource(BaseLogSource):
    async def read(self) -> AsyncIterator[str]:
        # 自定义读取逻辑
        pass

    async def start(self) -> None:
        # 启动逻辑
        pass

    async def stop(self) -> None:
        # 停止逻辑
        pass

    @property
    def name(self) -> str:
        return "custom"
```

### 添加新的适配器

```python
class CustomAdapter(BaseLogAdapter):
    def parse(self, raw_line: str) -> LogEntry:
        # 自定义解析逻辑
        pass
```

## 性能考虑

### 批量处理

```python
# 使用 pipeline 提高 Redis 写入性能
async def send_batch(self, entries: list[LogEntry]):
    pipe = self._redis.pipeline()
    for entry in entries:
        pipe.xadd(self.stream_name, {"data": entry.to_dict()})
    await pipe.execute()
```

### 异步 IO

全异步设计，支持高并发：

```python
async def collect(self):
    async for line in self.source.read():  # 异步读取
        entry = self.adapter.parse(line)
        await self.sender.send(entry)       # 异步发送
```

## 容错机制

### 自动重试

```python
async def send(self, entry: LogEntry, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await self._send(entry)
        except RedisError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

### 优雅关闭

```python
async def stop(self):
    self._running = False
    await self.source.stop()
    await self.sender.close()
```

## 监控指标

建议监控以下指标：

- 采集速率 (条/秒)
- 发送延迟 (毫秒)
- 错误率 (%)
- Redis Stream 积压数量
