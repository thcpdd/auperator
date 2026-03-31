"""Middleware for automatically sending agent events to the event center."""

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.config import get_config
from langgraph.types import Command

from auperator.events import EventCenter
from auperator.schemas.event import Event, EventType
from auperator.utils.checkpointer import generate_thread_id

logger = logging.getLogger(__name__)


class EventAutoSendMiddleware(AgentMiddleware[AgentState, ContextT, ResponseT]):
    """Middleware for automatically sending agent events to the event center.

    This middleware automatically sends:
    - Tool calls (tool name and arguments)
    - Agent text outputs

    to the event center for consumption by downstream services (Web UI, storage, etc.).

    Note: Event sending only works in async mode (awrap_model_call, awrap_tool_call).
    Sync methods (wrap_model_call, wrap_tool_call) are provided for interface
    compatibility but do not send events.

    The thread_id is automatically extracted from the LangGraph config context.

    Args:
        event_center: The EventCenter instance for sending events. If None,
            creates a new instance automatically.

    Example:
        ```python
        from auperator.deepagents.middleware import EventAutoSendMiddleware

        # EventCenter is created automatically if not provided
        middleware = EventAutoSendMiddleware()

        # Or provide a custom EventCenter
        from auperator.events import EventCenter
        event_center = EventCenter()
        middleware = EventAutoSendMiddleware(event_center=event_center)

        # Use with async agent
        agent = create_auperator(middleware=[middleware])
        await agent.ainvoke(
            {"messages": [HumanMessage("...")]},
            config={"configurable": {"thread_id": "th-001"}}
        )
        ```
    """

    def __init__(self, event_center: EventCenter | None = None):
        """Initialize the EventAutoSendMiddleware.

        Args:
            event_center: The EventCenter instance for sending events.
                If None, creates a new instance automatically.
        """
        super().__init__()
        self.event_center = event_center or EventCenter()

    def _get_thread_id(self) -> str:
        """Extract thread_id from LangGraph config.

        Uses get_config() to access the RunnableConfig from langgraph's
        contextvar. Falls back to a generated session ID if not available.

        Returns:
            Thread ID string from config, or a generated session ID
                (e.g., 'session_a1b2c3d4') if not in a runnable context.
        """
        try:
            config = get_config()
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id is not None:
                return str(thread_id)
        except RuntimeError:
            # Not in a runnable context
            pass

        # Fallback: generate thread ID
        generated_id = generate_thread_id()
        logger.warning("No thread_id found, using generated thread ID: %s", generated_id)
        return generated_id

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Capture model outputs and send as agent events.

        Note: This method is required by the middleware interface but only delegates
        to the async implementation. Use the async version for proper event sending.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        logger.warning(
            "EventAutoSendMiddleware: wrap_model_call (sync) does not send events. "
            "Use async methods (ainvoke, astream) for event sending."
        )
        # For sync path, just call handler without event sending
        # Event sending requires async execution
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT]:
        """(async) Capture model outputs and send as agent events.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        # Get thread_id from config
        thread_id = self._get_thread_id()
        # Call the handler to get the response
        response = await handler(request)

        # Extract and send AIMessage content
        try:
            if hasattr(response, "result") and response.result:
                last_message = response.result[-1]

                if isinstance(last_message, AIMessage):
                    # Extract text content
                    content = self._extract_text_content(last_message)

                    if content:
                        # Send as agent event (text type)
                        event = Event.create_agent_event(
                            thread_id=thread_id,
                            content=content,
                        )
                        await self.event_center.publish_event(event)
                        logger.debug(f"Sent agent text event: {content[:100]}...")
        except Exception as e:
            logger.error(f"Error capturing model output: {e}")

        return response

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Capture tool calls and send as agent events.

        Note: This method is required by the middleware interface but only delegates
        to the async implementation. Use the async version for proper event sending.

        Args:
            request: The tool call request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The tool message or command from the handler.
        """
        logger.warning(
            "EventAutoSendMiddleware: wrap_tool_call (sync) does not send events. "
            "Use async methods (ainvoke, astream) for event sending."
        )
        # For sync path, just call handler without event sending
        # Event sending requires async execution
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """(async) Capture tool calls and send as agent events.

        Args:
            request: The tool call request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The tool message or command from the handler.
        """
        # Get thread_id from config
        thread_id = self._get_thread_id()
        # Extract tool call info
        tool_name = request.tool_call.get("name", "")
        tool_args = request.tool_call.get("args", {})

        # 生成唯一的 event_id，用于关联工具调用和结果
        tool_event_id = str(uuid.uuid4())

        # Send tool call event (before execution)
        try:
            event = Event.create_tool_event(
                thread_id=thread_id,
                tool=tool_name,
                args=tool_args,
                content="",  # 工具调用前，content 为空
                event_id=tool_event_id,  # 使用相同的 event_id
            )
            await self.event_center.publish_event(event)
            logger.debug(f"Sent tool call event: {tool_name}, event_id: {tool_event_id}")
        except Exception as e:
            logger.error(f"Error capturing tool call: {e}")

        # Call the handler and capture result
        result = await handler(request)

        # Send tool result event (after execution)
        try:
            if isinstance(result, ToolMessage):
                # Extract content from ToolMessage
                content = result.content
                tool_result_event = Event.create_tool_event(
                    thread_id=thread_id,
                    tool=tool_name,
                    args=tool_args,
                    content=content,  # 工具执行结果
                    event_id=tool_event_id,  # 使用相同的 event_id
                )
                await self.event_center.publish_event(tool_result_event)
                logger.debug(f"Sent tool result event: {tool_name}, event_id: {tool_event_id}")
        except Exception as e:
            logger.error(f"Error capturing tool result: {e}")

        return result

    def _extract_text_content(self, message: AIMessage) -> str:
        """Extract text content from an AIMessage.

        Args:
            message: The AIMessage to extract text from.

        Returns:
            The extracted text content.
        """
        # If content is a string, return it directly
        if isinstance(message.content, str):
            return message.content

        # If content is a list, extract text blocks
        if isinstance(message.content, list):
            text_parts = []
            for block in message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "\n".join(text_parts)

        # Fallback: return stringified content
        return str(message.content)
