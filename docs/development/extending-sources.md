# 扩展日志源

本文档介绍如何自定义日志源。

## 基础类

所有日志源都需要继承 `BaseLogSource`：

```python
from auperator.collector.sources.base import BaseLogSource
from typing import AsyncIterator

class BaseLogSource(ABC):
    @abstractmethod
    async def read(self) -> AsyncIterator[str]:
        """读取原始日志行"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动日志源"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止日志源"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """日志源名称"""
        pass
```

## 实现示例

### 文件日志源

```python
import asyncio
from pathlib import Path
from typing import AsyncIterator

from .base import BaseLogSource


class FileSource(BaseLogSource):
    """文件日志源"""

    def __init__(
        self,
        path: str,
        follow: bool = True,
        service: str | None = None,
        environment: str = "unknown",
    ):
        self.path = Path(path)
        self.follow = follow
        self._service = service
        self._environment = environment
        self._running = False
        self._file = None

    @property
    def name(self) -> str:
        return f"file://{self.path}"

    async def start(self) -> None:
        """打开文件"""
        if not self.path.exists():
            raise FileNotFoundError(f"文件不存在：{self.path}")
        self._file = open(self.path, "r")
        self._running = True

    async def stop(self) -> None:
        """关闭文件"""
        self._running = False
        if self._file:
            self._file.close()

    async def read(self) -> AsyncIterator[str]:
        """读取文件内容"""
        if not self._file:
            await self.start()

        while self._running:
            line = self._file.readline()
            if line:
                yield line
            elif self.follow:
                await asyncio.sleep(1)
            else:
                break
```

### Kubernetes 日志源

```python
import asyncio
from kubernetes import client, config
from typing import AsyncIterator

from .base import BaseLogSource


class K8sSource(BaseLogSource):
    """Kubernetes Pod 日志源"""

    def __init__(
        self,
        namespace: str = "default",
        labels: dict | None = None,
        follow: bool = True,
        service: str | None = None,
        environment: str = "unknown",
    ):
        self.namespace = namespace
        self.labels = labels or {}
        self.follow = follow
        self._service = service
        self._environment = environment
        self._running = False
        self._v1 = None

    @property
    def name(self) -> str:
        label_str = ",".join(f"{k}={v}" for k, v in self.labels.items())
        return f"k8s://{self.namespace}/{label_str}"

    async def start(self) -> None:
        """连接 K8s"""
        config.load_kube_config()
        self._v1 = client.CoreV1Api()
        self._running = True

    async def stop(self) -> None:
        """断开连接"""
        self._running = False

    async def read(self) -> AsyncIterator[str]:
        """读取 Pod 日志"""
        pods = self._list_pods()

        for pod in pods:
            async for line in self._read_pod_logs(pod):
                yield line

    def _list_pods(self):
        """列出匹配的 Pod"""
        label_selector = ",".join(f"{k}={v}" for k, v in self.labels.items())
        return self._v1.list_namespaced_pod(
            self.namespace,
            label_selector=label_selector,
        ).items

    async def _read_pod_logs(self, pod):
        """读取单个 Pod 的日志"""
        while self._running:
            try:
                resp = self._v1.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=self.namespace,
                    follow=self.follow,
                    _preload_content=False,
                )
                for line in resp.stream():
                    if not self._running:
                        break
                    yield line.decode()
            except Exception as e:
                if self._running:
                    await asyncio.sleep(5)
                else:
                    break
```

## 注册日志源

在 `sources/__init__.py` 中导出：

```python
from .base import BaseLogSource
from .docker_source import DockerSource
from .file_source import FileSource
from .k8s_source import K8sSource

__all__ = [
    "BaseLogSource",
    "DockerSource",
    "FileSource",
    "K8sSource",
]
```

## 使用自定义日志源

```python
from auperator.collector import LogCollector, FileSource, JsonAdapter

source = FileSource("/var/log/app.log", follow=True)
adapter = JsonAdapter(service="my-app")

collector = LogCollector(source, adapter)
await collector.collect(handler)
```

## 注意事项

1. **异步 IO**: 使用异步方法避免阻塞
2. **资源管理**: 确保 `stop()` 正确释放资源
3. **错误处理**: 处理连接失败、文件不存在等情况
4. **重连机制**: 实现自动重连提高可靠性

## 文档导航

- [采集器概述](collector/overview.md)
- [架构设计](collector/architecture.md)
- [扩展适配器](extending-adapters.md)
