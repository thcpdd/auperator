"""文本嵌入工具

提供文本向量嵌入的公用函数
"""

import asyncio
import logging

import httpx

from auperator.config import settings

logger = logging.getLogger(__name__)


async def get_text_embedding(text: str) -> list[float] | None:
    """获取文本的向量嵌入

    Args:
        text: 输入文本

    Returns:
        向量嵌入列表，失败返回None
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.embedding_api_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": text
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"获取向量嵌入失败: {e}")
        return None


async def get_text_embeddings(texts: list[str]) -> list[list[float] | None]:
    """批量获取文本的向量嵌入

    Args:
        texts: 输入文本列表

    Returns:
        向量嵌入列表，每个元素对应输入文本的嵌入（失败则为None）
    """
    tasks = [get_text_embedding(text) for text in texts]
    return await asyncio.gather(*tasks)
