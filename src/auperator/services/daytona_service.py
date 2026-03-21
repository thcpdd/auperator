"""Daytona service for sandbox management."""

import logging
from typing import Any

from daytona import AsyncDaytona, DaytonaConfig, AsyncSandbox

from auperator.config import settings

logger = logging.getLogger(__name__)


class SandboxNotFoundError(Exception):
    """Sandbox not found error."""
    pass


class SandboxCommandError(Exception):
    """Sandbox command execution error."""
    pass


class DaytonaService:
    """Daytona service wrapper for auperator.

    Provides async methods for sandbox lifecycle management, command execution,
    and file operations using the Daytona SDK.

    Usage:
        async with DaytonaService() as service:
            sandbox_id = await service.create_sandbox()
            await service.execute_command(sandbox_id, "ls /workspace")
    """

    def __init__(self) -> None:
        """Initialize Daytona service configuration.

        Reads configuration from settings:
        - daytona_api_key: API key for authentication
        - daytona_api_url: API URL
        """
        self._config = DaytonaConfig(
            api_key=settings.daytona_api_key,
            api_url=settings.daytona_api_url,
            target="us"
        )
        self._daytona: AsyncDaytona | None = None

    async def __aenter__(self) -> "DaytonaService":
        """Enter the context manager and initialize the Daytona client.

        Returns:
            self: The service instance ready for use
        """
        self._daytona = AsyncDaytona(self._config)
        logger.info(f"Daytona service initialized with API URL: {settings.daytona_api_url}")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and close the Daytona client.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if self._daytona:
            await self._daytona.close()
            logger.info("Daytona service closed")

    def _ensure_initialized(self) -> None:
        """Ensure the Daytona client is initialized.

        Raises:
            RuntimeError: If the service is not used as a context manager
        """
        if self._daytona is None:
            raise RuntimeError(
                "DaytonaService must be used as an async context manager. "
                "Use 'async with DaytonaService() as service:' instead."
            )

    async def create_sandbox(self) -> str:
        """Create a new sandbox with default configuration.

        Returns:
            Sandbox ID

        Raises:
            Exception: If sandbox creation fails
        """
        self._ensure_initialized()
        logger.info("Creating sandbox")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.create(timeout=settings.daytona_sandbox_timeout)
            logger.info(f"Sandbox created: {sandbox.id}")

            # Auto-configure Git authentication for GitHub
            await self._configure_git_auth(sandbox)

            return sandbox.id

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise

    async def _configure_git_auth(self, sandbox: AsyncSandbox) -> None:
        """Configure Git authentication in the sandbox.

        Sets up Git user info and GitHub token authentication.

        Args:
            sandbox: Sandbox instance
        """
        try:
            # Configure Git user info
            await sandbox.process.exec('git config --global user.name "Auperator Bot"')
            await sandbox.process.exec('git config --global user.email "auperator@example.com"')

            # Configure GitHub token authentication if available
            github_token = settings.github_token
            if github_token:
                # URL rewriting to inject token into GitHub HTTPS URLs
                await sandbox.process.exec(
                    f'git config --global url."https://{github_token}@github.com/".insteadOf "https://github.com/"'
                )
                logger.info("GitHub token authentication configured")
            else:
                logger.warning("GITHUB_TOKEN not set, Git push operations may fail")

        except Exception as e:
            logger.warning(f"Failed to configure Git authentication: {e}")

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Destroy a sandbox.

        Args:
            sandbox_id: Sandbox ID to destroy

        Raises:
            SandboxNotFoundError: If sandbox not found
            Exception: If destruction fails
        """
        self._ensure_initialized()
        logger.info(f"Destroying sandbox: {sandbox_id}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            await sandbox.delete()
            logger.info(f"Sandbox destroyed: {sandbox_id}")

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            logger.error(f"Failed to destroy sandbox: {e}")
            raise

    async def get_sandbox_info(self, sandbox_id: str) -> dict[str, Any]:
        """Get sandbox information.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            Sandbox information dict with keys: id, state, cpu, memory, etc.

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            return {
                "id": sandbox.id,
                "state": sandbox.state,
                "cpu": sandbox.cpu,
                "memory": sandbox.memory,
                "disk": sandbox.disk,
                "created_at": sandbox.created_at,
            }

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise

    async def execute_command(
        self,
        sandbox_id: str,
        command: str,
        cwd: str | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Execute a shell command in the sandbox.

        Args:
            sandbox_id: Sandbox ID
            command: Shell command to execute
            cwd: Working directory (optional)
            timeout_seconds: Command timeout (default: 300)

        Returns:
            Dict with keys:
            - stdout: str - Standard output
            - stderr: str - Standard error (empty for Daytona)
            - exit_code: int - Exit code
            - execution_time_ms: int - Execution time (not provided by Daytona)

        Raises:
            SandboxNotFoundError: If sandbox not found
            SandboxCommandError: If command execution fails
        """
        self._ensure_initialized()
        logger.info(f"Executing command in sandbox {sandbox_id}: {command[:100]}...")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            response = await sandbox.process.exec(command, cwd=cwd, timeout=timeout_seconds)

            result = {
                "stdout": response.result or "",
                "stderr": "",  # Daytona combines stdout/stderr in result
                "exit_code": response.exit_code,
                "execution_time_ms": 0,  # Daytona doesn't provide this
            }

            logger.info(f"Command completed with exit code: {result['exit_code']}")
            return result

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            logger.error(f"Command execution failed: {e}")
            raise SandboxCommandError(f"Command failed: {e}")

    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read a file from the sandbox.

        Args:
            sandbox_id: Sandbox ID
            path: File path in sandbox

        Returns:
            File content as string

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        logger.debug(f"Reading file in sandbox {sandbox_id}: {path}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            content_bytes = await sandbox.fs.download_file(path)
            return content_bytes.decode("utf-8")

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise

    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str,
    ) -> None:
        """Write a file to the sandbox.

        Args:
            sandbox_id: Sandbox ID
            path: File path in sandbox
            content: File content

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        logger.debug(f"Writing file in sandbox {sandbox_id}: {path}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            content_bytes = content.encode("utf-8")
            await sandbox.fs.upload_file(content_bytes, path)

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise

    async def list_files(
        self,
        sandbox_id: str,
        path: str,
    ) -> list[dict[str, Any]]:
        """List files in the sandbox.

        Args:
            sandbox_id: Sandbox ID
            path: Directory path

        Returns:
            List of file info dicts with keys: name, is_dir, size, mod_time

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        logger.debug(f"Listing files in sandbox {sandbox_id}: {path}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            files = await sandbox.fs.list_files(path)

            return [
                {
                    "name": f.name,
                    "is_dir": f.is_dir,
                    "size": f.size,
                    "mod_time": f.mod_time,
                }
                for f in files
            ]

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise

    async def delete_file(self, sandbox_id: str, path: str) -> None:
        """Delete a file from the sandbox.

        Args:
            sandbox_id: Sandbox ID
            path: File path to delete

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        logger.debug(f"Deleting file in sandbox {sandbox_id}: {path}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)
            await sandbox.fs.delete_file(path)

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise

    async def clone_repository(
        self,
        sandbox_id: str,
        repo_url: str,
        branch: str = "main",
        target_dir: str = "workspace/repo",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Clone a Git repository in the sandbox.

        Args:
            sandbox_id: Sandbox ID
            repo_url: Git repository URL
            branch: Branch to clone (default: "main")
            target_dir: Target directory (default: "workspace/repo")
            username: Git username for authentication (optional)
            password: Git password/token for authentication (optional)

        Raises:
            SandboxNotFoundError: If sandbox not found
            SandboxCommandError: If git clone fails
        """
        self._ensure_initialized()
        logger.info(f"Cloning repository in sandbox {sandbox_id}: {repo_url}")

        try:
            assert self._daytona is not None
            sandbox = await self._daytona.get(sandbox_id)

            # Use Daytona's built-in git.clone method
            clone_kwargs = {
                "url": repo_url,
                "path": target_dir,
            }

            if branch:
                clone_kwargs["branch"] = branch
            if username and password:
                clone_kwargs["username"] = username
                clone_kwargs["password"] = password

            await sandbox.git.clone(**clone_kwargs)

            logger.info(f"Repository cloned to {target_dir}")

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            logger.error(f"Git clone failed: {e}")
            raise SandboxCommandError(f"Git clone failed: {e}")

    async def list_active_sandboxes(self) -> list[dict[str, Any]]:
        """List all active sandboxes.

        Returns:
            List of sandbox info dicts

        Raises:
            Exception: If listing fails
        """
        self._ensure_initialized()
        logger.info("Listing active sandboxes")

        try:
            assert self._daytona is not None
            sandboxes = await self._daytona.list()

            return [
                {
                    "id": sb.id,
                    "state": sb.state,
                    "cpu": sb.cpu,
                    "memory": sb.memory,
                    "created_at": sb.created_at,
                }
                for sb in sandboxes.items
                if sb.state == "started"
            ]

        except Exception as e:
            logger.error(f"Failed to list sandboxes: {e}")
            raise

    async def get_sandbox(self, sandbox_id: str):
        """Get a sandbox instance for direct operations.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            Sandbox instance

        Raises:
            SandboxNotFoundError: If sandbox not found
        """
        self._ensure_initialized()
        try:
            assert self._daytona is not None
            return await self._daytona.get(sandbox_id)
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise SandboxNotFoundError(f"Sandbox {sandbox_id} not found")
            raise
