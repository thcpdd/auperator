"""Pull Request tools for Auperator Agent.

These tools allow the agent to create and manage pull requests
on Git platforms (GitHub, GitLab, Gitee, etc.).
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from github import Github, Auth
from langchain.tools import tool, BaseTool

from auperator.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PullRequestResult:
    """Pull Request 创建结果"""
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_title: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class GitProvider(ABC):
    """Git 平台提供者抽象基类"""

    @abstractmethod
    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> PullRequestResult:
        """创建 Pull Request

        Args:
            repo: 仓库名称，格式：owner/repo
            title: PR 标题
            body: PR 描述
            head: 源分支
            base: 目标分支
            draft: 是否为 Draft PR

        Returns:
            PullRequestResult 对象
        """
        pass

    @abstractmethod
    def get_repository(self, repo: str) -> dict:
        """获取仓库信息

        Args:
            repo: 仓库名称，格式：owner/repo

        Returns:
            仓库信息字典
        """
        pass

    @abstractmethod
    def get_pull_request(self, repo: str, pr_number: int) -> dict:
        """获取 Pull Request 信息

        Args:
            repo: 仓库名称，格式：owner/repo
            pr_number: PR 编号

        Returns:
            PR 信息字典
        """
        pass


class GitHubProvider(GitProvider):
    """GitHub 平台实现"""

    def __init__(self):
        """初始化 GitHub 提供者"""
        token = settings.github_token

        if not token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN in .env file, "
                "GITHUB_TOKEN environment variable, or pass token parameter."
            )

        self.auth = Auth.Token(token)
        self.github = Github(auth=self.auth)

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> PullRequestResult:
        """在 GitHub 上创建 Pull Request

        Args:
            repo: 仓库名称，格式：owner/repo
            title: PR 标题
            body: PR 描述
            head: 源分支
            base: 目标分支
            draft: 是否为 Draft PR

        Returns:
            PullRequestResult 对象
        """
        try:
            repository = self.github.get_repo(repo)

            # 检查源分支是否存在
            try:
                repository.get_branch(head)
            except Exception:
                return PullRequestResult(
                    success=False,
                    error=f"源分支 '{head}' 不存在"
                )

            # 检查目标分支是否存在
            try:
                repository.get_branch(base)
            except Exception:
                return PullRequestResult(
                    success=False,
                    error=f"目标分支 '{base}' 不存在"
                )

            # 创建 PR
            pr = repository.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft,
            )

            return PullRequestResult(
                success=True,
                pr_number=pr.number,
                pr_url=pr.html_url,
                pr_title=pr.title,
                message=f"成功创建 Pull Request #{pr.number}: {pr.html_url}"
            )

        except Exception as e:
            logger.exception(f"创建 GitHub PR 时出错：{e}")
            return PullRequestResult(
                success=False,
                error=f"创建 PR 失败：{str(e)}"
            )

    def get_repository(self, repo: str) -> dict:
        """获取 GitHub 仓库信息

        Args:
            repo: 仓库名称，格式：owner/repo

        Returns:
            仓库信息字典
        """
        try:
            repository = self.github.get_repo(repo)
            return {
                "name": repository.name,
                "full_name": repository.full_name,
                "description": repository.description,
                "html_url": repository.html_url,
                "default_branch": repository.default_branch,
                "private": repository.private,
                "forks_count": repository.forks_count,
                "stargazers_count": repository.stargazers_count,
                "open_issues_count": repository.open_issues_count,
                "language": repository.language,
                "created_at": repository.created_at.isoformat(),
                "updated_at": repository.updated_at.isoformat(),
            }
        except Exception as e:
            logger.exception(f"获取 GitHub 仓库信息时出错：{e}")
            return {"error": f"获取仓库信息失败：{str(e)}"}

    def get_pull_request(self, repo: str, pr_number: int) -> dict:
        """获取 GitHub Pull Request 信息

        Args:
            repo: 仓库名称，格式：owner/repo
            pr_number: PR 编号

        Returns:
            PR 信息字典
        """
        try:
            repository = self.github.get_repo(repo)
            pr = repository.get_pull(pr_number)
            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "html_url": pr.html_url,
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha,
                },
                "user": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "merged": pr.merged,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "mergeable": pr.mergeable,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
            }
        except Exception as e:
            logger.exception(f"获取 GitHub PR 信息时出错：{e}")
            return {"error": f"获取 PR 信息失败：{str(e)}"}


# 全局提供者实例缓存
_providers: dict[str, GitProvider] = {}


def get_provider(provider: str = "github", token: Optional[str] = None) -> GitProvider:
    """获取 Git 提供者实例

    Args:
        provider: 提供者名称 (github, gitlab, gitee, ...)
        token: 认证 token

    Returns:
        GitProvider 实例
    """
    if provider not in _providers:
        if provider == "github":
            _providers[provider] = GitHubProvider(token=token)
        else:
            raise ValueError(f"不支持的 Git 提供者：{provider}")

    return _providers[provider]


@tool
def create_pull_request(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str,
    provider: str = "github",
    draft: bool = False,
) -> dict:
    """创建 Pull Request

    Args:
        repo: 仓库名称，格式：owner/repo (例如：tensorflow/tensorflow)
        title: Pull Request 标题
        body: Pull Request 描述（支持 Markdown）
        head: 源分支名称
        base: 目标分支名称
        provider: Git 提供者，默认 github
        draft: 是否创建 Draft PR，默认 False

    Returns:
        字典包含：
            - success: 是否成功
            - pr_number: PR 编号
            - pr_url: PR URL
            - pr_title: PR 标题
            - message: 状态消息
            - error: 错误信息（如果有）

    Example:
        ```python
        create_pull_request(
            repo="owner/repo",
            title="Fix bug in API",
            body="This PR fixes the bug...",
            head="fix-bug",
            base="main"
        )
        ```
    """
    try:
        git_provider = get_provider(provider)
        result = git_provider.create_pull_request(
            repo=repo,
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft,
        )

        return {
            "success": result.success,
            "pr_number": result.pr_number,
            "pr_url": result.pr_url,
            "pr_title": result.pr_title,
            "message": result.message,
            "error": result.error,
        }

    except Exception as e:
        logger.exception(f"创建 PR 时出错：{e}")
        return {
            "success": False,
            "error": f"创建 PR 失败：{str(e)}"
        }


@tool
def get_repository_info(
    repo: str,
    provider: str = "github",
) -> dict:
    """获取仓库信息

    Args:
        repo: 仓库名称，格式：owner/repo
        provider: Git 提供者，默认 github

    Returns:
        仓库信息字典，包含：
            - name: 仓库名称
            - full_name: 完整名称
            - description: 描述
            - html_url: 仓库 URL
            - default_branch: 默认分支
            - private: 是否私有
            - forks_count: Fork 数量
            - stargazers_count: Star 数量
            - open_issues_count: 打开的 Issue 数量
            - language: 主要语言
            - created_at: 创建时间
            - updated_at: 更新时间
            - error: 错误信息（如果有）
    """
    try:
        git_provider = get_provider(provider)
        return git_provider.get_repository(repo)
    except Exception as e:
        logger.exception(f"获取仓库信息时出错：{e}")
        return {
            "error": f"获取仓库信息失败：{str(e)}"
        }


@tool
def get_pull_request_info(
    repo: str,
    pr_number: int,
    provider: str = "github",
) -> dict:
    """获取 Pull Request 信息

    Args:
        repo: 仓库名称，格式：owner/repo
        pr_number: PR 编号
        provider: Git 提供者，默认 github

    Returns:
        PR 信息字典，包含：
            - number: PR 编号
            - title: PR 标题
            - body: PR 描述
            - state: 状态 (open/closed)
            - html_url: PR URL
            - head: 源分支信息
            - base: 目标分支信息
            - user: 创建者
            - created_at: 创建时间
            - updated_at: 更新时间
            - merged: 是否已合并
            - merged_at: 合并时间
            - mergeable: 是否可合并
            - additions: 新增行数
            - deletions: 删除行数
            - changed_files: 修改文件数
            - error: 错误信息（如果有）
    """
    try:
        git_provider = get_provider(provider)
        return git_provider.get_pull_request(repo, pr_number)
    except Exception as e:
        logger.exception(f"获取 PR 信息时出错：{e}")
        return {
            "error": f"获取 PR 信息失败：{str(e)}"
        }


def get_tools() -> list[BaseTool]:
    """获取所有 Pull Request 相关工具"""
    return [
        create_pull_request,
        get_repository_info,
        get_pull_request_info,
    ]
