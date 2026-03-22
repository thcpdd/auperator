"""配置管理模块

基于 pydantic-settings 的配置管理类，从.env 文件读取配置
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from langfuse import Langfuse
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
        redis_key_prefix: str,
        redis_list_name: str,
    ):
        self.host = redis_host
        self.port = redis_port
        self.password = redis_password
        self.db = redis_db
        self.key_prefix = redis_key_prefix
        self.list_name = redis_list_name

    def add_prefix(self, key: str) -> str:
        """为 Redis key 添加前缀

        Args:
            key: 原始 key

        Returns:
            带前缀的 key
        """
        if self.key_prefix and not key.startswith(self.key_prefix):
            return f"{self.key_prefix}{key}"
        return key

    @property
    def url(self):
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class Consumer:
    def __init__(
        self,
        batch_size: int,
        block_timeout: int,
    ):
        self.batch_size = batch_size
        self.block_timeout = block_timeout


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

    # API 配置
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=7000, alias="API_PORT")
    api_reload: bool = Field(default=False, alias="API_RELOAD")
    api_workers: int = Field(default=1, alias="API_WORKERS")

    # OpenAI 配置
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="", alias="OPENAI_MODEL")

    # Embedding 配置
    embedding_api_base_url: str = Field(default="https://api.openai.com/v1", alias="EMBEDDING_API_BASE_URL")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_vector_size: int = Field(default=1536, alias="EMBEDDING_VECTOR_SIZE")

    # Redis 配置
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_key_prefix: str = Field(default="auperator:", alias="REDIS_KEY_PREFIX")
    redis_list_name: str = Field(default="logs:main", alias="REDIS_LIST_NAME")

    # 消费者配置
    consumer_batch_size: int = Field(default=1, alias="CONSUMER_BATCH_SIZE")
    consumer_block_timeout: int = Field(default=5, alias="CONSUMER_BLOCK_TIMEOUT")

    # 通用配置
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # LangFuse 配置
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")

    # Daytona 配置
    daytona_api_key: str = Field(default="", alias="DAYTONA_API_KEY")
    daytona_api_url: str = Field(default="https://app.daytona.io/api", alias="DAYTONA_API_URL")
    daytona_sandbox_timeout: int = Field(default=3600, alias="DAYTONA_SANDBOX_TIMEOUT")

    # 远程仓库配置
    remote_repo_url: str = Field(default="", alias="REMOTE_REPO_URL")

    # GitHub 配置
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    # Drain3 配置
    drain3_state_file: str = Field(default="drain3.json", alias="DRAIN3_STATE_FILE")
    drain3_depth: int = Field(default=4, alias="DRAIN3_DEPTH")
    drain3_max_clusters: int = Field(default=1000, alias="DRAIN3_MAX_CLUSTERS")
    drain3_max_children: int = Field(default=100, alias="DRAIN3_MAX_CHILDREN")
    drain3_sim_th: float = Field(default=0.4, alias="DRAIN3_SIM_TH")

    # Qdrant 配置
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="auperator_memories", alias="QDRANT_COLLECTION")

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
            self.redis_key_prefix,
            self.redis_list_name,
        )

    @property
    def consumer(self):
        return Consumer(
            self.consumer_batch_size,
            self.consumer_block_timeout,
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
    _settings = Settings()

    if all([
        _settings.langfuse_public_key, 
        _settings.langfuse_secret_key,
        _settings.langfuse_host
    ]):
        # 初始化 Langfuse
        Langfuse(
            public_key=_settings.langfuse_public_key,
            secret_key=_settings.langfuse_secret_key,
            host=_settings.langfuse_host,
        )
    return _settings


settings = get_settings()
