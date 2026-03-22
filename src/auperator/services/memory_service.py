"""记忆服务

基于向量嵌入的动态记忆存储与检索服务
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import PointIdsList, PointStruct

from auperator.config import settings
from auperator.utils.embeddings import get_text_embeddings

# 记忆section定义
MEMORY_SECTIONS = ["problem", "root_cause", "solution"]

# 默认权重配置
DEFAULT_MEMORY_WEIGHTS = {
    "problem": 1.2,
    "root_cause": 1.8,
    "solution": 2.0,
}

logger = logging.getLogger(__name__)


class MemoryService:
    """记忆服务

    负责记忆的向量化、存储和检索
    QdrantClient通过依赖注入传入，保持解耦
    """

    def __init__(self, qdrant_client: AsyncQdrantClient):
        """初始化记忆服务

        Args:
            qdrant_client: Qdrant客户端实例（通过依赖注入）
        """
        self.qdrant_client = qdrant_client

    async def save_memory(
        self,
        sections: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """保存记忆

        Args:
            sections: 记忆sections，格式: {"problem": str, "root_cause": str, "solution": str}
            metadata: 元数据（可选）

        Returns:
            memory_id

        Raises:
            ValueError: sections格式不正确
            Exception: 保存失败
        """
        # 验证sections
        for section in MEMORY_SECTIONS:
            if section not in sections:
                raise ValueError(f"缺少必需的section: {section}")

        # 生成memory_id（使用UUID）
        memory_uuid = uuid.uuid4()
        memory_id = str(memory_uuid)
        created_at = datetime.now().isoformat()

        # 对每个section并发获取embedding
        section_texts = [sections[section] for section in MEMORY_SECTIONS]
        embedding_results = await get_text_embeddings(section_texts)

        embeddings = {}
        for section, embedding in zip(MEMORY_SECTIONS, embedding_results):
            if embedding is None:
                raise Exception(f"获取 {section} 的向量嵌入失败")
            embeddings[section] = embedding

        # 构建point
        point = PointStruct(
            id=memory_uuid,  # Qdrant要求使用UUID或整数
            vector=embeddings,
            payload={
                "memory_id": memory_id,  # 在payload中保存字符串形式的ID
                "sections": sections,
                "metadata": metadata or {},
                "created_at": created_at,
            },
        )

        # 存储到Qdrant
        await self.qdrant_client.upsert(
            collection_name=settings.qdrant_collection,
            points=[point],
        )

        logger.info(f"记忆已保存: {memory_id}")
        return memory_id

    async def retrieve_memories(
        self,
        queries: dict[str, str],
        top_k: int = 3,
        weights: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """检索相关记忆

        Args:
            queries: 各section的查询文本，格式: {"problem": str, "root_cause": str, "solution": str}
            top_k: 返回最相关的k条记忆
            weights: 各section的权重，默认使用DEFAULT_WEIGHTS

        Returns:
            相关记忆列表，按加权相似度排序
        """
        weights = weights or DEFAULT_MEMORY_WEIGHTS

        # 对每个查询并发获取embedding
        query_sections = [s for s in MEMORY_SECTIONS if s in queries and queries[s]]
        if not query_sections:
            logger.warning("没有有效的查询文本")
            return []

        query_texts = [queries[section] for section in query_sections]
        embedding_results = await get_text_embeddings(query_texts)

        query_embeddings = {}
        for section, embedding in zip(query_sections, embedding_results):
            if embedding is None:
                logger.warning(f"获取 {section} 查询的向量嵌入失败，跳过")
                continue
            query_embeddings[section] = embedding

        if not query_embeddings:
            logger.warning("没有有效的查询向量")
            return []

        # 并发查询每个section
        section_results: dict[str, dict[str, float]] = {}  # {memory_id: score}

        search_tasks = [
            self.qdrant_client.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vector,
                using=section,  # 指定使用哪个命名的向量字段
                limit=top_k * 2,  # 多查一些，后面合并去重
            )
            for section, query_vector in query_embeddings.items()
        ]

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for (section, query_vector), results in zip(query_embeddings.items(), search_results):
            if isinstance(results, Exception):
                logger.error(f"查询 {section} 失败: {results}")
                continue

            for result in results.points:
                memory_id = result.id
                score = result.score * weights.get(section, 1.0)

                if memory_id not in section_results:
                    section_results[memory_id] = score
                else:
                    section_results[memory_id] += score

        # 排序并获取top-k
        sorted_ids = sorted(
            section_results.keys(),
            key=lambda mid: section_results[mid],
            reverse=True,
        )[:top_k]

        # 获取完整的记忆数据
        memories = []
        if sorted_ids:
            # 批量获取points
            points = await self.qdrant_client.retrieve(
                collection_name=settings.qdrant_collection,
                ids=sorted_ids,
            )

            for point in points:
                memories.append(
                    {
                        "memory_id": point.payload.get("memory_id", str(point.id)),
                        "sections": point.payload.get("sections", {}),
                        "metadata": point.payload.get("metadata", {}),
                        "created_at": point.payload.get("created_at", ""),
                        "score": section_results.get(point.id, 0.0),
                    }
                )

        return memories

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """获取指定记忆

        Args:
            memory_id: 记忆ID（字符串形式的UUID）

        Returns:
            记忆数据，不存在返回None
        """
        try:
            points = await self.qdrant_client.retrieve(
                collection_name=settings.qdrant_collection,
                ids=[uuid.UUID(memory_id)],
            )

            if not points:
                return None

            point = points[0]
            return {
                "memory_id": memory_id,
                "sections": point.payload.get("sections", {}),
                "metadata": point.payload.get("metadata", {}),
                "created_at": point.payload.get("created_at", ""),
            }

        except Exception as e:
            logger.error(f"获取记忆失败: {e}")
            return None

    async def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆

        Args:
            memory_id: 记忆ID（字符串形式的UUID）

        Returns:
            是否删除成功
        """
        try:
            await self.qdrant_client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=PointIdsList(points=[uuid.UUID(memory_id)]),
            )
            logger.info(f"记忆已删除: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
