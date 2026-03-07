"""Docker tools for Auperator Agent.

These tools allow the agent to inspect and manage Docker containers
for error diagnosis and remediation.
"""

import logging
from typing import Optional

import docker
from langchain.tools import tool, BaseTool

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
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"].percpu_usage) * 100.0

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


def get_tools() -> list[BaseTool]:
    return [
        get_container_info,
        get_container_logs,
        restart_container,
        get_container_stats,
        list_containers,
        get_container_processes
    ]
