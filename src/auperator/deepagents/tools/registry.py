"""工具注册表 - 统一管理所有 Agent 工具

使用示例:
    # 获取所有工具
    from auperator.deepagents.tools.registry import ToolRegistry
    tools = ToolRegistry.get_all()

    # 获取特定类别的工具
    docker_tools = ToolRegistry.get("docker")
    pr_tools = ToolRegistry.get("pr")
    memory_tools = ToolRegistry.get("memory")

    # 获取多个类别的工具
    tools = ToolRegistry.get("docker", "pr", "memory")

    # 查看工具信息
    info = ToolRegistry.info()

自动发现机制:
    ToolRegistry 会自动扫描 tools 目录下以 _tools.py 结尾的模块，
    并调用每个模块的 get_tools() 函数来注册工具。
    工具类别名从文件名推断（如 docker_tools.py -> docker）

    注册规则:
    - 只注册以 _tools.py 结尾的文件
    - 忽略 __init__.py、registry.py 和以 _ 开头的私有模块
"""

import importlib
import logging
from pathlib import Path

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表 - 统一管理所有 Agent 工具

    这是一个单例类，提供工具的注册、查询和管理功能。
    """

    # 类变量：工具注册表
    _registry: dict[str, list[BaseTool]] = {}
    _initialized = False

    @classmethod
    def _initialize(cls) -> None:
        """初始化注册表，自动扫描并导入所有工具模块

        自动发现机制:
        1. 扫描 tools 目录下的所有 .py 文件
        2. 排除 __init__.py, registry.py 和以 _ 开头的文件
        3. 动态导入每个模块
        4. 调用模块的 get_tools() 函数
        5. 从文件名推断类别名（如 docker_tools.py -> docker）
        """
        if cls._initialized:
            return

        # 获取 tools 目录路径
        tools_dir = Path(__file__).parent

        # 排除的文件列表
        excluded_files = {"__init__.py", "registry.py"}

        # 扫描所有 Python 模块
        for py_file in tools_dir.glob("*.py"):
            filename = py_file.name

            # 跳过排除的文件和私有模块
            if filename in excluded_files or filename.startswith("_"):
                continue

            # 只处理以 _tools.py 结尾的工具模块
            if not filename.endswith("_tools.py"):
                continue

            # 从文件名推断模块名和类别名
            # xxx_tools.py -> xxx
            module_name = py_file.stem  # 去掉 .py 后缀
            category = module_name.rsplit("_tools", 1)[0]  # 去掉 _tools 后缀

            try:
                # 动态导入模块
                full_module_name = f"auperator.deepagents.tools.{module_name}"
                module = importlib.import_module(full_module_name)

                # 调用 get_tools() 函数
                if hasattr(module, "get_tools"):
                    tools = module.get_tools()
                    cls._registry[category] = tools
                    logger.debug(f"已注册工具类别 '{category}': {len(tools)} 个工具")
                else:
                    logger.warning(
                        f"模块 {module_name} 没有 get_tools() 函数，跳过注册"
                    )

            except ImportError as e:
                logger.warning(f"无法导入模块 {module_name}: {e}")
            except Exception as e:
                logger.error(f"注册工具类别 '{category}' 时出错: {e}")

        cls._initialized = True

        # 输出注册摘要
        category_summary = ", ".join(
            f"{cat}={len(tools)}"
            for cat, tools in cls._registry.items()
        )
        logger.info(f"工具注册完成: {category_summary}")

    @classmethod
    def get(cls, *categories: str) -> list[BaseTool]:
        """获取指定类别的工具

        Args:
            *categories: 工具类别，可选值: "docker", "pr", "memory"
                         如果不指定，返回所有工具

        Returns:
            工具列表

        Examples:
            >>> # 获取 Docker 工具
            >>> tools = ToolRegistry.get("docker")

            >>> # 获取多个类别的工具
            >>> tools = ToolRegistry.get("docker", "pr")

            >>> # 获取所有工具
            >>> tools = ToolRegistry.get()
        """
        cls._initialize()

        if not categories:
            # 返回所有工具
            all_tools = []
            for tools_list in cls._registry.values():
                all_tools.extend(tools_list)
            return all_tools

        # 返回指定类别的工具
        result = []
        for category in categories:
            if category not in cls._registry:
                logger.warning(f"未知的工具类别: {category}")
                continue
            result.extend(cls._registry[category])

        return result

    @classmethod
    def get_all(cls) -> list[BaseTool]:
        """获取所有已注册的工具

        Returns:
            所有工具的列表
        """
        return cls.get()

    @classmethod
    def categories(cls) -> list[str]:
        """列出所有可用的工具类别

        Returns:
            工具类别列表
        """
        cls._initialize()
        return list(cls._registry.keys())

    @classmethod
    def list_tools(cls, category: str) -> list[str]:
        """列出指定类别下的所有工具名称

        Args:
            category: 工具类别

        Returns:
            工具名称列表
        """
        cls._initialize()

        if category not in cls._registry:
            logger.warning(f"未知的工具类别: {category}")
            return []

        return [tool.name for tool in cls._registry[category]]

    @classmethod
    def info(cls) -> dict[str, list[dict]]:
        """获取所有工具的详细信息

        Returns:
            字典，键为类别，值为工具信息列表
            每个工具信息包含 name 和 description
        """
        cls._initialize()

        info = {}
        for category, tools in cls._registry.items():
            info[category] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ]

        return info
