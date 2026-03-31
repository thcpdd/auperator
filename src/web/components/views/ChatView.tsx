"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Plus, MessageSquare, MoreHorizontal, ChevronRight, ChevronLeft, Pencil, Trash2, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { Markdown } from "@/components/ui/markdown";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useChat } from "@/hooks/useChat";
import { useSSE } from "@/hooks/useSSE";
import { useConversations } from "@/hooks/useConversations";
import { Message as MessageType, Event } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatViewProps {
  initialThreadId?: string;
  onThreadIdChange?: (threadId: string | undefined) => void;
}

export function ChatView({ initialThreadId, onThreadIdChange }: ChatViewProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showAllConversations, setShowAllConversations] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const onEventRef = useRef<(event: Event) => void>(undefined);

  // Rename dialog state
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renamingThreadId, setRenamingThreadId] = useState<string | undefined>();
  const [newTitle, setNewTitle] = useState("");

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingThreadId, setDeletingThreadId] = useState<string | undefined>();

  const { conversations, isLoading: isLoadingConversations, renameConversation, deleteConversation, addConversation } = useConversations();

  // Handle new conversation creation
  const handleNewConversation = useCallback((threadId: string, title: string) => {
    const now = new Date().toISOString();
    addConversation({
      thread_id: threadId,
      title,
      created_at: now,
      updated_at: now,
    });
  }, [addConversation]);

  const { messages, threadId, isLoading, isLoadingHistory, sendMessage, handleEvent, clearMessages, loadConversation } =
    useChat({
      initialThreadId,
      onSendingComplete: () => setIsSending(false),
      onNewConversation: handleNewConversation,
    });

  // Store the latest handleEvent in ref
  onEventRef.current = handleEvent;

  // Stable callback for SSE events - won't change on re-renders
  const handleSSEEvent = useCallback((event: Event) => {
    onEventRef.current?.(event);
  }, []); // Empty dependency array - this function never changes

  // Notify parent when threadId changes (but only when it's set to a real value)
  useEffect(() => {
    if (threadId && threadId !== initialThreadId) {
      onThreadIdChange?.(threadId);
    }
  }, [threadId, initialThreadId, onThreadIdChange]);

  // Connect to SSE for current thread
  useSSE({
    threadId: threadId,
    onEvent: handleSSEEvent,
    enabled: !!threadId,
  });

  // Auto-scroll to bottom when new messages arrive or when history finishes loading
  useEffect(() => {
    const scrollToBottom = () => {
      // Find the actual scrollable viewport inside ScrollArea
      const viewport = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement;
      if (viewport) {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: 'smooth'
        });
      }
    };

    // Use setTimeout to ensure DOM has updated
    setTimeout(scrollToBottom, 100);
  }, [messages, isLoadingHistory]);

  const handleSend = async () => {
    if (!input.trim() || isLoading || isSending) return;

    const messageContent = input.trim();
    setInput("");
    setIsSending(true); // 开始发送，显示加载状态
    await sendMessage(messageContent);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    clearMessages();
    setInput("");
    // Notify parent to clear threadId from URL
    onThreadIdChange?.(undefined);
  };

  const handleRenameClick = (conv: typeof conversations[0]) => {
    setRenamingThreadId(conv.thread_id);
    setNewTitle(conv.title);
    setRenameDialogOpen(true);
  };

  const handleRenameConfirm = async () => {
    if (!renamingThreadId || !newTitle.trim()) return;

    try {
      await renameConversation(renamingThreadId, newTitle.trim());
      setRenameDialogOpen(false);
      setNewTitle("");
      setRenamingThreadId(undefined);
    } catch (error) {
      console.error("Failed to rename conversation:", error);
      alert("重命名失败，请重试");
    }
  };

  const handleDeleteClick = (threadId: string) => {
    setDeletingThreadId(threadId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingThreadId) return;

    try {
      await deleteConversation(deletingThreadId);
      setDeleteDialogOpen(false);
      setDeletingThreadId(undefined);

      // If deleted conversation was the current one, clear it
      if (deletingThreadId === threadId) {
        handleNewChat();
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
      alert("删除失败，请重试");
    }
  };

  // Show all conversations if less than 15, otherwise paginate
  const shouldPaginate = conversations.length > 15;
  const displayedConversations = showAllConversations || !shouldPaginate
    ? conversations
    : conversations.slice(0, 15);

  return (
    <div className="flex h-full relative">
      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Messages Area */}
        <ScrollArea className="flex-1 p-4 scrollbar-thin" ref={scrollRef}>
          <div className="mx-auto max-w-5xl space-y-4 pb-4">
            {isLoadingHistory ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="flex gap-1.5 justify-center mb-4">
                    <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary" />
                    <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary [animation-delay:0.2s]" />
                    <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary [animation-delay:0.4s]" />
                  </div>
                  <p className="text-sm text-muted-foreground">加载会话历史...</p>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <h2 className="text-2xl font-semibold text-foreground">
                    开始与 Auperator 对话
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    询问关于系统状态、日志分析或问题修复的问题
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <MessageBubble key={`${message.timestamp}-${index}`} message={message} />
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-3 px-4 py-3">
                  <div className="flex gap-1.5">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                    <div className="h-2 w-2 animate-pulse rounded-full bg-primary [animation-delay:0.2s]" />
                    <div className="h-2 w-2 animate-pulse rounded-full bg-primary [animation-delay:0.4s]" />
                  </div>
                  <span className="text-sm text-muted-foreground">Auperator 正在思考...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t bg-background p-4">
          <div className="mx-auto max-w-5xl">
            <div className="flex items-end gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
                className="min-h-[60px] max-h-[200px] resize-none"
                disabled={isLoading || isSending}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading || isSending}
                size="icon"
                className="h-[60px] w-[60px] shrink-0"
              >
                {isSending ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent"></div>
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Agent 可以访问系统日志、容器状态和自动化工具来帮助解决问题
            </p>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Conversations */}
      <div
        className={cn(
          "border-l bg-background flex flex-col transition-all duration-300",
          isSidebarOpen ? "w-72" : "w-0"
        )}
      >
        {/* Header with Toggle Button */}
        <div className="p-4 border-b flex items-center gap-2">
          <Button
            variant="default"
            className="flex-1 gap-2"
            onClick={handleNewChat}
          >
            <Plus className="h-4 w-4" />
            新对话
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className={cn(
              "transition-transform",
              !isSidebarOpen && "rotate-180"
            )}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Conversations List */}
        {isSidebarOpen && (
          <ScrollArea className="flex-1 px-3 py-2">
          <div className="space-y-2">
            {conversations.length > 0 && (
              <>
                <div className="px-3 py-2 text-xs font-medium text-muted-foreground">
                  历史会话 ({conversations.length})
                </div>
                <div className="space-y-1">
                  {displayedConversations.map((conv) => (
                    <div
                      key={conv.thread_id}
                      className={cn(
                        "flex items-center gap-1 rounded-lg px-3 py-2 text-sm transition-colors group relative",
                        threadId === conv.thread_id
                          ? "bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                      )}
                    >
                      <button
                        onClick={() => {
                          if (conv.thread_id !== threadId) {
                            loadConversation(conv.thread_id);
                          }
                        }}
                        className="flex min-w-0 items-center gap-2 text-left"
                        style={{ maxWidth: "calc(100% - 36px)" }}
                      >
                        <MessageSquare className="h-4 w-4 shrink-0" />
                        <span className="min-w-0 flex-1 truncate font-medium">
                          {conv.title}
                        </span>
                      </button>
                      <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleRenameClick(conv)}>
                              <Pencil className="h-4 w-4 mr-2" />
                              重命名
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleDeleteClick(conv.thread_id)}
                              className="text-destructive focus:text-destructive"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  ))}

                  {/* Show More/Less Button */}
                  {shouldPaginate && (
                    <button
                      onClick={() => setShowAllConversations(!showAllConversations)}
                      className="flex w-full items-center justify-center gap-1 px-3 py-1.5 text-xs text-muted-foreground hover:text-accent-foreground"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                      {showAllConversations
                        ? "收起"
                        : `查看全部 (${conversations.length})`}
                    </button>
                  )}
                </div>
              </>
            )}

            {isLoadingConversations && (
              <div className="px-3 py-2 text-xs text-muted-foreground">
                加载中...
              </div>
            )}

            {!isLoadingConversations && conversations.length === 0 && (
              <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                还没有历史会话
              </div>
            )}
          </div>
        </ScrollArea>
        )}
      </div>

      {/* Floating Toggle Button (when sidebar is closed) */}
      {!isSidebarOpen && (
        <Button
          variant="default"
          size="icon"
          onClick={() => setIsSidebarOpen(true)}
          className="absolute top-4 right-4 z-10 h-8 w-8"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      )}

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重命名对话</DialogTitle>
            <DialogDescription>
              为这个对话输入一个新的标题
            </DialogDescription>
          </DialogHeader>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="输入新的对话标题"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleRenameConfirm();
              }
            }}
            autoFocus
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleRenameConfirm} disabled={!newTitle.trim()}>
              确定
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除对话</DialogTitle>
            <DialogDescription>
              确定要删除这个对话吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} className="text-white hover:text-white">
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface MessageBubbleProps {
  message: MessageType;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isToolCall = !!message.toolName;

  // User message: bubble style, right aligned
  if (isUser) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Card className="max-w-[80%] bg-primary text-primary-foreground">
          <div className="px-4 py-3">
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          </div>
        </Card>
      </div>
    );
  }

  // Agent message: full width, no bubble
  return (
    <div className="flex flex-col gap-1">
      {isToolCall ? (
        <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
          <CardContent className="p-4">
            {/* Header */}
            <div className="flex items-center gap-2 mb-3">
              {message.isToolComplete ? (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                  <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                </div>
              ) : (
                <div className="flex h-6 w-6 items-center justify-center">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
                </div>
              )}
              <div className="flex-1">
                <div className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  {message.isToolComplete ? "工具调用完成" : "正在执行工具"}
                </div>
                <code className="text-xs text-blue-700 dark:text-blue-300 font-mono">
                  {message.toolName}
                </code>
              </div>
            </div>

            {/* Args */}
            {message.toolArgs && Object.keys(message.toolArgs).length > 0 && (
              <details className="group/args">
                <summary className="flex items-center gap-1 text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground list-none mb-2">
                  <ChevronRight className="h-3 w-3 transition-transform group-open/args:rotate-90" />
                  调用参数
                </summary>
                <div className="ml-4 mt-1">
                  <pre className="text-xs bg-background border rounded-md p-2 overflow-auto max-h-32">
                    {JSON.stringify(message.toolArgs, null, 2)}
                  </pre>
                </div>
              </details>
            )}

            {/* Output */}
            {message.isToolComplete && message.toolOutput && (
              <details className="group/output" open>
                <summary className="flex items-center gap-1 text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground list-none mb-2">
                  <ChevronRight className="h-3 w-3 transition-transform group-open/output:rotate-90" />
                  执行结果
                </summary>
                <div className="ml-4 mt-1">
                  <div className="bg-background border rounded-md p-3 max-h-96 overflow-auto">
                    <pre className="text-xs whitespace-pre-wrap font-mono">
                      {message.toolOutput}
                    </pre>
                  </div>
                </div>
              </details>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <Markdown content={message.content} />
        </div>
      )}
    </div>
  );
}
