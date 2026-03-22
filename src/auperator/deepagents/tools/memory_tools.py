"""记忆工具

Agent使用的记忆存储和检索工具
"""

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
    metadata: dict[str, Any] | None = None,
) -> str:
    """保存记忆到知识库

    当你完成了任务修复，并且从中学到了有价值的经验时，使用此工具保存。

    Args:
        problem: 具体遇到了什么错误，错误表现是什么
        root_cause: 错误的根本原因是什么，如何定位的
        solution: 采取了什么修复措施，具体的代码变更内容是什么
        metadata: 其他元数据（可选）

    Returns:
        memory_id: 记忆ID
    """
    try:
        response = httpx.post(
            f"{BASE_URL}/memory/save",
            json={
                "problem": problem,
                "root_cause": root_cause,
                "solution": solution,
                "metadata": metadata,
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
    root_cause_query: str,
    solution_query: str,
    top_k: int = 3,
) -> str:
    """检索相关历史记忆

    在开始处理新的错误前，可以先检索是否有类似的历史经验可以参考。

    Args:
        problem_query: 针对问题描述的查询文本，描述当前遇到的症状
        root_cause_query: 针对根本原因的查询文本，描述可能的问题原因
        solution_query: 针对解决方案的查询文本，描述想要找什么样的解决方法
        top_k: 返回最相关的几条记忆，默认3条

    Returns:
        相关记忆列表，包含问题描述、根本原因、解决方案
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

            result_parts.append(f"\n## 记忆 {i} (相似度: {score:.2f})")
            result_parts.append(f"创建时间: {created_at}")
            result_parts.append(f"\n**问题描述:**\n{sections.get('problem', '')}")
            result_parts.append(f"\n**根本原因:**\n{sections.get('root_cause', '')}")
            result_parts.append(f"\n**解决方案:**\n{sections.get('solution', '')}")

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
