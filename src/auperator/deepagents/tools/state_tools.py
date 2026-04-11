"""状态访问工具

Agent使用的状态读写工具，用于在工作流中传递信息
"""

import logging
from typing import Annotated

from langchain_core.tools import tool
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime
from langchain.agents.middleware.types import AgentState
from langgraph.types import Command

from auperator.deepagents.state import AuperatorState

logger = logging.getLogger(__name__)


# 可用的状态字段
AVAILABLE_STATE_FIELDS = {
    "error_log": "完整的错误日志",
    "analysed_result": "日志分析结果（由log_analysis子agent生成）",
    "fixed_result": "代码修复结果（由fix子agent生成）",
}


@tool
def get_state(
    runtime: ToolRuntime[None, AuperatorState],
    names: Annotated[
        list[str],
        f"状态字段名称列表。可用字段：{', '.join(AVAILABLE_STATE_FIELDS.keys())}。"
        f"必须提供一个或多个字段名。"
    ],
) -> str:
    """获取一个或多个状态字段的值

    用于在工作流中获取其他子agent生成的信息。

    Args:
        names: 状态字段名称列表（必须提供一个或多个）

    Returns:
        状态字段的值，格式化为易读的文本。

    Examples:
        # 获取单个字段
        get_state(names=["error_log"])

        # 获取多个字段
        get_state(names=["error_log", "analysed_result"])
    """
    state = runtime.state

    # 构建结果
    results = []
    for name in names:
        value = state.get(name)
        if value is not None:
            # 添加字段标题
            field_desc = AVAILABLE_STATE_FIELDS.get(name, name)
            results.append(f"## {field_desc}\n\n{value}")
        else:
            results.append(f"## {name}\n\n（该字段为空）")

    return "\n\n---\n\n".join(results)


@tool
def set_state(
    runtime: ToolRuntime[None, AuperatorState],
    name: Annotated[str, f"状态字段名称。可用字段：{', '.join(AVAILABLE_STATE_FIELDS.keys())}"],
    value: Annotated[str, "状态字段的值"],
) -> Command:
    """设置状态字段的值

    用于在工作流中保存信息，供其他子agent使用。

    Args:
        name: 状态字段名称
        value: 状态字段的值

    Returns:
        Command对象，用于更新state
    """
    # 验证字段名是否有效
    if name not in AVAILABLE_STATE_FIELDS:
        available = ", ".join(AVAILABLE_STATE_FIELDS.keys())
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"无效的状态字段名 '{name}'。可用字段：{available}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })

    return Command(update={
        name: value,
        "messages": [
            ToolMessage(
                content=f"成功保存状态字段 '{name}'！",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


def get_tools():
    return [get_state, set_state]
