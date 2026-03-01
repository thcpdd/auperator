# 监控与告警

本文档介绍如何监控 Auperator 和配置告警。

## 监控指标

### Redis 指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| `used_memory` | Redis 内存使用 | > 80% |
| `connected_clients` | 连接数 | > 1000 |
| `blocked_clients` | 阻塞客户端数 | > 100 |
| `stream_length` | Stream 长度 | > 10000 |
| `pending_messages` | 待处理消息数 | > 1000 |

### 采集器指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| `logs_per_second` | 日志采集速率 | 突增/突降 |
| `error_rate` | 错误率 | > 1% |
| `send_latency` | 发送延迟 | > 5s |
| `reconnect_count` | 重连次数 | > 10/h |

### Agent 指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| `consume_lag` | 消费延迟 | > 60s |
| `process_time` | 处理时间 | > 1s |
| `analysis_count` | 分析次数 | - |
| `alert_count` | 告警次数 | - |

## Prometheus 配置

### 安装 Exporter

```bash
# Redis Exporter
docker run -d --name redis-exporter \
  -p 9121:9121 \
  oliver006/redis_exporter \
  --redis.addr redis://localhost:6379
```

### Prometheus 配置

```yaml
# prometheus.yml

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'auperator'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard

导入 Redis 和 Auperator 的 Dashboard 模板。

## 告警规则

### Prometheus Alertmanager

```yaml
# alertmanager.yml

groups:
  - name: auperator
    rules:
      # Redis 内存告警
      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 内存使用过高"
          description: "Redis 内存使用率 {{ $value | humanizePercentage }}"

      # Stream 堆积告警
      - alert: RedisStreamBacklog
        expr: redis_stream_length > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis Stream 消息堆积"
          description: "Stream 长度：{{ $value }}"

      # 消费者延迟告警
      - alert: ConsumerLag
        expr: auperator_consumer_lag_seconds > 60
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "消费者处理延迟"
          description: "延迟 {{ $value }} 秒"

      # 采集器错误率告警
      - alert: CollectorErrorRate
        expr: rate(auperator_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "采集器错误率过高"
          description: "错误率 {{ $value | humanizePercentage }}"
```

## 日志告警

### 告警规则配置

```yaml
# alert_rules.yaml

rules:
  - name: error_spike
    condition: "level == 'ERROR' and count > 100 in 1m"
    action:
      type: slack
      channel: "#alerts"
      message: "错误日志激增：{{ count }} 条/分钟"

  - name: critical_error
    condition: "level == 'CRITICAL'"
    action:
      type: pagerduty
      severity: critical
      message: "严重错误：{{ message }}"

  - name: service_down
    condition: "no logs from service 'web-app' in 5m"
    action:
      type: slack
      channel: "#alerts"
      message: "服务 web-app 无日志，可能已宕机"
```

### 通知渠道

#### Slack

```yaml
notification:
  slack:
    webhook_url: "https://hooks.slack.com/services/xxx/yyy/zzz"
    channel: "#alerts"
    username: "Auperator Bot"
    icon_emoji: ":robot_face:"
```

#### 邮件

```yaml
notification:
  email:
    smtp_server: "smtp.example.com"
    smtp_port: 587
    username: "alerts@example.com"
    password: "${SMTP_PASSWORD}"
    from: "auperator@example.com"
    to:
      - "ops-team@example.com"
```

#### PagerDuty

```yaml
notification:
  pagerduty:
    service_key: "${PAGERDUTY_SERVICE_KEY}"
    severity_map:
      critical: critical
      error: error
      warning: warning
```

#### Webhook

```yaml
notification:
  webhook:
    url: "https://api.example.com/alerts"
    method: POST
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
      Content-Type: "application/json"
```

## 监控脚本

### 健康检查脚本

```bash
#!/bin/bash
# check_health.sh

# 检查 Redis
if ! redis-cli ping > /dev/null; then
    echo "CRITICAL: Redis 无法连接"
    exit 2
fi

# 检查 Stream 长度
LENGTH=$(redis-cli XLEN logs:production)
if [ "$LENGTH" -gt 10000 ]; then
    echo "WARNING: Stream 长度 $LENGTH"
    exit 1
fi

# 检查采集器进程
if ! pgrep -f "auperator-collector" > /dev/null; then
    echo "CRITICAL: 采集器进程未运行"
    exit 2
fi

echo "OK: 所有检查通过"
exit 0
```

### 监控 Consumer Lag

```python
#!/usr/bin/env python3
# check_consumer_lag.py

import asyncio
import sys
import redis.asyncio as redis

async def check_lag():
    r = redis.from_url("redis://localhost:6379")

    # 获取 Stream 信息
    info = await r.xinfo_stream("logs:production")
    length = info.get("length", 0)

    # 获取待处理消息
    pending = await r.xpending("logs:production", "auperator-group")
    pending_count = pending.get("pending", 0)

    # 告警阈值
    if length > 10000 or pending_count > 1000:
        print(f"CRITICAL: Stream 长度={length}, 待处理={pending_count}")
        return 2

    if length > 5000 or pending_count > 500:
        print(f"WARNING: Stream 长度={length}, 待处理={pending_count}")
        return 1

    print(f"OK: Stream 长度={length}, 待处理={pending_count}")
    return 0

if __name__ == "__main__":
    code = asyncio.run(check_lag())
    sys.exit(code)
```

## Dashboard 示例

### Grafana JSON

```json
{
  "dashboard": {
    "title": "Auperator Overview",
    "panels": [
      {
        "title": "Logs per Second",
        "targets": [
          {
            "expr": "rate(auperator_logs_received_total[1m])"
          }
        ]
      },
      {
        "title": "Stream Length",
        "targets": [
          {
            "expr": "redis_stream_length"
          }
        ]
      },
      {
        "title": "Consumer Lag",
        "targets": [
          {
            "expr": "auperator_consumer_lag_seconds"
          }
        ]
      }
    ]
  }
}
```

## 告警分级

| 级别 | 描述 | 响应时间 | 通知渠道 |
|------|------|----------|----------|
| Critical | 服务不可用 | 5 分钟 | PagerDuty + Slack + 邮件 |
| Warning | 性能下降 | 30 分钟 | Slack + 邮件 |
| Info | 信息通知 | - | 邮件 |

## 告警降噪

### 分组规则

```yaml
group_wait: 30s
group_interval: 5m
repeat_interval: 4h

group_by:
  - alertname
  - severity
  - service
```

### 静默规则

```yaml
inhibit_rules:
  # Critical 告警时静默 Warning
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
```

## 文档导航

- [部署指南](deployment.md) - 部署配置
- [故障排查](troubleshooting.md) - 常见问题
