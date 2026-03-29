"""聊天 API 路由"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status

from auperator.config import settings
from auperator.database.db import get_db_session
from auperator.database.models import Conversation
from auperator.schemas.conversation import Conversation as ConversationSchema, SendMessageRequest, RenameConversationRequest
from auperator.schemas.event import Event
from auperator.dependencies import get_event_center, get_agent_worker
from auperator.utils.checkpointer import generate_thread_id
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
        # 确定使用哪个 thread_id
        if thread_id:
            # 继续对话
            is_new = False

            # 查询会话
            conversation = await Conversation.get_by_thread_id(db, thread_id)
            if conversation:
                # 触发 updated_at 更新（通过修改属性）
                conversation.updated_at = func.now()
                await db.commit()
        else:
            # 新对话
            thread_id = generate_thread_id()
            is_new = True

            # 创建会话记录
            title = message[:10]  # 取前 10 个字符作为标题
            if len(message) > 10:
                title += "..."

            conversation = Conversation(
                thread_id=thread_id,
                title=title,
            )
            db.add(conversation)
            await db.commit()

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
        for msg in messages:
            content = msg.content if hasattr(msg, "content") else str(msg)

            message_data = {
                "type": msg.type,
                "content": content,
            }

            # 如果是工具调用消息
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name"):
                        message_data["tool_name"] = tool_call["name"]
                        message_data["tool_args"] = tool_call.get("args")

            formatted_messages.append(message_data)

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
