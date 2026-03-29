import {
  SendMessageRequest,
  SendMessageResponse,
  Conversation,
  ConversationHistory,
  RenameConversationRequest,
  DeleteConversationRequest,
} from "./types";

// Use Next.js proxy to avoid CORS
const API_BASE_URL = "/api";

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  // Chat API
  async sendMessage(request: SendMessageRequest): Promise<SendMessageResponse> {
    return this.request<SendMessageResponse>("/chat/messages", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>("/chat/conversations");
  }

  async getConversation(threadId: string): Promise<ConversationHistory> {
    return this.request<ConversationHistory>(`/chat/conversations/${threadId}`);
  }

  async renameConversation(request: RenameConversationRequest): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/chat/conversations/${request.thread_id}/title`, {
      method: "PATCH",
      body: JSON.stringify({ title: request.title }),
    });
  }

  async deleteConversation(request: DeleteConversationRequest): Promise<{ success: boolean }> {
    const url = `${this.baseUrl}/chat/conversations/${request.thread_id}`;
    const response = await fetch(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} - ${error}`);
    }

    // 204 No Content - return success without parsing JSON
    return { success: true };
  }

  // SSE Events (using Next.js API route to support streaming)
  connectEvents(
    threadId?: string,
    onEvent?: (data: unknown) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): () => void {
    let controller: AbortController | null = new AbortController();
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

    const connect = async () => {
      try {
        // Use Next.js API route instead of backend directly
        const url = `/api/events/web-ui`;
        console.log("[SSE] Connecting to", url, "with thread_id:", threadId);

        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
          },
          body: JSON.stringify({ thread_id: threadId || null }),
          signal: controller!.signal,
        });

        console.log("[SSE] Response status:", response.status, response.statusText);

        if (!response.ok) {
          throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
        }

        reader = response.body?.getReader() || null;
        if (!reader) {
          throw new Error("Response body is null");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        console.log("[SSE] Starting to read stream...");

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log("[SSE] Stream completed");
            onComplete?.();
            break;
          }

          // Decode and process data
          buffer += decoder.decode(value, { stream: true });

          // Split by SSE format (data: {json}\n\n)
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (data) {
                console.log("[SSE] Received data:", data);
                try {
                  const parsed = JSON.parse(data);
                  console.log("[SSE] Parsed event:", parsed);
                  onEvent?.(parsed);
                } catch (e) {
                  console.error("[SSE] Failed to parse SSE data:", e, "Raw data:", data);
                }
              }
            }
          }
        }
      } catch (error) {
        // Don't treat abort as an error (it's expected on cleanup)
        if (error instanceof Error && error.name === "AbortError") {
          console.log("[SSE] Connection aborted");
          return;
        }
        console.error("[SSE] Connection error:", error);
        onError?.(error as Error);
      }
    };

    // Start connection (don't await)
    connect().catch((error) => {
      onError?.(error);
    });

    // Return cleanup function
    return () => {
      if (controller) {
        try {
          controller.abort();
        } catch (e) {
          // Ignore abort errors - this is expected
          if (e instanceof Error && e.name !== "AbortError") {
            console.warn("[SSE] Error during cleanup:", e);
          }
        }
        controller = null;
      }
      if (reader) {
        reader.cancel().catch(() => {
          // Ignore cancel errors
        });
        reader = null;
      }
    };
  }
}

export const apiClient = new APIClient();
