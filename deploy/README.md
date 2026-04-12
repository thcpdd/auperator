# Auperator 部署文档

## 项目介绍

Auperator 是一个智能运维助手，用于监控和管理容器化应用。它结合了 AI 技术，能够自动分析日志、处理事件，并提供智能运维建议。

## 项目结构

```
auperator/
├── src/             # 源代码目录
│   ├── auperator/   # 后端代码
│   │   ├── collector/    # 日志收集模块
│   │   ├── database/     # 数据库模块
│   │   ├── deepagents/   # AI 代理模块
│   │   ├── events/       # 事件系统
│   │   ├── routes/       # API 路由
│   │   ├── schemas/      # 数据模型
│   │   ├── services/     # 服务模块
│   │   ├── utils/        # 工具函数
│   │   └── server.py     # 服务器入口
│   └── web/         # 前端代码
│       ├── app/          # Next.js 应用
│       ├── components/   # 前端组件
│       ├── hooks/        # React 钩子
│       └── lib/          # 前端库函数
├── deploy/          # 部署文件目录
│   ├── docker-compose.yml    # Docker 编排文件
│   ├── Dockerfile.api        # API 服务 Dockerfile
│   ├── Dockerfile.web        # Web 服务 Dockerfile
│   └── nginx.conf            # Nginx 配置
├── .env.example     # 环境变量示例
├── vector.yaml      # Vector 配置文件
└── pyproject.toml   # Python 项目配置
```

## 环境要求

- **Docker**：版本 20.10 或更高
- **Docker Compose**：版本 1.29 或更高
- **Git**：用于克隆仓库
- **内存**：至少 4GB（推荐 8GB 以上）
- **磁盘空间**：至少 20GB
- **网络**：能够访问 Docker Hub 和必要的 API 服务

## 部署步骤

### 1. 克隆仓库

```bash
git clone https://github.com/thcpdd/auperator.git
cd auperator
```

### 2. 配置环境变量

**创建环境变量文件：**

```bash
cp .env.example .env
```

**关键配置项说明：**

| 配置项                           | 说明                     | 必须设置      |
| ----------------------------- | ---------------------- | --------- |
| QDRANT\_\_SERVICE\_\_API\_KEY | Qdrant 向量数据库 API 密钥    | ✅ 必须设置    |
| OPENAI\_API\_KEY              | OpenAI API 密钥，用于 AI 功能 | ✅ 必须设置    |
| OPENAI\_BASE\_URL             | OpenAI API 基础 URL      | 推荐设置      |
| OPENAI\_MODEL                 | 使用的 AI 模型              | 推荐设置      |
| EMBEDDING\_API\_KEY           | 嵌入模型 API 密钥            | 推荐设置      |
| EMBEDDING\_MODEL              | 嵌入模型名称                 | 推荐设置      |
| EMBEDDING\_VECTOR\_SIZE       | 嵌入向量大小                 | 必须与模型匹配   |
| REDIS\_HOST                   | Redis 主机地址             | 容器部署时无需修改 |
| REDIS\_PORT                   | Redis 端口               | 容器部署时无需修改 |

**示例配置：**

```env
# Qdrant 配置
QDRANT__SERVICE__API_KEY=your_qdrant_api_key

# OpenAI 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=glm-4.7

# 嵌入配置
EMBEDDING_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_VECTOR_SIZE=1536
```

### 3. 进入部署目录

```bash
cd deploy
```

### 4. 拉取 Vector 镜像

Vector 是日志收集服务，需要先拉取镜像：

```bash
docker compose pull vector
```

### 5. 启动核心服务

启动除 Vector 以外的所有服务：

```bash
docker compose up -d --build
```

### 6. 验证核心服务启动状态

```bash
docker compose ps
```

确保所有服务状态为 `Up`：

- auperator-redis
- auperator-qdrant
- auperator-api
- auperator-web

### 7. 启动 Vector 服务

有两种方式启动 Vector 服务：

#### 方式一：通过 Web UI 自动配置

1. 访问 Web UI（默认地址：<http://localhost:3000）>
2. 登录系统（如果需要）
3. 使用 Agent 编写 Vector 配置
4. 让 Agent 启动 Vector 容器

#### 方式二：手动配置

1. 确保 `vector.yaml` 配置文件存在且格式正确
2. 启动 Vector 容器：
   ```bash
   docker compose --profile vector up -d
   ```

## 服务架构详解

### 核心服务

| 服务名称   | 容器名称             | 端口   | 功能描述                 |
| ------ | ---------------- | ---- | -------------------- |
| Redis  | auperator-redis  | 6379 | 缓存和消息队列，用于日志处理和事件传递  |
| Qdrant | auperator-qdrant | 6333 | 向量数据库，用于存储和检索向量数据    |
| API    | auperator-api    | 7000 | 核心业务逻辑，处理 HTTP 请求和事件 |
| Web    | auperator-web    | 3000 | 前端界面，提供用户交互          |
| Vector | auperator-vector | -    | 日志收集服务，可选            |

### 数据流程

1. **日志收集**：Vector 收集容器日志并发送到 Redis
2. **日志处理**：API 服务从 Redis 消费日志并处理
3. **事件触发**：处理后的日志生成事件
4. **AI 分析**：Agent Worker 分析事件并生成智能建议
5. **数据存储**：向量数据存储在 Qdrant，其他数据存储在 SQLite

## 访问地址

| 服务         | 地址                                | 说明        |
| ---------- | --------------------------------- | --------- |
| Web UI     | <http://localhost:3000>           | 前端管理界面    |
| API 接口     | <http://localhost:7000>           | 后端 API 服务 |
| API 健康检查   | <http://localhost:7000/health>    | 服务健康状态    |
| Qdrant 控制台 | <http://localhost:6333/dashboard> | 向量数据库管理界面 |

## 详细配置说明

### 环境变量文件

`../.env` 文件包含所有必要的配置参数，主要分为以下几个部分：

1. **API 配置**：API 服务的基本设置
2. **OpenAI 配置**：AI 模型和 API 密钥
3. **嵌入配置**：向量嵌入模型设置
4. **Redis 配置**：Redis 连接参数
5. **Qdrant 配置**：向量数据库设置
6. **其他服务配置**：如 Telegram、Daytona 等

### Docker Compose 配置

`docker-compose.yml` 文件定义了所有服务的部署配置：

- **网络配置**：使用 `auperator-network` 桥接网络
- **卷配置**：持久化存储 Redis 和 Qdrant 数据
- **依赖关系**：定义服务启动顺序和健康检查
- **资源限制**：可根据服务器配置调整

## 服务管理

### 启动服务

- **启动核心服务**：
  ```bash
  docker compose up -d --build
  ```
- **启动包含 Vector 的所有服务**：
  ```bash
  docker compose --profile vector up -d
  ```
- **仅启动特定服务**：
  ```bash
  docker compose up -d redis qdrant
  ```

### 停止服务

- **停止所有服务**：
  ```bash
  docker compose down
  ```
- **停止特定服务**：
  ```bash
  docker compose stop api web
  ```

### 查看服务状态

```bash
docker compose ps
```

### 查看服务日志

- **查看所有服务日志**：
  ```bash
  docker compose logs
  ```
- **查看特定服务日志**：
  ```bash
  docker compose logs -f api
  ```
- **查看最新日志**：
  ```bash
  docker compose logs -f --tail=100 api
  ```

## 日志管理

### Vector 配置

Vector 服务使用 `../vector.yaml` 配置文件，主要功能：

- 收集 Docker 容器日志
- 解析和处理日志格式
- 将日志发送到 Redis 消息队列

### 日志处理流程

1. Vector 收集容器日志
2. 日志被发送到 Redis List
3. API 服务的 `VectorRedisConsumer` 消费日志
4. 日志经过处理后生成事件
5. 事件被发送到事件中心
6. Agent Worker 处理事件并生成智能建议

## 常见问题排查

### 服务启动失败

1. **检查 Docker 状态**：
   ```bash
   sudo systemctl status docker
   ```
2. **检查环境变量**：
   ```bash
   cat .env | grep -E "QDRANT__SERVICE__API_KEY|OPENAI_API_KEY"
   ```
3. **查看容器日志**：
   ```bash
   docker compose logs -f api
   ```

### Qdrant 连接问题

- **检查 Qdrant 状态**：
  ```bash
  docker compose logs -f qdrant
  ```
- **验证 Qdrant API 密钥**：
  确保 `QDRANT__SERVICE__API_KEY` 在 `.env` 文件中正确设置
- **检查网络连接**：
  ```bash
  docker exec -it auperator-api curl http://qdrant:6333/health
  ```

### API 服务问题

- **检查依赖服务**：
  ```bash
  docker compose ps redis qdrant
  ```
- **检查 OpenAI API 配置**：
  确保 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 正确设置
- **查看 API 服务日志**：
  ```bash
  docker compose logs -f api
  ```

### Vector 服务问题

- **检查 vector.yaml 配置**：
  ```bash
  cat ../vector.yaml
  ```
- **检查 Docker 权限**：
  确保容器有访问 `/var/run/docker.sock` 的权限
- **查看 Vector 日志**：
  ```bash
  docker compose logs -f vector
  ```

## 性能优化

### 服务器配置

- **CPU**：至少 2 核，推荐 4 核以上
- **内存**：至少 4GB，推荐 8GB 以上
- **磁盘**：SSD 存储，至少 20GB 空间

### 服务配置优化

1. **API 服务**：
   - 根据 CPU 核心数调整 `API_WORKERS` 参数
   - 生产环境设置 `API_RELOAD=false`
2. **Redis**：
   - 调整内存限制：在 `docker-compose.yml` 中添加 `command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru`
3. **Qdrant**：
   - 为 Qdrant 分配足够的内存：在 `docker-compose.yml` 中添加 `mem_limit: 2g`
4. **Vector**：
   - 根据日志量调整缓冲区大小

## 安全建议

### 生产环境配置

1. **HTTPS**：
   - 使用反向代理（如 Nginx）配置 HTTPS
   - 配置 SSL 证书
2. **网络安全**：
   - 限制容器网络访问
   - 使用 Docker 网络隔离
   - 配置防火墙规则
3. **密钥管理**：
   - 使用环境变量管理敏感信息
   - 定期更新 API 密钥
   - 避免在代码中硬编码密钥
4. **访问控制**：
   - 为 Web UI 添加认证
   - 限制 API 访问范围
   - 使用 API 密钥保护接口

## 版本更新

### 代码更新

1. **拉取最新代码**：
   ```bash
   git pull
   ```
2. **更新依赖**：
   ```bash
   cd src/web && npm install
   ```
3. **重新构建并启动服务**：
   ```bash
   cd ../../deploy
   docker compose up -d --build
   ```

### 数据迁移

- **SQLite 数据库**：数据会自动迁移
- **Qdrant 数据**：向量数据会保留在持久卷中
- **Redis 数据**：缓存数据会保留在持久卷中

## 监控与维护

### 健康检查

- **API 健康检查**：<http://localhost:7000/health>
- **服务状态监控**：
  ```bash
  docker compose ps
  ```

### 日志监控

- **查看系统日志**：
  ```bash
  docker compose logs -f
  ```
- **设置日志轮转**：在 `docker-compose.yml` 中配置日志驱动

### 定期维护

1. **备份数据**：
   - 备份 SQLite 数据库
   - 备份 Qdrant 数据卷
2. **清理资源**：
   ```bash
   docker system prune -f
   ```
3. **更新 Docker 镜像**：
   ```bash
   docker compose pull
   docker compose up -d --build
   ```

## 开发环境配置

### 本地开发

1. **安装依赖**：
   ```bash
   # 后端依赖
   pip install -e .

   # 前端依赖
   cd src/web && npm install
   ```
2. **启动开发服务**：
   ```bash
   # 启动后端服务
   python -m auperator.server

   # 启动前端服务
   cd src/web && npm run dev
   ```

### 调试模式

- **API 调试**：设置 `API_RELOAD=true` 和 `LOG_LEVEL=DEBUG`
- **前端调试**：使用 `npm run dev` 启动开发服务器

