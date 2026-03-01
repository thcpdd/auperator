# 故障排查

本文档介绍常见问题和解决方案。

## 快速诊断

```bash
# 1. 检查 Redis 状态
redis-cli ping

# 2. 检查 Stream 状态
redis-cli XINFO STREAM logs:main

# 3. 检查采集器进程
systemctl status auperator-collector

# 4. 查看采集器日志
journalctl -u auperator-collector -f

# 5. 查看 Docker 容器
docker ps
```

---

## 常见问题

### 1. 无法连接 Redis

**症状:**

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**原因:**
- Redis 服务未启动
- 网络连接问题
- 认证失败

**解决方案:**

```bash
# 检查 Redis 是否运行
systemctl status redis

# 测试连接
redis-cli ping

# 检查端口
netstat -tlnp | grep 6379

# 检查防火墙
ufw status

# 检查认证
redis-cli -a your-password ping
```

---

### 2. 采集器无法启动

**症状:**

```bash
systemctl status auperator-collector
# 显示 failed 状态
```

**原因:**
- 配置文件错误
- 权限问题
- 依赖未安装

**解决方案:**

```bash
# 查看详细日志
journalctl -u auperator-collector -f

# 检查配置文件
auperator-collector config --validate /etc/auperator/config.yaml

# 检查 Python 环境
source /opt/auperator/.venv/bin/activate
python -c "import auperator; print('OK')"

# 检查权限
ls -la /opt/auperator
```

---

### 3. 无法连接 Docker

**症状:**

```
docker.errors.DockerException: Error while fetching server API version
```

**原因:**
- Docker 服务未启动
- 权限不足

**解决方案:**

```bash
# 检查 Docker 状态
systemctl status docker

# 测试 Docker 连接
docker ps

# 添加用户到 docker 组
sudo usermod -aG docker $USER
sudo systemctl restart auperator-collector

# 或者使用 socket 挂载
# docker-compose.yml 中:
# volumes:
#   - /var/run/docker.sock:/var/run/docker.sock
```

---

### 4. 日志堆积

**症状:**

```bash
redis-cli XLEN logs:main
# 返回 > 10000
```

**原因:**
- 消费者处理速度慢
- 消费者进程宕机
- Stream 配置不当

**解决方案:**

```bash
# 查看消费者组状态
redis-cli XINFO GROUPS logs:main

# 查看待处理消息
redis-cli XPENDING logs:main auperator-group

# 增加消费者实例
auperator-collector consume -n agent-2 &
auperator-collector consume -n agent-3 &

# 清理旧日志（谨慎操作）
redis-cli XTRIM logs:main MAXLEN ~10000

# 认领超时消息
redis-cli XAUTOCLAIM logs:main auperator-group agent-1 30000 0-0
```

---

### 5. 容器日志采集中断

**症状:**

```
RuntimeError: 容器 xxx 未找到
```

**原因:**
- 容器已停止或删除
- 容器名称变更

**解决方案:**

```bash
# 检查容器状态
docker ps -a | grep my-app

# 重启容器
docker restart my-app

# 更新采集器配置
# 使用容器 ID 而不是名称，更稳定
```

---

### 6. 日志解析失败

**症状:**

```
parse_error: invalid_json
```

**原因:**
- 日志格式不匹配
- 编码器问题

**解决方案:**

```python
# 切换到通用适配器
auperator-collector docker my-app -a generic

# 或者自定义适配器
# 参考 docs/development/extending-adapters.md
```

---

### 7. 内存使用过高

**症状:**

```bash
# Redis 内存告警
redis-cli INFO memory
# used_memory 过高
```

**原因:**
- Stream 数据过多
- 未配置过期策略

**解决方案:**

```bash
# 配置 Stream 自动修剪
redis-cli CONFIG SET stream-node-max-bytes 1048576

# 手动修剪
redis-cli XTRIM logs:main MAXLEN ~10000

# 配置 Redis 最大内存
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 定期清理
# 添加 cron 任务
0 * * * * redis-cli XTRIM logs:main MAXLEN ~10000
```

---

### 8. 消费者重复消费

**症状:**

同一条日志被多次处理。

**原因:**
- 消费者组配置不当
- XACK 未正确调用

**解决方案:**

```python
# 确保正确处理消息
async def consume(self, handler):
    for message_id, fields in messages:
        try:
            entry = self._parse(fields)
            await handler(entry)
            # 确保调用 XACK
            await self._redis.xack(
                self.stream_name,
                self.group_name,
                message_id,
            )
        except Exception as e:
            # 记录错误但不确认消息，让其重新消费
            logger.error(f"处理失败：{e}")
```

---

### 9. 采集器频繁重启

**症状:**

```bash
systemctl status auperator-collector
# 显示 restarting 状态
```

**原因:**
- 配置错误
- 资源不足
- 依赖服务不稳定

**解决方案:**

```bash
# 查看详细日志
journalctl -u auperator-collector -n 100

# 增加重启延迟
# /etc/systemd/system/auperator-collector.service
[Service]
RestartSec=10

# 增加资源限制
LimitNOFILE=65535
MemoryLimit=1G

# 检查依赖服务
systemctl status redis
systemctl status docker
```

---

## 调试技巧

### 开启调试日志

```yaml
# config.yaml
logging:
  level: DEBUG
```

```bash
# 重启服务
systemctl restart auperator-collector
```

### 使用 Python 调试

```python
# 手动测试采集器
import asyncio
from auperator.collector import DockerSource, JsonAdapter

async def test():
    source = DockerSource("my-app", follow=False, tail=10)
    adapter = JsonAdapter()

    await source.start()
    async for line in source.read():
        entry = adapter.parse(line)
        print(f"Parsed: {entry}")
    await source.stop()

asyncio.run(test())
```

### 网络抓包

```bash
# 抓取 Redis 流量
tcpdump -i lo port 6379 -w redis.pcap

# 分析
tcpdump -r redis.pcap -X
```

---

## 性能诊断

### 查看慢查询

```bash
# Redis 慢查询日志
redis-cli SLOWLOG GET 10

# 配置慢查询阈值
redis-cli CONFIG SET slowlog-log-slower-than 10000
```

### 分析 Stream 性能

```bash
# Stream 信息
redis-cli XINFO STREAM logs:main

# 消费者组信息
redis-cli XINFO GROUPS logs:main

# 消费者信息
redis-cli XINFO CONSUMERS logs:main auperator-group
```

---

## 应急处理

### 停止所有采集器

```bash
# 停止服务
systemctl stop auperator-collector

# 或者 Docker
docker-compose down
```

### 清空 Stream

```bash
# 警告：会丢失所有待处理日志
redis-cli DEL logs:main
```

### 回滚配置

```bash
# 备份当前配置
cp /etc/auperator/config.yaml /etc/auperator/config.yaml.bak

# 恢复旧配置
cp /etc/auperator/config.yaml.bak /etc/auperator/config.yaml
systemctl restart auperator-collector
```

---

## 获取帮助

### 日志位置

```bash
# 系统日志
journalctl -u auperator-collector

# Redis 日志
/var/log/redis/redis-server.log

# Docker 日志
docker logs my-app
```

### 报告问题

在 GitHub Issues 提供以下信息：

1. Auperator 版本
2. Python 版本
3. Redis 版本
4. 操作系统
5. 错误日志
6. 配置文件（脱敏）
7. 复现步骤

---

## 文档导航

- [部署指南](deployment.md) - 部署配置
- [监控与告警](monitoring.md) - 监控配置
