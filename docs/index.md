# Auperator 文档索引

## 快速开始

- [README](../README.md) - 项目概述和快速开始
- [.env.example](../.env.example) - 环境变量配置示例

## 核心文档

- [CLAUDE.md](../CLAUDE.md) - Claude Code 开发指南
- [vector.yaml](../vector.yaml) - Vector 配置文件

## 架构

Auperator 使用 **Vector.dev** 进行日志采集和处理：

```
Log Source → Vector → Redis List → Consumer → Agent
```

### 核心组件

1. **Vector** - 日志采集、多行聚合、错误过滤
2. **Redis** - 消息队列（List 类型）
3. **Auperator Consumer** - 日志消费和格式转换
4. **Agent** - 智能分析和自动修复

## 使用指南

### CLI 命令

```bash
# 消费日志
auperator-collector consume -v

# 查看 List 信息
auperator-collector list-info
```

### 配置文件

- `.env` - 环境变量配置
- `vector.yaml` - Vector 日志处理配置

## 开发指南

### 扩展组件

- **自定义适配器**：继承 `BaseLogAdapter`
- **自定义处理器**：继承 `BaseLogHandler`

### 项目结构

```
src/auperator/
├── cli.py                    # 主命令行接口
├── config.py                 # 配置管理
└── collector/
    ├── cli.py                # 采集器 CLI
    ├── models.py             # 数据模型
    ├── adapters/             # 日志适配器
    ├── handlers/             # 日志处理器
    ├── sources/              # 日志源（保留用于扩展）
    └── vector_consumer.py    # Vector Redis 消费者
```

---

## 项目链接

- [GitHub 仓库](https://github.com/thcpdd/auperator)
- [问题反馈](https://github.com/thcpdd/auperator/issues)
