import {
  SendMessageRequest,
  SendMessageResponse,
  Conversation,
  ConversationHistory,
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

  // SSE Events (using fetch for POST support)
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
        const response = await fetch(`${this.baseUrl}/events/web-ui`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
          },
          body: JSON.stringify({ thread_id: threadId || null }),
          signal: controller!.signal,
        });

        if (!response.ok) {
          throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
        }

        reader = response.body?.getReader() || null;
        if (!reader) {
          throw new Error("Response body is null");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
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
                try {
                  const parsed = JSON.parse(data);
                  onEvent?.(parsed);
                } catch (e) {
                  console.error("Failed to parse SSE data:", e, "Raw data:", data);
                }
              }
            }
          }
        }
      } catch (error) {
        // Don't treat abort as an error (it's expected on cleanup)
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }
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
        controller.abort();
        controller = null;
      }
      if (reader) {
        reader.cancel().catch(console.error);
        reader = null;
      }
    };
  }
}

export const apiClient = new APIClient();
