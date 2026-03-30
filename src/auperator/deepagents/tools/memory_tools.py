"""记忆工具

Agent使用的记忆存储和检索工具
"""

import json
import logging
import os
from typing import Any

import httpx
from langchain_core.tools import tool

from auperator.config import settings

logger = logging.getLogger(__name__)


BASE_URL = f"http://{settings.api_host}:{settings.api_port}"


@tool
def save_memory(
    problem: str,
    root_cause: str,
    solution: str,
    metadata: dict[str, Any] | str | None = None,
) -> str:
    """保存记忆到知识库

    当你完成了任务修复，并且从中学到了有价值的经验时，使用此工具保存。

    Args:
        problem: 具体遇到了什么错误，错误表现是什么
        root_cause: 错误的根本原因是什么，如何定位的
        solution: 采取了什么修复措施，具体的代码变更内容是什么
        metadata: 其他元数据（可选），可以是字典或 JSON 字符串

    Returns:
        memory_id: 记忆ID
    """
    try:
        # 处理 metadata 参数：如果传入的是字符串，尝试解析为字典
        parsed_metadata = metadata
        if metadata is not None:
            if isinstance(metadata, str):
                try:
                    parsed_metadata = json.loads(metadata)
                    logger.debug(f"已将 metadata 从 JSON 字符串解析为字典")
                except json.JSONDecodeError as e:
                    logger.warning(f"无法解析 metadata JSON 字符串: {e}，将忽略 metadata")
                    parsed_metadata = None
            elif not isinstance(metadata, dict):
                logger.warning(f"metadata 类型错误: {type(metadata)}，将忽略 metadata")
                parsed_metadata = None

        response = httpx.post(
            f"{BASE_URL}/memory/save",
            json={
                "problem": problem,
                "root_cause": root_cause,
                "solution": solution,
                "metadata": parsed_metadata,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        memory_id = data.get("memory_id")
        logger.info(f"记忆已保存: {memory_id}")
        return f"记忆已保存，ID: {memory_id}"

    except httpx.HTTPError as e:
        logger.error(f"保存记忆失败: {e}")
        return f"保存记忆失败: {str(e)}"
    except Exception as e:
        logger.error(f"保存记忆失败: {e}")
        return f"保存记忆失败: {str(e)}"


@tool
def retrieve_memories(
    problem_query: str,
    root_cause_query: str = "",
    solution_query: str = "",
    top_k: int = 3,
) -> str:
    """检索相关历史记忆

    在开始修复错误前，使用此工具查找是否有类似的历史经验可以参考。
    只需要提供简单的关键词或一句话描述即可，系统会自动进行语义匹配。

    使用示例：
    - problem_query: "ZeroDivisionError division by zero" 或 "除以零错误"
    - root_cause_query: "missing null check" 或 "没有检查空值" (可选)
    - solution_query: "add conditional check" 或 "添加条件判断" (可选)

    Args:
        problem_query: 必填。描述当前遇到的症状或问题，可以是关键词或一句话。
                      例如: "连接数据库失败"、"502 Bad Gateway"、"内存溢出"
        root_cause_query: 可选。描述可能的原因或怀疑的问题点。
                        例如: "数据库未启动"、"配置错误"、"空指针"
        solution_query: 可选。描述想要寻找的解决方式类型。
                       例如: "重启服务"、"修改配置"、"添加异常处理"
        top_k: 返回最相关的几条记忆，默认3条。建议使用默认值。

    Returns:
        相关记忆列表，按相似度排序，包含问题描述、根本原因、解决方案和元数据
    """
    try:
        response = httpx.get(
            f"{BASE_URL}/memory/retrieve",
            params={
                "problem_query": problem_query,
                "root_cause_query": root_cause_query,
                "solution_query": solution_query,
                "top_k": top_k,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        memories = data.get("memories", [])
        count = data.get("count", 0)

        if count == 0:
            return "未找到相关的历史记忆"

        # 格式化返回结果
        result_parts = [f"找到 {count} 条相关记忆:\n"]

        for i, mem in enumerate(memories, 1):
            sections = mem.get("sections", {})
            score = mem.get("score", 0.0)
            created_at = mem.get("created_at", "")
            metadata = mem.get("metadata", {})

            result_parts.append(f"\n## 记忆 {i} (相似度: {score:.2f})")
            result_parts.append(f"创建时间: {created_at}")
            result_parts.append(f"\n**问题描述:**\n{sections.get('problem', '')}")
            result_parts.append(f"\n**根本原因:**\n{sections.get('root_cause', '')}")
            result_parts.append(f"\n**解决方案:**\n{sections.get('solution', '')}")

            # 添加 metadata（如果有）
            if metadata:
                result_parts.append(f"\n**元数据:**\n{json.dumps(metadata, ensure_ascii=False, indent=2)}")

        return "\n".join(result_parts)

    except httpx.HTTPError as e:
        logger.error(f"检索记忆失败: {e}")
        return f"检索记忆失败: {str(e)}"
    except Exception as e:
        logger.error(f"检索记忆失败: {e}")
        return f"检索记忆失败: {str(e)}"


def get_tools():
    """获取所有记忆工具

    Returns:
        记忆工具列表
    """
    return [save_memory, retrieve_memories]
