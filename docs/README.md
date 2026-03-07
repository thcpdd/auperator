# Auperator 文档

欢迎使用 Auperator - 智能运维 Agent。

## 文档导航

### 核心文档

- [README](../README.md) - 项目概述和快速开始
- [CLAUDE.md](../CLAUDE.md) - Claude Code 开发指南

### 配置文件

- [.env.example](../.env.example) - 环境变量配置示例
- [vector.yaml](../vector.yaml) - Vector 日志处理配置

## 项目概述

Auperator 使用 **Vector.dev** 进行日志采集和处理，通过 Redis List 进行消息传递。

### 架构

```
Log Source → Vector → Redis List → Consumer → Agent
```

### 核心组件

1. **Vector** - 日志采集、多行聚合、错误过滤
2. **Redis** - 消息队列（List 类型）
3. **Auperator Consumer** - 日志消费和格式转换
4. **Agent** - 智能分析和自动修复

## 快速开始

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置环境变量
cp .env.example .env

# 3. 启动 Vector
vector --config vector.yaml

# 4. 消费日志
auperator-collector consume -v
```

## 项目链接

- [GitHub 仓库](https://github.com/thcpdd/auperator)
- [问题反馈](https://github.com/thcpdd/auperator/issues)
