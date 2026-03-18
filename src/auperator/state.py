"""全局状态管理

管理 API 服务需要的全局状态
"""

import logging

from redis.asyncio import Redis as AsyncRedis

from auperator.config import settings
from auperator.services.daytona_service import DaytonaService
from auperator.services.drain3_service import Drain3Service

logger = logging.getLogger(__name__)


class GlobalState:
    """全局状态管理"""

    def __init__(self):
        # Daytona 服务
        self.daytona_service: DaytonaService | None = None
        # Redis 客户端（异步）
        self.redis_client: AsyncRedis | None = None
        # Drain3 服务
        self.drain3_service: Drain3Service | None = None

    async def initialize_all(self):
        """初始化所有服务"""
        logger.info("Initializing all services...")
        self._initialize_redis()
        self._initialize_drain3()
        await self._initialize_daytona()
        logger.info("✅ All services initialized successfully")

    def _initialize_drain3(self):
        """初始化 Drain3 服务"""
        if self.drain3_service is None:
            logger.info("Initializing Drain3 service...")
            self.drain3_service = Drain3Service()
            logger.info("Drain3 service initialized")

    def _initialize_redis(self):
        """初始化 Redis 客户端"""
        if self.redis_client is None:
            logger.info("Initializing Redis client...")
            self.redis_client = AsyncRedis(**settings.get_redis_connection_kwargs())
            logger.info("Redis client initialized")

    async def _initialize_daytona(self):
        """初始化 Daytona 服务"""
        logger.info("Initializing Daytona service...")
        self.daytona_service = DaytonaService()
        await self.daytona_service.__aenter__()
        logger.info("Daytona service initialized")

    async def cleanup_all(self):
        """清理所有服务"""
        logger.info("Cleaning up all services...")
        await self._cleanup_redis()
        await self._cleanup_daytona()
        logger.info("✅ All services cleaned up successfully")

    async def _cleanup_redis(self):
        """清理 Redis 客户端"""
        if self.redis_client:
            logger.info("Cleaning up Redis client...")
            await self.redis_client.aclose()
            self.redis_client = None

    async def _cleanup_daytona(self):
        """清理 Daytona 服务"""
        if self.daytona_service:
            logger.info("Cleaning up Daytona service...")
            await self.daytona_service.__aexit__(None, None, None)
            self.daytona_service = None


global_state = GlobalState()
