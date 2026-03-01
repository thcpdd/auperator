"""日志采集器核心模块

组合日志源和适配器，实现完整的日志采集流程
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

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


class LogHandler(Protocol):
    """日志处理器协议

    用于处理采集到的日志条目
    """

    async def handle(self, entry: LogEntry) -> None:
        """处理日志条目

        Args:
            entry: 日志条目
        """
        ...


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

    async def collect(self, handler: LogHandler) -> None:
        """开始采集日志

        Args:
            handler: 日志处理器
        """
        self._status = CollectorStatus.RUNNING

        try:
            await self.source.start()

            if self.batch_size > 0:
                await self._collect_batched(handler)
            else:
                await self._collect_streaming(handler)

        except Exception as e:
            self._error = e
            self._status = CollectorStatus.ERROR
            raise
        finally:
            if self._status == CollectorStatus.RUNNING:
                self._status = CollectorStatus.STOPPED
            await self.source.stop()

    async def _collect_streaming(self, handler: LogHandler) -> None:
        """流式采集 (逐条处理)"""
        async for raw_line in self.source.read():
            if self._status != CollectorStatus.RUNNING:
                break

            entry = self.adapter.parse(raw_line)
            await handler.handle(entry)

    async def _collect_batched(self, handler: LogHandler) -> None:
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

    async def start(self, handler: LogHandler) -> None:
        """后台启动采集器

        Args:
            handler: 日志处理器
        """
        self._task = asyncio.create_task(self.collect(handler))

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


@dataclass
class CollectorInstance:
    """采集器实例 (用于管理器)"""

    id: str
    config: CollectorConfig
    collector: LogCollector
    handler: LogHandler
    status: CollectorStatus = CollectorStatus.PENDING
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class LogCollectorManager:
    """日志采集器管理器

    管理多个采集器实例，支持动态添加/移除采集任务

    Example:
        >>> manager = LogCollectorManager()
        >>>
        >>> # 添加采集任务
        >>> await manager.add(
        ...     id="app-logs",
        ...     source=DockerSource("my-app"),
        ...     adapter=JsonAdapter(service="my-app"),
        ...     handler=my_handler
        ... )
        >>>
        >>> # 启动所有采集器
        >>> await manager.start_all()
        >>>
        >>> # 停止特定采集器
        >>> await manager.stop("app-logs")
    """

    def __init__(self):
        """初始化管理器"""
        self._collectors: dict[str, CollectorInstance] = {}
        self._running = False

    @property
    def collector_ids(self) -> list[str]:
        """所有采集器 ID 列表"""
        return list(self._collectors.keys())

    @property
    def running_count(self) -> int:
        """运行中的采集器数量"""
        return sum(1 for c in self._collectors.values() if c.status == CollectorStatus.RUNNING)

    async def add(
        self,
        id: str,
        source: BaseLogSource,
        adapter: BaseLogAdapter,
        handler: LogHandler,
        **collector_kwargs,
    ) -> LogCollector:
        """添加采集器

        Args:
            id: 采集器唯一标识
            source: 日志源
            adapter: 日志适配器
            handler: 日志处理器
            **collector_kwargs: 传递给 LogCollector 的其他参数

        Returns:
            创建的 LogCollector 实例

        Raises:
            ValueError: ID 已存在
        """
        if id in self._collectors:
            raise ValueError(f"采集器已存在：{id}")

        collector = LogCollector(
            source=source,
            adapter=adapter,
            **collector_kwargs,
        )

        instance = CollectorInstance(
            id=id,
            config=CollectorConfig(source=source, adapter=adapter),
            collector=collector,
            handler=handler,
        )

        self._collectors[id] = instance
        return collector

    async def remove(self, id: str) -> None:
        """移除采集器

        Args:
            id: 采集器 ID
        """
        if id not in self._collectors:
            return

        instance = self._collectors[id]
        if instance.status == CollectorStatus.RUNNING:
            await self.stop(id)

        del self._collectors[id]

    async def start(self, id: str) -> None:
        """启动指定采集器

        Args:
            id: 采集器 ID
        """
        if id not in self._collectors:
            raise ValueError(f"采集器不存在：{id}")

        instance = self._collectors[id]
        if instance.status == CollectorStatus.RUNNING:
            return

        await instance.collector.start(instance.handler)
        instance.status = CollectorStatus.RUNNING

    async def stop(self, id: str) -> None:
        """停止指定采集器

        Args:
            id: 采集器 ID
        """
        if id not in self._collectors:
            return

        instance = self._collectors[id]
        await instance.collector.stop()
        instance.status = instance.collector.status

    async def start_all(self) -> None:
        """启动所有采集器"""
        for id in self.collector_ids:
            try:
                await self.start(id)
            except Exception as e:
                # 记录错误但继续启动其他采集器
                print(f"启动采集器 {id} 失败：{e}")

    async def stop_all(self) -> None:
        """停止所有采集器"""
        tasks = [self.stop(id) for id in self.collector_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_status(self, id: str) -> CollectorStatus | None:
        """获取采集器状态

        Args:
            id: 采集器 ID

        Returns:
            状态，不存在则返回 None
        """
        if id not in self._collectors:
            return None
        return self._collectors[id].status

    def get_collector(self, id: str) -> LogCollector | None:
        """获取采集器实例

        Args:
            id: 采集器 ID

        Returns:
            采集器实例，不存在则返回 None
        """
        if id not in self._collectors:
            return None
        return self._collectors[id].collector
