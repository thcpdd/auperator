"""数据库模型"""

import logging
from typing import Tuple

from sqlalchemy import Column, Integer, String, DateTime, select, func

from auperator.database.base import Base
from auperator.utils.checkpointer import generate_thread_id


logger = logging.getLogger(__name__)


class Conversation(Base):
    """会话表"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    async def get_by_thread_id(cls, session, thread_id: str):
        """通过 thread_id 获取会话

        Args:
            session: 异步数据库会话
            thread_id: thread_id

        Returns:
            Conversation 对象或 None
        """
        result = await session.execute(
            select(cls).where(cls.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def list_all(cls, session, limit: int | None = None):
        """获取所有会话列表

        Args:
            session: 异步数据库会话
            limit: 限制数量

        Returns:
            Conversation 对象列表
        """
        stmt = select(cls).order_by(cls.updated_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_or_create(
        cls,
        session,
        thread_id: str | None,
        title: str,
    ) -> Tuple[str, bool]:
        """获取或创建对话

        统一的对话管理逻辑：
        - 如果 thread_id 存在且对应的对话存在，更新 updated_at 并返回
        - 如果 thread_id 为 None 或对话不存在，创建新对话

        Args:
            session: 异步数据库会话
            thread_id: 会话 thread_id（可选）
            title: 对话标题

        Returns:
            Tuple[thread_id, is_new]: (会话ID, 是否为新对话)
        """
        is_new = False

        if thread_id:
            # 尝试获取现有对话
            conversation = await cls.get_by_thread_id(session, thread_id)
            if conversation:
                # 更新 updated_at
                conversation.updated_at = func.now()
                await session.commit()
                logger.debug(f"✅ 找到现有对话: {thread_id}")
                return thread_id, False

        # 创建新对话
        thread_id = thread_id or generate_thread_id()
        is_new = True

        conversation = cls(
            thread_id=thread_id,
            title=title,
        )
        session.add(conversation)
        await session.commit()
        logger.info(f"✅ 创建新对话: {thread_id}, title: {title}")

        return thread_id, is_new
