"""Vector日志相关的Pydantic模型.

Vector是schema-neutral的，不要求特定字段。
不同source会提供不同的字段，我们采用灵活的方式来接收。
"""

from typing import Any

from pydantic import BaseModel, Field


class VectorLogEvent(BaseModel):
    """Vector日志事件模型.

    基于Vector的schema-neutral特性，接收任意字段的日志。
    参考: https://vector.dev/docs/architecture/data-model/log/
    """

    message: str = Field(description="日志消息内容")
    timestamp: str = Field(default="", description="时间戳（ISO 8601格式）")
    host: str = Field(default="", description="主机名")
    source_type: str = Field(default="", description="源类型（如docker、file、kubernetes等）")

    # 允许任意额外字段
    extra: dict[str, Any] = Field(default_factory=dict, description="其他自定义字段")

    model_config = {"extra": "allow"}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        data = {
            "message": self.message,
            "timestamp": self.timestamp,
            "host": self.host,
            "source_type": self.source_type,
        }
        # 添加extra字段
        data.update(self.extra)
        # 添加模型中定义的其他字段
        for key, value in self.model_dump(exclude={"message", "timestamp", "host", "source_type", "extra"}).items():
            if value is not None:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorLogEvent":
        """从字典创建实例."""
        # 提取基本字段
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")
        host = data.get("host", "")
        source_type = data.get("source_type", "")

        # 提取extra字段（排除基本字段）
        extra = {
            k: v for k, v in data.items()
            if k not in {"message", "timestamp", "host", "source_type"}
        }

        return cls(
            message=message,
            timestamp=timestamp,
            host=host,
            source_type=source_type,
            extra=extra,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """获取字段值，支持从extra中获取."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)

    def get_container_info(self) -> dict[str, str]:
        """获取容器相关信息（如果存在）."""
        return {
            "container_id": self.get("container_id", ""),
            "container_name": self.get("container_name", ""),
            "image": self.get("image", ""),
        }
