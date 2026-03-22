"""Auperator CLI"""

import asyncio
import sys
from typing import Annotated

import typer
import uvicorn
from langchain.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from auperator.config import settings
from auperator.deepagents import create_auperator
from auperator.deepagents.tools.docker_tools import get_tools as docker_tools
from auperator.deepagents.tools.memory_tools import get_tools as memory_tools
from auperator.deepagents.tools.pull_request import get_tools as pr_tools
from auperator.schemas.log import LogEntry
from auperator.collector.handlers.console import ConsoleHandler
from auperator.collector.handlers.agent import AgentHandler
from auperator.collector.vector_consumer import VectorRedisConsumer
from auperator.deepagents.prompts.initialize import INITIALIZE_PROMPT

app = typer.Typer(help="Auperator - 智能运维 Agent")


def run_async(coro):
    """运行异步函数的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
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
        workers=settings.api_workers
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
        print(f"错误：{e}", file=sys.stderr)

    async def run():
        try:
            print(f"开始从 Redis List '{list_name}' 消费日志...")
            print("按 Ctrl+C 停止\n")
            await consumer.consume(handler.handle, on_error=on_error)
        except KeyboardInterrupt:
            print("\n正在停止...")
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
    tools = docker_tools() + pr_tools() + memory_tools()
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
        print(f"❌ 错误：{e}", file=sys.stderr)

    async def run():
        print("✅ 系统已启动，等待日志...\n")
        try:
            await consumer.consume(handler.handle, on_error=on_error)
        except KeyboardInterrupt:
            print("\n\n正在停止...")
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
            print(f"List: {info['list_name']}")
            print(f"  消息数量：{info['length']}")
        finally:
            await consumer.close()

    run_async(get_info())


@app.command()
def init():
    """初始化项目记忆 - 分析被监控的项目并生成 AUPERATOR.md"""
    if not settings.remote_repo_url:
        print("❌ 错误：未配置 REMOTE_REPO_URL")
        print("请在 .env 文件中设置 REMOTE_REPO_URL")
        raise typer.Exit(1)

    print(f"📂 目标项目: {settings.remote_repo_url}")
    print("🔍 正在分析项目结构...\n")

    langfuse_handler = CallbackHandler()
    agent = create_auperator(skills=["./src/auperator/deepagents/skills"])

    async def run():
        try:
            async for _ in agent.astream(
                {"messages": [HumanMessage(INITIALIZE_PROMPT)]},
                {"callbacks": [langfuse_handler]}
            ):
                pass
            print("\n✅ AUPERATOR.md 已生成到项目根目录")
        except Exception as e:
            print(f"\n❌ 初始化失败: {e}", file=sys.stderr)
            raise

    run_async(run())


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
