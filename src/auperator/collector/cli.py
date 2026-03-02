"""日志采集器命令行接口"""

import asyncio
import json
import sys
from typing import Annotated

import docker
import typer
import redis.asyncio as redis

from auperator.config import settings
from .adapters import GenericAdapter, JsonAdapter
from .collector import LogCollector
from .consumer import RedisConsumer
from .models import LogEntry
from .position_manager import PositionManager
from .sender import RedisSender
from .sources.docker_source import DockerSource

app = typer.Typer(help="日志采集器 CLI")


class ConsoleHandler:
    """控制台日志处理器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def handle(self, entry: LogEntry) -> None:
        """处理日志条目"""
        if self.verbose:
            print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        else:
            level_color = {
                "DEBUG": "\033[36m",
                "INFO": "\033[32m",
                "WARNING": "\033[33m",
                "ERROR": "\033[31m",
                "CRITICAL": "\033[35m",
            }
            color = level_color.get(entry.level.value, "\033[0m")
            reset = "\033[0m"
            print(f"{color}[{entry.level.value}]{reset} {entry.message}")


@app.command("docker")
def collect_docker(
    container: Annotated[str, typer.Argument(help="容器名称或 ID")],
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    stream_name: Annotated[
        str,
        typer.Option("--stream", "-s", help="Stream 名称"),
    ] = None,
    adapter: Annotated[
        str,
        typer.Option("--adapter", "-a", help="日志适配器类型 (json/generic)"),
    ] = "json",
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="持续跟踪日志"),
    ] = True,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="初始显示的行数 (0 表示全部)"),
    ] = None,
    service: Annotated[
        str | None,
        typer.Option("--service", help="服务名称"),
    ] = None,
    environment: Annotated[
        str,
        typer.Option("--env", "-e", help="环境标识"),
    ] = None,
    no_dedup: Annotated[
        bool,
        typer.Option("--no-dedup", help="禁用去重功能"),
    ] = False,
) -> None:
    """采集 Docker 日志并发送到 Redis"""
    # 使用 settings 默认值
    redis_url = redis_url or settings.get_redis_url()
    stream_name = stream_name or settings.redis.stream_name
    tail = tail if tail is not None else settings.docker.tail
    environment = environment or settings.environment
    deduplication_enabled = settings.deduplication.enabled and not no_dedup

    # 创建位置管理器
    position_manager = None
    if deduplication_enabled:
        position_manager = PositionManager(
            redis_url=redis_url,
            deduplication_enabled=deduplication_enabled,
        )

    source = DockerSource(
        container_name=container,
        follow=follow,
        tail=tail,
        service=service,
        environment=environment,
        position_manager=position_manager,
        deduplication_enabled=deduplication_enabled,
    )

    if adapter == "json":
        log_adapter = JsonAdapter(
            source=container,
            source_type="docker",
            service=service or container,
            environment=environment,
        )
    else:
        log_adapter = GenericAdapter(
            source=container,
            source_type="docker",
            service=service or container,
            environment=environment,
        )

    sender = RedisSender(redis_url=redis_url, stream_name=stream_name)
    collector = LogCollector(source, log_adapter)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        await sender.connect()
        try:
            async for raw_line in source.read():
                entry = log_adapter.parse(raw_line)
                await sender.send(entry)
        except KeyboardInterrupt:
            print("\n正在停止...")
        finally:
            await sender.close()
            await source.stop()

    try:
        loop.run_until_complete(run())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        loop.close()


@app.command("consume")
def consume_logs(
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    stream_name: Annotated[
        str,
        typer.Option("--stream", "-s", help="Stream 名称"),
    ] = None,
    group_name: Annotated[
        str,
        typer.Option("--group", "-g", help="消费者组名称"),
    ] = None,
    consumer_name: Annotated[
        str,
        typer.Option("--name", "-n", help="消费者名称"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="详细输出模式"),
    ] = False,
) -> None:
    """从 Redis 消费日志"""
    # 使用 settings 默认值
    redis_url = redis_url or settings.get_redis_url()
    stream_name = stream_name or settings.redis.stream_name
    group_name = group_name or settings.redis.consumer_group
    consumer_name = consumer_name or "agent-1"

    consumer = RedisConsumer(
        redis_url=redis_url,
        stream_name=stream_name,
        group_name=group_name,
        consumer_name=consumer_name,
    )

    handler = ConsoleHandler(verbose=verbose)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def on_error(e: Exception, entry: LogEntry | None):
        print(f"错误：{e}", file=sys.stderr)

    try:
        print(f"开始从 Redis Stream '{stream_name}' 消费日志...")
        print(f"消费者组：{group_name}, 消费者：{consumer_name}")
        print("按 Ctrl+C 停止\n")
        loop.run_until_complete(consumer.consume(handler.handle, on_error=on_error))
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        loop.run_until_complete(consumer.close())
        loop.close()


@app.command("list")
def list_containers(
    all: Annotated[
        bool,
        typer.Option("--all", "-a", help="显示所有容器 (包括已停止的)"),
    ] = False,
) -> None:
    """列出可用的 Docker 容器"""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=all)

        if not containers:
            print("没有找到容器")
            return

        print(f"{'容器 ID':<15} {'名称':<20} {'镜像':<30} {'状态':<15}")
        print("-" * 80)
        for container in containers:
            name = container.name
            image = container.image.tags[0] if container.image.tags else container.image.short_id
            status = container.status
            print(f"{container.short_id:<15} {name:<20} {image:<30} {status:<15}")

    except docker.errors.DockerException as e:
        print(f"无法连接 Docker: {e}", file=sys.stderr)
        sys.exit(1)


@app.command("redis-info")
def redis_info(
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    stream_name: Annotated[
        str,
        typer.Option("--stream", "-s", help="Stream 名称"),
    ] = None,
) -> None:
    """查看 Redis Stream 信息"""
    
    # 使用 settings 默认值
    redis_url = redis_url or settings.get_redis_url()
    stream_name = stream_name or settings.redis.stream_name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def get_info():
        r = redis.from_url(redis_url, decode_responses=True)
        try:
            info = await r.xinfo_stream(stream_name)
            print(f"Stream: {stream_name}")
            print(f"  消息数量：{info.get('length', 0)}")
            print(f"  消费者组数：{info.get('groups', 0)}")
            print(f"  第一个消息：{info.get('first-entry')}")
            print(f"  最后一个消息：{info.get('last-entry')}")
        except redis.ResponseError as e:
            print(f"Stream 不存在或错误：{e}")
        finally:
            await r.close()

    try:
        loop.run_until_complete(get_info())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        loop.close()


@app.command("test")
def test_adapter(
    adapter: Annotated[
        str,
        typer.Option("--adapter", "-a", help="适配器类型 (json/generic)"),
    ] = "json",
) -> None:
    """测试日志适配器"""
    test_lines = [
        '{"level": "INFO", "msg": "Server started", "time": "2024-01-01T00:00:00Z"}',
        '{"level": "ERROR", "msg": "Database connection failed", "stack": "Error: ..."}',
        '2024-01-01 12:00:00 INFO Application initialized',
        '2024-01-01 12:00:01 ERROR Something went wrong',
    ]

    if adapter == "json":
        log_adapter = JsonAdapter()
    else:
        log_adapter = GenericAdapter()

    print(f"使用 {adapter} 适配器测试:\n")
    print("-" * 60)

    for line in test_lines:
        print(f"\n原始：{line}")
        try:
            entry = log_adapter.parse(line)
            print(f"解析：level={entry.level.value}, message={entry.message[:50]}...")
        except Exception as e:
            print(f"错误：{e}")

    print("\n" + "-" * 60)


@app.command("show-position")
def show_position(
    source_id: Annotated[
        str,
        typer.Argument(help="日志源标识（容器名、文件路径等）"),
    ],
    source_type: Annotated[
        str,
        typer.Option("--type", "-t", help="日志源类型 (docker/file/kubernetes)"),
    ] = "docker",
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
) -> None:
    """显示日志源的采集位置"""
    redis_url = redis_url or settings.get_redis_url()

    position_manager = PositionManager(
        redis_url=redis_url,
        source_type=source_type,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def get_position():
        stats = await position_manager.get_stats(source_id)
        print(f"\n日志源类型：{stats['source_type']}")
        print(f"日志源标识：{stats['source_id']}")
        print("-" * 60)

        if stats["position"]:
            pos = stats["position"]
            print(f"最后时间戳：{pos['last_docker_ts']}")
            print(f"Unix 时间戳：{pos['last_timestamp']}")
            print(f"最后采集时间：{pos['last_collected_at']}")
            print(f"最后日志哈希：{pos['last_hash'][:16]}...")
        else:
            print("未找到位置记录（可能从未采集过）")

        print("-" * 60)
        print(f"去重集合数：{stats['dedup_sets']}")
        print(f"总去重记录数：{stats['total_hashes']}")

        await position_manager.close()

    try:
        loop.run_until_complete(get_position())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        loop.close()


@app.command("reset-position")
def reset_position(
    source_id: Annotated[
        str,
        typer.Argument(help="日志源标识（容器名、文件路径等）"),
    ],
    source_type: Annotated[
        str,
        typer.Option("--type", "-t", help="日志源类型 (docker/file/kubernetes)"),
    ] = "docker",
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
    confirm: Annotated[
        bool,
        typer.Option("--confirm", "-y", help="确认重置"),
    ] = False,
) -> None:
    """重置日志源的采集位置（下次启动将从头开始采集）"""
    if not confirm:
        typer.confirm(
            f"确定要重置 '{source_type}:{source_id}' 的采集位置吗？\n"
            "这将导致下次采集时重新读取所有日志。",
            abort=True,
        )

    redis_url = redis_url or settings.get_redis_url()

    position_manager = PositionManager(
        redis_url=redis_url,
        source_type=source_type,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def do_reset():
        await position_manager.reset(source_id)
        print(f"已重置 '{source_type}:{source_id}' 的采集位置")
        await position_manager.close()

    try:
        loop.run_until_complete(do_reset())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        loop.close()


@app.command("cleanup-records")
def cleanup_records(
    source_id: Annotated[
        str,
        typer.Argument(help="日志源标识（容器名、文件路径等）"),
    ],
    source_type: Annotated[
        str,
        typer.Option("--type", "-t", help="日志源类型 (docker/file/kubernetes)"),
    ] = "docker",
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="保留天数"),
    ] = 7,
    redis_url: Annotated[
        str,
        typer.Option("--redis", "-r", help="Redis 连接 URL"),
    ] = None,
) -> None:
    """清理旧的去重记录"""
    redis_url = redis_url or settings.get_redis_url()

    position_manager = PositionManager(
        redis_url=redis_url,
        source_type=source_type,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def do_cleanup():
        deleted = await position_manager.cleanup_old_records(source_id, days)
        print(f"已清理 '{source_type}:{source_id}' 的 {deleted} 条过期记录")
        await position_manager.close()

    try:
        loop.run_until_complete(do_cleanup())
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        loop.close()


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
