# Drain3 服务

## 概述

Drain3 是一个在线日志模板挖掘算法，用于从日志消息中提取固定模板并识别变量部分。

## 工作原理

### 日志模板提取

原始日志：
```
ERROR: Connection refused to 192.168.1.100:5432
ERROR: Connection refused to 10.0.0.1:5432
ERROR: Connection refused to 172.16.0.5:5432
```

提取后的模板：
```
ERROR: Connection refused to <IP>:<PORT>
```

### 模板变量标识

| 标识 | 说明 | 示例 |
|------|------|------|
| `<*>` | 任意字符 | `abc`, `hello` |
| `<:NUM:>` | 数字 | `123`, `456` |
| `<:ALNUM:>` | 字母数字 | `abc123` |
| `<:IP:>` | IP 地址 | `192.168.1.1` |

## 配置

```python
# 配置参数
DRAIN3_DEPTH = 4           # 解析树深度
DRAIN3_MAX_CLUSTERS = 1000 # 最大聚类数
DRAIN3_MAX_CHILDREN = 100  # 每个节点最大子节点数
DRAIN3_SIM_TH = 0.4        # 相似度阈值
DRAIN3_STATE_FILE = "drain3.json"  # 状态文件路径
```

## 使用

### 基本用法

```python
from auperator.services.drain3_service import Drain3Service

service = Drain3Service()

# 处理日志
result = service.process_log("ERROR: Connection refused to 192.168.1.1:5432")

print(result)
# {
#   "change_type": "cluster_created",
#   "cluster_id": 1,
#   "cluster_size": 1,
#   "template_mined": "ERROR: Connection refused to <IP>:<PORT>",
#   "is_new_template": True
# }
```

### 返回值

```python
@dataclass
class Drain3Result:
    change_type: str       # "cluster_created" | "cluster_template_changed" | "none"
    cluster_id: int        # 聚类 ID
    cluster_size: int       # 该聚类的日志数量
    template_mined: str    # 提取的模板
    is_new_template: bool  # 是否是新模板
```

### 仅处理新模板

```python
service = Drain3Service()

result = service.process_log("same error message again")

if result.is_new_template:
    # 只有新模板才推送到 Redis
    push_to_redis(result)
```

## 状态持久化

Drain3 会将学习到的模板保存到 `drain3.json`：

```json
{
  "clusters": [
    {
      "cluster_id": 1,
      "template": "ERROR: Connection refused to <IP>:<PORT>",
      "size": 42
    },
    {
      "cluster_id": 2,
      "template": "Connection timeout for <*>",
      "size": 15
    }
  ]
}
```

## 集成到 API

Drain3 服务在 FastAPI 启动时初始化：

```python
# server.py
from auperator.services.drain3_service import Drain3Service

app = FastAPI()

@app.on_event("startup")
async def startup():
    state.drain3 = Drain3Service()

@app.post("/vector/ingest")
async def ingest_log(log: VectorLog):
    result = state.drain3.process_log(log.message)

    if result.is_new_template:
        await redis.lpush("auperator:logs:main", json.dumps({
            "message": log.message,
            "template": result.template_mined,
            "cluster_id": result.cluster_id,
            "timestamp": log.timestamp,
        }))

    return {"status": "ok", "is_new_template": result.is_new_template}
```

## 调试

### 查看当前模板

```bash
cat drain3.json | jq '.clusters[] | {cluster_id, template, size}'
```

### 重置状态

```bash
rm drain3.json
# 重启服务后会重新学习
```

### 调整相似度阈值

```bash
# 更严格（更少聚类）
DRAIN3_SIM_TH=0.6

# 更宽松（更多聚类）
DRAIN3_SIM_TH=0.3
```
