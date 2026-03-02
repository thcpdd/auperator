"""日志采集位置和去重管理器

使用 Redis 存储采集位置和去重记录，实现断点续传功能。
支持多种日志源类型（docker、file、kubernetes 等）。
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import redis.asyncio as redis

from auperator.config import settings
from .models import LogSource


@dataclass
class Position:
    """采集位置信息"""

    last_timestamp: int  # 最后处理的 Unix 时间戳（秒）
    last_docker_ts: str  # Docker 日志时间戳
    last_collected_at: str  # 最后采集时间
    last_hash: str  # 最后处理的日志哈希

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "last_timestamp": self.last_timestamp,
            "last_docker_ts": self.last_docker_ts,
            "last_collected_at": self.last_collected_at,
            "last_hash": self.last_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """从字典创建 Position"""
        return cls(
            last_timestamp=int(data.get("last_timestamp", 0)),
            last_docker_ts=data.get("last_docker_ts", ""),
            last_collected_at=data.get("last_collected_at", ""),
            last_hash=data.get("last_hash", ""),
        )


class PositionManager:
    """日志采集位置和去重管理器

    功能：
    1. 记录每个日志源的最后采集位置
    2. 通过哈希去重，避免重复处理日志
    3. 自动清理过期的去重记录
    4. 支持多种日志源类型（docker、file、kubernetes 等）
    """

    # Redis 键前缀
    POSITION_PREFIX = "logs:position:"
    DEDUP_PREFIX = "logs:dedup:"

    def __init__(
        self,
        redis_url: str | None = None,
        deduplication_enabled: bool | None = None,
        deduplication_ttl: int | None = None,
        source_type: LogSource | str = LogSource.DOCKER,
    ):
        """初始化位置管理器

        Args:
            redis_url: Redis 连接 URL（默认从 settings 读取）
            deduplication_enabled: 是否启用去重（默认从 settings 读取）
            deduplication_ttl: 去重记录 TTL（秒，默认从 settings 读取）
            source_type: 日志源类型（docker/file/kubernetes），默认 docker
        """
        self.redis_url = redis_url or settings.get_redis_url()
        self.deduplication_enabled = (
            deduplication_enabled
            if deduplication_enabled is not None
            else settings.deduplication.enabled
        )
        self.deduplication_ttl = (
            deduplication_ttl
            if deduplication_ttl is not None
            else settings.deduplication.ttl
        )

        # 处理 source_type
        if isinstance(source_type, str):
            self.source_type = source_type.lower()
        else:
            self.source_type = source_type.value if source_type else "docker"

        self._redis: redis.Redis | None = None
        self._connected = False

    def _add_prefix(self, key: str) -> str:
        """为 Redis key 添加前缀

        Args:
            key: 原始 key

        Returns:
            带前缀的 key
        """
        return settings.redis.add_prefix(key)

    def _get_position_key(self, source_id: str) -> str:
        """获取位置记录的 Redis 键

        Args:
            source_id: 日志源标识（容器名、文件路径等）

        Returns:
            Redis 键
        """
        key = f"{self.POSITION_PREFIX}{self.source_type}:{source_id}"
        return self._add_prefix(key)

    def _get_dedup_key(self, source_id: str, date: str | None = None) -> str:
        """获取去重集合的 Redis 键

        Args:
            source_id: 日志源标识
            date: 日期字符串（YYYY-MM-DD），默认今天

        Returns:
            Redis 键
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{self.DEDUP_PREFIX}{self.source_type}:{source_id}:{date}"
        return self._add_prefix(key)

    async def _ensure_connected(self) -> None:
        """确保已连接 Redis"""
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

    async def get_last_position(self, source_id: str) -> Position | None:
        """获取日志源最后的采集位置

        Args:
            source_id: 日志源标识（容器名、文件路径等）

        Returns:
            Position 对象，如果不存在返回 None
        """
        await self._ensure_connected()

        key = self._get_position_key(source_id)
        data = await self._redis.hgetall(key)

        if not data:
            return None

        return Position.from_dict(data)

    async def save_position(self, source_id: str, position: Position) -> None:
        """保存日志源采集位置

        Args:
            source_id: 日志源标识
            position: 位置信息
        """
        await self._ensure_connected()

        key = self._get_position_key(source_id)
        await self._redis.hset(key, mapping=position.to_dict())

    async def update_position(
        self,
        source_id: str,
        timestamp: str,
        log_hash: str,
    ) -> None:
        """更新日志源采集位置

        Args:
            source_id: 日志源标识
            timestamp: 日志时间戳（ISO8601 格式）
            log_hash: 日志哈希
        """
        await self._ensure_connected()

        # 解析时间戳为 Unix 时间戳
        unix_ts = self._parse_timestamp(timestamp)
        now = datetime.now(timezone.utc).isoformat()

        position = Position(
            last_timestamp=unix_ts,
            last_docker_ts=timestamp,
            last_collected_at=now,
            last_hash=log_hash,
        )

        await self.save_position(source_id, position)

    def _parse_timestamp(self, timestamp: str) -> int:
        """解析时间戳为 Unix 时间戳

        Args:
            timestamp: 时间戳（ISO8601 格式）

        Returns:
            Unix 时间戳（秒）
        """
        try:
            # Docker 时间戳格式: 2024-03-02T10:30:00.123456789Z
            # 去掉纳秒部分
            if "." in timestamp:
                timestamp = timestamp.split(".")[0]
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1]

            dt = datetime.fromisoformat(timestamp)
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            # 解析失败，返回当前时间
            return int(asyncio.get_event_loop().time())

    def calculate_hash(self, content: str, timestamp: str) -> str:
        """计算日志哈希

        Args:
            content: 日志内容
            timestamp: 日志时间戳

        Returns:
            SHA256 哈希值
        """
        combined = f"{timestamp}:{content}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def is_duplicate(self, source_id: str, log_hash: str) -> bool:
        """检查日志是否已处理

        Args:
            source_id: 日志源标识
            log_hash: 日志哈希

        Returns:
            如果已处理返回 True，否则返回 False
        """
        if not self.deduplication_enabled:
            return False

        await self._ensure_connected()

        # 检查今天的去重集合
        key = self._get_dedup_key(source_id)

        return await self._redis.sismember(key, log_hash)

    async def mark_processed(
        self,
        source_id: str,
        log_hash: str,
        timestamp: str,
    ) -> None:
        """标记日志为已处理

        Args:
            source_id: 日志源标识
            log_hash: 日志哈希
            timestamp: 日志时间戳
        """
        await self._ensure_connected()

        # 添加到今天的去重集合
        key = self._get_dedup_key(source_id)

        # 添加到集合并设置 TTL
        await self._redis.sadd(key, log_hash)
        await self._redis.expire(key, self.deduplication_ttl)

        # 更新位置
        await self.update_position(source_id, timestamp, log_hash)

    async def reset(self, source_id: str) -> None:
        """重置日志源的采集位置

        Args:
            source_id: 日志源标识
        """
        await self._ensure_connected()

        # 删除位置记录
        position_key = self._get_position_key(source_id)
        await self._redis.delete(position_key)

        # 删除所有去重记录
        pattern = self._get_dedup_key(source_id, date="*")
        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await self._redis.delete(*keys)

    async def cleanup_old_records(self, source_id: str, days: int = 7) -> int:
        """清理旧的去重记录

        Args:
            source_id: 日志源标识
            days: 保留天数

        Returns:
            删除的记录数
        """
        await self._ensure_connected()

        cutoff_date = datetime.now(timezone.utc)
        cutoff_date = cutoff_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        deleted_count = 0

        # 扫描所有去重集合
        pattern = self._get_dedup_key(source_id, date="*")
        async for key in self._redis.scan_iter(match=pattern):
            # 从键中提取日期
            try:
                date_str = key.split(":")[-1]
                key_date = datetime.fromisoformat(date_str)

                # 如果日期早于截止日期，删除
                if (cutoff_date - key_date).days > days:
                    await self._redis.delete(key)
                    deleted_count += 1
            except (ValueError, IndexError):
                # 忽略格式错误的键
                pass

        return deleted_count

    async def get_stats(self, source_id: str) -> dict:
        """获取日志源的去重统计信息

        Args:
            source_id: 日志源标识

        Returns:
            统计信息字典
        """
        await self._ensure_connected()

        # 获取位置信息
        position = await self.get_last_position(source_id)

        # 统计去重集合数量和大小
        pattern = self._get_dedup_key(source_id, date="*")
        dedup_sets = 0
        total_hashes = 0

        async for key in self._redis.scan_iter(match=pattern):
            dedup_sets += 1
            total_hashes += await self._redis.scard(key)

        return {
            "source_type": self.source_type,
            "source_id": source_id,
            "position": position.to_dict() if position else None,
            "dedup_sets": dedup_sets,
            "total_hashes": total_hashes,
        }
