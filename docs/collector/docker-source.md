# Docker 日志源

Docker 日志源用于从 Docker 容器采集日志。

## 功能特性

- 实时流式读取 (类似 `docker logs -f`)
- 支持 tail 参数控制初始行数
- 支持时间过滤 (since/until)
- 自动重连机制
- 支持容器名称和 ID

## 基本使用

### CLI 方式

```bash
# 采集容器日志
auperator-collector docker my-app

# 持续跟踪日志
auperator-collector docker my-app -f

# 采集最近 1000 行
auperator-collector docker my-app -n 1000
```

### Python API

```python
from auperator.collector import DockerSource

source = DockerSource(
    container_name="my-app",
    follow=True,
    tail=100,
)

await source.start()

async for line in source.read():
    print(line)

await source.stop()
```

## 配置参数

### DockerSource 参数

```python
class DockerSource(BaseLogSource):
    def __init__(
        self,
        container_name: str,        # 容器名称或 ID (必填)
        follow: bool = True,        # 是否持续跟踪日志
        tail: int = 100,            # 初始读取行数 (0 表示全部)
        since: str | None = None,   # 从此时间之后的日志
        until: str | None = None,   # 到此时间之前的日志
        timestamps: bool = False,   # 是否包含时间戳
        service: str | None = None, # 服务名称
        environment: str = "unknown", # 环境标识
    ):
```

### 参数说明

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `container_name` | str | - | 容器名称或 ID (必填) |
| `follow` | bool | `True` | 是否持续跟踪日志 |
| `tail` | int | `100` | 初始读取行数，0 表示全部 |
| `since` | str | `None` | 从此时间之后的日志 |
| `until` | str | `None` | 到此时间之前的日志 |
| `timestamps` | bool | `False` | 是否包含时间戳 |
| `service` | str | `None` | 服务名称 (用于标识) |
| `environment` | str | `"unknown"` | 环境标识 |

## 使用场景

### 场景 1: 实时采集应用日志

```python
source = DockerSource(
    container_name="web-app",
    follow=True,
    tail=0,  # 从最新日志开始
    service="web-app",
    environment="production",
)
```

### 场景 2: 采集指定时间范围的日志

```python
source = DockerSource(
    container_name="api-server",
    follow=False,
    since="2024-01-01T00:00:00Z",
    until="2024-01-01T23:59:59Z",
)
```

### 场景 3: 采集多个容器日志

```python
containers = ["web-app", "api-server", "db"]

for container in containers:
    source = DockerSource(
        container_name=container,
        follow=True,
        service=container,
    )
    # 添加到采集管理器
```

## 与适配器配合使用

### JSON 格式日志

```python
from auperator.collector import DockerSource, JsonAdapter, LogCollector

source = DockerSource("my-app")
adapter = JsonAdapter(service="my-app")

collector = LogCollector(source, adapter)
await collector.collect(handler)
```

### 通用格式日志

```python
from auperator.collector import DockerSource, GenericAdapter

source = DockerSource("nginx")
adapter = GenericAdapter(service="nginx")
```

## 错误处理

### 容器不存在

```python
try:
    source = DockerSource("non-existent-container")
    await source.start()
except RuntimeError as e:
    print(f"容器未找到：{e}")
```

### Docker 未运行

```python
try:
    source = DockerSource("my-app")
    await source.start()
except RuntimeError as e:
    print(f"无法连接 Docker: {e}")
```

## 完整示例

### 采集日志到 Redis

```python
import asyncio
from auperator.collector import DockerSource, JsonAdapter, RedisSender

async def main():
    # 创建组件
    source = DockerSource(
        container_name="my-app",
        follow=True,
        tail=100,
        service="my-app",
        environment="production",
    )

    adapter = JsonAdapter(
        service="my-app",
        environment="production",
    )

    sender = RedisSender("redis://localhost:6379")

    # 连接
    await sender.connect()
    await source.start()

    # 采集日志
    try:
        async for line in source.read():
            entry = adapter.parse(line)
            await sender.send(entry)
    except KeyboardInterrupt:
        print("正在停止...")
    finally:
        await sender.close()
        await source.stop()

asyncio.run(main())
```

### 使用采集器管理器

```python
from auperator.collector import LogCollectorManager, DockerSource, JsonAdapter

async def main():
    manager = LogCollectorManager()

    # 添加多个采集任务
    await manager.add(
        id="web-logs",
        source=DockerSource("web-app"),
        adapter=JsonAdapter(service="web-app"),
        handler=my_handler,
    )

    await manager.add(
        id="api-logs",
        source=DockerSource("api-server"),
        adapter=JsonAdapter(service="api-server"),
        handler=my_handler,
    )

    # 启动所有
    await manager.start_all()

asyncio.run(main())
```

## 性能考虑

### Tail 参数优化

- `tail=0`: 从最新日志开始，适合实时采集
- `tail=100`: 采集最近 100 行，适合调试
- `tail=all` (0): 采集所有历史日志，首次启动时可能较慢

### Follow 模式

- `follow=True`: 持续跟踪，适合长期运行
- `follow=False`: 采集现有日志后退出，适合一次性采集

## 常见问题

### Q: 采集器无法连接 Docker？

确保 Docker 服务正在运行，并且当前用户有权限访问 Docker：

```bash
# 检查 Docker 状态
docker ps

# 添加用户到 docker 组
sudo usermod -aG docker $USER
```

### Q: 日志乱码？

确保容器日志使用 UTF-8 编码：

```python
# 采集器会自动处理编码问题
# 使用 errors="replace" 处理无法解码的字符
```

### Q: 如何采集多行日志（如堆栈跟踪）？

使用支持多行合并的适配器，或在应用层配置单行日志。

## 文档导航

- [采集器概述](collector/overview.md) - 功能概览
- [配置指南](collector/configuration.md) - 配置选项
- [日志适配器](collector/adapters.md) - 适配器详解
