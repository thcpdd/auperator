"""日志处理器抽象基类"""

from abc import ABC, abstractmethod

from ..models import LogEntry


class BaseLogHandler(ABC):
    """日志处理器抽象基类

    所有日志处理器都应继承此类并实现 handle 方法
    """

    @abstractmethod
    async def handle(self, entry: LogEntry) -> None:
        """处理日志条目

        Args:
            entry: 日志条目
        """
        pass
