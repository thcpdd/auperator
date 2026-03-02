"""Docker 容器日志源"""

import asyncio
import hashlib
from typing import AsyncIterator

import docker
from docker import DockerClient
from docker.models.containers import Container

from auperator.collector.position_manager import PositionManager
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
        position_manager: PositionManager | None = None,
        deduplication_enabled: bool = True,
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
            position_manager: 位置管理器（用于断点续传）
            deduplication_enabled: 是否启用去重
        """
        self.container_name = container_name
        self.follow = follow
        self.tail = tail
        self.since = since
        self.until = until
        # 强制启用时间戳以支持断点续传
        self.timestamps = True if position_manager else timestamps
        self._service = service
        self._environment = environment
        self._position_manager = position_manager
        self._deduplication_enabled = deduplication_enabled

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

        # 获取上次采集位置
        since_ts = None
        if self._position_manager and self._deduplication_enabled:
            try:
                position = await self._position_manager.get_last_position(
                    self.container_name
                )
                if position and position.last_timestamp > 0:
                    since_ts = position.last_timestamp
            except Exception as e:
                # 获取位置失败，继续使用默认行为
                print(f"警告：获取容器 {self.container_name} 位置失败：{e}")

        while self._running:
            try:
                # 获取日志流
                self._log_stream = self._container.logs(
                    stream=self.follow,
                    follow=self.follow,
                    tail=self.tail if self.tail > 0 else "all",
                    since=since_ts or self.since,  # 优先使用位置记录的时间戳
                    until=self.until,
                    timestamps=self.timestamps,
                )

                # 如果是流式模式，持续读取
                if self.follow:
                    for log_line in self._log_stream:
                        if not self._running:
                            break

                        # 解码字节为字符串
                        line = log_line.decode("utf-8", errors="replace")

                        # 如果启用了去重，进行去重处理
                        if self._position_manager and self._deduplication_enabled:
                            docker_ts, content = self._parse_docker_log(line)
                            if not content:
                                # 解析失败，直接返回原始行
                                yield line
                                continue

                            # 计算哈希并检查是否重复
                            log_hash = self._position_manager.calculate_hash(
                                content, docker_ts
                            )

                            try:
                                is_duplicate = await self._position_manager.is_duplicate(
                                    self.container_name, log_hash
                                )
                                if is_duplicate:
                                    # 跳过重复日志
                                    continue

                                # 标记为已处理
                                await self._position_manager.mark_processed(
                                    self.container_name, log_hash, docker_ts
                                )
                            except Exception as e:
                                # 去重失败，记录警告但继续处理
                                print(f"警告：去重检查失败：{e}")

                            yield content
                        else:
                            yield line
                else:
                    # 非流式模式，读取完成后返回
                    for log_line in self._log_stream:
                        line = log_line.decode("utf-8", errors="replace")
                        if self._position_manager and self._deduplication_enabled:
                            docker_ts, content = self._parse_docker_log(line)
                            if content:
                                log_hash = self._position_manager.calculate_hash(
                                    content, docker_ts
                                )
                                try:
                                    is_duplicate = (
                                        await self._position_manager.is_duplicate(
                                            self.container_name, log_hash
                                        )
                                    )
                                    if not is_duplicate:
                                        await self._position_manager.mark_processed(
                                            self.container_name, log_hash, docker_ts
                                        )
                                        yield content
                                except Exception:
                                    yield line
                            else:
                                yield line
                        else:
                            yield line
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

    def _parse_docker_log(self, line: str) -> tuple[str, str]:
        """解析 Docker 日志，返回 (时间戳, 内容)

        Args:
            line: Docker 日志行（包含时间戳）

        Returns:
            (时间戳, 内容) 元组
        """
        # Docker timestamps=True 时格式: "2024-03-02T10:30:00.123456789Z log content"
        if " " in line:
            parts = line.split(" ", 1)
            if len(parts) == 2:
                return parts[0], parts[1]
        return "", line

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
