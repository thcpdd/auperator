"""依赖注入

提供 FastAPI 路由的依赖注入函数
"""

import docker
from fastapi import HTTPException, Depends, status
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis as AsyncRedis

from auperator.services.memory_service import MemoryService
from auperator.state import global_state
from auperator.events import EventCenter


# Docker客户端单例
_docker_client = None


def get_docker_client() -> docker.DockerClient:
    """获取Docker客户端（依赖注入）

    用于日志流功能的Docker客户端，独立于Agent工具

    Returns:
        Docker客户端实例

    Raises:
        HTTPException: 如果无法连接到Docker守护进程
    """
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except docker.errors.DockerException as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Docker daemon: {str(e)}"
            )
    return _docker_client


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


def get_event_center() -> EventCenter:
    """获取事件中心（依赖注入）

    Returns:
        EventCenter实例

    Raises:
        HTTPException: 如果事件中心未初始化
    """
    if global_state.event_center is None:
        raise HTTPException(
            status_code=503,
            detail="Event center not initialized"
        )
    return global_state.event_center


def get_agent_worker():
    """获取 Agent Worker 依赖"""
    if global_state.agent_worker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent worker not initialized"
        )
    return global_state.agent_worker
