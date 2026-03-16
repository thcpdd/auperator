"""Daytona 相关的数据模型"""

from pydantic import BaseModel


class CreateSandboxResponse(BaseModel):
    """创建沙箱响应"""
    sandbox_id: str


class ExecuteCommandRequest(BaseModel):
    """执行命令请求"""
    command: str
    cwd: str | None = None
    timeout_seconds: int = 300


class ExecuteCommandResponse(BaseModel):
    """执行命令响应"""
    stdout: str
    stderr: str
    exit_code: int
