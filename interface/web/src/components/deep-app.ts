// <deep-app> — the application shell.
// Phase 2: state now lives in the signal store (core/store.ts); this component
// is a pure view over it via SignalWatcher. Includes a minimal chat probe to
// prove the full reactive pipeline (send → stream → render) before Phase 3
// builds the real chat surface.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { initStore, thinking, isStreaming, connection } from "../core/store";
import { socket } from "../core/ws";
import type { BrainState, BrainStatus } from "./deep-cortex-bg";
import "../core/commands";
import "./command-palette";
import "./deep-boot";
import "./toast-stack";
import "./voice/voice-status-orb";
import "./gpu/shader-bg";
import "./console/deep-console";
import type { CommandPalette } from "./command-palette";

// Heavy secondary views are code-split: their bundles load on first visit.
const lazyView: Record<string, () => Promise<unknown>> = {
  gallery: () => import("./gallery"),
  science: () => import("./science/science-view"),
  ops: () => import("./ops/ops-view"),
  agents: () => import("./ops/agents-view"),
  network: () => import("./ops/network-view"),
  audit: () => import("./ops/audit-view"),
  missions: () => import("./ops/missions-view"),
  memory: () => import("./memory/memory-graph"),
  system: () => import("./system/system-monitor"),
  connections: () => import("./network/connection-map"),
  stack: () => import("./system/stack-view"),
  calc: () => import("./science/calc-view"),
  projects: () => import("./knowledge/projects-view"),
  research: () => import("./knowledge/research-view"),
  finance: () => import("./finance/finance-view"),
  email: () => import("./email/email-view"),
};

@customElement("deep-app")
export class DeepApp extends SignalWatcher(LitElement) {
  @state() private _hudActive = true;

  // routes fully delegated to HUD widgets
  private onGlobalKey = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      (this.renderRoot.querySelector("command-palette") as CommandPalette | null)?.toggle();
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "h") {
      e.preventDefault();
      this._hudActive = !this._hudActive;
    }
  };

  // Transient subsystem activity for the living-brain background: maps a node
  // key → {status, expiry}. Fed by ambient WS telemetry (agents/security/…) and
  // a light /api/status poll, so the brain lights up reactively without polling
  // any heavy endpoint.
  private activity = new Map<string, { status: BrainStatus; until: number }>();
  private statusTimer = 0;

  private bumpNode(key: string, status: BrainStatus, ttl = 3500): void {
    this.activity.set(key, { status, until: Date.now() + ttl });
    this.requestUpdate();
  }

  // Map an ambient event type → which brain node it should light, and how.
  private onTelemetry = (m: { type?: string }): void => {
    const ty = m.type ?? "";
    if (ty.startsWith("agent_")) this.bumpNode("agents", "active");
    else if (ty === "security_alert") this.bumpNode("security", "warning", 6000);
    else if (ty.includes("proximity") || ty.includes("device") || ty.includes("unknown_ap"))
      this.bumpNode("security", "indexing");
    else if (ty.startsWith("predictive_") || ty.startsWith("proactive_")) this.bumpNode("predictive", "thinking");
    else if (ty.startsWith("knowledge_") || ty.startsWith("entity_")) this.bumpNode("memory", "indexing");
    else if (ty.startsWith("network_") || ty === "device_joined") this.bumpNode("network", "active");
    else if (ty.startsWith("research_")) this.bumpNode("research", "active");
  };

  connectedCallback(): void {
    super.connectedCallback();
    initStore();
    socket.on(this.onTelemetry as (m: unknown) => void);
    this.pollStatus();
    this.statusTimer = window.setInterval(() => this.pollStatus(), 15000);
    void lazyView; // lazy views available for HUD to trigger
    window.addEventListener("keydown", this.onGlobalKey);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.statusTimer);
    window.removeEventListener("keydown", this.onGlobalKey);
  }

  private async pollStatus(): Promise<void> {
    try {
      const r = await fetch("/api/status");
      const d = await r.json();
      // System node: green when brain ok; the cheap status endpoint, polled slow.
      this.bumpNode("system", d?.brain === "ok" ? "idle" : "warning", 16000);
    } catch { this.bumpNode("system", "warning", 16000); }
  }

  // Assemble the per-subsystem brain state from live signals + ambient activity.
  private brainState(): BrainState {
    const now = Date.now();
    const state: BrainState = {};
    for (const [k, v] of this.activity) if (v.until > now) state[k] = v.status;
    // Chat / Reasoning / Voice are driven directly by the reactive store + orb.
    const orb = this.getOrbState();
    if (isStreaming.get()) state.chat = "speaking";
    else if (thinking.get()) state.chat = "active";
    if (thinking.get()) state.reasoning = "thinking";
    if (orb === "listening") state.voice = "active";
    else if (orb === "speaking") state.voice = "speaking";
    if (connection.get() !== "open") state.system = "warning";
    return state;
  }

  // Collapse the per-subsystem brain state into a single (activity, status) pair
  // for the cinematic shader field: activity = share of active subsystems,
  // status = the most salient active one (warning wins, then output, etc.).
  private fieldState(bs: BrainState): { activity: number; status: string } {
    const PRIORITY: BrainStatus[] = ["warning", "speaking", "thinking", "indexing", "active"];
    let active = 0;
    let status = "idle";
    const present = new Set(Object.values(bs));
    for (const s of PRIORITY) { if (present.has(s)) { status = s; break; } }
    for (const v of Object.values(bs)) if (v && v !== "idle") active++;
    return { activity: Math.min(1, active / 4), status };
  }

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      background: #06080c;
    }
  `;

  private getOrbState(): "idle" | "listening" | "thinking" | "speaking" {
    if (isStreaming.get()) return "speaking";
    if (thinking.get()) return "thinking";
    return "idle";
  }

  render() {
    const fs = this.fieldState(this.brainState());
    return html`
      <!-- Cinematic background layer (disabled for now) -->

      <!-- Boot splash -->
      <deep-boot></deep-boot>

      <!-- Toast notifications -->
      <toast-stack></toast-stack>

      <!-- Command palette (Cmd+K) -->
      <command-palette></command-palette>

      <!-- Voice status indicator -->
      <voice-status-orb></voice-status-orb>

      <!-- THE CONSOLE — neural sphere + elements panel + chat dock. The primary
           interface; tools are added steadily via TOOL_REGISTRY. -->
      <deep-console .activity=${fs.activity} .status=${fs.status}></deep-console>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "deep-app": DeepApp;
  }
}
