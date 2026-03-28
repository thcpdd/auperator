"use client";

import { useState, useCallback, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { Message, Event, AgentEventData, UserEventData } from "@/lib/types";

interface UseChatOptions {
  initialThreadId?: string;
  onEvent?: (event: Event) => void;
}

export function useChat({ initialThreadId, onEvent }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string | undefined>(initialThreadId);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Load conversation history when initialThreadId changes
  useEffect(() => {
    if (initialThreadId && initialThreadId !== threadId) {
      loadConversation(initialThreadId);
    }
  }, [initialThreadId]);

  const loadConversation = useCallback(async (targetThreadId: string) => {
    setIsLoadingHistory(true);
    try {
      const history = await apiClient.getConversation(targetThreadId);

      // Convert backend messages to frontend format
      const formattedMessages: Message[] = history.messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp || new Date().toISOString(),
      }));

      setMessages(formattedMessages);
      setThreadId(targetThreadId);
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
      }
    },
    [threadId, isLoading]
  );

  const handleEvent = useCallback(
    (event: Event) => {
      onEvent?.(event);

      // Filter events for current thread
      if (threadId && event.thread_id !== threadId) {
        return;
      }

      // Handle different event types
      if (event.event_type === "AGENT") {
        const data = event.data as AgentEventData;

        if (data.message_type === "text" && data.content) {
          // Text response from agent
          const assistantMessage: Message = {
            role: "assistant",
            content: data.content,
            timestamp: event.timestamp,
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setIsLoading(false);
        } else if (data.message_type === "tool") {
          // Tool call - display it
          const toolMessage: Message = {
            role: "assistant",
            content: `🔧 调用工具: ${data.tool || "未知"}`,
            timestamp: event.timestamp,
            toolName: data.tool,
            toolArgs: data.args,
          };
          setMessages((prev) => [...prev, toolMessage]);
        }
      }
    },
    [threadId, onEvent]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setThreadId(undefined);
    setIsLoading(false);
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
