# 快速开始

本文档帮助你快速上手 Auperator 日志采集器。

## 前置条件

确保已完成 [安装](installation.md) 并启动 Redis：

```bash
docker run -d --name redis -p 6379:6379 redis:7
```

## 第一步：采集 Docker 容器日志

假设你有一个正在运行的 Docker 容器 `my-app`：

```bash
# 查看运行中的容器
uv run auperator-collector list

# 采集容器日志并发送到 Redis
uv run auperator-collector docker my-app -n 100
```

参数说明：
- `-n 100`: 采集最近 100 行日志
- `-f`: 持续跟踪新日志（类似 `docker logs -f`）
- `-r redis://localhost:6379`: Redis 地址
- `-s logs:main`: Stream 名称

## 第二步：从 Redis 消费日志

启动一个新的终端窗口，运行消费者：

```bash
uv run auperator-collector consume -v
```

参数说明：
- `-v`: 详细输出模式
- `-g auperator-group`: 消费者组名称
- `-n agent-1`: 消费者名称

## 第三步：查看 Redis Stream 状态

```bash
uv run auperator-collector redis-info
```

输出示例：

```
Stream: logs:main
  消息数量：150
  消费者组数：1
  第一个消息：1709251200000-0
  最后一个消息：1709251300000-0
```

## 使用 Python API

### 采集器示例

```python
import asyncio
from auperator.collector import DockerSource, JsonAdapter, RedisSender

async def main():
    source = DockerSource("my-app", follow=True, tail=100)
    adapter = JsonAdapter(service="my-app")
    sender = RedisSender("redis://localhost:6379")

    await sender.connect()
    await source.start()

    async for line in source.read():
        entry = adapter.parse(line)
        await sender.send(entry)

asyncio.run(main())
```

### 消费者示例

```python
import asyncio
from auperator.collector import RedisConsumer, LogEntry

async def handle_entry(entry: LogEntry):
    print(f"[{entry.level.value}] {entry.message}")

async def main():
    consumer = RedisConsumer(
        redis_url="redis://localhost:6379",
        stream_name="logs:main",
        group_name="auperator-group",
        consumer_name="agent-1",
    )
    await consumer.consume(handle_entry)

asyncio.run(main())
```

## 下一步

- [采集器概述](collector/overview.md) - 了解更多功能
- [配置指南](collector/configuration.md) - 高级配置
- [架构设计](architecture.md) - 了解系统架构
