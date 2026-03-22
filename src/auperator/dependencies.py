"""依赖注入

提供 FastAPI 路由的依赖注入函数
"""

from fastapi import HTTPException, Depends
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis as AsyncRedis

from auperator.services.memory_service import MemoryService
from auperator.state import global_state


def get_redis_client() -> AsyncRedis:
    """获取 Redis 客户端（依赖注入）

    Returns:
        异步Redis客户端实例

    Raises:
        HTTPException: 如果Redis客户端未初始化
    """
    if global_state.redis_client is None:
        raise HTTPException(
            status_code=503,
            detail="Redis client not initialized"
        )
    return global_state.redis_client


def get_daytona_service():
    """获取 Daytona 服务（依赖注入）"""
    if global_state.daytona_service is None:
        raise HTTPException(
            status_code=503,
            detail="Daytona service not initialized"
        )
    return global_state.daytona_service


def get_drain3_service():
    """获取 Drain3 服务（依赖注入）

    Returns:
        Drain3Service实例

    Raises:
        HTTPException: 如果Drain3服务未初始化
    """
    if global_state.drain3_service is None:
        raise HTTPException(
            status_code=503,
            detail="Drain3 service not initialized"
        )
    return global_state.drain3_service


def get_qdrant_client() -> AsyncQdrantClient:
    """获取 Qdrant 客户端（依赖注入）

    Returns:
        AsyncQdrantClient实例

    Raises:
        HTTPException: 如果Qdrant客户端未初始化
    """
    if global_state.qdrant_client is None:
        raise HTTPException(
            status_code=503,
            detail="Qdrant client not initialized"
        )
    return global_state.qdrant_client


def get_memory_service(
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant_client)
) -> MemoryService:
    """获取 Memory 服务（依赖注入）

    Args:
        qdrant_client: Qdrant客户端（通过依赖注入）

    Returns:
        MemoryService实例
    """
    return MemoryService(qdrant_client=qdrant_client)
