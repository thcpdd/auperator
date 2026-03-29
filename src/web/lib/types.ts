// Chat API Types
export interface SendMessageRequest {
  message: string;
  thread_id?: string;
}

export interface SendMessageResponse {
  thread_id: string;
  is_new: boolean;
  status: string;
}

export interface Conversation {
  id?: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface RenameConversationRequest {
  thread_id: string;
  title: string;
}

export interface DeleteConversationRequest {
  thread_id: string;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
}

export interface ConversationHistory {
  thread_id: string;
  messages: BackendMessage[];
}

// Backend message format (from API)
export interface BackendMessage {
  type: "human" | "ai" | "system";
  content: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  timestamp?: string;
}

// Event Types
export type EventType = "user" | "agent";

export interface UserEventData {
  message_type: string;
  content: string;
}

export interface AgentEventData {
  message_type: "text" | "tool";
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
}

export interface Event {
  event_id: string;
  event_type: EventType;
  thread_id: string;
  timestamp: string;
  data: UserEventData | AgentEventData;
}
