"""日志采集器模块"""

from .adapters import BaseLogAdapter, GenericAdapter, JsonAdapter
from .collector import CollectorStatus, LogCollector
from .consumer import RedisConsumer
from .handlers import ConsoleHandler, RedisHandler
from .models import LogEntry, LogLevel, LogSource
from .sources.docker_source import DockerSource
from .sources.base import BaseLogSource

__all__ = [
    # 数据模型
    "LogEntry",
    "LogLevel",
    "LogSource",
    # 抽象基类
    "BaseLogSource",
    "BaseLogAdapter",
    # 采集器
    "LogCollector",
    "LogCollectorManager",
    "CollectorStatus",
    # 消费者
    "RedisConsumer",
    # 日志处理器
    "ConsoleHandler",
    "RedisHandler",
    # 日志源
    "DockerSource",
    # 适配器
    "JsonAdapter",
    "GenericAdapter",
]
