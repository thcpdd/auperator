"""Event Handler

处理日志并发布事件
"""

import logging

from auperator.schemas.log import LogEntry
from auperator.schemas.event import Event
from auperator.events import EventCenter
from auperator.collector.handlers.base import BaseLogHandler
from auperator.database.db import get_db
from auperator.database.models import Conversation


logger = logging.getLogger(__name__)


class EventHandler(BaseLogHandler):
    """Event 日志处理器

    接收日志并发布 USER 事件到事件中心，并在数据库中创建对话记录
    """

    def __init__(self, event_center: EventCenter):
        """初始化 Event Handler

        Args:
            event_center: 事件中心
        """
        self.event_center = event_center

    async def handle(self, entry: LogEntry) -> None:
        """处理单条日志（Consumer回调）

        Args:
            entry: LogEntry对象
        """
        try:
            logger.info(f"📥 收到日志: {entry.message[:100]}")

            # 构建消息内容
            prompt = self._build_prompt(entry)

            # 生成对话标题
            if len(entry.message) <= 20:
                title = f"错误日志: {entry.message}"
            else:
                title = f"错误日志: {entry.message[:20]}..."

            # 在数据库中创建对话记录
            db = get_db()
            db_session = db.get_session()
            try:
                thread_id, is_new = await Conversation.get_or_create(
                    session=db_session,
                    thread_id=None,  # 每次错误日志都是新对话
                    title=title,
                )
                logger.info(f"🔖 Thread ID: {thread_id}, is_new: {is_new}")
            finally:
                await db_session.close()

            # 发布 user 事件到事件中心
            user_event = Event.create_user_event(
                thread_id=thread_id,
                content=prompt,
            )
            await self.event_center.publish_event(user_event)
            logger.info(f"✅ 已发布 user 事件: {user_event.event_id}")
        except Exception as e:
            logger.exception(f"❌ 处理日志时出错: {e}")
            raise

    def _build_prompt(self, entry: LogEntry) -> str:
        """构建Agent提示词

        Args:
            entry: LogEntry对象

        Returns:
            提示字符串
        """
        # 提取有用信息
        container = entry.metadata.get('container_name', entry.source or '未知')

        prompt = f"""# 错误日志分析任务

## 错误信息

**错误内容**: {entry.message}
**发生时间**: {entry.timestamp or '未知'}
**来源容器**: {container}

## 背景

这是系统中出现的一个错误日志。请分析这个错误的根本原因，并提供解决方案。

## 你的任务

请根据错误日志，执行以下步骤：

1. **分析错误**
   - 识别错误的类型和根本原因
   - 理解错误发生的上下文

2. **制定解决方案**
   - 设计合理的修复方案
   - 考虑方案的可行性和影响范围

3. **实施修复（如需要）**
   - 如果是代码问题，在沙箱中修复
   - 如果是配置问题，提供配置修改建议
   - 如果需要更多信息，说明需要哪些信息

4. **输出总结**
   - 清晰地说明问题原因
   - 提供具体的解决方案或建议
   - 如果创建了PR，提供PR链接

开始分析这个错误。"""

        return prompt
