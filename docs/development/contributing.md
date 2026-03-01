# 贡献指南

感谢你为 Auperator 做出贡献！

## 如何贡献

### 1. Fork 仓库

```bash
# 点击 GitHub 上的 Fork 按钮
# 然后克隆你的 fork
git clone https://github.com/thcpdd/auperator.git
cd auperator
```

### 2. 创建分支

```bash
# 创建特性分支
git checkout -b feature/your-feature-name

# 或者修复分支
git checkout -b fix/issue-123
```

### 3. 开发

```bash
# 安装开发依赖
uv sync

# 编写代码和测试
# 确保代码通过测试
```

### 4. 提交

```bash
# 添加修改的文件
git add src/auperator/collector/your_file.py

# 提交 (遵循约定式提交)
git commit -m "feat(collector): 添加文件日志源"

# 推送
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

在 GitHub 上创建 PR，描述你的修改。

---

## 代码风格

### Python 风格

- 遵循 PEP 8
- 使用类型注解
- 使用 docstring 文档

```python
from typing import AsyncIterator


class BaseLogSource:
    """日志源抽象基类"""

    async def read(self) -> AsyncIterator[str]:
        """读取原始日志行

        Yields:
            原始日志行 (字符串)
        """
        pass
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类 | PascalCase | `LogEntry`, `RedisSender` |
| 函数/方法 | snake_case | `parse_log`, `send_batch` |
| 常量 | UPPER_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| 私有属性 | _prefix | `_running`, `_client` |

### 提交信息规范

遵循 [约定式提交](https://www.conventionalcommits.org/)：

```
<type>(scope): <description>

[optional body]
```

**Type:**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例:**

```
feat(collector): 添加文件日志源

- 实现 FileSource 类
- 支持 tail -f 模式
- 添加单元测试

fix(redis): 修复连接超时问题

docs(readme): 更新快速开始
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_collector.py

# 查看覆盖率
uv run pytest --cov=auperator
```

### 编写测试

```python
# tests/test_json_adapter.py

import pytest
from auperator.collector import JsonAdapter, LogLevel, LogEntry


class TestJsonAdapter:
    """测试 JsonAdapter"""

    def test_parse_info_level(self):
        adapter = JsonAdapter()
        line = '{"level": "INFO", "msg": "Hello"}'
        entry = adapter.parse(line)

        assert entry.level == LogLevel.INFO
        assert entry.message == "Hello"

    def test_parse_error_level(self):
        adapter = JsonAdapter()
        line = '{"level": "ERROR", "msg": "Error occurred"}'
        entry = adapter.parse(line)

        assert entry.level == LogLevel.ERROR
        assert "Error occurred" in entry.message

    def test_parse_invalid_json(self):
        adapter = JsonAdapter()
        line = 'not valid json'
        entry = adapter.parse(line)

        # 应该有回退处理
        assert entry is not None
```

---

## 文档

### 编写文档

- 使用 Markdown 格式
- 放在 `docs/` 目录
- 在 `docs/index.md` 添加链接

### 文档结构

```markdown
# 标题

简要描述功能。

## 功能特性

- 特性 1
- 特性 2

## 使用示例

```python
# 代码示例
```

## 配置说明

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `param` | str | `""` | 参数说明 |
```

---

## 发布流程

### 版本号

遵循 [语义化版本](https://semver.org/)：

- MAJOR.MINOR.PATCH
- 例如：1.2.3

### 发布步骤

1. 更新版本号 (`pyproject.toml`)
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 发布到 PyPI

---

## 问题反馈

### 报告 Bug

在 GitHub Issues 创建 Issue，包含：

- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（Python 版本、OS 等）
- 日志/截图

### 功能请求

在 GitHub Issues 创建 Issue，描述：

- 功能需求
- 使用场景
- 期望的解决方案

---

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 安装开发工具
uv pip install pytest pytest-cov black ruff

# 运行测试
uv run pytest
```

---

## 代码审查清单

提交前检查：

- [ ] 代码通过测试
- [ ] 添加了必要的测试
- [ ] 遵循代码风格
- [ ] 更新了文档
- [ ] 提交信息规范

---

## 联系方式

- GitHub Issues: https://github.com/thcpdd/auperator/issues
- Email: 1834763300@qq.com

---

## 文档导航

- [扩展日志源](extending-sources.md)
- [扩展适配器](extending-adapters.md)
