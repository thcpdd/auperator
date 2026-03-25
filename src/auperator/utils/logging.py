"""统一日志配置模块

提供统一的日志格式和配置，确保所有模块的日志都能正常输出。
"""

import logging
import sys
from pathlib import Path
from typing import Literal

from auperator.config import settings

# 日志级别映射
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# 日志颜色映射（ANSI 转义码）
LOG_COLORS = {
    "DEBUG": "\033[36m",      # 青色
    "INFO": "\033[32m",       # 绿色
    "WARNING": "\033[33m",    # 黄色
    "ERROR": "\033[31m",      # 红色
    "CRITICAL": "\033[35m",   # 紫色
}
RESET_COLOR = "\033[0m"

# 全局格式字符串
FORMAT_STR = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LoggerNameFilter(logging.Filter):
    """重写 logger 名称的过滤器

    将 uvicorn.error 重写为 uvicorn，因为 uvicorn 用它来输出普通消息。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "uvicorn.error":
            record.name = "uvicorn"
        return True


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        use_colors: bool = True,
    ):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            # 获取日志级别对应的颜色
            levelname = record.levelname
            color = LOG_COLORS.get(levelname, "")
            record.levelname = f"{color}{levelname}{RESET_COLOR}"

        formatted = super().format(record)

        # 恢复原始 levelname（避免影响其他 handler）
        if self.use_colors:
            record.levelname = levelname

        return formatted


def setup_logging(
    level: LogLevel = "INFO",
    log_file: str | Path | None = None,
    use_colors: bool = True,
    include_timestamp: bool = True,
) -> None:
    """配置统一的全局日志

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选，如果指定则同时输出到文件）
        use_colors: 是否在控制台使用彩色输出
        include_timestamp: 是否包含时间戳

    Example:
        >>> from auperator.utils.logging import setup_logging
        >>> setup_logging(level="INFO")
    """
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    # 清除已有的 handlers（避免重复添加）
    root_logger.handlers.clear()

    # 构建日志格式
    if include_timestamp:
        format_str = FORMAT_STR
        date_format = DATE_FORMAT
    else:
        format_str = "%(levelname)-8s - %(name)s - %(message)s"
        date_format = None

    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    # 添加 filter 以重写 uvicorn.error 为 uvicorn
    console_handler.addFilter(LoggerNameFilter())

    # 设置格式化器
    console_formatter = ColoredFormatter(
        fmt=format_str,
        datefmt=date_format,
        use_colors=use_colors,
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 如果指定了日志文件，添加文件 handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(
            log_path,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level))

        # 文件输出不使用颜色
        file_formatter = ColoredFormatter(
            fmt=format_str,
            datefmt=date_format,
            use_colors=False,
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_uvicorn_log_config(
    level: str = "INFO",
    use_colors: bool = True,
) -> dict:
    """获取 uvicorn 的日志配置字典

    用于统一 uvicorn 和应用日志的格式。

    Args:
        level: 日志级别
        use_colors: 是否使用彩色输出

    Returns:
        uvicorn 的 log_config 字典

    Example:
        >>> uvicorn.run(
        ...     "auperator.server:app",
        ...     log_config=get_uvicorn_log_config(),
        ... )
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "auperator.utils.logging.ColoredFormatter",
                "fmt": FORMAT_STR,
                "datefmt": DATE_FORMAT,
                "use_colors": use_colors,
            },
            "access": {
                "()": "auperator.utils.logging.ColoredFormatter",
                "fmt": FORMAT_STR,
                "datefmt": DATE_FORMAT,
                "use_colors": use_colors,
            },
        },
        "filters": {
            "rename_uvicorn_error": {
                "()": "auperator.utils.logging.LoggerNameFilter",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["rename_uvicorn_error"],
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["rename_uvicorn_error"],
            },
        },
        "loggers": {
            # uvicorn 主日志
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            # uvicorn.error 用于启动和运行时消息（尽管名字叫 error）
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            # HTTP 访问日志
            "uvicorn.access": {
                "handlers": ["access"],
                "level": level,
                "propagate": False,
            },
        },
    }
