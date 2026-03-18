import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from auperator.config import settings
from auperator.routes import daytona_router, vector_router
from auperator.state import global_state

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """管理应用生命周期"""
    logger.info("=" * 60)
    logger.info("Starting Auperator API Server")
    logger.info("=" * 60)

    # 初始化所有服务
    try:
        await global_state.initialize_all()

        yield

    finally:
        # 清理所有服务
        logger.info("Shutting down Auperator API Server...")
        await global_state.cleanup_all()
        logger.info("✅ Shutdown complete")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="Auperator API",
    description="智能运维 Agent 统一 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(daytona_router)
app.include_router(vector_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "auperator-api"
    }


if __name__ == "__main__":
    uvicorn.run(
        "auperator.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers
    )
