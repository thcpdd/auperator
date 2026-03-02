"""基于 Redis Streams 的日志消费者

Agent 使用此消费者从 Redis Stream 读取日志并处理
"""

import asyncio
import json
from typing import Any, Callable

import redis.asyncio as redis

from auperator.config import settings
from .models import LogEntry


class RedisConsumer:
    """Redis Streams 消费者

    从 Redis Stream 读取日志并调用处理器

    Example:
        >>> consumer = RedisConsumer("redis://localhost:6379")
        >>>
        >>> async def handler(entry: LogEntry):
        ...     print(f"收到日志：{entry.message}")
        >>>
        >>> await consumer.consume(handler)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        stream_name: str | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
        batch_size: int | None = None,
        block_timeout: int | None = None,
    ):
        """初始化 Redis 消费者

        Args:
            redis_url: Redis 连接 URL（默认从 settings 读取）
            stream_name: Stream 名称（默认从 settings 读取）
            group_name: 消费者组名称（默认从 settings 读取）
            consumer_name: 消费者名称
            batch_size: 每次读取的消息数（默认从 settings 读取）
            block_timeout: 阻塞读取超时时间 (毫秒)
        """
        self.redis_url = redis_url or settings.get_redis_url()
        # 添加 key 前缀
        stream_name_raw = stream_name or settings.redis.stream_name
        self.stream_name = settings.redis.add_prefix(stream_name_raw)
        self.group_name = group_name or settings.redis.consumer_group
        self.consumer_name = consumer_name or "agent-1"
        self.batch_size = batch_size if batch_size is not None else settings.collector.batch_size
        self.block_timeout = block_timeout if block_timeout is not None else 5000

        self._redis: redis.Redis | None = None
        self._running = False

    async def connect(self) -> None:
        """连接 Redis 并加入消费者组"""
        self._redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # 尝试创建消费者组（如果不存在）
        try:
            await self._redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        self._running = True

    async def close(self) -> None:
        """关闭连接"""
        self._running = False
        if self._redis:
            await self._redis.close()

    async def consume(
        self,
        handler: Callable[[LogEntry], Any],
        on_error: Callable[[Exception, LogEntry | None], Any] | None = None,
    ) -> None:
        """持续消费日志

        Args:
            handler: 日志处理函数
            on_error: 错误处理函数
        """
        await self.connect()

        try:
            while self._running:
                try:
                    # 从消费者组读取消息
                    messages = await self._redis.xreadgroup(
                        groupname=self.group_name,
                        consumername=self.consumer_name,
                        streams={self.stream_name: ">"},  # ">" 表示新消息
                        count=self.batch_size,
                        block=self.block_timeout,
                    )

                    if not messages:
                        continue

                    # 处理消息
                    for stream_name, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                entry = self._parse_message(fields)
                                await handler(entry)
                                # 确认消息已处理
                                await self._redis.xack(
                                    self.stream_name,
                                    self.group_name,
                                    message_id,
                                )
                            except Exception as e:
                                if on_error:
                                    await on_error(e, None)
                                # 即使处理失败也确认消息，避免死循环

                except redis.RedisError as e:
                    if on_error:
                        await on_error(e, None)
                    await asyncio.sleep(1)

        finally:
            await self.close()

    def _parse_message(self, fields: dict[str, str]) -> LogEntry:
        """解析消息字段为 LogEntry"""
        data_str = fields.get("data", "{}")
        data = json.loads(data_str)
        return LogEntry.from_dict(data)

    async def consume_batch(
        self,
        batch_handler: Callable[[list[LogEntry]], Any],
        on_error: Callable[[Exception], Any] | None = None,
    ) -> None:
        """批量消费日志

        Args:
            batch_handler: 批量日志处理函数
            on_error: 错误处理函数
        """
        await self.connect()

        try:
            while self._running:
                try:
                    messages = await self._redis.xreadgroup(
                        groupname=self.group_name,
                        consumername=self.consumer_name,
                        streams={self.stream_name: ">"},
                        count=self.batch_size,
                        block=self.block_timeout,
                    )

                    if not messages:
                        continue

                    entries = []
                    message_ids = []

                    for stream_name, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                entry = self._parse_message(fields)
                                entries.append(entry)
                                message_ids.append(message_id)
                            except Exception as e:
                                if on_error:
                                    await on_error(e)

                    if entries:
                        await batch_handler(entries)
                        # 批量确认
                        await self._redis.xack(
                            self.stream_name,
                            self.group_name,
                            *message_ids,
                        )

                except redis.RedisError as e:
                    if on_error:
                        await on_error(e)
                    await asyncio.sleep(1)

        finally:
            await self.close()

    async def read_pending(self) -> list[tuple[str, LogEntry]]:
        """读取待处理的消息（已分配但未确认）

        Returns:
            [(message_id, LogEntry), ...]
        """
        if not self._redis:
            await self.connect()

        # 读取待处理消息
        pending = await self._redis.xpending_range(
            self.stream_name,
            self.group_name,
            min="-",
            max="+",
            count=self.batch_size,
        )

        results = []
        for p in pending:
            message_id = p["message_id"]
            fields = await self._redis.xrange(
                self.stream_name,
                min=message_id,
                max=message_id,
                count=1,
            )
            if fields:
                _, data = fields[0]
                entry = self._parse_message(data)
                results.append((message_id, entry))

        return results

    async def claim_pending(
        self,
        min_idle_time: int = 30000,  # 毫秒
    ) -> list[tuple[str, LogEntry]]:
        """获取并认领超时未处理的消息

        Args:
            min_idle_time: 最小空闲时间 (毫秒)

        Returns:
            [(message_id, LogEntry), ...]
        """
        if not self._redis:
            await self.connect()

        # 使用 XAUTOCLAIM 认领消息
        _, claimed = await self._redis.xautoclaim(
            self.stream_name,
            self.group_name,
            self.consumer_name,
            min_idle_time=min_idle_time,
            start_id="0-0",
            count=self.batch_size,
        )

        results = []
        for message_id, fields in claimed:
            entry = self._parse_message(fields)
            results.append((message_id, entry))

        return results

    async def stop(self) -> None:
        """停止消费"""
        self._running = False

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
