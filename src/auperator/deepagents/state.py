"""Auperator Agent 状态定义."""

from typing import Annotated, NotRequired, Required, TypedDict

from langchain.agents.middleware import AgentState
from langchain_core.messages import AnyMessage


class SubAgentExecution(TypedDict):
    """子 agent 执行记录.

    用于持久化子 agent 的执行过程，包括中间消息。
    通过 tool_call_id 与主 agent 的消息关联。
    """

    tool_call_id: Required[str]
    """工具调用 ID，用于关联主 agent 的消息"""

    subagent_name: Required[str]
    """子 agent 的名称（如 'general-purpose', 'researcher' 等）"""

    messages: Required[list[AnyMessage]]
    """子 agent 的中间消息列表

    这些消息是子 agent 执行过程中的中间步骤，
    不包括第一条（HumanMessage 输入）和最后一条（最终输出）。
    即：result["messages"][1:-1]
    """


def append_subagent_execution(
    left: list[SubAgentExecution] | None,
    right: list[SubAgentExecution] | None,
) -> list[SubAgentExecution]:
    """追加子 agent 执行记录.

    简单的列表追加函数，用于合并 subagent_messages.

    Args:
        left: 现有的执行记录列表
        right: 要追加的执行记录列表

    Returns:
        合并后的列表
    """
    if not left:
        return right or []
    if not right:
        return left or []
    return left + right


class AuperatorState(AgentState):
    """Auperator Agent 状态.

    继承自 LangChain 的 AgentState，添加了子 agent 消息历史记录。
    所有字段都会被 checkpointer 自动持久化。
    """

    subagent_messages: Annotated[list[SubAgentExecution], append_subagent_execution]
