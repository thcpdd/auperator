"""日志源抽象基类"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLogSource(ABC):
    """日志源抽象基类

    负责从特定来源读取原始日志行
    """

    @abstractmethod
    async def read(self) -> AsyncIterator[str]:
        """持续读取原始日志行

        Yields:
            原始日志行 (字符串)
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动日志源"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止日志源"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """日志源名称"""
        pass
