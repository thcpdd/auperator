"""记忆相关的API路由"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from auperator.dependencies import get_memory_service
from auperator.schemas.memory import (
    MemoryResponse,
    RetrieveMemoryRequest,
    RetrieveMemoryResponse,
    SaveMemoryRequest,
    SaveMemoryResponse,
)
from auperator.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/save", response_model=SaveMemoryResponse)
async def save_memory(
    request: SaveMemoryRequest,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """保存记忆

    将Agent的反思总结保存到向量数据库
    """
    try:
        sections = {
            "problem": request.problem,
            "root_cause": request.root_cause,
            "solution": request.solution,
        }

        memory_id = await memory_service.save_memory(
            sections=sections,
            metadata=request.metadata,
        )

        return SaveMemoryResponse(memory_id=memory_id)

    except ValueError as e:
        logger.error(f"保存记忆失败（参数错误）: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"保存记忆失败: {e}")
        raise HTTPException(status_code=500, detail="保存记忆失败")


@router.get("/retrieve", response_model=RetrieveMemoryResponse)
async def retrieve_memories(
    problem_query: str = Query(..., description="问题描述查询"),
    root_cause_query: str = Query(..., description="根本原因查询"),
    solution_query: str = Query(..., description="解决方案查询"),
    top_k: int = Query(default=3, ge=1, le=10, description="返回数量"),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """检索相关记忆

    根据查询文本检索相关的历史记忆
    """
    try:
        queries = {
            "problem": problem_query,
            "root_cause": root_cause_query,
            "solution": solution_query,
        }

        memories = await memory_service.retrieve_memories(
            queries=queries,
            top_k=top_k,
        )

        return RetrieveMemoryResponse(
            memories=[
                MemoryResponse(
                    memory_id=m["memory_id"],
                    sections=m["sections"],
                    metadata=m["metadata"],
                    created_at=m["created_at"],
                    score=m["score"],
                )
                for m in memories
            ],
            count=len(memories),
        )

    except Exception as e:
        logger.error(f"检索记忆失败: {e}")
        raise HTTPException(status_code=500, detail="检索记忆失败")
