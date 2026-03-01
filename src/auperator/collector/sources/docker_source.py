"""Docker 容器日志源"""

import asyncio
from typing import AsyncIterator

import docker
from docker import DockerClient
from docker.models.containers import Container

from .base import BaseLogSource


class DockerSource(BaseLogSource):
    """Docker 容器日志源

    从指定的 Docker 容器读取日志，支持流式读取和 follow 模式

    Attributes:
        container_name: 容器名称或 ID
        follow: 是否持续跟踪新日志 (类似 docker logs -f)
        tail: 初始读取的行数 (0 表示全部)
        since: 从此时间之后的日志 (datetime 或字符串)
        until: 到此时间之前的日志 (datetime 或字符串)
        timestamps: 是否包含时间戳
    """

    def __init__(
        self,
        container_name: str,
        follow: bool = True,
        tail: int = 0,
        since: str | None = None,
        until: str | None = None,
        timestamps: bool = False,
        service: str | None = None,
        environment: str = "unknown",
    ):
        """初始化 Docker 日志源

        Args:
            container_name: 容器名称或 ID
            follow: 是否持续跟踪新日志
            tail: 初始读取的行数，0 表示全部
            since: 从此时间之后的日志
            until: 到此时间之前的日志
            timestamps: 是否在日志中包含时间戳
            service: 服务名称 (可选，用于标识)
            environment: 环境标识
        """
        self.container_name = container_name
        self.follow = follow
        self.tail = tail
        self.since = since
        self.until = until
        self.timestamps = timestamps
        self._service = service
        self._environment = environment

        # Docker 客户端和容器引用
        self._client: DockerClient | None = None
        self._container: Container | None = None
        self._running = False
        self._log_stream = None

    @property
    def name(self) -> str:
        """日志源名称"""
        return f"docker://{self.container_name}"

    @property
    def service(self) -> str:
        """服务名称"""
        return self._service or self.container_name

    @property
    def environment(self) -> str:
        """环境标识"""
        return self._environment

    async def start(self) -> None:
        """启动 Docker 日志源

        连接 Docker 并获取容器引用
        """
        try:
            self._client = docker.from_env()
            # 尝试通过名称或 ID 获取容器
            self._container = self._client.containers.get(self.container_name)
            self._running = True
        except docker.errors.NotFound:
            raise RuntimeError(f"容器未找到：{self.container_name}")
        except docker.errors.DockerException as e:
            raise RuntimeError(f"无法连接 Docker: {e}")

    async def stop(self) -> None:
        """停止 Docker 日志源"""
        self._running = False
        if self._log_stream:
            try:
                self._log_stream.close()
            except Exception:
                pass
        self._container = None
        self._client = None

    async def read(self) -> AsyncIterator[str]:
        """持续读取 Docker 容器日志

        Yields:
            原始日志行 (已解码的字符串)
        """
        if not self._container:
            await self.start()

        while self._running:
            try:
                # 获取日志流
                self._log_stream = self._container.logs(
                    stream=self.follow,
                    follow=self.follow,
                    tail=self.tail if self.tail > 0 else "all",
                    since=self.since,
                    until=self.until,
                    timestamps=self.timestamps,
                )

                # 如果是流式模式，持续读取
                if self.follow:
                    for log_line in self._log_stream:
                        if not self._running:
                            break
                        # 解码字节为字符串
                        yield log_line.decode("utf-8", errors="replace")
                else:
                    # 非流式模式，读取完成后返回
                    for log_line in self._log_stream:
                        yield log_line.decode("utf-8", errors="replace")
                    break

            except docker.errors.NotFound:
                # 容器可能被删除
                raise RuntimeError(f"容器 {self.container_name} 未找到")
            except Exception as e:
                if self._running:
                    # 等待后重试
                    await asyncio.sleep(5)
                else:
                    break

    async def collect_all(self) -> list[str]:
        """一次性收集所有当前日志

        Returns:
            所有日志行的列表
        """
        lines = []
        # 临时设置为非 follow 模式
        original_follow = self.follow
        self.follow = False

        try:
            async for line in self.read():
                lines.append(line)
        finally:
            self.follow = original_follow

        return lines
