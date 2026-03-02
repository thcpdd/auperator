"""Redis 日志处理器"""

import asyncio
import json
from typing import Any

import redis.asyncio as redis

from auperator.config import settings
from auperator.collector.models import LogEntry
from .base import BaseLogHandler


class RedisSender:
    """Redis Streams 发送器

    将日志发送到 Redis Stream

    Example:
        >>> sender = RedisSender("redis://localhost:6379")
        >>> await sender.send(entry)
        >>> await sender.send_batch([entry1, entry2])
    """

    def __init__(self):
        """初始化 Redis 发送器

        Args:
            redis_url: Redis 连接 URL（默认从 settings 读取）
            stream_name: Stream 名称（默认从 settings 读取）
            max_retries: 最大重试次数（默认从 settings 读取）
            retry_delay: 重试延迟 (秒)（默认从 settings 读取）
        """
        self.redis_url = settings.get_redis_url()
        # 添加 key 前缀
        stream_name_raw = settings.redis.stream_name
        self.stream_name = settings.redis.add_prefix(stream_name_raw)
        self.max_retries = settings.collector.max_retries
        self.retry_delay = settings.collector.retry_delay

        self._redis: redis.Redis | None = None
        self._connected = False

    async def connect(self) -> None:
        """连接 Redis"""
        if not self._connected:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._connected = True

    async def close(self) -> None:
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._connected = False

    async def send(self, entry: LogEntry) -> str | None:
        """发送单条日志

        Args:
            entry: 日志条目

        Returns:
            消息 ID，发送失败返回 None
        """
        await self._ensure_connected()

        for attempt in range(self.max_retries):
            try:
                # 序列化日志
                data = entry.to_dict()
                message_id = await self._redis.xadd(
                    self.stream_name,
                    {"data": json.dumps(data, ensure_ascii=False)}
                )
                return message_id
            except redis.RedisError as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        return None

    async def send_batch(self, entries: list[LogEntry]) -> tuple[int, int]:
        """批量发送日志

        Args:
            entries: 日志条目列表

        Returns:
            (成功数，失败数)
        """
        await self._ensure_connected()

        success = 0
        failed = 0

        # 使用 pipeline 提高性能
        for attempt in range(self.max_retries):
            try:
                pipe = self._redis.pipeline()
                for entry in entries:
                    data = entry.to_dict()
                    pipe.xadd(
                        self.stream_name,
                        {"data": json.dumps(data, ensure_ascii=False)},
                    )
                results = await pipe.execute()
                return len(results), 0
            except redis.RedisError as e:
                if attempt == self.max_retries - 1:
                    return 0, len(entries)
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return success, failed

    async def _ensure_connected(self) -> None:
        """确保已连接"""
        if not self._connected:
            await self.connect()

    async def create_consumer_group(self, group_name: str = "auperator-group") -> None:
        """创建消费者组

        Args:
            group_name: 消费者组名称
        """
        await self._ensure_connected()

        try:
            await self._redis.xgroup_create(
                self.stream_name,
                group_name,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def get_stream_info(self) -> dict[str, Any]:
        """获取 Stream 信息"""
        await self._ensure_connected()

        info = await self._redis.xinfo_stream(self.stream_name)
        return {
            "length": info.get("length", 0),
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
            "groups": info.get("groups", 0),
        }

    async def clear(self) -> int:
        """清空 Stream

        Returns:
            删除的消息数
        """
        await self._ensure_connected()

        count = await self._redis.xtrim(self.stream_name, 0)
        return count


class RedisHandler(BaseLogHandler):
    """Redis 日志处理器

    将日志发送到 Redis Stream
    """

    def __init__(self):
        """初始化 Redis 处理器

        Args:
            sender: Redis 发送器实例
        """
        self.sender = RedisSender()

    async def handle(self, entry: LogEntry) -> None:
        """发送日志到 Redis

        Args:
            entry: 日志条目
        """
        await self.sender.send(entry)
