"""数据库管理"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from auperator.config import settings
from .base import Base


logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str | None = None):
        """初始化数据库

        Args:
            db_path: 数据库文件路径，如果为 None 则使用配置
        """
        self.db_path = db_path or settings.sqlite_db
        self.engine = None
        self.async_session_maker = None

    def connect(self):
        """连接数据库"""
        if self.engine is None:
            # SQLite 需要使用 aiosqlite
            database_url = f"sqlite+aiosqlite:///{self.db_path}"
            logger.info(f"📦 连接数据库: {self.db_path}")
            self.engine = create_async_engine(
                database_url,
                echo=False,
            )
            self.async_session_maker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            logger.info("✅ 数据库连接成功")

    async def create_tables(self):
        """创建所有表"""
        if self.engine is None:
            self.connect()
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ 数据库表创建成功")

    def get_session(self) -> AsyncSession:
        """获取数据库会话

        Returns:
            AsyncSession: SQLAlchemy 异步会话
        """
        if self.async_session_maker is None:
            self.connect()
        return self.async_session_maker()

    async def get_session_generator(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（生成器版本，用于依赖注入）

        Yields:
            AsyncSession: SQLAlchemy 异步会话
        """
        if self.async_session_maker is None:
            self.connect()
        async with self.async_session_maker() as session:
            yield session

    async def close(self):
        """关闭数据库连接"""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.async_session_maker = None
            logger.info("📦 数据库连接已关闭")


# 全局数据库实例
_db: Database | None = None


def get_db() -> Database:
    """获取全局数据库实例

    Returns:
        Database: 数据库实例
    """
    global _db
    if _db is None:
        _db = Database()
        _db.connect()
    return _db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（依赖注入）

    Yields:
        AsyncSession: 数据库会话
    """
    db = get_db()
    async with db.async_session_maker() as session:
        yield session


async def init_db():
    """初始化数据库（在应用启动时调用）"""
    db = get_db()
    await db.create_tables()
    logger.info(f"✅ 数据库初始化完成: {db.db_path}")


async def close_db():
    """关闭数据库（在应用关闭时调用）"""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
