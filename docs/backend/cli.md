# CLI 命令参考

## 完整命令列表

```bash
auperator --help
```

```
Usage: auperator [OPTIONS] COMMAND [ARGS]...

Options:
  --help  显示帮助信息

Commands:
  server              启动 API 服务
  start               启动自动修复模式
  terminal-consume    终端消费日志
  list-info           查看 Redis List 信息
  init                初始化项目记忆
```

## server

启动 FastAPI 服务器。

```bash
auperator server [OPTIONS]
```

### 选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-h`, `--host` | TEXT | `127.0.0.1` | API 服务监听地址 |
| `-p`, `--port` | INT | `7000` | API 服务监听端口 |
| `--reload` | FLAG | `False` | 启用代码热重载（开发模式） |
| `--workers` | INT | `1` | 工作进程数 |

### 示例

```bash
# 开发模式
auperator server --reload

# 生产模式
auperator server -h 0.0.0.0 -p 7000

# 多进程
auperator server --workers 4
```

## start

启动自动修复模式，Agent 会消费 Redis List 中的日志并自动修复问题。

```bash
auperator start [OPTIONS]
```

### 选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-r`, `--redis` | TEXT | 从 `.env` 读取 | Redis 连接 URL |
| `-e`, `--enable-langfuse` | FLAG | `False` | 启用 Langfuse 追踪 |

### 示例

```bash
# 基本启动
auperator start

# 启用 Langfuse 追踪
auperator start --enable-langfuse

# 指定 Redis
auperator start --redis redis://localhost:6379
```

## terminal-consume

在终端中消费日志，用于调试和查看实时日志。

```bash
auperator terminal-consume [OPTIONS]
```

### 选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-r`, `--redis` | TEXT | 从 `.env` 读取 | Redis 连接 URL |
| `-l`, `--list` | TEXT | `auperator:logs:main` | Redis List 名称 |
| `-v`, `--verbose` | FLAG | `False` | 详细输出模式 |

### 示例

```bash
# 基本消费
auperator terminal-consume

# 详细模式
auperator terminal-consume -v

# 指定 List
auperator terminal-consume --list custom:logs
```

## list-info

查看 Redis List 的统计信息。

```bash
auperator list-info [OPTIONS]
```

### 选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-r`, `--redis` | TEXT | 从 `.env` 读取 | Redis 连接 URL |
| `-l`, `--list` | TEXT | `auperator:logs:main` | Redis List 名称 |

### 输出示例

```
Redis List: auperator:logs:main
Length: 42
First item: {"message": "Error: Connection refused", ...}
```

## init

分析目标项目并生成 AUPERATOR.md 记忆文件。

```bash
auperator init [OPTIONS]
```

### 选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--project-path` | TEXT | 当前目录 | 目标项目路径 |

### 示例

```bash
# 分析当前目录
auperator init

# 分析指定项目
auperator init --project-path /path/to/project
```

## 环境变量

CLI 会从 `.env` 文件读取以下配置：

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_KEY_PREFIX=auperator
REDIS_LIST_NAME=logs:main

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

DAYTONA_API_KEY=
DAYTONA_API_URL=
```
