"""JSON 日志适配器

适用于结构化 JSON 格式的日志，如：
{"level": "INFO", "msg": "Server started", "time": "2024-01-01T00:00:00Z"}
"""

import json
from datetime import datetime, timezone
from typing import Any

from ..models import LogEntry, LogLevel
from .base import BaseLogAdapter


class JsonAdapter(BaseLogAdapter):
    """JSON 日志适配器

    解析标准 JSON 格式的日志

    支持的 JSON 字段:
        - level/LogLevel: 日志级别
        - msg/message/log: 日志消息
        - time/timestamp/@timestamp: 时间戳
        - context/extra/fields: 上下文字段
        - stack_trace/stack/exception: 堆栈跟踪
    """

    # 常见的日志级别字段名
    LEVEL_FIELDS = ["level", "LogLevel", "severity", "log_level"]

    # 常见的消息字段名
    MESSAGE_FIELDS = ["msg", "message", "log", "text", "content"]

    # 常见的时间戳字段名
    TIMESTAMP_FIELDS = ["time", "timestamp", "@timestamp", "datetime", "date", "ts"]

    # 常见的上下文字段名
    CONTEXT_FIELDS = ["context", "extra", "fields", "data", "meta", "metadata"]

    # 常见的堆栈字段名
    STACK_FIELDS = ["stack_trace", "stack", "exception", "traceback", "error_stack"]

    def __init__(
        self,
        source: str | None = None,
        source_type: str | None = None,
        service: str | None = None,
        environment: str = "unknown",
        fallback_level: LogLevel = LogLevel.INFO,
    ):
        """初始化 JSON 适配器

        Args:
            source: 日志来源标识
            source_type: 日志来源类型
            service: 服务名称
            environment: 环境标识
            fallback_level: 解析失败时的默认日志级别
        """
        self.source = source
        self.source_type = source_type
        self.service = service
        self.environment = environment
        self.fallback_level = fallback_level

    def parse(self, raw_line: str) -> LogEntry:
        """解析 JSON 日志行

        Args:
            raw_line: 原始 JSON 字符串

        Returns:
            标准化的 LogEntry
        """
        raw_line = raw_line.strip()
        if not raw_line:
            return self._create_empty_entry()

        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError:
            # JSON 解析失败，使用通用适配器处理
            return self._parse_fallback(raw_line)

        if not isinstance(data, dict):
            return self._parse_fallback(raw_line)

        # 提取各个字段
        level = self._extract_level(data)
        message = self._extract_message(data)
        timestamp = self._extract_timestamp(data)
        stack_trace = self._extract_stack_trace(data)
        context = self._extract_context(data)

        return LogEntry(
            message=message,
            level=level,
            timestamp=timestamp,
            source=self.source,
            source_type=self.source_type,
            service=self.service,
            environment=self.environment,
            stack_trace=stack_trace,
            context=context,
            metadata={"raw": raw_line},
        )

    def _create_empty_entry(self) -> LogEntry:
        """创建空日志条目"""
        return LogEntry(
            message="",
            level=self.fallback_level,
            source=self.source,
            source_type=self.source_type,
            service=self.service,
            environment=self.environment,
        )

    def _extract_level(self, data: dict[str, Any]) -> LogLevel:
        """提取日志级别"""
        for field in self.LEVEL_FIELDS:
            if field in data:
                return LogLevel.from_string(str(data[field]))
        return self.fallback_level

    def _extract_message(self, data: dict[str, Any]) -> str:
        """提取消息"""
        for field in self.MESSAGE_FIELDS:
            if field in data:
                return str(data[field])
        # 如果没有找到消息字段，返回整个 JSON 的字符串表示
        return json.dumps(data)

    def _extract_timestamp(self, data: dict[str, Any]) -> str | None:
        """提取时间戳"""
        for field in self.TIMESTAMP_FIELDS:
            if field in data:
                ts = data[field]
                if ts:
                    return self._normalize_timestamp(str(ts))
        return None

    def _extract_stack_trace(self, data: dict[str, Any]) -> str | None:
        """提取堆栈跟踪"""
        for field in self.STACK_FIELDS:
            if field in data:
                return str(data[field])
        return None

    def _extract_context(self, data: dict[str, Any]) -> dict[str, Any]:
        """提取上下文信息"""
        context = {}

        # 从上下文字段中提取
        for field in self.CONTEXT_FIELDS:
            if field in data and isinstance(data[field], dict):
                context.update(data[field])

        # 排除已处理的字段，剩余的放入 context
        known_fields = set(self.LEVEL_FIELDS + self.MESSAGE_FIELDS +
                          self.TIMESTAMP_FIELDS + self.STACK_FIELDS +
                          self.CONTEXT_FIELDS)
        for key, value in data.items():
            if key not in known_fields:
                context[key] = value

        return context

    def _normalize_timestamp(self, ts: str) -> str:
        """标准化时间戳格式"""
        # 尝试解析常见的时间戳格式
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                continue

        # 如果都失败，返回原始值
        return ts

    def _parse_fallback(self, raw_line: str) -> LogEntry:
        """回退解析 - 当 JSON 解析失败时"""
        # 尝试从行中提取一些信息
        line = raw_line.strip()

        # 检查是否包含常见级别关键词
        level = self.fallback_level
        for lvl in [LogLevel.CRITICAL, LogLevel.ERROR, LogLevel.WARNING, LogLevel.DEBUG]:
            if lvl.value.lower() in line.lower():
                level = lvl
                break

        return LogEntry(
            message=line,
            level=level,
            source=self.source,
            source_type=self.source_type,
            service=self.service,
            environment=self.environment,
            metadata={"raw": raw_line, "parse_error": "invalid_json"},
        )
