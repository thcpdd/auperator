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
  toolOutput?: string; // Tool execution result
  isToolComplete?: boolean; // Whether tool execution is complete
}

export interface ConversationHistory {
  thread_id: string;
  messages: BackendMessage[];
}

// Backend message format (from API)
export interface BackendMessage {
  type: "human" | "ai" | "system" | "tool";
  content: string;
  name?: string; // Tool name (for tool messages)
  args?: Record<string, unknown>; // Tool args (for tool messages)
  timestamp?: string;
}

// Event Types
export type EventType = "user" | "agent" | "tool";

export interface UserEventData {
  message_type: string;
  content: string;
}

export interface AgentEventData {
  message_type: "text";
  content: string;
}

export interface ToolEventData {
  message_type: "tool";
  tool: string;
  args?: Record<string, unknown>;
  content?: string; // Tool result (empty when calling, has content when done)
}

export interface Event {
  event_id: string;
  event_type: EventType;
  thread_id: string;
  timestamp: string;
  data: UserEventData | AgentEventData | ToolEventData;
}
