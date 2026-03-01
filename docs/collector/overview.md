# 日志采集器概述

日志采集器是 Auperator 的核心组件，负责从各种来源收集日志并标准化后发送到消息队列。

## 功能特性

- **多源支持**: Docker、File、Kubernetes 等多种日志源
- **格式解析**: 适配器模式解析不同格式的日志
- **实时采集**: 流式处理，实时传输
- **可靠传输**: 基于 Redis Streams 保证不丢日志
- **灵活配置**: 支持多种配置方式

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    日志采集器                                │
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────┐ │
│  │  DockerSource │    │  FileSource   │    │  K8sSource  │ │
│  │               │    │               │    │             │ │
│  │  读取原始日志 │    │  读取原始日志 │    │  读取原始日志│ │
│  └───────┬───────┘    └───────┬───────┘    └──────┬──────┘ │
│          │                    │                   │        │
│          └────────────────────┼───────────────────┘        │
│                               │                             │
│                               ▼                             │
│                   ┌───────────────────────┐                │
│                   │    BaseLogAdapter     │                │
│                   │    - JsonAdapter      │                │
│                   │    - GenericAdapter   │                │
│                   │    - NginxAdapter     │                │
│                   └───────────┬───────────┘                │
│                               │                             │
│                               ▼                             │
│                   ┌───────────────────────┐                │
│                   │     RedisSender       │                │
│                   │   (发送到 Redis)       │                │
│                   └───────────┬───────────┘                │
└───────────────────────────────┼─────────────────────────────┘
                                │
                                ▼
                       ┌────────────────┐
                       │ Redis Streams  │
                       └────────────────┘
```

## 核心组件

### 1. 日志源 (Log Source)

负责从特定来源读取原始日志行。

**接口定义：**

```python
class BaseLogSource(ABC):
    @abstractmethod
    async def read(self) -> AsyncIterator[str]:
        """读取原始日志行"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动日志源"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止日志源"""
        pass
```

**已实现：**
- `DockerSource` - Docker 容器日志
- 待实现：`FileSource` - 文件日志
- 待实现：`K8sSource` - Kubernetes 日志

### 2. 适配器 (Adapter)

负责将原始日志行解析为标准 `LogEntry` 格式。

**接口定义：**

```python
class BaseLogAdapter(ABC):
    @abstractmethod
    def parse(self, raw_line: str) -> LogEntry:
        """解析原始日志行"""
        pass
```

**已实现：**
- `JsonAdapter` - JSON 格式日志
- `GenericAdapter` - 非结构化日志
- 待实现：`NginxAdapter` - Nginx 日志
- 待实现：`ApacheAdapter` - Apache 日志

### 3. 发送器 (Sender)

负责将解析后的日志发送到 Redis Stream。

**主要功能：**
- 单条/批量发送
- 自动重试
- 连接管理

### 4. 采集器 (Collector)

组合 Source 和 Adapter，实现完整的采集流程。

```python
collector = LogCollector(
    source=DockerSource("my-app"),
    adapter=JsonAdapter(service="my-app")
)
await collector.collect(handler)
```

## 数据模型

### LogEntry

标准日志条目格式：

```python
@dataclass
class LogEntry:
    message: str                    # 日志消息
    level: LogLevel                 # 日志级别
    timestamp: str | None           # 日志时间戳
    source: str | None              # 日志来源
    source_type: LogSource | None   # 来源类型
    service: str | None             # 服务名称
    environment: str                # 环境
    stack_trace: str | None         # 堆栈跟踪
    context: dict[str, Any]         # 上下文
    metadata: dict[str, Any]        # 元数据
    collected_at: str               # 采集时间
```

### LogLevel

```python
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

## 使用示例

### 基础使用

```python
from auperator.collector import DockerSource, JsonAdapter, RedisSender, LogEntry

# 创建组件
source = DockerSource("my-app", follow=True)
adapter = JsonAdapter(service="my-app")
sender = RedisSender("redis://localhost:6379")

# 采集日志
await sender.connect()
await source.start()

async for line in source.read():
    entry = adapter.parse(line)
    await sender.send(entry)
```

### 使用管理器

```python
from auperator.collector import LogCollectorManager

manager = LogCollectorManager()

# 添加多个采集任务
await manager.add(
    id="app-logs",
    source=DockerSource("my-app"),
    adapter=JsonAdapter(service="my-app"),
    handler=my_handler,
)

# 启动所有
await manager.start_all()
```

## CLI 命令

```bash
# 采集 Docker 日志
auperator-collector docker <container> -n 100

# 从 Redis 消费日志
auperator-collector consume -v

# 查看 Redis Stream 信息
auperator-collector redis-info

# 测试适配器
auperator-collector test -a json

# 列出容器
auperator-collector list
```

## 文档导航

- [架构设计](collector/architecture.md) - 详细架构设计
- [配置指南](collector/configuration.md) - 配置选项
- [Docker 日志源](collector/docker-source.md) - Docker 采集详解
- [日志适配器](collector/adapters.md) - 适配器详解
- [Redis 消息队列](collector/redis-mq.md) - Redis Streams 使用
