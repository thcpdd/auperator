# 日志适配器

日志适配器负责将原始日志行解析为标准的 `LogEntry` 格式。

## 功能特性

- **适配器模式**: 易于扩展新的日志格式
- **自动检测**: 自动识别日志级别和时间戳
- **错误处理**: 解析失败时的回退机制
- **批量处理**: 支持批量解析

## 内置适配器

### JsonAdapter

解析 JSON 格式的结构化日志。

**适用场景:**
- 应用使用 JSON 格式输出日志
- 结构化日志 (如 Zap, Winston, Pino 等)

**示例日志:**

```json
{"level": "INFO", "msg": "Server started", "time": "2024-01-01T00:00:00Z"}
{"level": "ERROR", "msg": "Database connection failed", "stack": "..."}
```

**使用方式:**

```python
from auperator.collector import JsonAdapter

adapter = JsonAdapter(
    service="my-app",
    environment="production",
)

entry = adapter.parse('{"level": "INFO", "msg": "Hello"}')
```

**识别的字段:**

| 字段类型 | 支持的字段名 |
|----------|-------------|
| 日志级别 | `level`, `LogLevel`, `severity` |
| 消息 | `msg`, `message`, `log`, `text` |
| 时间戳 | `time`, `timestamp`, `@timestamp` |
| 上下文 | `context`, `extra`, `fields`, `data` |
| 堆栈跟踪 | `stack_trace`, `stack`, `exception` |

---

### GenericAdapter

解析非结构化的文本日志。

**适用场景:**
- 传统应用日志
- 系统日志
- 无法识别格式的日志

**示例日志:**

```
2024-01-01 12:00:00 INFO Application started
2024-01-01 12:00:01 ERROR Something went wrong
Jan 01 12:00:00 server sshd[1234]: Accepted password for user
```

**使用方式:**

```python
from auperator.collector import GenericAdapter

adapter = GenericAdapter(
    service="my-app",
    environment="production",
)

entry = adapter.parse("2024-01-01 12:00:00 INFO Hello")
```

**识别的格式:**

| 类型 | 示例 |
|------|------|
| ISO 8601 | `2024-01-01T12:00:00Z` |
| 常见格式 | `2024-01-01 12:00:00` |
| Syslog 格式 | `Jan 01 12:00:00` |
| Nginx 格式 | `01/Jan/2024:12:00:00` |

**识别的日志级别:**

- `ERROR` / `ERR`
- `WARNING` / `WARN`
- `INFO` / `INF`
- `DEBUG` / `DBG`
- `CRITICAL` / `FATAL` / `CRIT`

---

## 选择适配器

```
原始日志格式?
    │
    ├── JSON 格式 ──▶ JsonAdapter
    │
    ├── Nginx 格式 ──▶ NginxAdapter (待实现)
    │
    ├── Apache 格式 ──▶ ApacheAdapter (待实现)
    │
    └── 其他格式 ──▶ GenericAdapter
```

---

## 使用示例

### CLI 方式使用

```bash
# 使用 JSON 适配器
auperator-collector docker my-app -a json

# 使用通用适配器
auperator-collector docker my-app -a generic
```

### Python API 方式

```python
from auperator.collector import DockerSource, JsonAdapter, LogCollector

# 创建组件
source = DockerSource("my-app")
adapter = JsonAdapter(service="my-app")

# 创建采集器
collector = LogCollector(source, adapter)

# 采集日志
await collector.collect(handler)
```

### 批量解析

```python
from auperator.collector import JsonAdapter

adapter = JsonAdapter()

lines = [
    '{"level": "INFO", "msg": "Hello"}',
    '{"level": "ERROR", "msg": "Error"}',
]

entries = adapter.parse_batch(lines)
```

---

## 自定义适配器

继承 `BaseLogAdapter` 创建自定义适配器：

```python
from auperator.collector import BaseLogAdapter, LogEntry, LogLevel

class NginxAdapter(BaseLogAdapter):
    """Nginx 日志适配器"""

    def parse(self, raw_line: str) -> LogEntry:
        # 解析 Nginx 日志格式
        # 127.0.0.1 - - [01/Jan/2024:12:00:00 +0000] "GET /api HTTP/1.1" 200 1234
        match = self.pattern.match(raw_line)
        if match:
            return LogEntry(
                message=f"{match.group('method')} {match.group('path')}",
                level=LogLevel.ERROR if match.group('status').startswith('5') else LogLevel.INFO,
                context={
                    "ip": match.group("ip"),
                    "status": match.group("status"),
                }
            )
        return self._fallback(raw_line)
```

---

## 适配器对比

| 特性 | JsonAdapter | GenericAdapter |
|------|-------------|----------------|
| 解析精度 | 高 | 中 |
| 性能 | 高 | 中 |
| 容错性 | 中 | 高 |
| 适用场景 | 结构化日志 | 非结构化日志 |

---

## 错误处理

### JSON 解析失败

`JsonAdapter` 会在 JSON 解析失败时自动回退到通用解析：

```python
adapter = JsonAdapter()

# JSON 格式正确
entry = adapter.parse('{"level": "INFO", "msg": "Hello"}')
# 正常解析

# JSON 格式错误
entry = adapter.parse('not json format')
# 回退到通用解析，尝试提取级别等信息
```

### 完全无法解析

如果完全无法解析，返回最小化的 `LogEntry`:

```python
entry = adapter.parse("")
# LogEntry(message="", level=INFO, ...)
```

---

## 性能优化

### 批量解析

```python
# 推荐：批量解析
entries = adapter.parse_batch(lines)

# 不推荐：逐条解析
for line in lines:
    entry = adapter.parse(line)
```

### 选择专用适配器

专用适配器比通用适配器性能更好：

```python
# JSON 日志使用 JsonAdapter (更快)
adapter = JsonAdapter()

# 而不是
adapter = GenericAdapter()
```

---

## 文档导航

- [采集器概述](collector/overview.md) - 功能概览
- [Docker 日志源](collector/docker-source.md) - Docker 采集
- [Redis 消息队列](collector/redis-mq.md) - Redis Streams
