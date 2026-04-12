# Auperator 文档

智能运维 Agent 系统文档中心。

## 文档结构

```
docs/
├── index.md              # 文档首页（本文档）
│
├── backend/              # 后端文档
│   ├── getting-started.md  # 快速开始
│   ├── architecture.md     # 架构设计
│   ├── api-reference.md    # API 参考
│   ├── cli.md              # CLI 命令
│   ├── deepagents.md       # DeepAgents 架构
│   ├── events.md           # 事件系统
│   └── services/          # 服务详解
│       ├── README.md
│       ├── drain3.md      # Drain3 日志处理
│       ├── memory.md       # Qdrant 记忆系统
│       └── telegram.md     # Telegram 通知
│
├── frontend/             # 前端文档
│   ├── getting-started.md  # 快速开始
│   ├── architecture.md     # 架构设计
│   ├── components.md       # 组件文档
│   ├── pages.md            # 页面路由
│   └── api-client.md       # API 客户端
│
└── README.md             # 文档索引
```

## 快速导航

### 后端

| 模块 | 文档 | 说明 |
|------|------|------|
| 安装配置 | [快速开始](backend/getting-started.md) | 环境搭建和启动 |
| 系统架构 | [架构设计](backend/architecture.md) | 组件和数据流 |
| API 接口 | [API 参考](backend/api-reference.md) | 所有 REST 端点 |
| 命令行 | [CLI 参考](backend/cli.md) | 所有 CLI 命令 |
| Agent 核心 | [DeepAgents](backend/deepagents.md) | 多 Agent 协作 |
| 通信机制 | [事件系统](backend/events.md) | Redis Streams |
| 日志去重 | [Drain3](backend/services/drain3.md) | 日志模板提取 |
| 向量记忆 | [记忆服务](backend/services/memory.md) | Qdrant 集成 |
| 移动通知 | [Telegram](backend/services/telegram.md) | Bot 推送 |

### 前端

| 模块 | 文档 | 说明 |
|------|------|------|
| 安装配置 | [快速开始](frontend/getting-started.md) | 环境搭建 |
| 技术栈 | [架构设计](frontend/architecture.md) | 组件和架构 |
| 组件库 | [组件文档](frontend/components.md) | 所有 UI 组件 |
| 页面路由 | [页面路由](frontend/pages.md) | 页面说明 |
| API 调用 | [API 客户端](frontend/api-client.md) | 前端 API 层 |

## 相关文档

- [项目 README](../README.md) - 项目概述
- [CLAUDE.md](../CLAUDE.md) - 开发指南
- [.env.example](../.env.example) - 配置示例
- [deploy/README.md](../deploy/README.md) - Docker 部署
