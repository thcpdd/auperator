"""聊天 API 路由"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status, Body

from auperator.config import settings
from auperator.database.db import get_db_session
from auperator.database.models import Conversation
from auperator.schemas.conversation import Conversation as ConversationSchema, SendMessageRequest, RenameConversationRequest
from auperator.schemas.event import Event
from auperator.dependencies import get_event_center, get_agent_worker
from auperator.state import global_state
from auperator.events import EventCenter
from auperator.deepagents import AgentWorker


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", status_code=status.HTTP_200_OK)
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db_session),
    event_center: EventCenter = Depends(get_event_center),
):
    """发送消息给 Agent

    Args:
        request: 发送消息请求
        db: 数据库会话
        event_center: 事件中心

    Returns:
        dict: 包含 thread_id 和 is_new 的响应
    """
    message = request.message
    thread_id = request.thread_id

    try:
        # 生成对话标题（取前 20 个字符）
        title = message[:20]
        if len(message) > 20:
            title += "..."

        # 统一的对话管理逻辑
        thread_id, is_new = await Conversation.get_or_create(
            session=db,
            thread_id=thread_id,
            title=title,
        )

        logger.info(f"📤 发送消息: thread_id={thread_id}, is_new={is_new}")

        # 发布 user 事件
        user_event = Event.create_user_event(
            thread_id=thread_id,
            content=message,
        )
        await event_center.publish_event(user_event)
        logger.debug(f"✅ 已发布 user 事件: {user_event.event_id}")

        # 立即返回（Agent 在后台执行）
        return {
            "thread_id": thread_id,
            "is_new": is_new,
            "status": "processing",
            "title": title
        }

    except Exception as e:
        logger.exception(f"❌ 发送消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}",
        )


@router.get("/conversations", response_model=List[ConversationSchema])
async def list_conversations(db: AsyncSession = Depends(get_db_session)):
    """查询对话列表

    Args:
        db: 数据库会话

    Returns:
        List[ConversationSchema]: 对话列表
    """
    try:
        conversations = await Conversation.list_all(db)

        return [
            ConversationSchema(
                id=conv.id,
                thread_id=conv.thread_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv in conversations
        ]

    except Exception as e:
        logger.exception(f"❌ 查询对话列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询对话列表失败: {str(e)}",
        )


@router.get("/conversations/{thread_id}")
async def get_conversation(
    thread_id: str,
    agent_worker: AgentWorker = Depends(get_agent_worker),
):
    """查询对话详情

    Args:
        thread_id: thread_id
        agent_worker: Agent Worker

    Returns:
        dict: 包含消息历史的响应
    """
    try:
        # 从 agent_worker 获取消息历史
        messages = await agent_worker.get_history(thread_id)

        # 格式化消息
        formatted_messages = []
        pending_tool_calls = {}  # 记录待合并的工具调用 {tool_call_id: tool_call_data}

        for msg in messages:
            msg_type = msg.type if hasattr(msg, "type") else msg.__class__.__name__

            # 处理 AIMessage
            if msg_type == "ai":
                content = msg.content if hasattr(msg, "content") else ""

                # 如果有 content，先添加 AI 文本消息
                if content:
                    formatted_messages.append({
                        "type": "ai",
                        "content": content,
                    })

                # 如果有工具调用，记录下来等待 ToolMessage
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_call_id = tool_call.get("id")
                        if tool_call_id:
                            pending_tool_calls[tool_call_id] = {
                                "type": "tool",
                                "name": tool_call.get("name"),
                                "args": tool_call.get("args", {}),
                            }

            # 处理 ToolMessage（工具调用结果）
            elif msg_type == "tool":
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id and tool_call_id in pending_tool_calls:
                    # 合并工具调用和结果
                    tool_data = pending_tool_calls.pop(tool_call_id)
                    tool_data["content"] = msg.content if hasattr(msg, "content") else str(msg)
                    formatted_messages.append(tool_data)

            # 处理 HumanMessage
            elif msg_type == "human":
                content = msg.content if hasattr(msg, "content") else str(msg)
                formatted_messages.append({
                    "type": "human",
                    "content": content,
                })

            # 其他类型消息
            else:
                content = msg.content if hasattr(msg, "content") else str(msg)
                formatted_messages.append({
                    "type": msg_type,
                    "content": content,
                })

        return {
            "thread_id": thread_id,
            "messages": formatted_messages,
        }

    except Exception as e:
        logger.exception(f"❌ 查询对话详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询对话详情失败: {str(e)}",
        )


@router.delete("/conversations/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    thread_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除对话

    Args:
        thread_id: 会话 thread_id
        db: 数据库会话
    """
    try:
        # 查询会话
        conversation = await Conversation.get_by_thread_id(db, thread_id)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话不存在: {thread_id}",
            )

        # 删除会话
        await db.delete(conversation)
        await db.commit()

        logger.info(f"✅ 对话已删除: {thread_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ 删除对话失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败: {str(e)}",
        )


@router.patch("/conversations/{thread_id}/title")
async def rename_conversation(
    thread_id: str,
    request: RenameConversationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """重命名对话标题

    Args:
        thread_id: 会话 thread_id
        request: 重命名请求
        db: 数据库会话

    Returns:
        更新后的对话信息
    """
    try:
        # 查询会话
        conversation = await Conversation.get_by_thread_id(db, thread_id)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话不存在: {thread_id}",
            )

        # 更新标题
        conversation.title = request.title
        await db.commit()
        await db.refresh(conversation)

        logger.info(f"✅ 对话标题已更新: {thread_id} -> {request.title}")

        return ConversationSchema(
            id=conversation.id,
            thread_id=conversation.thread_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ 重命名对话失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重命名对话失败: {str(e)}",
        )


@router.post("/stop", status_code=status.HTTP_200_OK)
async def stop_conversation(
    thread_id: str = Body(..., description="要停止的对话 ID", embed=True),
    event_center: EventCenter = Depends(get_event_center)
):
    """停止正在运行的对话

    Args:
        thread_id: 要停止的对话 thread_id
        event_center: 事件中心

    Returns:
        dict: 停止确认
    """
    try:
        # 发布停止事件
        stop_event = Event.create_stop_event(
            thread_id=thread_id,
            reason="user_requested"
        )
        await event_center.publish_event(stop_event)

        logger.info(f"🛑 发送停止事件: {thread_id}")

        return {
            "status": "stopping",
            "thread_id": thread_id,
            "message": "停止信号已发送"
        }

    except Exception as e:
        logger.exception(f"❌ 停止对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止对话失败: {str(e)}",
        )


@router.get("/conversations/{thread_id}/queue-status")
async def get_queue_status(
    thread_id: str,
    agent_worker: AgentWorker = Depends(get_agent_worker)
):
    """查询对话的队列状态

    Args:
        thread_id: 会话 thread_id
        agent_worker: Agent Worker

    Returns:
        队列状态信息
    """
    try:
        status = agent_worker.get_queue_status(thread_id)

        if status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"队列不存在或已完成: {thread_id}"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ 查询队列状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询队列状态失败: {str(e)}",
        )
