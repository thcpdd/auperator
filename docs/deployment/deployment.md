# 部署指南

本文档介绍如何在生产环境部署 Auperator。

## 系统要求

| 组件 | 要求 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 2GB | 4GB |
| 磁盘 | 10GB | 50GB |
| Python | 3.11+ | 3.12 |
| Redis | 7.0+ | 7.2+ |

## 架构概述

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   采集器         │      │   Redis         │      │   Agent         │
│   (多个实例)     │      │   (主从)        │      │   (多实例)      │
│                 │      │                 │      │                 │
│  Collector ──▶  │─────▶│  Redis Master   │─────▶│  Consumer ──▶   │
│  Collector ──▶  │      │       │         │      │  Consumer ──▶   │
│  Collector ──▶  │      │       ▼         │      │  Consumer ──▶   │
│                 │      │  Redis Slave    │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 安装步骤

### 1. 安装 Redis

```bash
# 使用 Docker (推荐)
docker run -d --name redis \
  -p 6379:6379 \
  -v /data/redis:/data \
  redis:7 --appendonly yes

# 或使用系统包
# Ubuntu/Debian
apt-get install redis-server

# 配置持久化
echo "appendonly yes" >> /etc/redis/redis.conf
systemctl restart redis
```

### 2. 安装 Auperator

```bash
# 克隆仓库
git clone https://github.com/thcpdd/auperator.git
cd auperator

# 创建虚拟环境
python -m venv /opt/auperator/.venv
source /opt/auperator/.venv/bin/activate

# 安装依赖
uv sync --frozen
```

### 3. 创建配置文件

```yaml
# /etc/auperator/config.yaml

redis:
  url: "redis://localhost:6379"
  stream_name: "logs:production"

collector:
  batch_size: 500
  batch_timeout: 3.0
  max_retries: 5

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

### 4. 创建 Systemd 服务

```ini
# /etc/systemd/system/auperator-collector.service

[Unit]
Description=Auperator Log Collector
After=network.target redis.service

[Service]
Type=simple
User=auperator
Group=auperator
WorkingDirectory=/opt/auperator
Environment="PATH=/opt/auperator/.venv/bin"
ExecStart=/opt/auperator/.venv/bin/auperator-collector docker my-app -f
Restart=always
RestartSec=5

# 日志
StandardOutput=journal
StandardError=journal

# 资源限制
LimitNOFILE=65535
MemoryLimit=1G

[Install]
WantedBy=multi-user.target
```

### 5. 启动服务

```bash
# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl enable auperator-collector
systemctl start auperator-collector

# 查看状态
systemctl status auperator-collector
```

## Docker Compose 部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  collector-web:
    image: auperator:latest
    command: auperator-collector docker web-app -f -r redis://redis:6379
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - redis
    restart: unless-stopped

  collector-api:
    image: auperator:latest
    command: auperator-collector docker api-server -f -r redis://redis:6379
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - redis
    restart: unless-stopped

  consumer:
    image: auperator:latest
    command: auperator-collector consume -g auperator-group -n agent-1 -r redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis-data:
```

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f collector-web
```

## 高可用部署

### Redis 哨兵模式

```bash
# redis-sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
```

```yaml
# 采集器配置
redis:
  url: "redis://sentinel1:26379,sentinel2:26379,sentinel3:26379"
  master_name: "mymaster"
```

### 多消费者实例

```bash
# 启动多个消费者 (负载均衡)
auperator-collector consume -n agent-1 &
auperator-collector consume -n agent-2 &
auperator-collector consume -n agent-3 &
```

## 监控配置

### Prometheus Exporter

```python
# 导出监控指标
from prometheus_client import Counter, Histogram

LOGS_RECEIVED = Counter('auperator_logs_received_total', 'Total logs received')
LOGS_SENT = Counter('auperator_logs_sent_total', 'Total logs sent')
PROCESS_TIME = Histogram('auperator_process_seconds', 'Time spent processing')
```

### 健康检查

```bash
# 检查 Redis 连接
redis-cli ping

# 检查 Stream 状态
redis-cli XINFO STREAM logs:production

# 检查采集器进程
systemctl status auperator-collector
```

## 日志管理

### 日志轮转

```ini
# /etc/logrotate.d/auperator
/var/log/auperator/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 auperator auperator
}
```

### 日志级别

```yaml
# 配置日志级别
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 安全配置

### 网络隔离

```bash
# 只允许内网访问 Redis
bind 127.0.0.1
protected-mode yes
```

### 认证

```bash
# Redis 密码
requirepass your-strong-password
```

```yaml
# 采集器配置
redis:
  url: "redis://:your-strong-password@localhost:6379"
```

## 故障排查

### 常见问题

**采集器无法启动:**

```bash
# 检查日志
journalctl -u auperator-collector -f

# 检查 Docker 连接
docker ps
```

**Redis 连接失败:**

```bash
# 检查 Redis 状态
systemctl status redis

# 测试连接
redis-cli ping
```

**日志堆积:**

```bash
# 查看 Stream 长度
redis-cli XLEN logs:production

# 清理旧日志
redis-cli XTRIM logs:production MAXLEN ~10000
```

## 备份恢复

### Redis 备份

```bash
# 手动备份
redis-cli BGSAVE

# 复制 RDB 文件
cp /var/lib/redis/dump.rdb /backup/redis-dump-$(date +%Y%m%d).rdb
```

### 恢复数据

```bash
# 停止 Redis
systemctl stop redis

# 恢复 RDB 文件
cp /backup/redis-dump-20240101.rdb /var/lib/redis/dump.rdb

# 启动 Redis
systemctl start redis
```

## 性能调优

### Redis 配置

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### 采集器配置

```yaml
collector:
  # 增大批处理
  batch_size: 1000
  batch_timeout: 5.0

  # 增加重试
  max_retries: 5
  retry_delay: 2.0
```

## 文档导航

- [监控与告警](monitoring.md) - 监控配置
- [故障排查](troubleshooting.md) - 常见问题
