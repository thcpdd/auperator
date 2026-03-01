"""通用日志适配器

用于处理无法被特定格式适配器解析的日志
"""

import re
from datetime import datetime, timezone

from ..models import LogEntry, LogLevel
from .base import BaseLogAdapter


class GenericAdapter(BaseLogAdapter):
    """通用日志适配器

    使用启发式方法解析各种非结构化日志格式

    功能:
        - 自动检测日志级别
        - 提取时间戳 (支持多种格式)
        - 提取堆栈跟踪
    """

    # 常见时间戳格式
    TIMESTAMP_PATTERNS = [
        # ISO 8601
        (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", "%Y-%m-%dT%H:%M:%S"),
        # 常见格式：2024-01-01 12:00:00
        (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)", "%Y-%m-%d %H:%M:%S"),
        # 常见格式：01/Jan/2024:12:00:00
        (r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})", "%d/%b/%Y:%H:%M:%S"),
        # 常见格式：Jan 01 12:00:00
        (r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", None),  # 需要特殊处理
    ]

    # 日志级别匹配
    LEVEL_PATTERNS = [
        (r"\b(FATAL|CRITICAL|CRIT)\b", LogLevel.CRITICAL),
        (r"\b(ERROR|ERR)\b", LogLevel.ERROR),
        (r"\b(WARNING|WARN)\b", LogLevel.WARNING),
        (r"\b(DEBUG|DBG)\b", LogLevel.DEBUG),
        (r"\b(INFO|INF)\b", LogLevel.INFO),
    ]

    # 堆栈跟踪起始标记
    STACK_START_PATTERNS = [
        r"^\s*at\s+",  # Java: at com.example.Class.method(File.java:123)
        r"^\s*File\s+"  # Python: File "xxx.py", line 123
    ]

    def __init__(
        self,
        source: str | None = None,
        source_type: str | None = None,
        service: str | None = None,
        environment: str = "unknown",
        default_level: LogLevel = LogLevel.INFO,
    ):
        """初始化通用适配器

        Args:
            source: 日志来源标识
            source_type: 日志来源类型
            service: 服务名称
            environment: 环境标识
            default_level: 默认日志级别
        """
        self.source = source
        self.source_type = source_type
        self.service = service
        self.environment = environment
        self.default_level = default_level

        # 编译正则
        self._timestamp_regexes = [(re.compile(p), f) for p, f in self.TIMESTAMP_PATTERNS]
        self._level_regexes = [(re.compile(p, re.IGNORECASE), l) for p, l in self.LEVEL_PATTERNS]
        self._stack_regexes = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.STACK_START_PATTERNS]

    def parse(self, raw_line: str) -> LogEntry:
        """解析日志行

        Args:
            raw_line: 原始日志字符串

        Returns:
            标准化的 LogEntry
        """
        line = raw_line.strip()
        if not line:
            return self._create_empty_entry()

        # 提取时间戳
        timestamp = self._extract_timestamp(line)

        # 提取日志级别
        level = self._extract_level(line)

        # 检查是否是堆栈跟踪的一部分
        is_stack = self._is_stack_line(line)

        # 提取消息 (去除时间戳和级别后的内容)
        message = self._extract_message(line)

        return LogEntry(
            message=message,
            level=level,
            timestamp=timestamp,
            source=self.source,
            source_type=self.source_type,
            service=self.service,
            environment=self.environment,
            stack_trace=line if is_stack else None,
            metadata={"raw": raw_line},
        )

    def _create_empty_entry(self) -> LogEntry:
        """创建空日志条目"""
        return LogEntry(
            message="",
            level=self.default_level,
            source=self.source,
            source_type=self.source_type,
            service=self.service,
            environment=self.environment,
        )

    def _extract_timestamp(self, line: str) -> str | None:
        """提取时间戳"""
        for regex, fmt in self._timestamp_regexes:
            match = regex.search(line)
            if match:
                ts_str = match.group(1)
                # 特殊处理没有固定格式的
                if fmt is None:
                    # 对于 "Jan 01 12:00:00" 格式，添加当前年份
                    try:
                        current_year = datetime.now().year
                        ts_with_year = f"{current_year} {ts_str}"
                        dt = datetime.strptime(ts_with_year, "%Y %b %d %H:%M:%S")
                        return dt.replace(tzinfo=timezone.utc).isoformat()
                    except ValueError:
                        return ts_str
                else:
                    # 尝试解析并标准化
                    try:
                        # 处理带毫秒的情况
                        if "." in ts_str and "%f" not in fmt:
                            fmt = fmt.replace(":%S", ":%S.%f")
                        dt = datetime.strptime(ts_str.split("+")[0].split("-")[0] if "T" not in ts_str else ts_str.replace("Z", ""), fmt)
                        return dt.replace(tzinfo=timezone.utc).isoformat()
                    except ValueError:
                        return ts_str
        return None

    def _extract_level(self, line: str) -> LogLevel:
        """提取日志级别"""
        for regex, level in self._level_regexes:
            if regex.search(line):
                return level
        return self.default_level

    def _is_stack_line(self, line: str) -> bool:
        """检查是否是堆栈跟踪行"""
        for regex in self._stack_regexes:
            if regex.match(line):
                return True
        return False

    def _extract_message(self, line: str) -> str:
        """提取消息部分"""
        # 尝试移除时间戳
        for regex, _ in self._timestamp_regexes:
            line = regex.sub("", line).strip()

        # 尝试移除日志级别
        for regex, _ in self._level_regexes:
            line = regex.sub("", line).strip()

        # 清理多余的空格和分隔符
        line = re.sub(r"^\s*[\-\|:]\s*", "", line)
        line = line.strip()

        return line
