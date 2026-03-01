# 日志采集器实现总结

本文档记录日志采集器的实现状态和细节。

## 实现状态

| 模块 | 状态 | 文件 |
|------|------|------|
| 数据模型 | ✅ 完成 | `src/auperator/collector/models.py` |
| 抽象基类 | ✅ 完成 | `src/auperator/collector/base.py` |
| Docker 日志源 | ✅ 完成 | `src/auperator/collector/sources/docker_source.py` |
| JSON 适配器 | ✅ 完成 | `src/auperator/collector/adapters/json_adapter.py` |
| 通用适配器 | ✅ 完成 | `src/auperator/collector/adapters/generic_adapter.py` |
| 采集器核心 | ✅ 完成 | `src/auperator/collector/collector.py` |
| Redis 发送器 | ✅ 完成 | `src/auperator/collector/sender.py` |
| Redis 消费者 | ✅ 完成 | `src/auperator/collector/consumer.py` |
| CLI 命令行 | ✅ 完成 | `src/auperator/collector/cli.py` |

### 计划中

| 模块 | 优先级 | 描述 |
|------|--------|------|
| 文件日志源 | 高 | 支持从文件采集日志 |
| Kubernetes 日志源 | 中 | 支持从 K8s Pod 采集 |
| Nginx 适配器 | 中 | 解析 Nginx 日志格式 |
| Apache 适配器 | 低 | 解析 Apache 日志格式 |
| 配置管理 | 高 | YAML 配置文件支持 |

---

## 文件结构

```
src/auperator/
├── __init__.py
├── cli.py                          # 主 CLI 入口
├── main.py
│
└── collector/                      # 日志采集器模块
    ├── __init__.py
    ├── base.py                     # 抽象基类
    ├── models.py                   # 数据模型
    ├── collector.py                # 采集器核心
    ├── sender.py                   # Redis 发送器
    ├── consumer.py                 # Redis 消费者
    ├── cli.py                      # CLI 命令
    │
    ├── sources/                    # 日志源
    │   ├── __init__.py
    │   ├── base.py                 # 日志源抽象基类
    │   └── docker_source.py        # Docker 日志源
    │
    └── adapters/                   # 日志适配器
        ├── __init__.py
        ├── base.py                 # 适配器抽象基类
        ├── json_adapter.py         # JSON 适配器
        └── generic_adapter.py      # 通用适配器
```

---

## 核心设计

### 架构

```
Source (读取) ──▶ Adapter (解析) ──▶ Sender (发送) ──▶ Redis Streams
```

### 数据流

```
1. DockerSource.read() ──▶ 原始日志行 (str)
2. JsonAdapter.parse() ──▶ LogEntry
3. RedisSender.send() ──▶ Redis Stream
4. RedisConsumer.consume() ──▶ Agent 处理
```

---

## 使用示例

### 采集器

```python
from auperator.collector import DockerSource, JsonAdapter, RedisSender

source = DockerSource("my-app", follow=True)
adapter = JsonAdapter(service="my-app")
sender = RedisSender("redis://localhost:6379")

await sender.connect()
await source.start()

async for line in source.read():
    entry = adapter.parse(line)
    await sender.send(entry)
```

### 消费者

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

await consumer.consume(handler)
```

---

## CLI 命令

```bash
# 采集 Docker 日志
auperator-collector docker my-app -n 100

# 从 Redis 消费日志
auperator-collector consume -v

# 查看 Redis Stream 信息
auperator-collector redis-info

# 测试适配器
auperator-collector test -a json

# 列出容器
auperator-collector list
```

---

## 依赖

```toml
[dependencies]
docker>=7.1.0
redis>=7.2.1
typer>=0.9.0
pydantic>=2.0.0
```

---

## 测试

```bash
# 安装依赖
uv sync

# 运行测试
uv run python test_collector.py

# 测试 CLI
uv run auperator-collector test -a json
```

---

## 下一步计划

1. **文件日志源** - 支持从文件采集
2. **配置管理** - YAML 配置文件
3. **更多适配器** - Nginx/Apache 等
4. **Agent 集成** - 与 DeepAgents 集成

---

## 文档导航

- [采集器概述](collector/overview.md) - 功能介绍
- [架构设计](collector/architecture.md) - 详细架构
- [配置指南](collector/configuration.md) - 配置说明
- [CLI 参考](collector/cli-reference.md) - 命令手册
