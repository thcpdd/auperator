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

  // Rename conversation
  const renameConversation = useCallback(async (threadId: string, title: string) => {
    try {
      await apiClient.renameConversation({ thread_id: threadId, title });
      // Update local state
      setConversations(prev =>
        prev.map(conv =>
          conv.thread_id === threadId ? { ...conv, title } : conv
        )
      );
    } catch (err) {
      const error = err as Error;
      console.error("Failed to rename conversation:", error);
      throw error;
    }
  }, []);

  // Delete conversation
  const deleteConversation = useCallback(async (threadId: string) => {
    try {
      await apiClient.deleteConversation({ thread_id: threadId });
      // Remove from local state
      setConversations(prev => prev.filter(conv => conv.thread_id !== threadId));
    } catch (err) {
      const error = err as Error;
      console.error("Failed to delete conversation:", error);
      throw error;
    }
  }, []);

  return {
    conversations,
    isLoading,
    error,
    refetch: fetchConversations,
    renameConversation,
    deleteConversation,
  };
}
