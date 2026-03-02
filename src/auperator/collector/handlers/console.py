"""控制台日志处理器"""

import json

from .base import BaseLogHandler
from ..models import LogEntry


class ConsoleHandler(BaseLogHandler):
    """控制台日志处理器

    将日志输出到控制台，支持 verbose 详细模式和彩色输出
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def handle(self, entry: LogEntry) -> None:
        """处理日志条目

        Args:
            entry: 日志条目
        """
        if self.verbose:
            print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        else:
            level_color = {
                "DEBUG": "\033[36m",
                "INFO": "\033[32m",
                "WARNING": "\033[33m",
                "ERROR": "\033[31m",
                "CRITICAL": "\033[35m",
            }
            color = level_color.get(entry.level.value, "\033[0m")
            reset = "\033[0m"
            print(f"{color}[{entry.level.value}]{reset} {entry.message}")
