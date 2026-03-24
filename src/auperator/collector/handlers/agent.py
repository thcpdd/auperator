"""Agent Handler

处理日志并调用Agent
"""

import logging
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langchain.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from auperator.config import settings
from auperator.schemas.log import LogEntry
from auperator.schemas.event import Event
from auperator.events import EventCenter
from auperator.collector.handlers.base import BaseLogHandler
from auperator.utils.checkpointer import generate_thread_id


logger = logging.getLogger(__name__)


class AgentHandler(BaseLogHandler):
    """Agent 日志处理器

    接收日志并调用Agent处理
    """

    def __init__(
        self,
        agent: CompiledStateGraph | None = None,
        enable_langfuse: bool = True,
        event_center: EventCenter | None = None,
    ):
        """初始化 Agent Handler

        Args:
            agent: Agent实例（LangGraph CompiledStateGraph）
            enable_langfuse: 是否启用Langfuse追踪
            event_center: 事件中心（可选）
        """
        self.agent = agent
        self.enable_langfuse = enable_langfuse
        self.event_center = event_center  # 事件中心

        # Langfuse回调处理器
        self.langfuse_handler = None
        if enable_langfuse and all([
            settings.langfuse_public_key,
            settings.langfuse_secret_key,
        ]):
            self.langfuse_handler = CallbackHandler()

    async def handle(self, entry: LogEntry) -> None:
        """处理单条日志（Consumer回调）

        Args:
            entry: LogEntry对象
        """
        if self.agent is None:
            logger.warning("Agent未初始化")
            return

        try:
            logger.info(f"📥 收到日志: {entry.message[:100]}")

            # 生成 thread_id
            thread_id = generate_thread_id()
            logger.info(f"🔖 Thread ID: {thread_id}")

            # 调用Agent处理
            prompt = self._build_prompt(entry)

            # 发布 user 事件到事件中心
            if self.event_center:
                try:
                    user_event = Event.create_user_event(
                        thread_id=thread_id,
                        content=prompt,
                    )
                    await self.event_center.publish_event(user_event)
                    logger.debug(f"✅ 已发布 user 事件: {user_event.event_id}")
                except Exception as e:
                    logger.warning(f"⚠️  发布 user 事件失败: {e}")

            # 调用Agent
            callbacks = [self.langfuse_handler] if self.langfuse_handler else None

            config = {"configurable": {"thread_id": thread_id}}
            if callbacks:
                config["callbacks"] = callbacks

            async for _ in self.agent.astream(
                {"messages": [HumanMessage(prompt)]},
                config,
                stream_mode="updates",
                subgraphs=True,
            ):
                pass
            logger.info(f"✅ Agent 处理完成")
        except Exception as e:
            logger.exception(f"❌ 处理日志时出错: {e}")
            raise  # 重新抛出异常，让 Consumer 能够感知

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
