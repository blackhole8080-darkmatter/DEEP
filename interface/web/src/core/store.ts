// Reactive application state, driven by the WS message stream.
// Built on @lit-labs/signals so Lit components re-render automatically via
// SignalWatcher — no manual subscription bookkeeping in components.
import { signal, computed } from "@lit-labs/signals";
import { socket } from "./ws";
import type { ServerMessage, ReasoningStep } from "./events";

// ── Chat ────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  id: number;
  role: "user" | "ai";
  text: string;
  streaming?: boolean;
  image?: string | null;
  model?: string;
  latency?: number;
  reasoning?: ReasoningStep["step"][]; // grounding trail, pinned on completion
}

let nextId = 1;

export const connection = signal<"connecting" | "open" | "closed">("closed");
export const messages = signal<ChatMessage[]>([]);
export const thinking = signal(false);
export const reasoningSteps = signal<ReasoningStep["step"][]>([]);
export const activeModel = signal("—");
export const lastTelemetry = signal("");

// Live proximity / RF / device telemetry feed (newest first, capped).
export interface FeedEvent { time: string; label: string; type: string; }
export const proximityFeed = signal<FeedEvent[]>([]);

const PROX_TYPES = new Set([
  "ap_left_proximity", "persistent_unknown_ap", "device_unusual_time",
  "ap_entered_proximity", "new_device_detected", "network_flow_recorded",
  "device_joined", "security_alert",
]);

export const isStreaming = computed(() =>
  messages.get().some((m) => m.streaming),
);

// ── Actions ────────────────────────────────────────────────────────────────
export function sendChat(text: string, image: string | null = null): void {
  if (!text.trim() && !image) return;
  messages.set([
    ...messages.get(),
    { id: nextId++, role: "user", text, image },
  ]);
  thinking.set(true);
  reasoningSteps.set([]);
  socket.send({ type: "chat", text, mode: "auto", image });
}

// ── WS → state reducer ─────────────────────────────────────────────────────
function currentStream(): ChatMessage | undefined {
  return messages.get().find((m) => m.streaming);
}

function patchStream(patch: Partial<ChatMessage>): void {
  messages.set(
    messages.get().map((m) => (m.streaming ? { ...m, ...patch } : m)),
  );
}

function reduce(msg: ServerMessage): void {
  switch (msg.type) {
    case "_socket_open":
      connection.set("open");
      break;
    case "_socket_close":
      connection.set("closed");
      break;
    case "thinking":
      thinking.set(true);
      break;
    case "response_start":
      thinking.set(true);
      break;
    case "token": {
      thinking.set(false);
      const tok = String((msg as { content?: string }).content ?? "");
      const cur = currentStream();
      if (cur) {
        messages.set(
          messages.get().map((m) =>
            m.streaming ? { ...m, text: m.text + tok } : m,
          ),
        );
      } else {
        messages.set([
          ...messages.get(),
          { id: nextId++, role: "ai", text: tok, streaming: true },
        ]);
      }
      break;
    }
    case "response_end": {
      thinking.set(false);
      const end = msg as { model?: string; latency?: number };
      if (end.model) activeModel.set(end.model);
      // Pin this turn's grounding trail onto the finished message, then clear
      // the live buffer for the next turn.
      const trail = reasoningSteps.get();
      patchStream({
        streaming: false,
        model: end.model,
        latency: end.latency,
        reasoning: trail.length ? trail : undefined,
      });
      reasoningSteps.set([]);
      break;
    }
    case "reasoning": {
      const step = (msg as ReasoningStep).step;
      if (step) reasoningSteps.set([...reasoningSteps.get(), step]);
      break;
    }
    case "error": {
      thinking.set(false);
      patchStream({ streaming: false });
      messages.set([
        ...messages.get(),
        { id: nextId++, role: "ai", text: `⚠ ${(msg as { message?: string }).message ?? "error"}` },
      ]);
      break;
    }
    default:
      // ambient telemetry (security_*, predictive_*, agent_*…)
      lastTelemetry.set(msg.type);
      if (PROX_TYPES.has(msg.type)) {
        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        const label = msg.type.replace(/_/g, " ");
        proximityFeed.set([{ time, label, type: msg.type }, ...proximityFeed.get()].slice(0, 40));
      }
  }
}

let wired = false;
export function initStore(): void {
  if (wired) return;
  wired = true;
  socket.on((m) => reduce(m as ServerMessage));
  socket.connect();
}
