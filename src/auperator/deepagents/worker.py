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

        # 队列管理：thread_id -> asyncio.Queue[Event]
        self.event_queues: dict[str, asyncio.Queue[Event]] = {}
        # 队列处理任务：thread_id -> asyncio.Task
        self.queue_tasks: dict[str, asyncio.Task] = {}
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
            tools=ToolRegistry.get_all(),
            checkpointer=self.checkpointer,
        )
        logger.info("✅ Agent 已创建")

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理 Agent Worker 资源")

        # 停止主任务
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            finally:
                self.task = None

        # 停止所有队列处理任务
        async with self._lock:
            for thread_id, queue_task in list(self.queue_tasks.items()):
                queue_task.cancel()
            self.queue_tasks.clear()
            self.event_queues.clear()

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

        subagent_messages = state.values.get("subagent_messages", [])
        messages = state.values.get("messages", [])

        return messages, subagent_messages

    def get_queue_status(self, thread_id: str) -> dict | None:
        """获取队列状态

        Args:
            thread_id: 会话 ID

        Returns:
            队列状态字典，如果队列不存在则返回 None
        """
        queue = self.event_queues.get(thread_id)
        if queue is None:
            return None

        return {
            "thread_id": thread_id,
            "is_queued": True,
            "queue_size": queue.qsize(),
        }

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
            async for event in self.event_center.consume(self.consumer_group):
                if event.event_type == EventType.USER:
                    await self._handle_user_event(event)
                elif event.event_type == EventType.STOP:
                    await self._handle_stop_event(event)
        except asyncio.CancelledError:
            logger.info("Agent Worker 已取消")
        except Exception as e:
            logger.exception(f"❌ Agent Worker 出错: {e}")

    async def _handle_user_event(self, event: Event):
        """处理 USER 事件，加入队列或创建队列

        Args:
            event: 事件对象
        """
        thread_id = event.thread_id

        async with self._lock:
            is_new_queue = thread_id not in self.event_queues
            if is_new_queue:
                self.event_queues[thread_id] = asyncio.Queue()
                queue_task = asyncio.create_task(self._process_queue(thread_id))
                self.queue_tasks[thread_id] = queue_task
                logger.info(f"✅ 为 {thread_id} 创建事件队列")

        queue = self.event_queues[thread_id]
        queue_position = queue.qsize()

        # 只有需要排队时才发送排队事件
        if queue_position > 0:
            queued_event = Event.create_queued_event(
                thread_id=thread_id,
                queue_position=queue_position,
                queue_size=queue_position + 1
            )
            await self.event_center.publish_event(queued_event)
            logger.info(f"📥 消息已加入队列: {thread_id}, position: {queue_position}")
        else:
            logger.info(f"📥 消息立即处理: {thread_id}")

        # 加入队列
        await queue.put(event)

    async def _process_queue(self, thread_id: str):
        """处理单个 thread_id 的消息队列

        Args:
            thread_id: 会话 ID
        """
        try:
            while True:
                queue = self.event_queues.get(thread_id)
                if not queue:
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    if queue.empty():
                        logger.debug(f"✅ 队列空闲，退出处理: {thread_id}")
                        break
                    continue

                logger.info(f"🔄 开始处理队列消息: {thread_id}")

                try:
                    await self._run_agent(thread_id, event.data["content"])
                except asyncio.CancelledError:
                    logger.info(f"⏹️ 任务被取消: {thread_id}")
                    break
                except Exception as e:
                    logger.exception(f"❌ 处理消息失败: {thread_id}, {e}")
                finally:
                    queue.task_done()

        finally:
            async with self._lock:
                self.event_queues.pop(thread_id, None)
                self.queue_tasks.pop(thread_id, None)
                logger.info(f"🧹 队列已清理: {thread_id}")

    async def _handle_stop_event(self, event: Event):
        """处理 STOP 事件

        Args:
            event: 事件对象
        """
        thread_id = event.thread_id
        reason = event.data.get("reason", "unknown")
        logger.info(f"🛑 收到停止事件: {thread_id}, 原因: {reason}")

        async with self._lock:
            queue_task = self.queue_tasks.get(thread_id)
            if queue_task:
                queue_task.cancel()
                logger.info(f"✅ 队列任务已取消: {thread_id}")
            else:
                logger.warning(f"⚠️ 未找到运行中的队列: {thread_id}")

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
