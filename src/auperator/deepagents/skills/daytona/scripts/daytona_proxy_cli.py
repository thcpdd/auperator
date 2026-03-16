#!/usr/bin/env python3
"""Daytona Proxy CLI.

This script provides a simple CLI interface for the Daytona proxy server.
Agent uses this script to interact with sandboxes through the proxy.
"""

import json
import sys
from typing import Any

import httpx

from auperator.config import settings


# Proxy server configuration (from settings)
PROXY_BASE_URL = f"http://{settings.api_host}:{settings.api_port}"


def print_json(data: dict[str, Any]) -> None:
    """Print JSON output to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_error(error: str, error_type: str = "Error") -> None:
    """Print error to stderr and exit."""
    error_json = {"error": error, "error_type": error_type}
    print(json.dumps(error_json, ensure_ascii=False))
    sys.exit(1)


def create_sandbox() -> None:
    """Create a new sandbox."""
    response = httpx.post(f"{PROXY_BASE_URL}/sandbox/create")

    if response.status_code == 200:
        print_json(response.json())
    else:
        print_error(response.json().get("detail", "Unknown error"), "CreateError")


def execute_command(sandbox_id: str, command: str, cwd: str | None = None, timeout: int = 300) -> None:
    """Execute a command in the sandbox."""
    payload = {
        "command": command,
        "cwd": cwd,
        "timeout_seconds": timeout,
    }

    response = httpx.post(
        f"{PROXY_BASE_URL}/sandbox/{sandbox_id}/execute",
        json=payload,
    )

    if response.status_code == 200:
        print_json(response.json())
    else:
        print_error(response.json().get("detail", "Unknown error"), "ExecuteError")


def destroy_sandbox(sandbox_id: str) -> None:
    """Destroy a sandbox."""
    response = httpx.delete(f"{PROXY_BASE_URL}/sandbox/{sandbox_id}")

    if response.status_code == 200:
        print_json(response.json())
    else:
        print_error(response.json().get("detail", "Unknown error"), "DestroyError")


def get_sandbox_info(sandbox_id: str) -> None:
    """Get sandbox information."""
    response = httpx.get(f"{PROXY_BASE_URL}/sandbox/{sandbox_id}/info")

    if response.status_code == 200:
        print_json(response.json())
    else:
        print_error(response.json().get("detail", "Unknown error"), "InfoError")


def list_sandboxes() -> None:
    """List all sandboxes."""
    response = httpx.get(f"{PROXY_BASE_URL}/sandbox/list")

    if response.status_code == 200:
        print_json(response.json())
    else:
        print_error(response.json().get("detail", "Unknown error"), "ListError")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_error(
            "Usage: python daytona_proxy_cli.py <command> [args...]\n"
            "Commands: create, execute, destroy, info, list, health",
            "UsageError",
        )

    command = sys.argv[1]

    if command == "create":
        create_sandbox()

    elif command == "execute":
        if len(sys.argv) < 4:
            print_error(
                "Usage: python daytona_proxy_cli.py execute <sandbox_id> <command> [cwd] [timeout]",
                "UsageError",
            )
        sandbox_id = sys.argv[2]
        cmd = sys.argv[3]
        cwd = sys.argv[4] if len(sys.argv) > 4 else None
        timeout = int(sys.argv[5]) if len(sys.argv) > 5 else 300
        execute_command(sandbox_id, cmd, cwd, timeout)

    elif command == "destroy":
        if len(sys.argv) < 3:
            print_error(
                "Usage: python daytona_proxy_cli.py destroy <sandbox_id>",
                "UsageError",
            )
        destroy_sandbox(sys.argv[2])

    elif command == "info":
        if len(sys.argv) < 3:
            print_error(
                "Usage: python daytona_proxy_cli.py info <sandbox_id>",
                "UsageError",
            )
        get_sandbox_info(sys.argv[2])

    elif command == "list":
        list_sandboxes()

    else:
        print_error(f"Unknown command: {command}", "CommandError")


if __name__ == "__main__":
    main()
