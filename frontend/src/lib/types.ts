// WebSocket message types

// Client to Server
export type ClientMessage =
  | { type: 'chat'; content: string }
  | { type: 'interrupt' }
  | { type: 'suggestion'; content: string };

// Server to Client
export type ServerMessage =
  | { type: 'connected'; session_id: string; workspace: string }
  | { type: 'initializing'; message: string }
  | { type: 'session_ready'; session_id: string; workspace: string }
  | { type: 'processing'; task: string }
  | { type: 'thought'; content: string }
  | { type: 'action'; tool: string; params: Record<string, unknown> }
  | { type: 'observation'; content: string; tool?: string; file_created?: FileCreated | null }
  | { type: 'final_answer'; content: string }
  | { type: 'error'; message: string }
  | { type: 'interrupted' }
  | { type: 'interrupting' }
  | { type: 'complete'; task: string }
  | { type: 'suggestion_received'; content: string; status?: string }
  | { type: 'suggestion_applied'; content: string }
  | { type: 'recovery'; content: string }
  | { type: 'plan_requested'; task: string; message: string };

export interface FileCreated {
  path: string;
  content: string;
}

// Message display types
export interface Message {
  id: string;
  type: 'user' | 'thought' | 'action' | 'observation' | 'final_answer' | 'error' | 'system';
  content: string;
  timestamp: Date;
  tool?: string;
  params?: Record<string, unknown>;
  fileCreated?: FileCreated | null;
}

// Session types
export interface Session {
  session_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  file_count: number;
}

export interface SessionDetail extends Session {
  messages: SessionMessage[];
  created_files: string[];
  protected_files: string[];
}

export interface SessionMessage {
  role: string;
  content: string;
  timestamp: string;
}

// File types
export interface FileInfo {
  name: string;
  path: string;
  size: number;
  is_directory: boolean;
}

// Connection state
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

// Agent state
export interface AgentState {
  isProcessing: boolean;
  currentTask: string | null;
  currentThought: string | null;
  currentTool: string | null;
}
