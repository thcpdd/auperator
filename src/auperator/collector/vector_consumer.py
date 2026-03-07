"""Vector 日志消费者

从 Redis List 消费 Vector 写入的日志
"""

import asyncio
import json
from typing import Any, Callable

import redis.asyncio as redis

from auperator.config import settings
from auperator.collector.adapters import VectorAdapter
from auperator.collector.models import LogEntry


class VectorRedisConsumer:
    """Vector Redis List 消费者

    从 Redis List 读取 Vector 写入的日志并转换为 LogEntry

    Vector 使用 RPUSH 将 JSON 写入 List，我们使用 BRPOP 阻塞式读取

    Example:
        >>> consumer = VectorRedisConsumer()
        >>>
        >>> async def handler(entry: LogEntry):
        ...     print(f"收到日志：{entry.message}")
        >>>
        >>> await consumer.consume(handler)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        list_name: str | None = None,
        batch_size: int | None = None,
        block_timeout: int | None = None,
    ):
        """初始化 Vector Redis 消费者

        Args:
            redis_url: Redis 连接 URL（默认从 settings 读取）
            list_name: List 名称（默认从 settings 读取）
            batch_size: 每次读取的消息数
            block_timeout: 阻塞读取超时时间 (秒)
        """
        self.redis_url = redis_url or settings.get_redis_url()
        # 添加 key 前缀
        list_name_raw = list_name or settings.redis.list_name
        self.list_name = settings.redis.add_prefix(list_name_raw)
        self.batch_size = batch_size if batch_size is not None else settings.consumer.batch_size
        self.block_timeout = block_timeout if block_timeout is not None else settings.consumer.block_timeout

        self._redis: redis.Redis | None = None
        self._running = False
        self._adapter = VectorAdapter()

    async def connect(self) -> None:
        """连接 Redis"""
        self._redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
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
                    # 从列表右侧阻塞式弹出（使用 BRPOP）
                    # Vector 使用 RPUSH 写入，我们从右侧读取（FIFO）
                    result = await self._redis.brpop(
                        self.list_name,
                        timeout=self.block_timeout,
                    )

                    if not result:
                        continue

                    # result 是 tuple: (list_name, data)
                    _, data = result

                    try:
                        entry = self._parse_list_data(data)
                        await handler(entry)
                    except Exception as e:
                        if on_error:
                            await on_error(e, None)

                except redis.RedisError as e:
                    if on_error:
                        await on_error(e, None)
                    await asyncio.sleep(1)

        finally:
            await self.close()

    def _parse_list_data(self, data: str) -> LogEntry:
        """解析 List 数据为 LogEntry

        Vector 将 JSON 字符串写入 List

        Args:
            data: List 中的 JSON 字符串

        Returns:
            LogEntry 对象
        """
        try:
            # Vector 写入的是 JSON 字符串
            fields = json.loads(data)
            # 转换回 JSON 字符串给 VectorAdapter
            vector_json = json.dumps(fields)
            return self._adapter.parse(vector_json)
        except json.JSONDecodeError:
            # 如果不是 JSON，当作原始消息处理
            return self._adapter.parse(data)

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
                    entries = []

                    # 收集一批消息
                    for _ in range(self.batch_size):
                        try:
                            result = await self._redis.brpop(
                                self.list_name,
                                timeout=1,  # 短超时，避免阻塞太久
                            )
                            if result:
                                _, data = result
                                entry = self._parse_list_data(data)
                                entries.append(entry)
                        except redis.TimeoutError:
                            break

                    if entries:
                        await batch_handler(entries)
                    else:
                        # 没有消息时休眠一下
                        await asyncio.sleep(0.1)

                except redis.RedisError as e:
                    if on_error:
                        await on_error(e)
                    await asyncio.sleep(1)

        finally:
            await self.close()

    async def stop(self) -> None:
        """停止消费"""
        self._running = False

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    async def get_stream_info(self) -> dict[str, Any]:
        """获取 List 信息"""
        if not self._redis:
            await self.connect()

        length = await self._redis.llen(self.list_name)
        return {
            "length": length,
            "list_name": self.list_name,
        }
