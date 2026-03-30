"""Drain3日志模板提取服务."""

import logging

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig

from auperator.config import settings

logger = logging.getLogger(__name__)


class Drain3Service:
    """Drain3日志模板提取服务.

    功能：
    1. 使用Drain3提取日志模板并去重
    2. 判断是否为新模板或模板变化
    """

    def __init__(self):
        """初始化服务."""
        # 配置Drain3（从配置文件读取）
        config = TemplateMinerConfig()
        config.drain_depth = settings.drain3_depth
        config.drain_max_clusters = settings.drain3_max_clusters
        config.drain_max_children = settings.drain3_max_children
        config.drain_sim_th = settings.drain3_sim_th

        # 使用文件持久化（从配置读取）
        persistence = FilePersistence(settings.drain3_state_file)

        # 初始化TemplateMiner
        self.template_miner = TemplateMiner(persistence, config)

    def extract_template(self, log_message: str) -> dict | None:
        """提取日志模板.

        Args:
            log_message: 原始日志消息

        Returns:
            提取结果字典，包含：
            - change_type: "cluster_created" | "cluster_template_changed" | "none"
            - cluster_id: 集群ID
            - cluster_size: 集群大小
            - cluster_count: 总集群数
            - template_mined: 提取的模板
            如果解析失败返回None
        """
        result = self.template_miner.add_log_message(log_message)

        if result is None:
            logger.warning(f"Failed to parse log: {log_message[:100]}")
            return None

        result["is_new_template"] = self.is_new_template(result["change_type"])

        return result

    def is_new_template(self, change_type: str) -> bool:
        """判断是否为新模板或模板变化.

        Args:
            change_type: Drain3返回的change_type

        Returns:
            是否为新模板或模板变化
        """
        return change_type == "cluster_created"
