"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { Conversation } from "@/lib/types";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Fetch conversations list
  const fetchConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getConversations();
      setConversations(data);
    } catch (err) {
      const error = err as Error;
      console.error("Failed to fetch conversations:", error);
      setError(error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return {
    conversations,
    isLoading,
    error,
    refetch: fetchConversations,
  };
}
