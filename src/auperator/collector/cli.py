"""日志采集器命令行接口

与 Vector.dev 集成的 CLI
"""

import asyncio
import sys
from typing import Annotated

import typer

from auperator.config import settings
from .vector_consumer import VectorRedisConsumer
from .handlers import ConsoleHandler
from .models import LogEntry

app = typer.Typer(help="日志采集器 CLI")


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
def consume(
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
) -> None:
    """从 Redis 消费 Vector 发送的日志"""
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
) -> None:
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


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
