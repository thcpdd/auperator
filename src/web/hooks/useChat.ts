"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api";
import { Message, Event, AgentEventData, ToolEventData, QueuedEventData } from "@/lib/types";

// Queued message interface
export interface QueuedMessage {
  queuePosition: number;
  queueSize: number;
  message: string;
  userMessage?: string;
}

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
  const [queuedMessages, setQueuedMessages] = useState<QueuedMessage[]>([]);
  const loadedThreadIdRef = useRef<string | undefined>(undefined);
  const onSendingCompleteRef = useRef<(() => void) | undefined>(onSendingComplete);
  const hasClearedSendingRef = useRef(false);
  const processedDoneEventRef = useRef<string | undefined>(undefined); // Track processed [Done] events

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
      if (!content.trim()) return;

      // Reset sending complete flag for new message
      hasClearedSendingRef.current = false;

      // If agent is currently running and we have a threadId, check queue status first
      if (isLoading && threadId) {
        try {
          const queueStatus = await apiClient.getQueueStatus(threadId);
          if (queueStatus !== null) {
            // Queue exists - there is a task running or queued
            const queuedMsg: QueuedMessage = {
              queuePosition: queueStatus.queue_size,
              queueSize: queueStatus.queue_size + 1,
              message: queueStatus.queue_size > 0
                ? `您的消息已加入处理队列，前方还有 ${queueStatus.queue_size} 条消息`
                : "消息正在处理中",
              userMessage: content.trim(),
            };
            setQueuedMessages((prev) => [...prev, queuedMsg]);

            // Send to backend (backend will queue it)
            await apiClient.sendMessage({
              message: content.trim(),
              thread_id: threadId,
            });
            return; // Don't add to messages yet, it's queued
          }
          // queueStatus is null - no task running, send the message
        } catch (error) {
          console.warn("Failed to check queue status, sending anyway:", error);
        }
      }

      // Add user message immediately (only when not queuing)
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
            // Prevent duplicate processing of the same [Done] event
            if (processedDoneEventRef.current === event.event_id) {
              return;
            }
            processedDoneEventRef.current = event.event_id;

            // Process the queue when a task completes
            setQueuedMessages((prev) => {
              if (prev.length > 0) {
                const firstQueued = prev[0];
                const remainingQueue = prev.slice(1);

                // Add the first queued message to chat in the next render cycle
                // We'll use setTimeout to avoid state update during state update
                if (firstQueued.userMessage) {
                  setTimeout(() => {
                    setMessages((msgPrev) => {
                      // Check if this message already exists (avoid duplicates)
                      const exists = msgPrev.some(
                        (msg) => msg.role === "user" && msg.content === firstQueued.userMessage
                      );
                      if (!exists) {
                        const userMessage: Message = {
                          role: "user",
                          content: firstQueued.userMessage as string,
                          timestamp: new Date().toISOString(),
                        };
                        return [...msgPrev, userMessage];
                      }
                      return msgPrev;
                    });
                  }, 0);
                }

                // If no more queued messages, set loading to false
                if (remainingQueue.length === 0) {
                  setTimeout(() => setIsLoading(false), 0);
                }

                return remainingQueue;
              }

              // No queued messages, set loading to false
              setIsLoading(false);
              return prev;
            });

            onSendingCompleteRef.current?.();
            return;
          }

          // First agent response - clear sending state (only once)
          if (!hasClearedSendingRef.current) {
            hasClearedSendingRef.current = true;
            onSendingCompleteRef.current?.();
          }

          // Set loading to true if not already (for non-user-initiated conversations)
          setIsLoading(true);

          // Text response from agent - keep loading true until Done
          const assistantMessage: Message = {
            role: "assistant",
            content: data.content,
            timestamp: event.timestamp,
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
      } else if (event.event_type === "tool") {
        const data = event.data as ToolEventData;

        // First tool call - clear sending state (only once)
        if (!hasClearedSendingRef.current) {
          hasClearedSendingRef.current = true;
          onSendingCompleteRef.current?.();
        }

        // Set loading to true if not already (for non-user-initiated conversations)
        setIsLoading(true);

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
      } else if (event.event_type === "queued") {
        // Handle queued message event
        const data = event.data as QueuedEventData;
        const queuedMsg: QueuedMessage = {
          queuePosition: data.queue_position,
          queueSize: data.queue_size,
          message: data.message,
          userMessage: data.user_message,
        };

        setQueuedMessages((prev) => {
          // Check if this message is already in the queue (by userMessage)
          const exists = prev.some((msg) => msg.userMessage === data.user_message);
          if (!exists && data.user_message) {
            return [...prev, queuedMsg];
          }
          return prev;
        });

        // Set loading to true if not already
        setIsLoading(true);
      }
    },
    [threadId, onEvent]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setThreadId(undefined);
    setIsLoading(false);
    setQueuedMessages([]);
    loadedThreadIdRef.current = undefined;
  }, []);

  const stopGenerating = useCallback(() => {
    setIsLoading(false);
    setQueuedMessages([]); // Clear queue when stopping
    onSendingCompleteRef.current?.();
  }, []);

  return {
    messages,
    threadId,
    isLoading,
    isLoadingHistory,
    queuedMessages,
    sendMessage,
    handleEvent,
    clearMessages,
    loadConversation,
    stopGenerating,
  };
}
