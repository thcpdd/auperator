# 后端快速开始

## 环境要求

- Python 3.11+
- Redis 7.0+
- uv 包管理器

## 安装

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 使用 uv 安装依赖
uv pip install -e .
```

## 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env
```

### 关键配置项

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI 配置（Agent 核心）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Qdrant 配置（记忆系统）
QDRANT_URL=http://localhost:6333

# Daytona 配置（代码沙箱）
DAYTONA_API_KEY=your-daytona-key
```

## 启动服务

### 1. 启动 Redis（如果没有）

```bash
docker run -d -p 6379:6379 redis:alpine
```

### 2. 启动 API 服务

```bash
# 开发模式（代码热重载）
auperator server --reload

# 生产模式
auperator server -h 0.0.0.0 -p 7000
```

### 3. 启动 Vector 日志采集

```bash
vector --config vector.yaml
```

### 4. 启动自动修复模式

```bash
auperator start
```

## 验证安装

```bash
# 健康检查
curl http://localhost:7000/health

# 查看 Redis List 日志数量
redis-cli LLEN auperator:logs:main
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `auperator server` | 启动 API 服务 |
| `auperator start` | 启动自动修复模式 |
| `auperator terminal-consume -v` | 终端消费日志（调试） |
| `auperator list-info` | 查看 Redis List 信息 |
| `auperator init` | 初始化项目记忆 |

## 下一步

- [架构设计](architecture.md) - 深入了解系统架构
- [CLI 命令](cli.md) - 完整命令参考
- [API 参考](api-reference.md) - API 端点详解
