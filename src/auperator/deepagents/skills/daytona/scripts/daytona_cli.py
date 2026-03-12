#!/usr/bin/env python3
"""Daytona CLI for deepagents.

This script provides command-line access to Daytona sandbox operations.
Deepagents can execute this script directly without writing any code.
"""

import asyncio
import base64
import json
import sys
from pathlib import Path


async def main():
    """Main entry point for Daytona CLI."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: daytona_cli.py <command> [args...]"}))
        sys.exit(1)

    command = sys.argv[1]

    try:
        # Import here to avoid import errors when Daytona is not installed
        from auperator.services.daytona_service import (
            SandboxCommandError,
            SandboxNotFoundError,
            DaytonaService,
        )

        async with DaytonaService() as service:
            if command == "create":
                # Create a new sandbox
                sandbox_id = await service.create_sandbox()
                print(json.dumps({"sandbox_id": sandbox_id}))

            elif command == "destroy":
                # Destroy a sandbox
                # Usage: daytona_cli.py destroy <sandbox_id>
                if len(sys.argv) < 3:
                    print(json.dumps({"error": "Usage: daytona_cli.py destroy <sandbox_id>"}))
                    sys.exit(1)
                sandbox_id = sys.argv[2]
                await service.destroy_sandbox(sandbox_id)
                print(json.dumps({"status": "destroyed", "sandbox_id": sandbox_id}))

            elif command == "info":
                # Get sandbox info
                # Usage: daytona_cli.py info <sandbox_id>
                if len(sys.argv) < 3:
                    print(json.dumps({"error": "Usage: daytona_cli.py info <sandbox_id>"}))
                    sys.exit(1)
                sandbox_id = sys.argv[2]
                info = await service.get_sandbox_info(sandbox_id)
                print(json.dumps(info))

            elif command == "list":
                # List active sandboxes
                sandboxes = await service.list_active_sandboxes()
                print(json.dumps({"sandboxes": sandboxes}))

            elif command == "execute":
                # Execute command in sandbox
                # Usage: daytona_cli.py execute <sandbox_id> <command> [cwd] [timeout]
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Usage: daytona_cli.py execute <sandbox_id> <command> [cwd] [timeout]"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                cmd = sys.argv[3]
                cwd = sys.argv[4] if len(sys.argv) > 4 else None
                timeout = int(sys.argv[5]) if len(sys.argv) > 5 else 300

                result = await service.execute_command(sandbox_id, cmd, cwd=cwd, timeout_seconds=timeout)
                print(json.dumps(result))

            elif command == "read":
                # Read file from sandbox
                # Usage: daytona_cli.py read <sandbox_id> <path>
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Usage: daytona_cli.py read <sandbox_id> <path>"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                path = sys.argv[3]
                content = await service.read_file(sandbox_id, path)
                # Output as base64 to handle binary files and special characters
                content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
                print(json.dumps({"content": content, "content_b64": content_b64, "path": path}))

            elif command == "write":
                # Write file to sandbox
                # Usage: daytona_cli.py write <sandbox_id> <path> <content>
                if len(sys.argv) < 5:
                    print(json.dumps({"error": "Usage: daytona_cli.py write <sandbox_id> <path> <content>"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                path = sys.argv[3]
                content = sys.argv[4]
                await service.write_file(sandbox_id, path, content)
                print(json.dumps({"status": "written", "path": path}))

            elif command == "write-base64":
                # Write file to sandbox (content is base64 encoded)
                # Usage: daytona_cli.py write-base64 <sandbox_id> <path> <content_b64>
                if len(sys.argv) < 5:
                    print(json.dumps({"error": "Usage: daytona_cli.py write-base64 <sandbox_id> <path> <content_b64>"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                path = sys.argv[3]
                content_b64 = sys.argv[4]
                content = base64.b64decode(content_b64).decode("utf-8")
                await service.write_file(sandbox_id, path, content)
                print(json.dumps({"status": "written", "path": path}))

            elif command == "ls":
                # List files in sandbox
                # Usage: daytona_cli.py ls <sandbox_id> <path>
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Usage: daytona_cli.py ls <sandbox_id> <path>"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                path = sys.argv[3]
                files = await service.list_files(sandbox_id, path)
                print(json.dumps({"files": files, "path": path}))

            elif command == "delete":
                # Delete file in sandbox
                # Usage: daytona_cli.py delete <sandbox_id> <path>
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Usage: daytona_cli.py delete <sandbox_id> <path>"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                path = sys.argv[3]
                await service.delete_file(sandbox_id, path)
                print(json.dumps({"status": "deleted", "path": path}))

            elif command == "clone":
                # Clone Git repository in sandbox
                # Usage: daytona_cli.py clone <sandbox_id> <repo_url> [branch] [target_dir] [username] [password]
                if len(sys.argv) < 4:
                    print(json.dumps({"error": "Usage: daytona_cli.py clone <sandbox_id> <repo_url> [branch] [target_dir] [username] [password]"}))
                    sys.exit(1)

                sandbox_id = sys.argv[2]
                repo_url = sys.argv[3]
                branch = sys.argv[4] if len(sys.argv) > 4 else "main"
                target_dir = sys.argv[5] if len(sys.argv) > 5 else "workspace/repo"
                username = sys.argv[6] if len(sys.argv) > 6 else None
                password = sys.argv[7] if len(sys.argv) > 7 else None

                await service.clone_repository(sandbox_id, repo_url, branch, target_dir, username, password)
                print(json.dumps({"status": "cloned", "repo_url": repo_url, "target_dir": target_dir}))

            else:
                print(json.dumps({"error": f"Unknown command: {command}"}))
                sys.exit(1)

    except SandboxNotFoundError as e:
        print(json.dumps({"error": str(e), "error_type": "SandboxNotFoundError"}))
        sys.exit(1)
    except SandboxCommandError as e:
        print(json.dumps({"error": str(e), "error_type": "SandboxCommandError"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "error_type": type(e).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
