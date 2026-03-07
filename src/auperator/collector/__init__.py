"""日志采集器模块"""

from .adapters import BaseLogAdapter, VectorAdapter
from .handlers import BaseLogHandler, ConsoleHandler
from .models import LogEntry, LogLevel, LogSource
from .sources.base import BaseLogSource
from .vector_consumer import VectorRedisConsumer

__all__ = [
    # 数据模型
    "LogEntry",
    "LogLevel",
    "LogSource",
    # 抽象基类
    "BaseLogSource",
    "BaseLogAdapter",
    "BaseLogHandler",
    # Vector 集成
    "VectorAdapter",
    "VectorRedisConsumer",
    # 日志处理器
    "ConsoleHandler",
]
