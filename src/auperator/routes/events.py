"""事件路由"""

import logging
import json

from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse

from auperator.dependencies import get_event_center, EventCenter


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/web-ui")
async def stream_events(
    thread_id: str = Body(description="过滤特定会话的事件", embed=True),
    event_center: EventCenter = Depends(get_event_center),
):
    """SSE 事件流端点

    推送事件到前端（Server-Sent Events）

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
                event_data = event.model_dump()
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
