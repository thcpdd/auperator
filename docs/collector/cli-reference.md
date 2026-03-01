# CLI 参考

本文档介绍日志采集器的命令行接口。

## 命令概览

```bash
auperator-collector <command> [options]

# 或通过主入口
auperator collector <command> [options]
```

### 可用命令

| 命令 | 描述 |
|------|------|
| `docker` | 采集 Docker 容器日志 |
| `consume` | 从 Redis 消费日志 |
| `redis-info` | 查看 Redis Stream 信息 |
| `list` | 列出 Docker 容器 |
| `test` | 测试日志适配器 |

## 命令详解

### docker

采集 Docker 容器日志并发送到 Redis。

```bash
auperator-collector docker <container> [options]
```

**参数:**

| 参数 | 描述 |
|------|------|
| `<container>` | 容器名称或 ID (必填) |

**选项:**

| 选项 | 简写 | 默认值 | 描述 |
|------|------|--------|------|
| `--redis` | `-r` | `redis://localhost:6379` | Redis 连接 URL |
| `--stream` | `-s` | `logs:main` | Stream 名称 |
| `--adapter` | `-a` | `json` | 适配器类型 (json/generic) |
| `--follow` | `-f` | `true` | 持续跟踪日志 |
| `--tail` | `-n` | `100` | 初始显示的行数 (0 表示全部) |
| `--service` | | 容器名 | 服务名称 |
| `--env` | `-e` | `unknown` | 环境标识 |

**示例:**

```bash
# 采集容器日志
auperator-collector docker my-app

# 持续跟踪并发送到指定 Redis
auperator-collector docker my-app -r redis://192.168.1.100:6379

# 使用通用适配器
auperator-collector docker my-app -a generic

# 采集最近 1000 行
auperator-collector docker my-app -n 1000

# 指定服务和环境
auperator-collector docker my-app --service web-api --env production
```

---

### consume

从 Redis Stream 消费日志。

```bash
auperator-collector consume [options]
```

**选项:**

| 选项 | 简写 | 默认值 | 描述 |
|------|------|--------|------|
| `--redis` | `-r` | `redis://localhost:6379` | Redis 连接 URL |
| `--stream` | `-s` | `logs:main` | Stream 名称 |
| `--group` | `-g` | `auperator-group` | 消费者组名称 |
| `--name` | `-n` | `agent-1` | 消费者名称 |
| `--verbose` | `-v` | `false` | 详细输出模式 |

**示例:**

```bash
# 消费日志
auperator-collector consume

# 指定消费者组和名称
auperator-collector consume -g my-group -n agent-2

# 详细输出模式
auperator-collector consume -v

# 连接到远程 Redis
auperator-collector consume -r redis://192.168.1.100:6379
```

---

### redis-info

查看 Redis Stream 信息。

```bash
auperator-collector redis-info [options]
```

**选项:**

| 选项 | 简写 | 默认值 | 描述 |
|------|------|--------|------|
| `--redis` | `-r` | `redis://localhost:6379` | Redis 连接 URL |
| `--stream` | `-s` | `logs:main` | Stream 名称 |

**示例:**

```bash
# 查看 Stream 信息
auperator-collector redis-info

# 查看指定 Stream
auperator-collector redis-info -s logs:production

# 查看远程 Redis
auperator-collector redis-info -r redis://192.168.1.100:6379
```

**输出示例:**

```
Stream: logs:main
  消息数量：150
  消费者组数：1
  第一个消息：1709251200000-0
  最后一个消息：1709251300000-0
```

---

### list

列出 Docker 容器。

```bash
auperator-collector list [options]
```

**选项:**

| 选项 | 简写 | 默认值 | 描述 |
|------|------|--------|------|
| `--all` | `-a` | `false` | 显示所有容器 (包括已停止的) |

**示例:**

```bash
# 列出运行中的容器
auperator-collector list

# 列出所有容器
auperator-collector list -a
```

**输出示例:**

```
容器 ID          名称                   镜像                           状态
--------------------------------------------------------------------------------
abc123           my-app                my-app:latest                  running
def456           nginx                 nginx:alpine                   running
```

---

### test

测试日志适配器。

```bash
auperator-collector test [options]
```

**选项:**

| 选项 | 简写 | 默认值 | 描述 |
|------|------|--------|------|
| `--adapter` | `-a` | `json` | 适配器类型 (json/generic) |

**示例:**

```bash
# 测试 JSON 适配器
auperator-collector test -a json

# 测试通用适配器
auperator-collector test -a generic
```

**输出示例:**

```
使用 json 适配器测试:

------------------------------------------------------------

原始：{"level": "INFO", "msg": "Server started", "time": "2024-01-01T00:00:00Z"}
解析：level=INFO, message=Server started...

原始：{"level": "ERROR", "msg": "Database connection failed", "stack": "Error: ..."}
解析：level=ERROR, message=Database connection failed...

------------------------------------------------------------
```

---

## 全局选项

以下选项对所有命令有效：

| 选项 | 简写 | 描述 |
|------|------|------|
| `--help` | `-h` | 显示帮助信息 |
| `--version` | `-v` | 显示版本号 |

---

## 环境变量

可以使用环境变量配置：

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `AUPERATOR_REDIS_URL` | Redis 连接 URL | `redis://localhost:6379` |
| `AUPERATOR_STREAM_NAME` | Stream 名称 | `logs:main` |
| `AUPERATOR_CONSUMER_GROUP` | 消费者组名称 | `auperator-group` |

---

## 退出码

| 退出码 | 描述 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 127 | 命令不存在 |

---

## 使用技巧

### 后台运行

```bash
# 使用 nohup
nohup auperator-collector docker my-app -f > collector.log 2>&1 &

# 使用 screen
screen -S collector
auperator-collector docker my-app -f
# Ctrl+A, D 分离会话
```

### 多容器采集

```bash
# 启动多个采集器
auperator-collector docker web-app -s logs:web &
auperator-collector docker api-server -s logs:api &
auperator-collector docker db -s logs:db &
```

### 消费者组模式

```bash
# 启动多个消费者 (负载均衡)
auperator-collector consume -n agent-1 &
auperator-collector consume -n agent-2 &
auperator-collector consume -n agent-3 &
```

---

## 文档导航

- [采集器概述](collector/overview.md) - 功能概览
- [配置指南](collector/configuration.md) - 配置选项
- [Docker 日志源](collector/docker-source.md) - Docker 采集详解
