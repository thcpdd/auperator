"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api";
import { Message, Event, AgentEventData, ToolEventData } from "@/lib/types";

interface UseChatOptions {
  initialThreadId?: string;
  onEvent?: (event: Event) => void;
  onSendingComplete?: () => void;
  onNewConversation?: (threadId: string, title: string) => void;
}

export function useChat({ initialThreadId, onEvent, onSendingComplete, onNewConversation }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string | undefined>(initialThreadId);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const loadedThreadIdRef = useRef<string | undefined>(undefined);
  const onSendingCompleteRef = useRef<(() => void) | undefined>(onSendingComplete);

  // Update ref when callback changes
  useEffect(() => {
    onSendingCompleteRef.current = onSendingComplete;
  }, [onSendingComplete]);

  // Load conversation history on mount or when initialThreadId changes
  useEffect(() => {
    // Only load if initialThreadId is different from the last loaded one
    if (initialThreadId && initialThreadId !== loadedThreadIdRef.current) {
      // Mark as loading immediately to prevent duplicate calls
      loadedThreadIdRef.current = initialThreadId;
      loadConversation(initialThreadId);
    }
  }, [initialThreadId]);

  const loadConversation = useCallback(async (targetThreadId: string) => {
    setIsLoadingHistory(true);
    try {
      const history = await apiClient.getConversation(targetThreadId);

      // Convert backend messages to frontend format
      const formattedMessages: Message[] = history.messages.map((msg) => {
        // Convert backend type to frontend role
        let role: "user" | "assistant" | "system";
        if (msg.type === "human") {
          role = "user";
        } else if (msg.type === "ai") {
          role = "assistant";
        } else if (msg.type === "tool") {
          role = "assistant"; // Tool messages are from assistant
        } else {
          role = "system";
        }

        // Handle tool messages
        const isToolMessage = msg.type === "tool" && !!msg.name;
        const message: Message = {
          role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          toolName: msg.name,
          toolArgs: msg.args,
        };

        // For tool messages from history, set appropriate flags
        if (isToolMessage) {
          message.isToolComplete = true;
          message.toolOutput = msg.content || "";
          message.content = `🔧 工具调用: ${msg.name || "未知"}`;
        }

        return message;
      });

      setMessages(formattedMessages);
      setThreadId(targetThreadId);
      loadedThreadIdRef.current = targetThreadId; // Mark as loaded
    } catch (error) {
      console.error("Failed to load conversation:", error);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      // Add user message immediately
      const userMessage: Message = {
        role: "user",
        content: content.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const response = await apiClient.sendMessage({
          message: content.trim(),
          thread_id: threadId,
        });

        // Update thread ID
        if (response.is_new || !threadId) {
          setThreadId(response.thread_id);
          loadedThreadIdRef.current = response.thread_id;

          // Notify parent component about new conversation
          if (response.is_new && onNewConversation) {
            onNewConversation(response.thread_id, response.title || "新对话");
          }
        }

        // Note: Agent response will come through SSE events
      } catch (error) {
        console.error("Failed to send message:", error);
        // Add error message
        const errorMessage: Message = {
          role: "assistant",
          content: `Error: ${error instanceof Error ? error.message : "Failed to send message"}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsLoading(false);
        onSendingCompleteRef.current?.();
      }
    },
    [threadId, isLoading]
  );

  const handleEvent = useCallback(
    (event: Event) => {
      // Filter events for current thread
      if (threadId && event.thread_id !== threadId) {
        return;
      }

      // Handle different event types
      if (event.event_type === "agent") {
        const data = event.data as AgentEventData;

        if (data.content) {
          // Check if this is a Done message
          if (data.content === "[Done]") {
            setIsLoading(false);
            onSendingCompleteRef.current?.();
            return;
          }

          // Text response from agent
          const assistantMessage: Message = {
            role: "assistant",
            content: data.content,
            timestamp: event.timestamp,
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setIsLoading(false);
        }
      } else if (event.event_type === "tool") {
        const data = event.data as ToolEventData;

        // Check if this is a tool call result (has content) or initial call (no content)
        if (data.content && data.content.trim()) {
          // Tool result - find and update the pending tool message by event_id
          setMessages((prev) => {
            const updated = [...prev];
            // Find the message with matching event_id
            const index = updated.findIndex((msg) => msg.eventId === event.event_id);
            if (index !== -1) {
              // Update the message with result
              updated[index] = {
                ...updated[index],
                content: `🔧 工具调用: ${data.tool || "未知"}`,
                toolOutput: data.content,
                isToolComplete: true,
              };
            }
            return updated;
          });
        } else {
          // Initial tool call - add a pending message with event_id
          const toolMessage: Message = {
            role: "assistant",
            content: `⏳ 调用工具: ${data.tool || "未知"}...`,
            timestamp: event.timestamp,
            toolName: data.tool,
            toolArgs: data.args,
            isToolComplete: false,
            eventId: event.event_id, // Store event_id to match with result
          };
          setMessages((prev) => [...prev, toolMessage]);
        }
      } else if (event.event_type === "user") {
        // Skip user events - already added by sendMessage
      }
    },
    [threadId, onEvent]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setThreadId(undefined);
    setIsLoading(false);
    loadedThreadIdRef.current = undefined;
  }, []);

  return {
    messages,
    threadId,
    isLoading,
    isLoadingHistory,
    sendMessage,
    handleEvent,
    clearMessages,
    loadConversation,
  };
}
