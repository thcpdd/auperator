"""依赖注入

提供 FastAPI 路由的依赖注入函数
"""

from fastapi import HTTPException
from redis.asyncio import Redis as AsyncRedis

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
