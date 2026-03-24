"""事件相关的 Pydantic 模型."""

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """事件类型枚举."""

    USER = "user"
    AGENT = "agent"


class UserEventData(BaseModel):
    """用户事件数据.

    来源包括：日志触发、用户主动发送（API/Web/CLI）
    """

    message_type: str = Field(default="text", description="消息类型，目前只有 text")
    content: str = Field(description="用户发送的内容或日志内容")

    model_config = {"extra": "allow"}


class AgentEventData(BaseModel):
    """Agent 事件数据.

    来自 Agent.astream() 的输出
    """

    message_type: str = Field(description="消息类型：text 或 tool")
    content: str = Field(default="", description="Agent 输出内容（工具调用时为空字符串）")
    tool: str | None = Field(default=None, description="工具名称（仅当 message_type=tool 时有值）")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数（仅当 message_type=tool 时有值）")

    model_config = {"extra": "allow"}


class Event(BaseModel):
    """事件模型.

    统一的事件结构，用于事件中心。
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()), description="事件唯一标识")
    event_type: EventType = Field(description="事件类型：user 或 agent")
    thread_id: str = Field(description="会话标识（LangGraph thread_id）")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    data: dict[str, Any] = Field(description="事件数据（UserEventData 或 AgentEventData 的字典形式）")

    # 内部字段：用于 Redis
    message_id: str | None = Field(default=None, exclude=True, description="Redis Stream 消息 ID")

    model_config = {"extra": "allow"}

    @classmethod
    def create_user_event(
        cls,
        thread_id: str,
        content: str,
        **kwargs
    ) -> "Event":
        """创建用户事件.

        Args:
            thread_id: 会话标识
            content: 用户内容
            **kwargs: 其他字段

        Returns:
            Event 实例
        """
        return cls(
            event_type=EventType.USER,
            thread_id=thread_id,
            data={
                "message_type": "text",
                "content": content,
                **kwargs
            }
        )

    @classmethod
    def create_agent_event(
        cls,
        thread_id: str,
        content: str = "",
        tool: str | None = None,
        args: dict[str, Any] | None = None,
        **kwargs
    ) -> "Event":
        """创建 Agent 事件.

        Args:
            thread_id: 会话标识
            content: Agent 输出内容
            tool: 工具名称（可选）
            args: 工具参数（可选）
            **kwargs: 其他字段

        Returns:
            Event 实例
        """
        data: dict[str, Any] = {
            "message_type": "tool" if tool else "text",
            "content": content,
        }

        if tool:
            data["tool"] = tool
        if args:
            data["args"] = args

        data.update(kwargs)

        return cls(
            event_type=EventType.AGENT,
            thread_id=thread_id,
            data=data
        )

    def to_redis_dict(self) -> dict[str, str]:
        """转换为 Redis Stream 需要的字典格式（所有值转为字符串）.

        Returns:
            字典，所有值都是字符串
        """

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "thread_id": self.thread_id,
            "timestamp": self.timestamp.isoformat(),
            "data": json.dumps(self.data, ensure_ascii=False),
        }

    @classmethod
    def from_redis_dict(cls, data: dict[str, bytes | str], message_id: str | None = None) -> "Event":
        """从 Redis Stream 数据创建 Event 实例.

        Args:
            data: Redis Stream 消息数据
            message_id: Redis Stream 消息 ID

        Returns:
            Event 实例
        """

        # 处理 bytes 和 str 类型
        def to_str(v: bytes | str) -> str:
            if isinstance(v, bytes):
                return v.decode("utf-8")
            return v

        return cls(
            event_id=to_str(data[b"event_id"] if b"event_id" in data else data["event_id"]),
            event_type=EventType(to_str(data[b"event_type"] if b"event_type" in data else data["event_type"])),
            thread_id=to_str(data[b"thread_id"] if b"thread_id" in data else data["thread_id"]),
            timestamp=datetime.fromisoformat(
                to_str(data[b"timestamp"] if b"timestamp" in data else data["timestamp"])
            ),
            data=json.loads(
                to_str(data[b"data"] if b"data" in data else data["data"])
            ),
            message_id=message_id,
        )
