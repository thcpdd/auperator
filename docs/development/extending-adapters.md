# 扩展适配器

本文档介绍如何自定义日志适配器。

## 基础类

所有适配器都需要继承 `BaseLogAdapter`：

```python
from auperator.collector.adapters.base import BaseLogAdapter
from auperator.collector.models import LogEntry

class BaseLogAdapter(ABC):
    @abstractmethod
    def parse(self, raw_line: str) -> LogEntry:
        """解析原始日志行"""
        pass

    def parse_batch(self, lines: list[str]) -> list[LogEntry]:
        """批量解析"""
        return [self.parse(line) for line in lines]
```

## 实现示例

### Nginx 日志适配器

```python
import re
from datetime import datetime
from ..models import LogEntry, LogLevel
from .base import BaseLogAdapter


class NginxAdapter(BaseLogAdapter):
    """Nginx 日志适配器"""

    # Nginx 日志格式正则
    # 127.0.0.1 - - [01/Jan/2024:12:00:00 +0000] "GET /api HTTP/1.1" 200 1234
    PATTERN = re.compile(
        r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
        r'"(?P<method>\w+)\s+(?P<path>\S+)\s+[^"]*"\s+'
        r'(?P<status>\d+)\s+(?P<size>\d+)'
    )

    def __init__(
        self,
        service: str | None = None,
        environment: str = "unknown",
    ):
        self.service = service
        self.environment = environment

    def parse(self, raw_line: str) -> LogEntry:
        """解析 Nginx 日志"""
        match = self.PATTERN.match(raw_line.strip())

        if not match:
            return self._fallback(raw_line)

        groups = match.groupdict()

        # 解析时间
        timestamp = self._parse_time(groups["time"])

        # 根据状态码判断级别
        status = groups["status"]
        if status.startswith("5"):
            level = LogLevel.ERROR
        elif status.startswith("4"):
            level = LogLevel.WARNING
        else:
            level = LogLevel.INFO

        return LogEntry(
            message=f"{groups['method']} {groups['path']} {status}",
            level=level,
            timestamp=timestamp,
            service=self.service,
            environment=self.environment,
            context={
                "ip": groups["ip"],
                "method": groups["method"],
                "path": groups["path"],
                "status": status,
                "size": groups["size"],
            },
            metadata={"raw": raw_line},
        )

    def _parse_time(self, time_str: str) -> str:
        """解析 Nginx 时间格式"""
        try:
            dt = datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
            return dt.isoformat()
        except ValueError:
            return None

    def _fallback(self, raw_line: str) -> LogEntry:
        """回退处理"""
        return LogEntry(
            message=raw_line.strip(),
            level=LogLevel.INFO,
            service=self.service,
            environment=self.environment,
            metadata={"raw": raw_line, "parse_error": "nginx_pattern_mismatch"},
        )
```

### Python Logging 适配器

```python
import re
from ..models import LogEntry, LogLevel
from .base import BaseLogAdapter


class PythonLoggingAdapter(BaseLogAdapter):
    """Python logging 模块日志适配器"""

    # 2024-01-01 12:00:00,123 - module.name - INFO - Message
    PATTERN = re.compile(
        r'(?P<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+-\s+'
        r'(?P<logger>\S+)\s+-\s+(?P<level>\w+)\s+-\s+(?P<message>.*)'
    )

    def parse(self, raw_line: str) -> LogEntry:
        match = self.PATTERN.match(raw_line.strip())

        if not match:
            return LogEntry(
                message=raw_line.strip(),
                level=LogLevel.INFO,
            )

        groups = match.groupdict()

        return LogEntry(
            message=groups["message"],
            level=LogLevel.from_string(groups["level"]),
            timestamp=groups["time"].replace(",", "."),
            context={"logger": groups["logger"]},
        )
```

### Java Log4j 适配器

```python
import re
from ..models import LogEntry, LogLevel
from .base import BaseLogAdapter


class Log4jAdapter(BaseLogAdapter):
    """Java Log4j 日志适配器"""

    # 2024-01-01 12:00:00.123 INFO  [main] com.example.Class - Message
    PATTERN = re.compile(
        r'(?P<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+'
        r'(?P<level>\w+)\s+'
        r'(?:\[(?P<thread>\S+)\]\s+)?'
        r'(?P<logger>\S+)\s+-\s+(?P<message>.*)'
    )

    def parse(self, raw_line: str) -> LogEntry:
        match = self.PATTERN.match(raw_line.strip())

        if not match:
            return LogEntry(
                message=raw_line.strip(),
                level=LogLevel.INFO,
            )

        groups = match.groupdict()

        context = {"logger": groups["logger"]}
        if groups.get("thread"):
            context["thread"] = groups["thread"]

        return LogEntry(
            message=groups["message"],
            level=LogLevel.from_string(groups["level"]),
            timestamp=groups["time"],
            context=context,
        )
```

## 注册适配器

在 `adapters/__init__.py` 中导出：

```python
from .base import BaseLogAdapter
from .json_adapter import JsonAdapter
from .generic_adapter import GenericAdapter
from .nginx_adapter import NginxAdapter
from .log4j_adapter import Log4jAdapter

__all__ = [
    "BaseLogAdapter",
    "JsonAdapter",
    "GenericAdapter",
    "NginxAdapter",
    "Log4jAdapter",
]
```

## 使用自定义适配器

```python
from auperator.collector import DockerSource, NginxAdapter, LogCollector

source = DockerSource("nginx")
adapter = NginxAdapter(service="nginx", environment="production")

collector = LogCollector(source, adapter)
await collector.collect(handler)
```

## 适配器工厂

可以根据日志格式自动选择适配器：

```python
class AdapterFactory:
    """适配器工厂"""

    @staticmethod
    def detect_adapter(line: str) -> BaseLogAdapter:
        """根据日志行自动检测适配器"""
        if line.strip().startswith("{"):
            return JsonAdapter()
        elif NginxAdapter.PATTERN.match(line):
            return NginxAdapter()
        elif Log4jAdapter.PATTERN.match(line):
            return Log4jAdapter()
        else:
            return GenericAdapter()
```

## 注意事项

1. **性能**: 避免在 `parse()` 中执行耗时操作
2. **容错**: 解析失败时返回合理的默认值
3. **正则优化**: 预编译正则表达式
4. **内存**: 避免在解析时创建过多对象

## 文档导航

- [采集器概述](collector/overview.md)
- [日志适配器](collector/adapters.md)
- [扩展日志源](extending-sources.md)
