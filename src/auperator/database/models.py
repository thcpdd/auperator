"""数据库模型"""

from sqlalchemy import Column, Integer, String, DateTime, select, func

from auperator.database.base import Base


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
