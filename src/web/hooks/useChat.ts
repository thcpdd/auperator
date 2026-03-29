"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api";
import { Message, Event, AgentEventData, UserEventData, BackendMessage } from "@/lib/types";

interface UseChatOptions {
  initialThreadId?: string;
  onEvent?: (event: Event) => void;
  onSendingComplete?: () => void;
}

export function useChat({ initialThreadId, onEvent, onSendingComplete }: UseChatOptions = {}) {
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
        } else {
          role = "system";
        }

        return {
          role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          toolName: msg.tool_name,
          toolArgs: msg.tool_args,
        };
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

        if (data.message_type === "text" && data.content) {
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
