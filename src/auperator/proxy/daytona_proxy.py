"""Daytona Proxy Server.

This proxy server maintains a persistent connection to Daytona API and manages
sandbox lifecycle. It allows stateless agent processes to reuse sandboxes and
avoid repeated TCP connection overhead.
"""

from contextlib import asynccontextmanager
from urllib.parse import urlparse

import uvicorn
from uvicorn.config import logger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from auperator.config import settings
from auperator.services.daytona_service import (
    DaytonaService,
    SandboxNotFoundError,
    SandboxCommandError
)

# Request/Response models
class CreateSandboxResponse(BaseModel):
    sandbox_id: str


class ExecuteCommandRequest(BaseModel):
    command: str
    cwd: str | None = None
    timeout_seconds: int = 300


class ExecuteCommandResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


class ErrorResponse(BaseModel):
    error: str
    error_type: str


# Global state
daytona_service: DaytonaService | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage the Daytona service lifecycle."""
    global daytona_service

    logger.info("Starting Daytona proxy server...")

    # Initialize Daytona service
    async with DaytonaService() as service:
        daytona_service = service
        logger.info("Daytona service initialized")

        yield

        # Shutdown
        logger.info("Shutting down proxy server...")


# Create FastAPI app
app = FastAPI(
    title="Daytona Proxy",
    description="Proxy server for Daytona sandbox operations",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "daytona-proxy",
    }


@app.post("/sandbox/create", response_model=CreateSandboxResponse)
async def create_sandbox():
    """Create a new sandbox."""
    if daytona_service is None:
        raise HTTPException(status_code=503, detail="Daytona service not initialized")

    try:
        sandbox_id = await daytona_service.create_sandbox()
        logger.info(f"Created sandbox: {sandbox_id}")
        return CreateSandboxResponse(sandbox_id=sandbox_id)

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{sandbox_id}/execute", response_model=ExecuteCommandResponse)
async def execute_command(sandbox_id: str, request: ExecuteCommandRequest):
    """Execute a command in the sandbox."""
    if daytona_service is None:
        raise HTTPException(status_code=503, detail="Daytona service not initialized")

    try:
        result = await daytona_service.execute_command(
            sandbox_id=sandbox_id,
            command=request.command,
            cwd=request.cwd,
            timeout_seconds=request.timeout_seconds,
        )

        return ExecuteCommandResponse(
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
        )

    except SandboxNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SandboxCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sandbox/{sandbox_id}", response_model=dict)
async def destroy_sandbox(sandbox_id: str):
    """Destroy a sandbox."""
    if daytona_service is None:
        raise HTTPException(status_code=503, detail="Daytona service not initialized")

    try:
        await daytona_service.destroy_sandbox(sandbox_id)
        logger.info(f"Destroyed sandbox: {sandbox_id}")
        return {"status": "destroyed", "sandbox_id": sandbox_id}

    except SandboxNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to destroy sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sandbox/{sandbox_id}/info")
async def get_sandbox_info(sandbox_id: str):
    """Get information about a sandbox."""
    if daytona_service is None:
        raise HTTPException(status_code=503, detail="Daytona service not initialized")

    try:
        info = await daytona_service.get_sandbox_info(sandbox_id)
        return info

    except SandboxNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get sandbox info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sandbox/list")
async def list_sandboxes():
    """List all active sandboxes."""
    if daytona_service is None:
        raise HTTPException(status_code=503, detail="Daytona service not initialized")

    try:
        all_sandboxes = await daytona_service.list_active_sandboxes()
        return {
            "active": all_sandboxes,
        }

    except Exception as e:
        logger.error(f"Failed to list sandboxes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the proxy server."""
    # Parse proxy URL to get host and port
    parsed_url = urlparse(settings.daytona_proxy_url)
    host = parsed_url.hostname or "0.0.0.0"
    port = parsed_url.port or 8888

    uvicorn.run(
        "auperator.proxy.daytona_proxy:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
