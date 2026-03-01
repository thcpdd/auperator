# Auperator 文档索引

## 快速开始

- [安装指南](installation.md) - 安装和配置 Auperator
- [快速开始](quickstart.md) - 快速上手使用

## 架构设计

- [系统架构](architecture.md) - 整体架构设计
- [日志采集器架构](collector/architecture.md) - 日志采集器设计

## 使用指南

### 日志采集器

- [采集器概述](collector/overview.md) - 功能概览
- [配置指南](collector/configuration.md) - 配置采集器
- [CLI 参考](collector/cli-reference.md) - 命令行接口

### 组件文档

- [Docker 日志源](collector/docker-source.md) - Docker 容器日志采集
- [日志适配器](collector/adapters.md) - 日志格式解析
- [Redis 消息队列](collector/redis-mq.md) - 基于 Redis Streams 的消息队列

## API 参考

- [Python API](api/python.md) - Python 模块 API
- [REST API](api/rest.md) - RESTful API (待实现)

## 开发指南

- [扩展日志源](development/extending-sources.md) - 自定义日志源
- [扩展适配器](development/extending-adapters.md) - 自定义日志适配器
- [贡献指南](development/contributing.md) - 代码贡献

## 运维指南

- [部署指南](deployment/deployment.md) - 生产环境部署
- [监控与告警](deployment/monitoring.md) - 监控配置
- [故障排查](deployment/troubleshooting.md) - 常见问题

---

## 文档目录结构

```
docs/
├── index.md                    # 本文档索引
├── installation.md             # 安装指南
├── quickstart.md               # 快速开始
├── architecture.md             # 系统架构
│
├── collector/                  # 日志采集器文档
│   ├── overview.md             # 概述
│   ├── architecture.md         # 架构设计
│   ├── configuration.md        # 配置指南
│   ├── cli-reference.md        # CLI 参考
│   ├── docker-source.md        # Docker 日志源
│   ├── adapters.md             # 日志适配器
│   └── redis-mq.md             # Redis 消息队列
│
├── api/                        # API 文档
│   ├── python.md               # Python API
│   └── rest.md                 # REST API
│
├── development/                # 开发指南
│   ├── extending-sources.md    # 扩展日志源
│   ├── extending-adapters.md   # 扩展适配器
│   └── contributing.md         # 贡献指南
│
└── deployment/                 # 运维指南
    ├── deployment.md           # 部署指南
    ├── monitoring.md           # 监控与告警
    └── troubleshooting.md      # 故障排查
```
