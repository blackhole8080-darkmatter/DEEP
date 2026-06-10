// Typed WS message protocol — mirrors what interface/server.py actually emits
// over /ws/deep. One source of truth for the frontend; extend here first.

/** Client → server */
export interface ChatSend {
  type: "chat";
  text: string;
  mode?: "auto";
  image?: string | null; // data URL → routed to local vision
}
export interface Ping { type: "ping"; }

export type ClientMessage = ChatSend | Ping;

/** Server → client */
export interface ResponseStart { type: "response_start"; }
export interface Token { type: "token"; content: string; }
export interface ResponseEnd {
  type: "response_end";
  model?: string;
  latency?: number;
  tokens?: number;
}
export interface Thinking { type: "thinking"; ai?: string; mode?: string; }
export interface ReasoningStep {
  type: "reasoning";
  step: {
    t: "model" | "thinking" | "tool_call" | "tool_result" | "route" | "symbolic" | "oracle" | "final";
    [k: string]: unknown;
  };
}
export interface ToolCall { type: "tool_call"; tool: string; args?: Record<string, unknown>; call_id?: string; }
export interface ToolResult { type: "tool_result"; call_id?: string; }
export interface ErrorMsg { type: "error"; message: string; }
export interface Pong { type: "pong"; time: string; }
export interface SecurityAlert { type: "security_alert"; payload: Record<string, unknown>; }
export interface SecuritySnapshot { type: "security_snapshot"; payload: Record<string, unknown>; }
export interface AgentEvent { type: "agent_event"; event_type: string; payload: Record<string, unknown>; }
export interface PredictiveEvent { type: "predictive_event"; [k: string]: unknown; }

export type ServerMessage =
  | ResponseStart
  | Token
  | ResponseEnd
  | Thinking
  | ReasoningStep
  | ToolCall
  | ToolResult
  | ErrorMsg
  | Pong
  | SecurityAlert
  | SecuritySnapshot
  | AgentEvent
  | PredictiveEvent
  | { type: string; [k: string]: unknown }; // ambient telemetry passthrough
