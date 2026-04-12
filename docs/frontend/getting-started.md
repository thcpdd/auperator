# 前端快速开始

## 环境要求

- Node.js 18+
- npm / pnpm / yarn

## 安装

```bash
cd src/web

# 使用 npm
npm install

# 或使用 pnpm（推荐）
pnpm install
```

## 开发

```bash
# 开发模式
npm run dev

# 生产构建
npm run build

# 生产预览
npm run start
```

访问 <http://localhost:3000>

## 项目结构

```
src/web/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 首页
│   ├── layout.tsx         # 根布局
│   ├── globals.css        # 全局样式
│   ├── chat/page.tsx     # 聊天页面
│   ├── config/page.tsx   # 配置页面
│   ├── logs/page.tsx    # 日志页面
│   ├── status/page.tsx  # 状态页面
│   └── api/              # API 路由
│       └── events/       # SSE 端点
├── components/
│   ├── layout/           # 布局组件
│   ├── ui/               # UI 基础组件
│   └── views/            # 视图组件
├── hooks/                # 自定义 Hooks
├── lib/                  # 工具库
├── package.json
├── next.config.ts
└── tailwind.config.ts
```

## 配置文件

### 环境变量

```bash
# src/web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:7000
```

### API 代理配置

`next.config.ts` 已配置 API 代理：

```typescript
// 所有 /api/* 请求代理到后端
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:7000/:path*',
    },
  ];
}
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 开发模式 |
| `npm run build` | 生产构建 |
| `npm run start` | 生产预览 |
| `npm run lint` | 代码检查 |

## 依赖说明

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| next | 16.2.1 | React 框架 |
| react | 19.2.4 | UI 库 |
| @base-ui/react | 1.3.0 | Base UI 组件 |
| @radix-ui/* | - | Radix UI 组件 |

### 样式

| 依赖 | 用途 |
|------|------|
| tailwindcss | CSS 框架 |
| shadcn | 组件库 |
| lucide-react | 图标库 |

### 特殊

| 依赖 | 用途 |
|------|------|
| react-markdown | Markdown 渲染 |
| highlight.js | 代码高亮 |

## 下一步

- [架构设计](architecture.md) - 了解前端架构
- [组件文档](components.md) - 组件使用指南
- [页面路由](pages.md) - 页面和路由说明
