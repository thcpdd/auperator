# 安装指南

本文档介绍如何安装和配置 Auperator。

## 系统要求

- Python 3.11+
- Node.js 22+ (用于 Dashboard，待实现)
- Docker 20+ (可选，用于容器化部署)
- Redis 7+ (用于消息队列)
- PostgreSQL 15+ (可选，用于数据持久化)

## 安装方式

### 方式一：源码安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 使用 uv 安装依赖
uv sync

# 或者直接使用 pip
pip install -e .
```

### 方式二：使用 uv 安装

```bash
# 安装 uv (如果未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 安装项目
uv sync
```

## 安装 Redis

Redis 用于消息队列，是必需组件。

### Docker 方式（推荐）

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -v redis-data:/data \
  --restart unless-stopped \
  redis:7 --appendonly yes
```

### 验证 Redis 安装

```bash
redis-cli ping
# 应返回：PONG
```

## 安装 Docker SDK（用于采集容器日志）

如果使用 Docker 日志采集功能，确保已安装 Docker：

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh

# 验证安装
docker --version
docker run hello-world
```

## 验证安装

```bash
# 测试 CLI
uv run auperator-collector --help

# 测试适配器
uv run auperator-collector test -a json

# 列出 Docker 容器
uv run auperator-collector list
```

## 下一步

- [快速开始](quickstart.md) - 开始使用 Auperator
- [配置指南](collector/configuration.md) - 配置日志采集器
