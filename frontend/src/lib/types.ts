export type ClientMessage =
  | { type: 'chat'; content: string }
  | { type: 'interrupt' }
  | { type: 'suggestion'; content: string }
  | { type: 'approve_plan' }
  | { type: 'update_plan'; plan: ExecutionPlan };

export type ServerMessage =
  | { type: 'connected'; session_id: string; workspace: string }
  | { type: 'initializing'; message: string }
  | { type: 'session_ready'; session_id: string; workspace: string }
  | { type: 'status'; status: 'planning' | 'thinking' | 'working' }
  | { type: 'plan_proposal'; plan: ExecutionPlan; message: string }
  | { type: 'plan_updated'; plan: ExecutionPlan }
  | { type: 'plan_started'; plan: ExecutionPlan }
  | { type: 'activity'; activity_type: ActivityType; tool: string; params?: Record<string, unknown>; result?: string; status: 'running' | 'completed' | 'failed'; file_created?: FileCreated | null; error?: string }
  | { type: 'final_answer'; content: string }
  | { type: 'error'; message: string }
  | { type: 'interrupted' }
  | { type: 'interrupting' }
  | { type: 'complete'; task: string }
  | { type: 'suggestion_received'; content: string; status?: string }
  | { type: 'suggestion_applied'; content: string }
  | { type: 'thought'; content: string }
  | { type: 'action'; tool: string; params: Record<string, unknown> }
  | { type: 'observation'; content: string; tool?: string; file_created?: FileCreated | null }
  | { type: 'processing'; task: string };

export type ActivityType = 'terminal' | 'file' | 'search' | 'document' | 'compute' | 'tool' | 'error';

export interface FileCreated {
  path: string;
  content: string;
}

export interface PlanTask {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface PlanPhase {
  id: string;
  name: string;
  tasks: PlanTask[];
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface ExecutionPlan {
  id: string;
  title: string;
  phases: PlanPhase[];
  status: 'pending' | 'approved' | 'running' | 'completed' | 'failed';
  current_phase: number;
  current_task: number;
}

export interface Activity {
  id: string;
  type: ActivityType;
  tool: string;
  params?: Record<string, unknown>;
  result?: string;
  status: 'running' | 'completed' | 'failed';
  error?: string;
  fileCreated?: FileCreated | null;
  timestamp: Date;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

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

export interface FileInfo {
  name: string;
  path: string;
  size: number;
  is_directory: boolean;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export type AgentStatus = 'idle' | 'planning' | 'thinking' | 'working';

export interface TerminalSession {
  id: string;
  command: string;
  output: string;
  timestamp: Date;
}
