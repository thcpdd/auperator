"""日志采集器数据模型"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """从字符串解析日志级别"""
        level = level.upper().strip()
        level_map = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "INF": cls.INFO,  # 缩写
            "WARNING": cls.WARNING,
            "WARN": cls.WARNING,  # 缩写
            "ERROR": cls.ERROR,
            "ERR": cls.ERROR,  # 缩写
            "CRITICAL": cls.CRITICAL,
            "CRIT": cls.CRITICAL,  # 缩写
            "FATAL": cls.CRITICAL,  # FATAL 映射到 CRITICAL
        }
        return level_map.get(level, cls.INFO)


class LogSource(str, Enum):
    """日志来源类型"""

    FILE = "file"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CUSTOM = "custom"


@dataclass
class LogEntry:
    """标准化的日志条目"""

    # 必填字段
    message: str  # 日志消息
    level: LogLevel  # 日志级别

    # 可选字段
    timestamp: str | None = None  # 日志原始时间戳 (ISO8601)
    source: str | None = None  # 日志来源标识 (如文件名、容器名)
    source_type: LogSource | None = None  # 日志来源类型
    service: str | None = None  # 服务名称
    environment: str = "unknown"  # 环境 (production/staging/development)

    # 上下文信息
    stack_trace: str | None = None  # 堆栈跟踪
    context: dict[str, Any] = field(default_factory=dict)  # 额外上下文
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据

    # 系统自动填充
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value if isinstance(self.level, LogLevel) else str(self.level),
            "message": self.message,
            "source": self.source,
            "source_type": self.source_type.value if isinstance(self.source_type, LogSource) else self.source_type,
            "service": self.service,
            "environment": self.environment,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "metadata": self.metadata,
            "collected_at": self.collected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """从字典创建 LogEntry"""
        # 处理 level
        level = data.get("level", "INFO")
        if isinstance(level, str):
            level = LogLevel.from_string(level)

        # 处理 source_type
        source_type = data.get("source_type")
        if isinstance(source_type, str):
            source_type = LogSource(source_type)

        return cls(
            message=data.get("message", ""),
            level=level,
            timestamp=data.get("timestamp"),
            source=data.get("source"),
            source_type=source_type,
            service=data.get("service"),
            environment=data.get("environment", "unknown"),
            stack_trace=data.get("stack_trace"),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            collected_at=data.get("collected_at", datetime.now(timezone.utc).isoformat()),
        )

    def __str__(self) -> str:
        """字符串表示"""
        ts = self.timestamp or self.collected_at
        level_str = self.level.value if isinstance(self.level, LogLevel) else str(self.level)
        return f"[{ts}] [{level_str}] {self.message}"
