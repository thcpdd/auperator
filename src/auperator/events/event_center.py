"""事件中心：管理所有事件的发布和消费."""

import uuid
import asyncio
import logging
from typing import AsyncIterator

import redis.asyncio as aioredis
from redis import ResponseError

from auperator.config import settings
from auperator.schemas.event import Event, EventType

logger = logging.getLogger(__name__)


class EventCenter:
    """事件中心.

    负责：
    - 发布事件到 Redis Streams
    - 消费事件（异步生成器）
    - 管理消费者组
    """

    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._lock = asyncio.Lock()

    async def _get_redis(self) -> aioredis.Redis:
        """获取 Redis 连接（懒加载，单例）.

        Returns:
            Redis 客户端
        """
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    self._redis = await aioredis.from_url(
                        settings.get_redis_url(),
                        decode_responses=False,  # 保持 bytes，方便解析
                        encoding="utf-8",
                    )
                    logger.info(f"Redis 连接已建立: {settings.redis_host}:{settings.redis_port}")
        return self._redis

    async def close(self):
        """关闭 Redis 连接."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis 连接已关闭")

    async def publish_event(self, event: Event) -> str:
        """发布事件到事件流.

        Args:
            event: 事件对象

        Returns:
            Redis Stream 消息 ID
        """
        redis = await self._get_redis()

        # 转换为 Redis 格式
        data = event.to_redis_dict()

        # XADD 添加到 Stream
        # MAXLEN ~ 10000：自动清理旧事件，保留约 10000 条
        message_id = await redis.xadd(
            settings.redis.add_prefix(settings.redis_event_stream),
            data,
            maxlen=10000,
        )

        logger.debug(
            f"发布事件: {event.event_type.value} | {event.thread_id} | {message_id}"
        )

        return message_id

    async def create_consumer_group(self, group: str) -> None:
        """创建消费者组（如果不存在）.

        Args:
            group: 消费者组名称
        """
        redis = await self._get_redis()
        stream_key = settings.redis.add_prefix(settings.redis_event_stream)

        try:
            # XGROUP CREATE：创建消费者组
            # id="0"：从 Stream 开头开始消费
            # mkstream=True：如果 Stream 不存在则创建
            await redis.xgroup_create(
                name=stream_key,
                groupname=group,
                id="0",
                mkstream=True,
            )
            logger.info(f"消费者组创建成功: {group}")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # 消费者组已存在，不是错误
                logger.debug(f"消费者组已存在: {group}")
            else:
                logger.error(f"创建消费者组失败: {group}, 错误: {e}")
                raise

    async def consume(
        self,
        group: str,
        count: int = 1,
        block: int = 1000,
    ) -> AsyncIterator[Event]:
        """消费事件（异步生成器）.

        使用方式：
            async for event in event_center.consume("web-ui"):
                await handle_event(event)

        Args:
            group: 消费者组名称
            count: 每次获取的最大消息数
            block: 阻塞等待时间（毫秒）

        Yields:
            Event: 事件对象
        """
        consumer = f"consumer-{uuid.uuid4().hex[:8]}"

        # 确保消费者组存在
        await self.create_consumer_group(group)

        redis = await self._get_redis()
        stream_key = settings.redis.add_prefix(settings.redis_event_stream)

        logger.info(f"开始消费事件: group={group}, consumer={consumer}")

        try:
            while True:
                # XREADGROUP：读取消息
                # ">"：只接收新消息（未投递过的）
                messages = await redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream_key: ">"},
                    count=count,
                    block=block,
                )

                if not messages:
                    # 超时，继续循环
                    continue

                # 解析消息
                for stream, stream_messages in messages:
                    for message_id, data in stream_messages:
                        try:
                            event = Event.from_redis_dict(data, message_id)
                            yield event
                        except Exception as e:
                            logger.error(f"解析事件失败: {message_id}, 错误: {e}")
                            continue

                        # ACK 确认消息处理完成
                        await redis.xack(stream_key, group, message_id)
                        logger.debug(
                            f"事件已确认: {event.event_type.value} | {event.thread_id} | {message_id}"
                        )

        except asyncio.CancelledError:
            logger.info(f"消费任务被取消: group={group}, consumer={consumer}")
        except Exception as e:
            logger.error(f"消费过程出错: group={group}, 错误: {e}")
            raise
        finally:
            logger.info(f"停止消费事件: group={group}, consumer={consumer}")

    async def get_events_by_thread_id(
        self,
        thread_id: str,
        count: int = 100,
    ) -> list[Event]:
        """获取指定 thread_id 的所有事件.

        Args:
            thread_id: 会话标识
            count: 最大返回数量

        Returns:
            事件列表（按时间正序）
        """
        redis = await self._get_redis()
        stream_key = settings.redis.add_prefix(settings.redis_event_stream)

        # 先获取所有消息
        messages = await redis.xrange(stream_key, count=10000)

        # 过滤并解析
        events = []
        for message_id, data in messages:
            try:
                # 解析 thread_id
                thread_id_bytes = data.get(b"thread_id") or data.get("thread_id")
                if thread_id_bytes is None:
                    continue

                current_thread_id = (
                    thread_id_bytes.decode("utf-8")
                    if isinstance(thread_id_bytes, bytes)
                    else thread_id_bytes
                )

                if current_thread_id != thread_id:
                    continue

                event = Event.from_redis_dict(data, message_id)
                events.append(event)

                if len(events) >= count:
                    break
            except Exception as e:
                logger.error(f"解析事件失败: {message_id}, 错误: {e}")
                continue

        return events

    async def get_events_by_type(
        self,
        event_type: EventType,
        count: int = 100,
    ) -> list[Event]:
        """获取指定类型的所有事件.

        Args:
            event_type: 事件类型
            count: 最大返回数量

        Returns:
            事件列表（按时间正序）
        """
        redis = await self._get_redis()
        stream_key = settings.redis.add_prefix(settings.redis_event_stream)

        messages = await redis.xrange(stream_key, count=10000)

        events = []
        for message_id, data in messages:
            try:
                type_bytes = data.get(b"event_type") or data.get("event_type")
                if type_bytes is None:
                    continue

                current_type = (
                    type_bytes.decode("utf-8")
                    if isinstance(type_bytes, bytes)
                    else type_bytes
                )

                if current_type != event_type.value:
                    continue

                event = Event.from_redis_dict(data, message_id)
                events.append(event)

                if len(events) >= count:
                    break
            except Exception as e:
                logger.error(f"解析事件失败: {message_id}, 错误: {e}")
                continue

        return events

    async def list_consumer_groups(self) -> list[dict[str, any]]:
        """列出所有消费者组及其信息.

        Returns:
            消费者组信息列表
        """
        redis = await self._get_redis()
        stream_key = settings.redis.add_prefix(settings.redis_event_stream)

        try:
            groups_info = await redis.xinfo_groups(stream_key)

            result = []
            for info in groups_info:
                result.append({
                    "name": info.get(b"name", b"").decode("utf-8"),
                    "consumers": info.get(b"consumers", 0),
                    "pending": info.get(b"pending", 0),
                    "last_delivered_id": info.get(b"last-delivered-id", b"").decode("utf-8"),
                })

            return result
        except ResponseError as e:
            logger.error(f"获取消费者组信息失败: {e}")
            return []
