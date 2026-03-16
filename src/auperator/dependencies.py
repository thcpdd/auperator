"""依赖注入

提供 FastAPI 路由的依赖注入函数
"""

from fastapi import HTTPException

from auperator.state import global_state


def get_daytona_service():
    """获取 Daytona 服务（依赖注入）"""
    if global_state.daytona_service is None:
        raise HTTPException(
            status_code=503,
            detail="Daytona service not initialized"
        )
    return global_state.daytona_service
