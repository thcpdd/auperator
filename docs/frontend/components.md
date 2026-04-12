# 组件文档

## 组件结构

```
components/
├── layout/           # 布局组件
│   ├── Header.tsx
│   ├── Sidebar.tsx
│   └── MainLayout.tsx
├── ui/               # UI 基础组件
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   ├── input.tsx
│   ├── markdown.tsx
│   ├── scroll-area.tsx
│   ├── select.tsx
│   ├── separator.tsx
│   └── textarea.tsx
└── views/             # 视图组件
    ├── ChatView.tsx
    ├── ConfigView.tsx
    └── StatusView.tsx
```

## 布局组件

### MainLayout

主布局容器，包含 Header、Sidebar 和内容区。

```tsx
import { MainLayout } from '@/components/layout/MainLayout'

<MainLayout>
  <YourContent />
</MainLayout>
```

### Header

顶部导航栏。

```tsx
import { Header } from '@/components/layout/Header'

<Header
  title="页面标题"
  actions={<Button>操作</Button>}
/>
```

### Sidebar

侧边栏，显示对话列表。

```tsx
import { Sidebar } from '@/components/layout/Sidebar'

<Sidebar
  conversations={conversations}
  activeId={currentId}
  onSelect={handleSelect}
  onNew={handleNew}
/>
```

## UI 组件

### Markdown

Markdown 渲染组件，支持代码高亮。

```tsx
import { Markdown } from '@/components/ui/markdown'

<Markdown content="# Hello World" />

<Markdown content={`
\`\`\`javascript
console.log('Hello')
\`\`\`
`} />
```

**功能**：
- GitHub Flavored Markdown
- 代码语法高亮（highlight.js）
- 链接自动识别
- 表格支持

### ScrollArea

带自定义滚动条的容器。

```tsx
import { ScrollArea } from '@/components/ui/scroll-area'

<ScrollArea className="h-[500px]">
  <div>长内容...</div>
</ScrollArea>
```

### Button

按钮组件，支持多种变体。

```tsx
import { Button } from '@/components/ui/button'

// 变体
<Button variant="default">Default</Button>
<Button variant="destructive">Destructive</Button>
<Button variant="outline">Outline</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// 尺寸
<Button size="default">Default</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon">Icon</Button>
```

### Card

卡片容器。

```tsx
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/card'

<Card>
  <CardHeader>
    <h3>标题</h3>
  </CardHeader>
  <CardContent>
    <p>内容</p>
  </CardContent>
  <CardFooter>
    <Button>操作</Button>
  </CardFooter>
</Card>
```

### Input / Textarea

表单输入组件。

```tsx
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

<Input placeholder="输入内容" />
<Textarea placeholder="多行输入" rows={4} />
```

### Select

下拉选择组件。

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

<Select onValueChange={handleChange}>
  <SelectTrigger>
    <SelectValue placeholder="选择..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="1">选项 1</SelectItem>
    <SelectItem value="2">选项 2</SelectItem>
  </SelectContent>
</Select>
```

### Dialog

对话框组件。

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>标题</DialogTitle>
    </DialogHeader>
    <p>对话框内容</p>
  </DialogContent>
</Dialog>
```

### DropdownMenu

下拉菜单。

```tsx
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

<DropdownMenu>
  <DropdownMenuTrigger>触发器</DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem>菜单项 1</DropdownMenuItem>
    <DropdownMenuItem>菜单项 2</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

## 视图组件

### ChatView

聊天主视图。

```tsx
import { ChatView } from '@/components/views/ChatView'

const { messages, sendMessage, isLoading } = useChat(conversationId)

<ChatView
  messages={messages}
  onSend={sendMessage}
  isLoading={isLoading}
/>
```

**功能**：
- 消息列表展示
- 用户/Agent 消息区分
- Markdown 渲染
- 流式响应显示
- 加载状态指示

### ConfigView

配置管理视图。

```tsx
import { ConfigView } from '@/components/views/ConfigView'

<ConfigView
  config={currentConfig}
  onSave={handleSave}
/>
```

**功能**：
- 配置表单
- 实时验证
- 保存/重置

### StatusView

系统状态视图。

```tsx
import { StatusView } from '@/components/views/StatusView'

<StatusView />
```

**功能**：
- Redis 连接状态
- Qdrant 连接状态
- Agent 状态
- 实时更新

## 自定义 Hooks

### useChat

```typescript
const {
  messages: Message[],      // 消息列表
  sendMessage: (content: string) => Promise<void>,
  isLoading: boolean,        // 是否加载中
  error: Error | null,      // 错误信息
} = useChat(conversationId?: string)
```

### useConversations

```typescript
const {
  conversations: Conversation[],  // 对话列表
  create: (title?: string) => Promise<Conversation>,
  rename: (id: string, title: string) => Promise<void>,
  remove: (id: string) => Promise<void>,
  select: (id: string) => void,
  currentId: string | null,
} = useConversations()
```

### useSSE

```typescript
const {
  events: Event[],          // 事件列表
  connect: () => void,       // 建立连接
  disconnect: () => void,    // 断开连接
  isConnected: boolean,      // 连接状态
} = useSSE({
  endpoint: string,
  threadId?: string,
})
```
