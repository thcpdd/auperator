"use client";

import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { Event } from "@/lib/types";

interface UseSSEOptions {
  threadId?: string;
  onEvent?: (event: Event) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

export function useSSE({
  threadId,
  onEvent,
  onError,
  enabled = true,
}: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!enabled) {
      cleanupRef.current?.();
      cleanupRef.current = null;
      setIsConnected(false);
      return;
    }

    // Cleanup previous connection
    cleanupRef.current?.();

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
            const errorEvent = event as { error: boolean; message: string };
            onError?.(new Error(errorEvent.message));
            return;
          }

          onEvent?.(event);
        },
        (error: Error) => {
          console.error("SSE connection error:", error);
          setError(error);
          setIsConnected(false);
          onError?.(error);
        },
        () => {
          // Connection completed
          setIsConnected(false);
        }
      );
    } catch (error) {
      const err = error as Error;
      console.error("Failed to connect to SSE:", err);
      setError(err);
      setIsConnected(false);
      onError?.(err);
    }

    // Cleanup on unmount or when threadId changes
    return () => {
      cleanupRef.current?.();
      cleanupRef.current = null;
      setIsConnected(false);
    };
  }, [threadId, onEvent, onError, enabled]);

  return { isConnected, error };
}
