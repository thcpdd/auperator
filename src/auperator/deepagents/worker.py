"""Agent Worker

Agent 后台任务管理器，负责监听事件并执行 Agent
"""

import asyncio
import logging

import aiosqlite
from langchain.messages import HumanMessage
from langchain_core.messages import BaseMessage
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from auperator.config import settings
from auperator.schemas.event import Event, EventType
from auperator.events import EventCenter
from auperator.deepagents import create_auperator
from auperator.deepagents.tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


class AgentWorker:
    """Agent 后台任务执行器

    负责执行从事件中心监听 USER 事件并执行 Agent 的任务
    管理 checkpointer 和 agent 的生命周期，提供获取历史消息的接口
    """

    def __init__(
        self,
        event_center: EventCenter,
        consumer_group: str = "agent-worker",
        enable_langfuse: bool = True
    ):
        """初始化 Agent Worker

        Args:
            event_center: 事件中心
            consumer_group: 消费者组名称
            enable_langfuse: 是否启用 Langfuse 追踪
        """
        self.event_center = event_center
        self.consumer_group = consumer_group
        self.enable_langfuse = enable_langfuse

        self.checkpointer = None
        self.agent = None
        self.task: asyncio.Task | None = None
        self.langfuse_handler: CallbackHandler | None = None
        self._conn: aiosqlite.Connection | None = None

        # 任务管理：thread_id -> asyncio.Task
        self.running_tasks: dict[str, asyncio.Task] = {}
        # 字典访问锁
        self._lock = asyncio.Lock()

        # Langfuse 回调处理器
        if self.enable_langfuse and all([
            settings.langfuse_public_key,
            settings.langfuse_secret_key,
        ]):
            self.langfuse_handler = CallbackHandler()

    async def initialize(self):
        """初始化 checkpointer 和 agent"""

        logger.info("🔧 初始化 Agent Worker")

        # 创建 SQLite 连接
        self._conn = await aiosqlite.connect(settings.sqlite_db)

        # 创建 checkpointer
        self.checkpointer = AsyncSqliteSaver(self._conn)
        logger.info("✅ Checkpointer 已初始化")

        # 创建 Agent
        self.agent = create_auperator(
            skills=["./src/auperator/deepagents/skills"],
            tools=ToolRegistry.get_all(),
            checkpointer=self.checkpointer,
        )
        logger.info("✅ Agent 已创建")

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理 Agent Worker 资源")

        # 停止任务
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            finally:
                self.task = None

        # 关闭 SQLite 连接
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

        self.checkpointer = None
        self.agent = None

    async def get_history(self, thread_id: str) -> list[BaseMessage]:
        """获取对话历史

        Args:
            thread_id: 会话 ID

        Returns:
            消息列表
        """
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        state = await self.agent.aget_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        return messages

    async def start(self):
        """启动 Agent Worker

        Returns:
            后台任务对象
        """
        if self.task is not None:
            logger.warning("Agent Worker 已经在运行")
            return self.task

        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info("🚀 启动 Agent Worker")
        self.task = asyncio.create_task(self._run())
        return self.task

    async def stop(self):
        """停止 Agent Worker"""
        if self.task is None:
            return

        logger.info("⏹️  停止 Agent Worker")
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        finally:
            self.task = None

    async def _run(self):
        """运行消费循环"""
        try:
            # 开始消费事件
            async for event in self.event_center.consume(self.consumer_group):
                # 处理不同类型的事件
                if event.event_type == EventType.USER:
                    # 创建后台任务并记录
                    task = asyncio.create_task(self._handle_user_event(event))

                    async with self._lock:
                        self.running_tasks[event.thread_id] = task

                elif event.event_type == EventType.STOP:
                    await self._handle_stop_event(event)
        except asyncio.CancelledError:
            logger.info("Agent Worker 已取消")
        except Exception as e:
            logger.exception(f"❌ Agent Worker 出错: {e}")

    async def _handle_user_event(self, event: Event):
        """处理 USER 事件

        Args:
            event: 事件对象
        """
        thread_id = event.thread_id
        logger.info(f"📨 收到 user 事件: {thread_id}")

        try:
            # 创建并启动 agent 任务
            await self._run_agent(thread_id, event.data["content"])
        except asyncio.CancelledError:
            logger.info(f"⏹️ 任务被取消: {thread_id}")
        finally:
            # 清理任务记录
            async with self._lock:
                self.running_tasks.pop(thread_id, None)
                logger.debug(f"🧹 任务已清理: {thread_id}")

    async def _handle_stop_event(self, event: Event):
        """处理 STOP 事件

        Args:
            event: 事件对象
        """
        thread_id = event.thread_id
        reason = event.data.get("reason", "unknown")
        logger.info(f"🛑 收到停止事件: {thread_id}, 原因: {reason}")

        async with self._lock:
            # 取消正在运行的任务
            if thread_id in self.running_tasks:
                task = self.running_tasks[thread_id]
                task.cancel()
                logger.info(f"✅ 任务已取消: {thread_id}")
            else:
                logger.warning(f"⚠️ 未找到运行中的任务: {thread_id}")

    async def _run_agent(self, thread_id: str, content: str):
        """运行 Agent

        Args:
            thread_id: 会话 ID
            content: 用户消息内容
        """
        try:
            # 构建配置
            config = {
                "configurable": {"thread_id": thread_id}
            }
            if self.langfuse_handler:
                config["callbacks"] = [self.langfuse_handler]

            # 执行 Agent
            await self.agent.ainvoke(
                {"messages": [HumanMessage(content)]},
                config,
                subgraphs=True
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"❌ Agent 执行失败: {thread_id}, 错误: {e}")
        finally:
            agent_event = Event.create_agent_event(
                thread_id=thread_id,
                content="[Done]"
            )
            await self.event_center.publish_event(agent_event)
