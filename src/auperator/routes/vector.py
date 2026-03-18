"""Vector日志接收路由."""

import json
import logging

from fastapi import APIRouter, Depends
from redis.asyncio import Redis as AsyncRedis

from auperator.config import settings
from auperator.dependencies import get_drain3_service, get_redis_client
from auperator.schemas.vector import VectorLogEvent
from auperator.services.drain3_service import Drain3Service

router = APIRouter(prefix="/vector", tags=["vector"])
logger = logging.getLogger(__name__)


@router.post("/ingest")
async def ingest_logs(
    logs: list[dict],
    drain3_service: Drain3Service = Depends(get_drain3_service),
    redis_client: AsyncRedis = Depends(get_redis_client)
):
    """接收Vector发送的日志.

    Args:
        logs: 日志列表，每条日志是一个字典
        drain3_service: Drain3服务（依赖注入）
        redis_client: Redis客户端（依赖注入）

    Vector的HTTP sink会发送批量日志，格式为：
    [
      {"message": "...", "timestamp": "...", "host": "...", ...},
      {"message": "...", "timestamp": "...", "host": "...", ...},
    ]

    处理流程：
    1. 使用Drain3提取日志模板
    2. 判断是否为新模板或模板变化
    3. 只有新模板才推送到Redis List
    4. 重复模板直接丢弃
    """
    processed_count = 0
    new_template_count = 0

    for log_data in logs:
        try:
            # 转换为VectorLogEvent
            log_event = VectorLogEvent.from_dict(log_data)

            # 提取日志模板
            result = drain3_service.extract_template(log_event.message)

            if result is None:
                continue

            processed_count += 1

            # 只有新模板或模板变化时才推送到Redis
            if result["is_new_template"]:
                log_entry = {
                    "message": result["template_mined"],  # 保存日志模板
                    "timestamp": log_event.timestamp,
                    "cluster_id": result["cluster_id"],
                    "host": log_event.host,
                    "source_type": log_event.source_type,
                }

                # 推送到Redis List
                list_key = settings.redis.add_prefix(settings.redis.list_name)
                await redis_client.lpush(list_key, json.dumps(log_entry, ensure_ascii=False))

                new_template_count += 1

                logger.info(
                    f"New template pushed to Redis: cluster_id={result['cluster_id']}, "
                    f"template={result['template_mined'][:50]}, "
                    f"change_type={result['change_type']}"
                )

        except Exception as e:
            logger.error(f"Error processing log: {e}, log: {log_data}")

    return {
        "status": "success",
        "processed": processed_count,
        "new_templates": new_template_count,
        "duplicates": processed_count - new_template_count,
    }
