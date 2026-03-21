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
from auperator.collector.handlers.base import BaseLogHandler


logger = logging.getLogger(__name__)


class AgentHandler(BaseLogHandler):
    """Agent 日志处理器

    接收日志并调用Agent处理
    """

    def __init__(
        self,
        agent: CompiledStateGraph | None = None,
        enable_langfuse: bool = True,
    ):
        """初始化 Agent Handler

        Args:
            agent: Agent实例（LangGraph CompiledStateGraph）
            enable_langfuse: 是否启用Langfuse追踪
        """
        self.agent = agent
        self.enable_langfuse = enable_langfuse

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

            # 调用Agent处理
            prompt = self._build_prompt(entry)

            # 调用Agent
            callbacks = [self.langfuse_handler] if self.langfuse_handler else None

            async for _ in self.agent.astream(
                {"messages": [HumanMessage(prompt)]},
                {"callbacks": callbacks} if callbacks else {},
                stream_mode="updates",
                subgraphs=True,
            ):
                pass
            print("Done")
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
