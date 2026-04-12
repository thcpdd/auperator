# Auperator 文档

> 智能运维 Agent 系统文档

## 文档导航

### 快速入门

- [项目概述](../README.md) - 项目简介和核心功能
- [后端快速开始](backend/getting-started.md) - 后端环境配置和启动
- [前端快速开始](frontend/getting-started.md) - 前端开发环境

### 后端文档

- [架构设计](backend/architecture.md) - 后端系统架构详解
- [CLI 命令](backend/cli.md) - 命令行接口完整参考
- [API 参考](backend/api-reference.md) - REST API 端点详解
- [事件系统](backend/events.md) - Redis Streams 事件驱动架构
- [DeepAgents](backend/deepagents.md) - 多 Agent 协作架构
- [服务详解](backend/services/) - Drain3、记忆、Telegram 等服务

### 前端文档

- [架构设计](frontend/architecture.md) - Next.js Web UI 架构
- [组件文档](frontend/components.md) - React 组件库
- [页面路由](frontend/pages.md) - 页面和路由说明
- [API 客户端](frontend/api-client.md) - 前端 API 调用层

### 部署运维

- [Docker 部署](../deploy/README.md) - Docker Compose 部署指南
- [配置参考](../.env.example) - 环境变量配置

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.11+ | 主语言 |
| FastAPI | API 框架 |
| Redis | 消息队列 + 事件流 |
| Drain3 | 日志模板提取 |
| LangGraph | Agent 编排 |
| Daytona | 代码沙箱 |

### 前端

| 技术 | 用途 |
|------|------|
| Next.js 16 | React 框架 |
| TypeScript | 类型安全 |
| shadcn/ui | UI 组件库 |
| Tailwind CSS 4 | 样式方案 |
| SSE | 实时通信 |

## 项目链接

- [GitHub 仓库](https://github.com/thcpdd/auperator)
- [问题反馈](https://github.com/thcpdd/auperator/issues)
