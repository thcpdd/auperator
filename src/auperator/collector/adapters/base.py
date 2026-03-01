"""日志适配器抽象基类"""

from abc import ABC, abstractmethod

from ..models import LogEntry


class BaseLogAdapter(ABC):
    """日志适配器抽象基类

    负责将原始日志行解析为标准 LogEntry
    """

    @abstractmethod
    def parse(self, raw_line: str) -> LogEntry:
        """解析原始日志行

        Args:
            raw_line: 原始日志字符串

        Returns:
            标准化的 LogEntry
        """
        pass

    def parse_batch(self, lines: list[str]) -> list[LogEntry]:
        """批量解析日志行

        Args:
            lines: 原始日志字符串列表

        Returns:
            LogEntry 列表
        """
        return [self.parse(line) for line in lines]
