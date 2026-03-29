"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { Event } from "@/lib/types";

interface UseSSEOptions {
  threadId?: string;
  onEvent?: (event: Event) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

// Helper function for exponential backoff delay
function getRetryDelay(attemptNumber: number): number {
  // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
  return Math.min(1000 * Math.pow(2, attemptNumber), 30000);
}

export function useSSE({
  threadId,
  onEvent,
  onError,
  enabled = true,
}: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);
  const cleanupRef = useRef<(() => void) | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clear retry timeout
  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
  }, []);

  // Attempt to reconnect with exponential backoff
  const scheduleReconnect = useCallback(() => {
    clearRetryTimeout();

    const delay = getRetryDelay(retryCountRef.current);

    retryTimeoutRef.current = setTimeout(() => {
      retryCountRef.current++;
      // Force re-connect by incrementing trigger
      setReconnectTrigger(prev => prev + 1);
    }, delay);
  }, [clearRetryTimeout]);

  useEffect(() => {
    if (!enabled) {
      cleanupRef.current?.();
      cleanupRef.current = null;
      clearRetryTimeout();
      setIsConnected(false);
      retryCountRef.current = 0;
      return;
    }

    // Cleanup previous connection and retry
    cleanupRef.current?.();
    clearRetryTimeout();

    try {
      setIsConnected(true);
      setError(null);

      // Connect to SSE
      cleanupRef.current = apiClient.connectEvents(
        threadId,
        (data: unknown) => {
          // Parse event data
          const event = data as Event;

          // Check for error events from server
          if (event && typeof event === "object" && "error" in event) {
            const errorEvent = event as unknown as { error: boolean; message: string };
            if (errorEvent.message) {
              onError?.(new Error(errorEvent.message));
            }
            return;
          }

          // Reset retry count on successful event
          retryCountRef.current = 0;
          onEvent?.(event);
        },
        (error: Error) => {
          console.error("SSE connection error:", error);
          setError(error);
          setIsConnected(false);
          onError?.(error);

          // Schedule reconnect
          scheduleReconnect();
        },
        () => {
          // Connection completed (server closed connection)
          console.log("[SSE] Connection closed by server");
          setIsConnected(false);

          // Schedule reconnect
          scheduleReconnect();
        }
      );
    } catch (error) {
      const err = error as Error;
      console.error("Failed to connect to SSE:", err);
      setError(err);
      setIsConnected(false);
      onError?.(err);

      // Schedule reconnect
      scheduleReconnect();
    }

    // Cleanup on unmount or when threadId changes
    return () => {
      cleanupRef.current?.();
      cleanupRef.current = null;
      clearRetryTimeout();
      setIsConnected(false);
    };
  }, [threadId, onEvent, onError, enabled, scheduleReconnect, clearRetryTimeout, reconnectTrigger]);

  return { isConnected, error };
}
