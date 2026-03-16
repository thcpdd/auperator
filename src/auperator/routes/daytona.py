"""Daytona 沙箱管理路由"""

import logging

from fastapi import APIRouter, HTTPException, Depends

from auperator.dependencies import get_daytona_service
from auperator.schemas.daytona import (
    CreateSandboxResponse,
    ExecuteCommandRequest,
    ExecuteCommandResponse,
)
from auperator.services.daytona_service import (
    SandboxNotFoundError,
    SandboxCommandError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/create", response_model=CreateSandboxResponse)
async def create_sandbox(daytona_service=Depends(get_daytona_service)):
    """创建新的沙箱"""
    try:
        sandbox_id = await daytona_service.create_sandbox()
        logger.info(f"Created sandbox: {sandbox_id}")
        return CreateSandboxResponse(sandbox_id=sandbox_id)

    except Exception as e:
        logger.error(f"Failed to create sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sandbox_id}/execute", response_model=ExecuteCommandResponse)
async def execute_command(
    sandbox_id: str,
    request: ExecuteCommandRequest,
    daytona_service=Depends(get_daytona_service)
):
    """在沙箱中执行命令"""
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


@router.delete("/{sandbox_id}")
async def destroy_sandbox(
    sandbox_id: str,
    daytona_service=Depends(get_daytona_service)
):
    """销毁沙箱"""
    try:
        await daytona_service.destroy_sandbox(sandbox_id)
        logger.info(f"Destroyed sandbox: {sandbox_id}")
        return {"status": "destroyed", "sandbox_id": sandbox_id}

    except SandboxNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to destroy sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sandbox_id}/info")
async def get_sandbox_info(
    sandbox_id: str,
    daytona_service=Depends(get_daytona_service)
):
    """获取沙箱信息"""
    try:
        info = await daytona_service.get_sandbox_info(sandbox_id)
        return info

    except SandboxNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get sandbox info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_sandboxes(daytona_service=Depends(get_daytona_service)):
    """列出所有活跃的沙箱"""
    try:
        all_sandboxes = await daytona_service.list_active_sandboxes()
        return {
            "active": all_sandboxes,
        }

    except Exception as e:
        logger.error(f"Failed to list sandboxes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
