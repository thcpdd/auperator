"""日志处理器模块"""

from .base import BaseLogHandler
from .console import ConsoleHandler

__all__ = [
    "BaseLogHandler",
    "ConsoleHandler",
]
