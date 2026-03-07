"""Vector 日志适配器

将 Vector 输出的 JSON 格式转换为 LogEntry
"""

import json
import re
from typing import Any

from auperator.collector.models import LogEntry, LogLevel, LogSource
from .base import BaseLogAdapter


class VectorAdapter(BaseLogAdapter):
    """Vector 日志适配器

    解析 Vector 输出的结构化 JSON 日志

    Vector 输出示例：
    {
        "container_created_at": "2026-03-02T12:50:21.602172058Z",
        "container_id": "6a0964310ac34e3d73749237210b664791042e0632f9c3177cd47f7154f2a175",
        "container_name": "bug-web-backend-1",
        "host": "6f29d7e9cc5b",
        "image": "bug-web-backend",
        "message": "INFO: 172.18.0.1:43532 - \"GET /api/stats HTTP/1.1\" 500 Internal Server Error",
        "source_type": "docker_logs",
        "stream": "stdout",
        "timestamp": "2026-03-07T02:29:19.941390846Z"
    }
    """

    def __init__(self):
        """初始化 Vector 适配器"""
        # 从消息中提取日志级别的正则
        self._log_level_pattern = re.compile(
            r'\[?(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\]?\s*:',
            re.IGNORECASE
        )

    def parse(self, raw_line: str) -> LogEntry:
        """解析 Vector JSON 为 LogEntry

        Args:
            raw_line: Vector 输出的 JSON 字符串

        Returns:
            LogEntry 对象
        """
        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError:
            # 如果不是 JSON，当作普通消息处理
            return LogEntry(
                message=raw_line,
                level=LogLevel.INFO,
                source_type=LogSource.CUSTOM,
                metadata={"raw": raw_line}
            )

        # 提取基本信息
        message = data.get("message", "")
        timestamp = data.get("timestamp") or data.get("container_created_at")

        # 从消息中提取日志级别
        level = self._extract_level(message)

        # 提取容器信息
        container_name = data.get("container_name")
        container_id = data.get("container_id")
        image = data.get("image")

        # 构建 source 标识
        source = container_name or image or container_id or "unknown"

        # 构建元数据
        metadata = {
            "container_id": container_id,
            "container_name": container_name,
            "image": image,
            "host": data.get("host"),
            "stream": data.get("stream"),
            "source_type": data.get("source_type"),
        }

        # 添加 labels 到元数据
        labels = data.get("label", {})
        if labels:
            metadata["labels"] = labels
            # 尝试从 labels 中提取服务名
            service = labels.get("com.docker.compose.service")
            if service:
                metadata["service"] = service

        # 检测是否包含堆栈跟踪
        stack_trace = self._extract_stack_trace(message)
        if stack_trace:
            metadata["stack_trace"] = stack_trace

        return LogEntry(
            message=message,
            level=level,
            timestamp=timestamp,
            source=source,
            source_type=LogSource.DOCKER,
            service=metadata.get("service"),
            metadata=metadata,
        )

    def _extract_level(self, message: str) -> LogLevel:
        """从消息中提取日志级别

        Args:
            message: 日志消息

        Returns:
            日志级别
        """
        match = self._log_level_pattern.search(message)
        if match:
            level_str = match.group(1).upper()
            return LogLevel.from_string(level_str)

        # 如果没有明确的级别，尝试根据内容推断
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in ["error", "exception", "traceback", "failed", "failure"]):
            return LogLevel.ERROR
        elif any(keyword in message_lower for keyword in ["warn", "warning"]):
            return LogLevel.WARNING
        elif any(keyword in message_lower for keyword in ["critical", "fatal", "panic"]):
            return LogLevel.CRITICAL

        return LogLevel.INFO

    def _extract_stack_trace(self, message: str) -> str | None:
        """从消息中提取堆栈跟踪

        Args:
            message: 日志消息

        Returns:
            堆栈跟踪内容，如果不存在返回 None
        """
        # Python 异常
        if "Traceback" in message:
            # 提取整个 Traceback 部分
            lines = message.split("\n")
            traceback_lines = []
            in_traceback = False

            for line in lines:
                if "Traceback" in line:
                    in_traceback = True
                if in_traceback:
                    traceback_lines.append(line)

            return "\n".join(traceback_lines) if traceback_lines else None

        # Java 堆栈跟踪
        if "Exception" in message or "Error" in message:
            lines = message.split("\n")
            # 查找 "at " 开头的行
            stack_lines = []
            for i, line in enumerate(lines):
                if line.strip().startswith("at "):
                    # 收集所有相关的堆栈行
                    for j in range(i, len(lines)):
                        if lines[j].strip().startswith("at ") or lines[j].strip().startswith("Caused by:"):
                            stack_lines.append(lines[j])
                        else:
                            break
                    if stack_lines:
                        return "\n".join(stack_lines)

        return None
