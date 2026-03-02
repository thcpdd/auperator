"""配置管理模块

基于 pydantic-settings 的配置管理类，从.env 文件读取配置
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """查找项目根目录（包含 .env 文件的目录）"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".env").exists() or (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"


class Redis:
    def __init__(
        self, 
        redis_host: str, 
        redis_port: int, 
        redis_password: str | None, 
        redis_db: int, 
        redis_stream_name: str, 
        redis_consumer_group: str
    ):
        self.host = redis_host
        self.port = redis_port
        self.password = redis_password
        self.db = redis_db
        self.stream_name = redis_stream_name
        self.consumer_group = redis_consumer_group

    @property
    def url(self):
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class Collector:
    def __init__(
        self, 
        batch_size: int, 
        batch_timeout: float, 
        max_retries: int, 
        retry_delay: float
    ):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class Docker:
    def __init__(
        self,
        docker_socket: str,
        docker_tail: int,
        docker_follow: bool
    ):
        self.socket = docker_socket
        self.tail = docker_tail
        self.follow = docker_follow


class Deduplication:
    def __init__(
        self,
        enabled: bool,
        window: int,
        ttl: int,
    ):
        self.enabled = enabled
        self.window = window
        self.ttl = ttl


class Settings(BaseSettings):
    """Auperator 全局配置

    默认从 .env 文件读取配置，支持环境变量覆盖
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Redis 配置
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_stream_name: str = Field(default="logs:main", alias="REDIS_STREAM_NAME")
    redis_consumer_group: str = Field(default="auperator-group", alias="REDIS_CONSUMER_GROUP")

    # 采集器配置
    collector_batch_size: int = Field(default=100, alias="COLLECTOR_BATCH_SIZE")
    collector_batch_timeout: float = Field(default=5.0, alias="COLLECTOR_BATCH_TIMEOUT")
    collector_max_retries: int = Field(default=3, alias="COLLECTOR_MAX_RETRIES")
    collector_retry_delay: float = Field(default=1.0, alias="COLLECTOR_RETRY_DELAY")

    # Docker 配置
    docker_socket: str = Field(default="/var/run/docker.sock", alias="DOCKER_SOCKET")
    docker_tail: int = Field(default=100, alias="DOCKER_TAIL")
    docker_follow: bool = Field(default=True, alias="DOCKER_FOLLOW")

    # 去重配置
    deduplication_enabled: bool = Field(default=True, alias="DEDUPLICATION_ENABLED")
    deduplication_window: int = Field(default=86400, alias="DEDUPLICATION_WINDOW")  # 24小时
    deduplication_ttl: int = Field(default=604800, alias="DEDUPLICATION_TTL")  # 7天

    # 通用配置
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    agent_service: str = Field(default="auperator", alias="AGENT_SERVICE")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"日志级别必须是 {valid_levels} 之一，got {v}")
        return v

    @property
    def redis(self):
        return Redis(
            self.redis_host, 
            self.redis_port, 
            self.redis_password, 
            self.redis_db, 
            self.redis_stream_name, 
            self.redis_consumer_group
        )

    @property
    def collector(self):
        return Collector(
            self.collector_batch_size, 
            self.collector_batch_timeout, 
            self.collector_max_retries, 
            self.collector_retry_delay
        )

    @property
    def docker(self):
        return Docker(self.docker_socket, self.docker_tail, self.docker_follow)

    @property
    def deduplication(self):
        return Deduplication(
            self.deduplication_enabled,
            self.deduplication_window,
            self.deduplication_ttl,
        )

    def get_redis_url(self) -> str:
        return self.redis.url

    def get_redis_connection_kwargs(self) -> dict[str, Any]:
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "password": self.redis_password,
            "db": self.redis_db,
            "decode_responses": True,
            "encoding": "utf-8",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
