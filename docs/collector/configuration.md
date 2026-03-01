# 配置指南

本文档介绍如何配置日志采集器。

## 配置文件格式

Auperator 支持 YAML 格式的配置文件。

## 基本配置

```yaml
# config.yaml

# Redis 配置
redis:
  url: "redis://localhost:6379"
  stream_name: "logs:main"

# 日志采集器配置
collector:
  # 全局设置
  batch_size: 100           # 批处理大小
  batch_timeout: 5.0        # 批处理超时 (秒)
  max_retries: 3            # 最大重试次数
  retry_delay: 1.0          # 重试延迟 (秒)

  # 日志源配置
  sources:
    - type: docker
      container: my-app
      follow: true
      tail: 100
      adapter: json
      service: my-app
      environment: production

    - type: docker
      container: nginx
      follow: true
      tail: 50
      adapter: nginx
      service: nginx
      environment: production

  # 文件日志源 (待实现)
  # - type: file
  #   path: /var/log/app/*.log
  #   follow: true
  #   adapter: generic

  # Kubernetes 日志源 (待实现)
  # - type: kubernetes
  #   namespace: default
  #   labels:
  #     app: my-app
  #   adapter: json
```

## Redis 配置

```yaml
redis:
  # 连接 URL
  url: "redis://localhost:6379"

  # Stream 名称
  stream_name: "logs:main"

  # 可选：认证
  # password: "your-password"

  # 可选：数据库
  # db: 0
```

## 日志源配置

### Docker 日志源

```yaml
sources:
  - type: docker
    # 容器名称或 ID (必填)
    container: my-app

    # 是否持续跟踪日志
    follow: true

    # 初始读取行数 (0 表示全部)
    tail: 100

    # 时间过滤
    # since: "2024-01-01T00:00:00Z"
    # until: "2024-01-02T00:00:00Z"

    # 是否包含时间戳
    # timestamps: false

    # 使用的适配器
    adapter: json

    # 服务名称 (用于标识)
    service: my-app

    # 环境标识
    environment: production
```

### 文件日志源 (待实现)

```yaml
sources:
  - type: file
    # 文件路径 (支持 glob)
    path: /var/log/app/*.log

    # 是否持续跟踪 (类似 tail -f)
    follow: true

    # 使用的适配器
    adapter: generic

    # 服务名称
    service: my-app

    # 环境标识
    environment: production
```

### Kubernetes 日志源 (待实现)

```yaml
sources:
  - type: kubernetes
    # 命名空间
    namespace: default

    # Label 选择器
    labels:
      app: my-app

    # 使用的适配器
    adapter: json

    # 服务名称
    service: my-app

    # 环境标识
    environment: production
```

## 适配器配置

### JSON 适配器

```yaml
adapter:
  type: json

  # 默认日志级别 (解析失败时使用)
  fallback_level: INFO

  # 服务名称
  service: my-app

  # 环境标识
  environment: production
```

### 通用适配器

```yaml
adapter:
  type: generic

  # 默认日志级别
  default_level: INFO

  # 服务名称
  service: my-app

  # 环境标识
  environment: production
```

### Nginx 适配器 (待实现)

```yaml
adapter:
  type: nginx

  # Nginx 日志格式
  # format: '$remote_addr - $remote_user [$time_local] "$request" $status'

  # 服务名称
  service: nginx

  # 环境标识
  environment: production
```

## 高级配置

### 批处理配置

```yaml
collector:
  # 批处理大小
  batch_size: 100

  # 批处理超时 (秒)
  # 即使未达到 batch_size，到达超时时间也会发送
  batch_timeout: 5.0
```

### 重试配置

```yaml
collector:
  # 最大重试次数
  max_retries: 3

  # 重试延迟 (秒)
  retry_delay: 1.0

  # 重试延迟递增系数
  # retry_delay * (attempt ^ backoff_multiplier)
  backoff_multiplier: 2
```

### 多采集器配置

```yaml
collectors:
  # 采集器 1
  - id: app-logs
    sources:
      - type: docker
        container: my-app
        adapter: json
    redis:
      stream_name: "logs:app"

  # 采集器 2
  - id: nginx-logs
    sources:
      - type: docker
        container: nginx
        adapter: nginx
    redis:
      stream_name: "logs:nginx"

  # 采集器 3
  - id: db-logs
    sources:
      - type: docker
        container: postgres
        adapter: json
    redis:
      stream_name: "logs:db"
```

## 环境变量

支持使用环境变量：

```yaml
redis:
  url: "${REDIS_URL:-redis://localhost:6379}"

collector:
  sources:
    - type: docker
      container: "${CONTAINER_NAME:-my-app}"
      service: "${SERVICE_NAME:-my-app}"
      environment: "${ENVIRONMENT:-production}"
```

## 配置文件位置

默认配置文件位置：

```
/etc/auperator/config.yaml       # 系统级配置
~/.auperator/config.yaml         # 用户级配置
./config.yaml                    # 当前目录配置
```

## 使用配置文件

```bash
# 指定配置文件
uv run auperator-collector docker my-app --config /path/to/config.yaml

# 或使用环境变量
export AUPERATOR_CONFIG=/path/to/config.yaml
uv run auperator-collector docker my-app
```

## 配置验证

```bash
# 验证配置文件
uv run auperator-collector config --validate /path/to/config.yaml
```

## 示例配置

### 最小配置

```yaml
redis:
  url: "redis://localhost:6379"
  stream_name: "logs:main"

collector:
  sources:
    - type: docker
      container: my-app
```

### 生产环境配置

```yaml
redis:
  url: "redis://redis-master:6379"
  stream_name: "logs:production"

collector:
  batch_size: 500
  batch_timeout: 3.0
  max_retries: 5
  retry_delay: 2.0

  sources:
    - type: docker
      container: web-app
      follow: true
      tail: 0
      adapter: json
      service: web-app
      environment: production

    - type: docker
      container: api-server
      follow: true
      tail: 0
      adapter: json
      service: api-server
      environment: production
```

## 文档导航

- [采集器概述](collector/overview.md) - 功能概览
- [架构设计](collector/architecture.md) - 架构详解
- [CLI 参考](collector/cli-reference.md) - 命令行接口
- [Docker 日志源](collector/docker-source.md) - Docker 采集
