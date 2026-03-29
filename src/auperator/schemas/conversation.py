"""Conversation 数据模型"""

from datetime import datetime
from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """会话模型"""

    id: int
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    """创建会话模型"""

    thread_id: str
    title: str


class Message(BaseModel):
    """消息模型"""

    type: str  # human, ai, tool, etc.
    content: str
    tool_name: str | None = None
    tool_args: dict | None = None


class SendMessageRequest(BaseModel):
    """发送消息请求模型"""

    message: str = Field(..., description="用户消息内容")
    thread_id: str | None = Field(None, description="会话 thread_id，不提供则创建新会话")


class RenameConversationRequest(BaseModel):
    """重命名对话请求模型"""

    title: str = Field(..., description="新标题", min_length=1, max_length=200)
