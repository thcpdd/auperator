"""全局状态管理

管理 API 服务需要的全局状态
"""

import logging

from qdrant_client import AsyncQdrantClient, models
from redis.asyncio import Redis as AsyncRedis

from auperator.config import settings
from auperator.services.daytona_service import DaytonaService
from auperator.services.drain3_service import Drain3Service
from auperator.services.memory_service import (
    DEFAULT_MEMORY_WEIGHTS,
    MEMORY_SECTIONS
)
from auperator.events import EventCenter
from auperator.deepagents.worker import AgentWorker


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
        # Qdrant 客户端
        self.qdrant_client: AsyncQdrantClient | None = None
        # 事件中心
        self.event_center: EventCenter | None = None
        # Agent Worker
        self.agent_worker: AgentWorker | None = None

    async def initialize_all(self):
        """初始化所有服务"""
        logger.info("Initializing all services...")
        self._initialize_redis()
        self._initialize_drain3()
        self._initialize_event_center()
        await self._initialize_daytona()
        await self._initialize_qdrant()
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

    def _initialize_event_center(self):
        """初始化事件中心"""
        if self.event_center is None:
            logger.info("Initializing Event Center...")
            self.event_center = EventCenter()
            logger.info("Event Center initialized")

    async def _initialize_daytona(self):
        """初始化 Daytona 服务"""
        logger.info("Initializing Daytona service...")
        self.daytona_service = DaytonaService()
        await self.daytona_service.__aenter__()
        logger.info("Daytona service initialized")

    async def _initialize_qdrant(self):
        """初始化 Qdrant 客户端和collection"""
        if self.qdrant_client is None:
            logger.info("Initializing Qdrant client...")
            self.qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
            # 初始化collection
            if not await self.qdrant_client.collection_exists(settings.qdrant_collection):
                await self.qdrant_client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config={
                        section: models.VectorParams(
                            size=settings.embedding_vector_size,
                            distance=models.Distance.COSINE,
                        )
                        for section in MEMORY_SECTIONS
                    },
                )
                logger.info(f"Collection '{settings.qdrant_collection}' 已创建")
            else:
                logger.info(f"Collection '{settings.qdrant_collection}' 已存在")
            logger.info("Qdrant client initialized")

    async def cleanup_all(self):
        """清理所有服务"""
        logger.info("Cleaning up all services...")
        await self._cleanup_redis()
        await self._cleanup_event_center()
        await self._cleanup_daytona()
        await self._cleanup_qdrant()
        logger.info("✅ All services cleaned up successfully")

    async def _cleanup_redis(self):
        """清理 Redis 客户端"""
        if self.redis_client:
            logger.info("Cleaning up Redis client...")
            await self.redis_client.aclose()
            self.redis_client = None

    async def _cleanup_event_center(self):
        """清理事件中心"""
        if self.event_center:
            logger.info("Cleaning up Event Center...")
            await self.event_center.close()
            self.event_center = None
            self.redis_client = None

    async def _cleanup_daytona(self):
        """清理 Daytona 服务"""
        if self.daytona_service:
            logger.info("Cleaning up Daytona service...")
            await self.daytona_service.__aexit__(None, None, None)
            self.daytona_service = None

    async def _cleanup_qdrant(self):
        """清理 Qdrant 客户端"""
        if self.qdrant_client:
            logger.info("Cleaning up Qdrant client...")
            # AsyncQdrantClient会自动清理连接
            self.qdrant_client = None


global_state = GlobalState()
