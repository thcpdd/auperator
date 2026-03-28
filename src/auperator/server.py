import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from auperator.config import settings
from auperator.routes import (
    daytona_router,
    memory_router,
    vector_router,
    chat_router,
    events_router
)
from auperator.state import global_state
from auperator.database.db import init_db, close_db
from auperator.collector.vector_consumer import VectorRedisConsumer
from auperator.collector.handlers.event import EventHandler
from auperator.deepagents.worker import AgentWorker

logger = logging.getLogger(__name__)


async def log_consumer():
    """后台任务：从 Redis List 消费日志并发布事件"""
    logger.info("🚀 启动日志消费后台任务")

    event_center = global_state.event_center
    handler = EventHandler(event_center=event_center)

    redis_url = settings.get_redis_url()
    list_name = settings.redis.add_prefix(settings.redis.list_name)

    consumer = VectorRedisConsumer(
        redis_url=redis_url,
        list_name=list_name,
    )

    async def on_error(e: Exception, entry):
        logger.error(f"❌ 日志消费错误: {e}")

    try:
        logger.info(f"✅ 开始从 Redis List '{list_name}' 消费日志")
        await consumer.consume(handler.handle, on_error=on_error)
    except asyncio.CancelledError:
        logger.info("⏹️  日志消费后台任务已取消")
    except Exception as e:
        logger.exception(f"❌ 日志消费后台任务出错: {e}")
    finally:
        await consumer.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """管理应用生命周期"""
    logger.info("=" * 60)
    logger.info("Starting Auperator API Server")
    logger.info("=" * 60)

    consumer_task: asyncio.Task | None = None

    # 初始化所有服务
    try:
        await global_state.initialize_all()

        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库已初始化")

        # 初始化并启动 Agent Worker
        agent_worker = AgentWorker(
            event_center=global_state.event_center,
            consumer_group="agent-worker",
            enable_langfuse=True,
        )
        await agent_worker.initialize()
        await agent_worker.start()
        global_state.agent_worker = agent_worker
        logger.info("✅ Agent Worker 已启动")

        # 启动日志消费后台任务
        consumer_task = asyncio.create_task(log_consumer())
        logger.info("✅ 日志消费后台任务已启动")

        yield

    finally:
        # 清理所有服务
        logger.info("Shutting down Auperator API Server...")

        # 清理 Agent Worker
        if global_state.agent_worker:
            await global_state.agent_worker.cleanup()

        # 取消日志消费任务
        if consumer_task:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

        await global_state.cleanup_all()
        await close_db()
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
app.include_router(memory_router)
app.include_router(vector_router)
app.include_router(chat_router)
app.include_router(events_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "auperator-api"
    }


if __name__ == "__main__":
    uvicorn.run(
        "auperator.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers
    )
