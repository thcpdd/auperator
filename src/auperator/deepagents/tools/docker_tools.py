"""Docker tools for Auperator Agent.

These tools allow the agent to inspect and manage Docker containers
for error diagnosis and remediation.
"""

import logging
import os
from typing import Optional

import docker
from langchain.tools import tool, BaseTool

from auperator.config import settings


logger = logging.getLogger(__name__)

# Global Docker client instance
_docker_client = None


def get_docker_client():
    """Get or create a Docker client instance.

    Returns:
        docker.DockerClient: Docker client instance
    """
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise RuntimeError(
                "Cannot connect to Docker daemon. "
                "Ensure Docker is running and accessible."
            ) from e
    return _docker_client


@tool
def get_container_info(container_name: str) -> dict:
    """Get detailed information about a Docker container.

    Args:
        container_name: Name or ID of the container

    Returns:
        Dictionary containing:
            - name: Container name
            - status: Container status (running, exited, etc.)
            - image: Image name and tag
            - state: Detailed state information
            - created: Creation timestamp
            - restart_count: Number of times the container has restarted
            - ports: Port mappings
            - mounts: Volume mounts
            - env: Environment variables (names only, values masked)
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)

        info = container.attrs

        # Extract relevant information
        result = {
            "name": container.name,
            "id": container.id[:12],
            "status": container.status,
            "image": info["Config"]["Image"],
            "state": {
                "status": info["State"]["Status"],
                "running": info["State"]["Running"],
                "paused": info["State"]["Paused"],
                "restarting": info["State"]["Restarting"],
                "oom_killed": info["State"]["OOMKilled"],
                "pid": info["State"]["Pid"],
                "exit_code": info["State"].get("ExitCode", 0),
            },
            "created": info["Created"],
            "restart_count": info["RestartCount"],
        }

        # Add port mappings if available
        if "NetworkSettings" in info and info["NetworkSettings"]["Ports"]:
            result["ports"] = {
                port: mappings[0]["HostPort"] if mappings else None
                for port, mappings in info["NetworkSettings"]["Ports"].items()
            }

        # Add mounts if available
        if "Mounts" in info:
            result["mounts"] = [
                {
                    "source": m.get("Source"),
                    "destination": m.get("Destination"),
                    "type": m.get("Type"),
                    "rw": m.get("RW", True),
                }
                for m in info["Mounts"]
            ]

        # Add environment variable names (mask values for security)
        if "Config" in info and info["Config"].get("Env"):
            result["env_count"] = len(info["Config"]["Env"])
            result["env_names"] = [env.split("=")[0] for env in info["Config"]["Env"][:10]]

        # Add resource limits if available
        if "HostConfig" in info:
            host_config = info["HostConfig"]
            result["resources"] = {}
            if host_config.get("Memory"):
                result["resources"]["memory_limit"] = f"{host_config['Memory'] / 1024 / 1024:.0f}MB"
            if host_config.get("NanoCpus"):
                result["resources"]["cpu_quota"] = f"{host_config['NanoCpus'] / 1e9:.2f} cores"

        return result

    except docker.errors.NotFound:
        return {
            "error": f"Container '{container_name}' not found",
            "suggestion": "Use list_containers to see all available containers"
        }
    except docker.errors.DockerException as e:
        return {
            "error": f"Docker error: {str(e)}",
            "container": container_name
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting container info: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "container": container_name
        }


@tool
def get_container_logs(
    container_name: str,
    tail: int = 100,
    since: Optional[str] = None
) -> dict:
    """Get logs from a Docker container.

    Args:
        container_name: Name or ID of the container
        tail: Number of lines to fetch from the end of logs (default: 100)
        since: Timestamp to fetch logs since (ISO 8601 format or Go duration, e.g., "1h")

    Returns:
        Dictionary containing:
            - container: Container name
            - logs: Log content
            - lines: Number of lines returned
            - tail: Lines requested
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)

        # Fetch logs
        logs = container.logs(tail=tail, since=since, timestamps=True).decode("utf-8")

        lines = logs.split("\n")
        # Remove empty last line if present
        if lines and lines[-1] == "":
            lines.pop()

        return {
            "container": container_name,
            "logs": "\n".join(lines[-tail:]),
            "lines": len(lines),
            "tail_requested": tail,
        }

    except docker.errors.NotFound:
        return {
            "error": f"Container '{container_name}' not found",
            "container": container_name
        }
    except docker.errors.DockerException as e:
        return {
            "error": f"Docker error: {str(e)}",
            "container": container_name
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting container logs: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "container": container_name
        }


@tool
def restart_container(container_name: str) -> dict:
    """Restart a Docker container.

    Warning: This will briefly interrupt the service running in the container.

    Args:
        container_name: Name or ID of the container to restart

    Returns:
        Dictionary containing:
            - container: Container name
            - success: Whether restart was successful
            - message: Status message
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)

        # Get status before restart
        status_before = container.status

        # Restart the container (timeout 10 seconds)
        container.restart(timeout=10)

        # Refresh to get new status
        container.reload()
        status_after = container.status

        return {
            "container": container_name,
            "success": True,
            "status_before": status_before,
            "status_after": status_after,
            "message": f"Container '{container_name}' restarted successfully"
        }

    except docker.errors.NotFound:
        return {
            "container": container_name,
            "success": False,
            "error": f"Container '{container_name}' not found"
        }
    except docker.errors.DockerException as e:
        return {
            "container": container_name,
            "success": False,
            "error": f"Docker error: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error restarting container: {e}")
        return {
            "container": container_name,
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def get_container_stats(container_name: str) -> dict:
    """Get live resource usage statistics for a Docker container.

    Args:
        container_name: Name or ID of the container

    Returns:
        Dictionary containing:
            - container: Container name
            - cpu_percent: CPU usage percentage
            - memory_usage: Memory usage in bytes
            - memory_limit: Memory limit in bytes
            - memory_percent: Memory usage percentage
            - network_rx: Bytes received
            - network_tx: Bytes transmitted
            - block_read: Bytes read from disk
            - block_write: Bytes written to disk
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)

        # Get stats (stream=False for single snapshot)
        stats = container.stats(stream=False)

        # Calculate CPU percentage
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                      stats["precpu_stats"]["system_cpu_usage"]
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            # Use online_cpus if available, otherwise try percpu_usage, default to 1
            num_cpus = stats["cpu_stats"].get("online_cpus")
            if num_cpus is None:
                percpu_usage = stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [])
                num_cpus = len(percpu_usage) if percpu_usage else 1
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Memory stats
        memory_stats = stats["memory_stats"]
        memory_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 0)
        memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0

        # Network stats
        network_stats = stats.get("networks", {})
        network_rx = sum(n.get("rx_bytes", 0) for n in network_stats.values())
        network_tx = sum(n.get("tx_bytes", 0) for n in network_stats.values())

        # Block I/O stats
        blkio_stats = stats.get("blkio_stats", {}).get("io_service_bytes_recursive", [])
        block_read = sum(b.get("value", 0) for b in blkio_stats if b.get("op") == "Read")
        block_write = sum(b.get("value", 0) for b in blkio_stats if b.get("op") == "Write")

        return {
            "container": container_name,
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage": memory_usage,
            "memory_limit": memory_limit,
            "memory_percent": round(memory_percent, 2),
            "memory_mb": round(memory_usage / 1024 / 1024, 2),
            "memory_limit_mb": round(memory_limit / 1024 / 1024, 2),
            "network_rx_mb": round(network_rx / 1024 / 1024, 2),
            "network_tx_mb": round(network_tx / 1024 / 1024, 2),
            "block_read_mb": round(block_read / 1024 / 1024, 2),
            "block_write_mb": round(block_write / 1024 / 1024, 2),
        }

    except docker.errors.NotFound:
        return {
            "error": f"Container '{container_name}' not found",
            "container": container_name
        }
    except docker.errors.DockerException as e:
        return {
            "error": f"Docker error: {str(e)}",
            "container": container_name
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting container stats: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "container": container_name
        }


@tool
def list_containers(all: bool = True) -> dict:
    """List all Docker containers.

    Args:
        all: If True, include stopped containers. If False, only running containers.

    Returns:
        Dictionary containing:
            - count: Number of containers
            - containers: List of container information
                - name: Container name
                - status: Container status
                - image: Image name
                - id: Short container ID
    """
    try:
        client = get_docker_client()
        containers = client.containers.list(all=all)

        result = {
            "count": len(containers),
            "containers": [
                {
                    "name": c.name,
                    "id": c.id[:12],
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                }
                for c in containers
            ]
        }

        return result

    except docker.errors.DockerException as e:
        return {
            "error": f"Docker error: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error listing containers: {e}")
        return {
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def get_container_processes(container_name: str) -> dict:
    """Get running processes inside a Docker container.

    Args:
        container_name: Name or ID of the container

    Returns:
        Dictionary containing:
            - container: Container name
            - processes: List of processes with PID, user, command, etc.
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)

        # top() returns process information
        # Default args are 'aux' for detailed process list
        processes = container.top(ps_args="aux")

        if not processes or "Processes" not in processes:
            return {
                "container": container_name,
                "processes": [],
                "message": "No processes found or container is not running"
            }

        # Parse process list
        # First element is headers (Titles), rest are process rows
        titles = processes["Titles"]
        process_rows = processes["Processes"]

        result_processes = []
        for row in process_rows:
            process = dict(zip(titles, row))
            result_processes.append({
                "user": process.get("USER", ""),
                "pid": process.get("PID", ""),
                "cpu": process.get("%CPU", ""),
                "mem": process.get("%MEM", ""),
                "vsz": process.get("VSZ", ""),
                "rss": process.get("RSS", ""),
                "command": process.get("COMMAND", "")
            })

        return {
            "container": container_name,
            "process_count": len(result_processes),
            "processes": result_processes[:50]  # Limit to first 50 processes
        }

    except docker.errors.NotFound:
        return {
            "error": f"Container '{container_name}' not found",
            "container": container_name
        }
    except docker.errors.APIError as e:
        if "not running" in str(e).lower():
            return {
                "container": container_name,
                "error": "Container is not running"
            }
        return {
            "error": f"Docker API error: {str(e)}",
            "container": container_name
        }
    except docker.errors.DockerException as e:
        return {
            "error": f"Docker error: {str(e)}",
            "container": container_name
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting container processes: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "container": container_name
        }


@tool
def start_container(
    docker_image: str,
    container_name: str,
    volume_mounts: dict[str, str] | None = None,
    environment_vars: dict[str, str] | None = None,
    port_mappings: dict[str, str] | None = None,
    restart_policy: str = "unless-stopped",
    command: str | None = None
) -> dict:
    """Start a Docker container with specified configuration.

    Args:
        docker_image: Docker image ID or name (e.g., "postgres:13" or "abc123")
        container_name: Name for the container
        volume_mounts: Dictionary of volume mounts {host_path: container_path}
                       e.g., {"/host/path": "/container/path"}
        environment_vars: Dictionary of environment variables
        port_mappings: Dictionary of port mappings {container_port: host_port}
        restart_policy: Container restart policy (default: unless-stopped)
        command: Command to run in the container

    Returns:
        Dictionary containing:
            - success: bool - Whether container was started successfully
            - container_id: str - Container ID
            - container_name: str - Container name
            - status: str - Container status
            - message: str - Status message
            - error: str | None - Error message if failed

    Example:
        >>> result = start_container(
        ...     docker_image="postgres:13",
        ...     container_name="my-postgres",
        ...     volume_mounts={"/data/postgres": "/var/lib/postgresql/data"},
        ...     environment_vars={"POSTGRES_PASSWORD": "secret"},
        ...     port_mappings={"5432": "5432"}
        ... )
        >>> if result['success']:
        ...     print(f"Container started: {result['container_id']}")
    """
    try:
        client = get_docker_client()

        # 检查容器是否已存在
        try:
            existing_container = client.containers.get(container_name)
            if existing_container.status == 'running':
                return {
                    'success': True,
                    'container_id': existing_container.id,
                    'container_name': container_name,
                    'status': 'running',
                    'message': f"Container '{container_name}' is already running",
                    'error': None
                }
            else:
                # 删除已存在的停止容器
                existing_container.remove()
                logger.info(f"Removed existing container: {container_name}")
        except docker.errors.NotFound:
            pass  # 容器不存在，继续创建

        # 准备容器配置
        container_config = {
            'image': docker_image,
            'name': container_name,
            'detach': True,
            'restart_policy': {"Name": restart_policy}
        }

        # 添加卷挂载
        volumes_dict = {}

        # 默认挂载 Docker socket
        volumes_dict['/var/run/docker.sock'] = {'bind': '/var/run/docker.sock', 'mode': 'rw'}

        # 添加用户指定的卷挂载
        if volume_mounts:
            for host_path, container_path in volume_mounts.items():
                # 将相对路径转换为绝对路径
                if not os.path.isabs(host_path):
                    host_path = os.path.abspath(host_path)
                volumes_dict[host_path] = {'bind': container_path, 'mode': 'rw'}

        container_config['volumes'] = volumes_dict

        # 添加环境变量
        if environment_vars:
            container_config['environment'] = environment_vars

        # 添加端口映射
        if port_mappings:
            ports_dict = {}
            for container_port, host_port in port_mappings.items():
                ports_dict[f"{container_port}/tcp"] = host_port
            container_config['ports'] = ports_dict

        # 添加命令
        if command:
            container_config['command'] = command

        # 启动容器
        container = client.containers.run(**container_config)

        return {
            'success': True,
            'container_id': container.id,
            'container_name': container_name,
            'status': container.status,
            'message': f"Container '{container_name}' started successfully",
            'error': None
        }

    except docker.errors.NotFound:
        return {
            'success': False,
            'container_id': None,
            'container_name': container_name,
            'status': None,
            'message': None,
            'error': f"Docker image not found: {docker_image}"
        }
    except docker.errors.DockerException as e:
        return {
            'success': False,
            'container_id': None,
            'container_name': container_name,
            'status': None,
            'message': None,
            'error': f"Docker error: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error starting container: {e}")
        return {
            'success': False,
            'container_id': None,
            'container_name': container_name,
            'status': None,
            'message': None,
            'error': f"Unexpected error: {str(e)}"
        }


@tool
def stop_container(container_name: str, timeout: int = 10) -> dict:
    """Stop a running Docker container.

    Args:
        container_name: Name of the container
        timeout: Timeout in seconds before forcing stop (default: 10)

    Returns:
        Dictionary containing:
            - success: bool - Whether container was stopped successfully
            - container_name: str - Container name
            - message: str - Status message
            - error: str | None - Error message if failed

    Example:
        >>> result = stop_container("my-postgres")
        >>> if result['success']:
        ...     print(f"Container stopped successfully")
    """
    try:
        client = get_docker_client()

        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            return {
                'success': True,
                'container_name': container_name,
                'message': f"Container '{container_name}' not found (already stopped)",
                'error': None
            }

        # 停止容器
        container.stop(timeout=timeout)

        return {
            'success': True,
            'container_name': container_name,
            'message': f"Container '{container_name}' stopped successfully",
            'error': None
        }

    except docker.errors.DockerException as e:
        return {
            'success': False,
            'container_name': container_name,
            'message': None,
            'error': f"Docker error: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error stopping container: {e}")
        return {
            'success': False,
            'container_name': container_name,
            'message': None,
            'error': f"Unexpected error: {str(e)}"
        }


@tool
def get_vector_image() -> str:
    """Get the Docker image ID or name for Vector.

    Returns:
        str: Docker image ID or name for Vector
    """
    return settings.vector_image


@tool
def get_monitored_container() -> str:
    """Get the name of the monitored container.

    Returns:
        str: Name of the monitored container
    """
    return settings.monitored_container


def get_tools() -> list[BaseTool]:
    return [
        get_container_info,
        get_container_logs,
        restart_container,
        get_container_stats,
        list_containers,
        get_container_processes,
        start_container,
        stop_container,
        get_vector_image,
        get_monitored_container
    ]
