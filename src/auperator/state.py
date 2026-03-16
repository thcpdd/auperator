"""全局状态管理

管理 API 服务需要的全局状态
"""

import logging

from auperator.services.daytona_service import DaytonaService

logger = logging.getLogger(__name__)


class GlobalState:
    """全局状态管理"""

    def __init__(self):
        # Daytona 服务
        self.daytona_service: DaytonaService | None = None

    async def initialize_daytona(self):
        """初始化 Daytona 服务"""
        logger.info("Initializing Daytona service...")
        self.daytona_service = DaytonaService()
        await self.daytona_service.__aenter__()
        logger.info("Daytona service initialized")

    async def cleanup_daytona(self):
        """清理 Daytona 服务"""
        if self.daytona_service:
            logger.info("Cleaning up Daytona service...")
            await self.daytona_service.__aexit__(None, None, None)
            self.daytona_service = None


global_state = GlobalState()
