"""Docker日志相关的Pydantic模型."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DockerLogEntry(BaseModel):
    """Docker日志条目模型.

    用于SSE推送的Docker容器日志条目
    """

    container_name: str = Field(description="容器名称")
    container_id: str = Field(description="容器ID（短格式，前12位）")
    timestamp: datetime = Field(description="日志时间戳")
    log_line: str = Field(description="日志内容")
    stream: Literal["stdout", "stderr"] = Field(description="输出流类型")

    model_config = {"extra": "allow"}
