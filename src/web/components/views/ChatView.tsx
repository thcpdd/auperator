"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Plus, MessageSquare, MoreHorizontal, ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Markdown } from "@/components/ui/markdown";
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

  const { conversations, isLoading: isLoadingConversations } = useConversations();

  const { messages, threadId, isLoading, isLoadingHistory, sendMessage, handleEvent, clearMessages, loadConversation } =
    useChat({
      initialThreadId,
      onSendingComplete: () => setIsSending(false),
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

  const displayedConversations = showAllConversations
    ? conversations
    : conversations.slice(0, 5);

  return (
    <div className="flex h-full relative">
      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Messages Area */}
        <ScrollArea className="flex-1 p-4 scrollbar-thin" ref={scrollRef}>
          <div className="mx-auto max-w-3xl space-y-4 pb-4">
            {isLoadingHistory ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="flex gap-1 justify-center mb-4">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.2s]" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.4s]" />
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
                <Card className="max-w-[80%] px-4 py-3 bg-muted">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="flex gap-1">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50" />
                      <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.2s]" />
                      <div className="h-2 w-2 animate-bounce rounded-full bg-foreground/50 [animation-delay:-0.4s]" />
                    </div>
                    <span>Agent 正在思考...</span>
                  </div>
                </Card>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t bg-background p-4">
          <div className="mx-auto max-w-3xl">
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
                    <button
                      key={conv.thread_id}
                      onClick={() => {
                        if (conv.thread_id !== threadId) {
                          loadConversation(conv.thread_id);
                        }
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors text-left",
                        threadId === conv.thread_id
                          ? "bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                      )}
                    >
                      <MessageSquare className="h-4 w-4 shrink-0" />
                      <div className="min-w-0 flex-1 truncate">
                        <div className="truncate font-medium">
                          {conv.title}
                        </div>
                      </div>
                    </button>
                  ))}

                  {/* Show More/Less Button */}
                  {conversations.length > 5 && (
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
      <div className="flex justify-end">
        <Card className="max-w-[80%] bg-primary text-primary-foreground">
          <div className="px-4 py-3">
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
            <div className="mt-2 text-xs text-primary-foreground/70">
              {message.timestamp
                ? new Date(message.timestamp).toLocaleTimeString()
                : new Date().toLocaleTimeString()}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Agent message: full width, no bubble
  return (
    <div className="w-full">
      {isToolCall ? (
        <div className="border-l-4 border-l-blue-500 bg-muted/50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            🔧 工具调用
          </div>
          <div className="mt-1 text-xs font-mono bg-background rounded px-2 py-1">
            {message.toolName}
          </div>
          {message.toolArgs && Object.keys(message.toolArgs).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs cursor-pointer hover:underline">
                参数
              </summary>
              <pre className="mt-1 text-xs overflow-auto max-h-32 bg-background p-2 rounded">
                {JSON.stringify(message.toolArgs, null, 2)}
              </pre>
            </details>
          )}
          <div className="mt-2 text-xs text-muted-foreground">
            {message.timestamp
              ? new Date(message.timestamp).toLocaleTimeString()
              : new Date().toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <>
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <Markdown content={message.content} />
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            {message.timestamp
              ? new Date(message.timestamp).toLocaleTimeString()
              : new Date().toLocaleTimeString()}
          </div>
        </>
      )}
    </div>
  );
}
