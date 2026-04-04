"""事件路由"""

import asyncio
import json
import logging
import re
import threading
from datetime import datetime, timedelta

from docker.errors import DockerException, APIError
from fastapi import APIRouter, Depends, Body, HTTPException, status
from fastapi.responses import StreamingResponse

from auperator.config import settings
from auperator.dependencies import get_event_center, get_docker_client, EventCenter
from auperator.schemas.docker_log import DockerLogEntry


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


def parse_since_to_timestamp(since: str | None) -> int | None:
    """将时间字符串解析为 Unix 时间戳.

    Args:
        since: 时间字符串，如 "1h", "30m", "1h30m"

    Returns:
        Unix 时间戳（秒），如果 since 为空则返回 None

    Examples:
        >>> parse_since_to_timestamp("1h")
        1723456789
        >>> parse_since_to_timestamp("30m")
        1723456789
        >>> parse_since_to_timestamp("1h30m")
        1723456789
        >>> parse_since_to_timestamp("")
        None
        >>> parse_since_to_timestamp(None)
        None
    """
    if not since:
        return None

    # 匹配格式: 1h, 30m, 1h30m, 2h15m30s 等
    pattern = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.fullmatch(pattern, since.strip())

    if not match:
        logger.warning(f"无法解析时间格式: {since}，将获取所有历史日志")
        return None

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    # 如果没有任何时间单位，返回 None
    if hours == 0 and minutes == 0 and seconds == 0:
        return None

    # 计算时间差并转换为 Unix 时间戳
    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    timestamp = int((datetime.now() - delta).timestamp())

    logger.debug(f"解析时间字符串: {since} -> Unix时间戳: {timestamp}")
    return timestamp


@router.post("/web-ui")
async def conversation_events_for_web_ui(
    thread_id: str = Body(description="过滤特定会话的事件", embed=True),
    event_center: EventCenter = Depends(get_event_center),
):
    """SSE 对话事件流端点

    推送对话事件到前端（Server-Sent Events）

    Args:
        thread_id: 会话ID，只推送该会话的事件
        event_center: 事件中心

    Returns:
        StreamingResponse: SSE 事件流
    """
    async def event_stream():
        """生成 SSE 事件流"""
        logger.info(f"✅ SSE 连接已建立，thread_id: {thread_id}")

        try:
            async for event in event_center.consume("web-ui"):
                # 如果指定了 thread_id，只推送该会话的事件
                if thread_id and event.thread_id != thread_id:
                    continue

                # SSE 格式: data: <json>\n\n
                # mode='json' 会自动将 datetime 转换为 ISO 格式字符串
                event_data = event.model_dump(mode='json')
                yield f"data: {json.dumps(event_data)}\n\n"
        except Exception as e:
            logger.exception(f"❌ SSE 错误: {e}")
            # 发送错误事件
            error_event = {
                "error": True,
                "message": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.post("/docker-logs")
async def docker_logs_stream(
    since: str | None = Body(default="1h", description="获取从指定时间开始的日志（如：1h=1小时前，30m=30分钟前，空值=从容器创建开始）"),
    tail: int | None = Body(default=None, description="从末尾获取的日志行数（优先级高于since）")
):
    """SSE Docker日志流端点

    实时推送Docker容器的所有日志（不经过Vector过滤）

    需要在.env中配置MONITORED_CONTAINER才能启用此功能

    Args:
        since: 时间范围（如"1h"、"30m"、"1h30m"），默认"1h"（最近一小时）
        tail: 从末尾获取的行数（优先级高于since）

    Returns:
        StreamingResponse: SSE 日志流
    """
    # 检查是否配置了监控容器
    if not settings.monitored_container:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker日志流未启用。请在.env中设置MONITORED_CONTAINER"
        )

    docker_client = get_docker_client()
    container_name = settings.monitored_container

    async def stream_container_logs():
        """流式推送容器日志（异步生成器）"""
        logger.info(f"🐳 开始推送Docker日志: {container_name}, since={since}, tail={tail}")

        # 获取当前事件循环（主循环）
        loop = asyncio.get_event_loop()

        # 使用异步队列来在线程和生成器之间传递日志
        log_queue = asyncio.Queue()
        stop_event = threading.Event()

        def log_producer():
            """后台线程：从Docker读取日志"""
            try:
                # 获取容器
                try:
                    container = docker_client.containers.get(container_name)
                except APIError as e:
                    logger.error(f"❌ 容器不存在: {container_name}, 错误: {e}")
                    asyncio.run_coroutine_threadsafe(
                        log_queue.put(("error", f"容器 '{container_name}' 不存在")),
                        loop
                    )
                    return

                # 使用Docker低级API获取日志流
                api_client = docker_client.api

                # 构建日志参数
                log_kwargs = {
                    "stream": True,
                    "follow": True,
                    "timestamps": True,
                    "stdout": True,
                    "stderr": True
                }

                # tail优先级高于since
                if tail is not None:
                    log_kwargs["tail"] = tail
                elif since:
                    # 将时间字符串转换为 Unix 时间戳
                    since_timestamp = parse_since_to_timestamp(since)
                    if since_timestamp is not None:
                        log_kwargs["since"] = since_timestamp

                log_stream = api_client.logs(
                    container.id,
                    **log_kwargs
                )

                for log_line in log_stream:
                    if stop_event.is_set():
                        logger.info(f"🛑 日志生产者收到停止信号: {container_name}")
                        break

                    if log_line:
                        asyncio.run_coroutine_threadsafe(
                            log_queue.put(("log", log_line)),
                            loop
                        )

                logger.info(f"📴 Docker日志流结束: {container_name}")

            except Exception as e:
                logger.exception(f"❌ 日志生产者异常: {e}")
                asyncio.run_coroutine_threadsafe(
                    log_queue.put(("error", str(e))),
                    loop
                )
            finally:
                asyncio.run_coroutine_threadsafe(
                    log_queue.put(("eof", None)),
                    loop
                )

        # 启动后台线程
        producer_thread = threading.Thread(target=log_producer, daemon=True)
        producer_thread.start()

        # 心跳间隔（秒）
        heartbeat_interval = 15

        try:
            while True:
                try:
                    # 使用 asyncio.wait_for 实现超时
                    item_type, item_data = await asyncio.wait_for(
                        log_queue.get(),
                        timeout=heartbeat_interval
                    )

                    if item_type == "log":
                        # 处理日志行
                        try:
                            log_line_str = item_data.decode('utf-8', errors='replace').strip()

                            # 分离时间戳和内容
                            if ' ' in log_line_str and 'T' in log_line_str:
                                space_idx = log_line_str.index(' ', log_line_str.index('T'))
                                timestamp_str = log_line_str[:space_idx]
                                content = log_line_str[space_idx + 1:]
                            else:
                                timestamp_str = None
                                content = log_line_str

                            # 判断是stdout还是stderr
                            stream_type = "stdout"
                            if content.startswith("stdout "):
                                stream_type = "stdout"
                                content = content[7:]
                            elif content.startswith("stderr "):
                                stream_type = "stderr"
                                content = content[7:]

                            # 创建日志条目
                            log_entry = DockerLogEntry(
                                container_name=container_name,
                                container_id="unknown",
                                timestamp=datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')) if timestamp_str else datetime.now(),
                                log_line=content,
                                stream=stream_type
                            )

                            # 推送到SSE
                            log_data = log_entry.model_dump(mode='json')
                            yield f"data: {json.dumps(log_data)}\n\n"

                        except Exception as e:
                            logger.error(f"❌ 解析日志行失败: {e}")

                    elif item_type == "error":
                        # 推送错误信息
                        error_data = {"error": True, "message": item_data}
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return

                    elif item_type == "eof":
                        # 日志流结束
                        logger.info(f"✅ Docker日志流正常结束: {container_name}")
                        return

                except asyncio.TimeoutError:
                    # 超时，发送心跳以检测连接状态
                    logger.debug(f"💓 发送心跳检测连接状态: {container_name}")
                    try:
                        # 发送SSE注释作为心跳
                        yield ": heartbeat\n\n"
                        logger.debug(f"💓 心跳成功: {container_name}")
                    except Exception as e:
                        # 捕获所有可能的异常
                        logger.info(f"📴 心跳失败，客户端断开连接: {container_name}, 原因: {type(e).__name__}: {e}")
                        stop_event.set()
                        return

        except asyncio.CancelledError:
            # 异步任务被取消（客户端断开连接）
            logger.info(f"📴 客户端断开连接: {container_name}")
            raise
        finally:
            stop_event.set()
            logger.info(f"✅ Docker日志流已结束: {container_name}")

    return StreamingResponse(
        stream_container_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
