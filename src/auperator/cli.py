"""Auperator CLI"""

import asyncio
import logging
import sys
from typing import Annotated

import typer
import uvicorn
from langchain.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from auperator.config import settings
from auperator.utils.logging import setup_logging, get_uvicorn_log_config
from auperator.deepagents import create_auperator
from auperator.deepagents.tools.registry import ToolRegistry
from auperator.schemas.log import LogEntry
from auperator.collector.handlers.console import ConsoleHandler
from auperator.collector.handlers.agent import AgentHandler
from auperator.collector.vector_consumer import VectorRedisConsumer
from auperator.deepagents.prompts.initialize import INITIALIZE_PROMPT

# 初始化日志配置
setup_logging(
    level=settings.log_level,
    log_file=settings.log_file,
    use_colors=not settings.log_no_color,
)

logger = logging.getLogger(__name__)

app = typer.Typer(help="Auperator - 智能运维 Agent")


def run_async(coro):
    """运行异步函数的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        logger.warning("操作已取消")
        sys.exit(130)
    except Exception as e:
        logger.error(f"错误：{e}")
        sys.exit(1)
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


@app.command()
def server(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="API server host"),
    ] = None,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="API server port"),
    ] = None,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload"),
    ] = False,
):
    """启动 Auperator API 服务"""
    host = host or settings.api_host
    port = port or settings.api_port

    uvicorn.run(
        "auperator.server:app",
        host=host,
        port=port,
        reload=reload,
        workers=settings.api_workers,
        log_config=get_uvicorn_log_config(
            level=settings.log_level,
            use_colors=not settings.log_no_color,
        ),
    )


@app.command("terminal-consume")
def terminal_consume(
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    list_name: Annotated[
        str,
        typer.Option("--list", "-l", help="List 名称"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="详细输出模式"),
    ] = False,
):
    """从 Redis 消费 Vector 发送的日志，并在终端显示"""
    redis_url = redis_url or settings.get_redis_url()
    list_name = list_name or settings.redis.list_name

    consumer = VectorRedisConsumer(
        redis_url=redis_url,
        list_name=list_name,
    )

    handler = ConsoleHandler(verbose=verbose)

    async def on_error(e: Exception, entry: LogEntry | None):
        logger.error(f"错误：{e}")

    async def run():
        try:
            logger.info(f"开始从 Redis List '{list_name}' 消费日志...")
            logger.info("按 Ctrl+C 停止")
            await consumer.consume(handler.handle, on_error=on_error)
        except KeyboardInterrupt:
            logger.info("正在停止...")
        finally:
            await consumer.close()

    run_async(run())


@app.command()
def start(
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    enable_langfuse: Annotated[
        bool,
        typer.Option("--enable-langfuse", "-e", help="启用 Langfuse"),
    ] = True,
):
    """启动 Auperator 系统，从 Redis List 消费日志并处理"""
    redis_url = redis_url or settings.get_redis_url()
    list_name = settings.redis.add_prefix(settings.redis.list_name)

    # 创建 Agent
    tools = ToolRegistry.get_all()
    agent = create_auperator(
        skills=["./src/auperator/deepagents/skills"],
        tools=tools,
    )

    # 创建 Agent Handler
    handler = AgentHandler(
        agent=agent,
        enable_langfuse=enable_langfuse,
    )

    # 创建消费者
    consumer = VectorRedisConsumer(
        redis_url=redis_url,
        list_name=list_name,
    )

    async def on_error(e: Exception, entry: LogEntry | None):
        """错误回调"""
        logger.error(f"❌ 错误：{e}")

    async def run():
        logger.info("✅ 系统已启动，等待日志...")
        try:
            await consumer.consume(handler.handle, on_error=on_error)
        except KeyboardInterrupt:
            logger.info("正在停止...")
        finally:
            await consumer.close()

    run_async(run())


@app.command("list-info")
def list_info(
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    list_name: Annotated[
        str,
        typer.Option("--list", "-l", help="List 名称"),
    ] = None,
):
    """查看 Redis List 信息"""
    redis_url = redis_url or settings.get_redis_url()
    list_name = list_name or settings.redis.list_name

    async def get_info():
        consumer = VectorRedisConsumer(
            redis_url=redis_url,
            list_name=list_name,
        )
        try:
            info = await consumer.get_stream_info()
            logger.info(f"List: {info['list_name']}")
            logger.info(f"  消息数量：{info['length']}")
        finally:
            await consumer.close()

    run_async(get_info())


@app.command()
def init():
    """初始化项目记忆 - 分析被监控的项目并生成 AUPERATOR.md"""
    if not settings.remote_repo_url:
        logger.error("❌ 错误：未配置 REMOTE_REPO_URL")
        logger.error("请在 .env 文件中设置 REMOTE_REPO_URL")
        raise typer.Exit(1)

    logger.info(f"📂 目标项目: {settings.remote_repo_url}")
    logger.info("🔍 正在分析项目结构...")

    langfuse_handler = CallbackHandler()
    agent = create_auperator(skills=["./src/auperator/deepagents/skills"])

    async def run():
        try:
            async for _ in agent.astream(
                {"messages": [HumanMessage(INITIALIZE_PROMPT)]},
                {"callbacks": [langfuse_handler]}
            ):
                pass
            logger.info("✅ AUPERATOR.md 已生成到项目根目录")
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise

    run_async(run())


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
