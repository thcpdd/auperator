"""日志采集器核心模块

组合日志源和适配器，实现完整的日志采集流程
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from auperator.collector.handlers import BaseLogHandler
from .adapters import BaseLogAdapter
from .models import LogEntry
from .sources.base import BaseLogSource


class CollectorStatus(Enum):
    """采集器状态"""

    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class CollectorConfig:
    """采集器配置"""

    # 日志源配置
    source: BaseLogSource

    # 日志适配器
    adapter: BaseLogAdapter

    # 批处理大小 (0 表示不批处理)
    batch_size: int = 0

    # 批处理超时 (秒)
    batch_timeout: float = 1.0

    # 重试次数
    max_retries: int = 3

    # 重试延迟 (秒)
    retry_delay: float = 5.0


class LogCollector:
    """日志采集器

    组合 BaseLogSource 和 BaseLogAdapter，实现完整的日志采集流程

    Example:
        >>> from collector.sources import DockerSource
        >>> from collector.adapters import JsonAdapter
        >>>
        >>> source = DockerSource("my-container")
        >>> adapter = JsonAdapter(service="my-app")
        >>> collector = LogCollector(source, adapter)
        >>>
        >>> async def handler(entry: LogEntry):
        ...     print(entry)
        >>>
        >>> await collector.collect(handler)
    """

    def __init__(
        self,
        source: BaseLogSource,
        adapter: BaseLogAdapter,
        handler: BaseLogHandler,
        batch_size: int = 0,
        batch_timeout: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        """初始化日志采集器

        Args:
            source: 日志源
            adapter: 日志适配器
            batch_size: 批处理大小 (0 表示不批处理)
            batch_timeout: 批处理超时 (秒)
            max_retries: 最大重试次数
            retry_delay: 重试延迟 (秒)
        """
        self.source = source
        self.adapter = adapter
        self.handler = handler

        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._status = CollectorStatus.PENDING
        self._task: asyncio.Task | None = None
        self._error: Exception | None = None

    @property
    def status(self) -> CollectorStatus:
        """当前状态"""
        return self._status

    @property
    def name(self) -> str:
        """采集器名称"""
        return self.source.name

    @property
    def error(self) -> Exception | None:
        """错误信息"""
        return self._error

    async def collect(self) -> None:
        """开始采集日志

        Args:
            handler: 日志处理器
        """
        self._status = CollectorStatus.RUNNING

        try:
            await self.source.start()

            if self.batch_size > 0:
                await self._collect_batched()
            else:
                await self._collect_streaming()

        except Exception as e:
            self._error = e
            self._status = CollectorStatus.ERROR
            raise
        finally:
            if self._status == CollectorStatus.RUNNING:
                self._status = CollectorStatus.STOPPED
            await self.source.stop()

    async def _collect_streaming(self) -> None:
        """流式采集 (逐条处理)"""
        async for raw_line in self.source.read():
            if self._status != CollectorStatus.RUNNING:
                break

            entry = self.adapter.parse(raw_line)
            await self.handler.handle(entry)

    async def _collect_batched(self) -> None:
        """批处理采集"""
        batch: list[LogEntry] = []
        last_flush = asyncio.get_event_loop().time()

        async for raw_line in self.source.read():
            if self._status != CollectorStatus.RUNNING:
                break

            entry = self.adapter.parse(raw_line)
            batch.append(entry)

            # 检查是否需要刷新批次
            now = asyncio.get_event_loop().time()
            if len(batch) >= self.batch_size or (now - last_flush) >= self.batch_timeout:
                for e in batch:
                    await handler.handle(e)
                batch = []
                last_flush = now

        # 处理剩余日志
        for e in batch:
            await handler.handle(e)

    async def start(self) -> None:
        """后台启动采集器"""
        self._task = asyncio.create_task(self.collect())

    async def stop(self) -> None:
        """停止采集器"""
        if self._status == CollectorStatus.RUNNING:
            self._status = CollectorStatus.STOPPING
            await self.source.stop()

            if self._task:
                try:
                    await asyncio.wait_for(self._task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._task.cancel()
                    try:
                        await self._task
                    except asyncio.CancelledError:
                        pass

    def collect_sync(self, lines: list[str]) -> list[LogEntry]:
        """同步批量解析日志 (用于测试)

        Args:
            lines: 原始日志行列表

        Returns:
            解析后的 LogEntry 列表
        """
        return self.adapter.parse_batch(lines)
