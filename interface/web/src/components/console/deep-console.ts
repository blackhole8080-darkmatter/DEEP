// <deep-console> — DEEP's primary interface shell. Layout:
//   • stage   : the live visualiser (threat globe or matrix waterfall)
//   • bottom  : a glassmorphic tool dock (all tools, added via TOOL_REGISTRY)
//               and a chat dock to talk to DEEP, stacked above it
//   • overlay : a focus surface — selecting a tool opens its full view here,
//               dimming the sphere; Esc / close returns to the sphere.
//
// Replaces the sprawling JARVIS HUD with one coherent surface. Reuses the signal
// store (sendChat sends the correct `text` field — fixes the broken HUD chat bar).
import { LitElement, html, css, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { messages, thinking, sendChat } from "../../core/store";
import { toolById } from "../../core/tool-registry";
import { skin, cycleSkin, type Skin } from "../../core/theme";
import "./matrix-waterfall";
import "./threat-globe";
import "./tool-dock";
import "../chat/chat-message";

type Status = "idle" | "active" | "speaking" | "thinking" | "warning" | "indexing";

@customElement("deep-console")
export class DeepConsole extends SignalWatcher(LitElement) {
  @property({ attribute: false }) activity = 0;
  @property({ attribute: false }) status: Status = "idle";

  @state() private visualizerMode: "matrix" | "globe" = "globe";
  @state() private _openTool = "";
  @state() private _toolView: TemplateResult | null = null;
  @state() private _loadingTool = false;
  @state() private _draft = "";

  private _audioAnalyser: { destroy(): void } | null = null;
  private _audioRaf = 0;

  static styles = css`
    :host {
      position: absolute; inset: 0; z-index: 20;
      pointer-events: none;
      font-family: var(--ds-font-sans, system-ui);
      color: rgba(220,240,255,0.92);
    }

    .stage { position: absolute; inset: 0; overflow: hidden; }
    /* Holographic aurora ambient — soft, slow-drifting iridescent glows */
    .stage::before {
      content: "";
      position: absolute; inset: -12%;
      z-index: 0; pointer-events: none;
      background:
        radial-gradient(38% 48% at 30% 34%, rgba(var(--ds-periwinkle-rgb), 0.12), transparent 70%),
        radial-gradient(44% 54% at 72% 60%, rgba(var(--ds-periwinkle-rgb), 0.08), transparent 70%),
        radial-gradient(40% 46% at 54% 80%, rgba(var(--ds-periwinkle-rgb), 0.05), transparent 70%),
        radial-gradient(36% 42% at 80% 22%, rgba(var(--ds-periwinkle-rgb), 0.1), transparent 70%);
      filter: blur(44px) saturate(140%);
      animation: aurora-drift 26s ease-in-out infinite alternate;
    }
    @keyframes aurora-drift {
      0%   { transform: translate3d(-2%, -1%, 0) scale(1);    opacity: 0.85; }
      50%  { transform: translate3d(2%, 1.5%, 0) scale(1.06); opacity: 1; }
      100% { transform: translate3d(-1%, 2%, 0) scale(1.02);  opacity: 0.9; }
    }
    @media (prefers-reduced-motion: reduce) { .stage::before { animation: none; } }
    matrix-waterfall, threat-globe { position: absolute; inset: 0; z-index: 1; transition: opacity 0.5s ease, filter 0.5s ease; }
    :host([data-focus]) matrix-waterfall, :host([data-focus]) threat-globe { opacity: 0.18; filter: blur(3px); }

    .viz-switcher {
      position: absolute; top: 24px; right: 24px; z-index: 10;
      display: flex; gap: 8px; pointer-events: auto;
    }
    .viz-btn {
      background: rgba(0,255,255,0.05); border: 1px solid rgba(0,255,255,0.2);
      color: rgba(0,255,255,0.6); padding: 4px 10px; border-radius: 4px;
      font-family: var(--ds-font-mono, monospace); font-size: 0.7rem; cursor: pointer;
      text-transform: uppercase; transition: all 0.2s ease;
    }
    .viz-btn.active, .viz-btn:hover {
      background: rgba(0,255,255,0.2); color: #fff; box-shadow: 0 0 10px rgba(0,255,255,0.4); border-color: rgba(0,255,255,0.5);
    }

    /* Skin switcher — was hidden behind Ctrl+K only; surfaced here so the
       skin system (calm/neon/etis/hacker, see design/themes.css) is actually
       discoverable. Same pill language as .viz-btn, opposite corner. */
    .skin-switcher {
      position: absolute; top: 24px; left: 24px; z-index: 10;
      pointer-events: auto;
    }
    .skin-btn {
      display: flex; align-items: center; gap: 6px;
      background: var(--ds-glass-thin, rgba(0,255,255,0.05));
      border: 1px solid var(--ds-border-accent, rgba(0,255,255,0.2));
      color: var(--ds-text-soft, rgba(0,255,255,0.6));
      padding: 4px 10px; border-radius: 4px;
      font-family: var(--ds-font-mono, monospace); font-size: 0.7rem; cursor: pointer;
      text-transform: uppercase; letter-spacing: 0.06em;
      transition: all 0.2s ease;
    }
    .skin-btn:hover {
      background: var(--ds-surface-3); color: var(--ds-text);
      box-shadow: var(--ds-glow); border-color: var(--ds-border-accent);
    }
    .skin-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--ds-accent);
      box-shadow: 0 0 6px var(--ds-accent), 0 0 12px var(--ds-accent);
      animation: skin-dot-pulse 2.4s ease-in-out infinite;
    }
    /* Defined locally (not just in design/animations.css): @keyframes don't
       resolve across the shadow-DOM boundary, so a component can only use
       an animation name if it's declared in its own stylesheet. */
    @keyframes skin-dot-pulse {
      0%, 100% { box-shadow: 0 0 6px var(--ds-accent), 0 0 12px var(--ds-accent); }
      50%      { box-shadow: 0 0 10px var(--ds-accent), 0 0 20px var(--ds-accent); }
    }
    @media (prefers-reduced-motion: reduce) { .skin-dot { animation: none; } }

    /* Glassmorphic tool dock — floating, bottom-centered */
    tool-dock {
      position: absolute;
      left: 0; right: 0; bottom: 22px;
      display: flex; justify-content: center;
      z-index: 8; pointer-events: none;
    }

    /* Focus surface — full tool view over the stage */
    .focus {
      /* bottom clears the chat dock (bottom:104px) + tool dock beneath it;
         without this the last rows of every tool sat behind them. */
      position: absolute; top: 24px; left: 24px; bottom: 188px; right: 24px; z-index: 5;
      pointer-events: auto;
      background: rgba(6,11,20,0.82);
      backdrop-filter: blur(20px) saturate(140%);
      -webkit-backdrop-filter: blur(20px) saturate(140%);
      border: 1px solid rgba(0,229,255,0.22);
      border-radius: 16px;
      box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(0,229,255,0.08);
      display: flex; flex-direction: column; overflow: hidden;
      animation: focus-in 0.32s cubic-bezier(0.16,1,0.3,1);
    }
    @keyframes focus-in { from { opacity: 0; transform: translateY(14px) scale(0.985); } to { opacity: 1; transform: none; } }
    .focus-head {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 18px; border-bottom: 1px solid rgba(0,229,255,0.14);
      font-family: var(--ds-font-mono, monospace);
      letter-spacing: 0.14em; text-transform: uppercase; font-size: 0.78rem;
      color: rgba(0,229,255,0.9);
    }
    .focus-head .spacer { flex: 1; }
    .focus-close {
      pointer-events: auto; cursor: pointer; font: inherit; font-size: 0.7rem;
      color: rgba(220,240,255,0.8); background: rgba(0,229,255,0.08);
      border: 1px solid rgba(0,229,255,0.25); border-radius: 8px; padding: 5px 12px;
      transition: all 0.15s ease;
    }
    .focus-close:hover { background: rgba(255,80,80,0.12); border-color: rgba(255,80,80,0.5); color: #fff; }
    .focus-body { flex: 1; overflow: auto; }
    .focus-loading { display: grid; place-items: center; height: 100%; color: rgba(0,229,255,0.6); letter-spacing: 0.2em; }

    /* Chat dock — centered, stacked above the tool dock */
    .dock {
      position: absolute;
      left: 0; right: 0; bottom: 104px;
      max-width: 680px; margin: 0 auto;
      padding: 0 20px;
      z-index: 6; pointer-events: none;
    }
    .transcript {
      pointer-events: auto;
      max-height: 34vh; overflow-y: auto; margin-bottom: 10px;
      display: flex; flex-direction: column; gap: 8px;
      mask-image: linear-gradient(to top, black 80%, transparent);
    }
    .msg { font-size: 0.9rem; line-height: 1.45; padding: 8px 14px; border-radius: 12px; max-width: 88%; white-space: pre-wrap; font-family: var(--ds-font-sans); }
    .msg.user { align-self: flex-end; background: var(--ds-surface-1); border: 1px solid var(--ds-border-strong); color: var(--ds-text); }
    .msg.ai { align-self: flex-start; background: var(--ds-surface-2); border: 1px solid var(--ds-border-accent); box-shadow: var(--ds-glow); color: var(--ds-text); }
    .composer {
      position: relative; isolation: isolate;
      pointer-events: auto;
      display: flex; align-items: center; gap: 10px;
      background: var(--ds-surface-1);
      backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%);
      border: 1px solid transparent; border-radius: 999px;
      padding: 6px 6px 6px 18px;
      box-shadow: 0 0 44px rgba(0,0,0,0.5), var(--ds-glow);
    }
    /* Animated iridescent gradient border on the composer */
    .composer::before {
      content: ""; position: absolute; inset: 0; border-radius: inherit;
      padding: 1.4px;
      background: linear-gradient(120deg, var(--ds-accent), transparent, var(--ds-success), transparent, var(--ds-accent));
      background-size: 320% 320%;
      animation: irid-border 9s ease infinite;
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      pointer-events: none; z-index: -1; opacity: 0.8;
    }
    @keyframes irid-border {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .composer input {
      flex: 1; background: none; border: none; outline: none;
      color: var(--ds-text); font: inherit; font-size: 0.95rem; font-family: var(--ds-font-sans);
    }
    .composer input::placeholder { color: var(--ds-text-muted); }
    .send {
      cursor: pointer; border: none; border-radius: 999px; width: 38px; height: 38px;
      background: var(--ds-surface-2); border: 1px solid var(--ds-border-accent); color: var(--ds-accent);
      background-size: 200% 200%; animation: irid-icon 8s ease infinite;
      font-size: 1.1rem; display: grid; place-items: center;
      transition: transform 0.15s ease, box-shadow 0.15s ease, color 0.15s ease, background 0.15s ease;
    }
    .send:hover { transform: scale(1.08); box-shadow: var(--ds-glow-strong); color: var(--ds-bg); background: var(--ds-accent); }
    @keyframes irid-icon {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .thinking {
      font-size: 0.72rem; letter-spacing: 0.15em; margin: 0 0 6px 16px;
      background: linear-gradient(90deg, var(--ds-accent), var(--ds-success));
      background-size: 200% 200%;
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent; color: transparent;
      animation: irid-icon 6s ease infinite;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKey);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._onKey);
    this._stopAudio();
  }

  private _stopAudio(): void {
    cancelAnimationFrame(this._audioRaf);
    this._audioAnalyser?.destroy();
    this._audioAnalyser = null;
  }

  private _onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" && this._openTool) this._closeTool();
  };

  private async _selectTool(id: string) {
    const tool = toolById(id);
    if (!tool) return;
    this._openTool = id;
    this.setAttribute("data-focus", "");
    this._loadingTool = true;
    this._toolView = null;
    try {
      await tool.load();               // lazy-load the view module
      this._toolView = tool.render();
    } catch {
      this._toolView = html`<div class="focus-loading">Failed to load ${tool.label}.</div>`;
    }
    this._loadingTool = false;
  }
  private _closeTool() {
    this._openTool = ""; this._toolView = null;
    this.removeAttribute("data-focus");
  }

  private _send() {
    const text = this._draft.trim();
    if (!text) return;
    sendChat(text);                    // store sends the correct {type:"chat", text}
    this._draft = "";
  }

  private static readonly SKIN_LABEL: Record<Skin, string> = {
    calm: "Calm", neon: "Neon", etis: "ETIS", hacker: "Hacker",
  };

  render() {
    const msgs = messages.get().slice(-6);
    const tool = this._openTool ? toolById(this._openTool) : null;
    const currentSkin = skin.get();
    return html`
      <div class="stage">
        ${this.visualizerMode === 'matrix' ? html`
          <matrix-waterfall .activity=${this.activity} .status=${this.status}></matrix-waterfall>
        ` : html`
          <threat-globe .activity=${this.activity} .status=${this.status}></threat-globe>
        `}

        <div class="skin-switcher">
          <button class="skin-btn" @click=${() => cycleSkin()} title="Cycle theme (Calm / Neon / ETIS / Hacker)">
            <span class="skin-dot"></span>${DeepConsole.SKIN_LABEL[currentSkin]}
          </button>
        </div>

        <div class="viz-switcher">
          <button class="viz-btn ${this.visualizerMode === 'globe' ? 'active' : ''}" @click=${() => this.visualizerMode = 'globe'}>Threat Globe</button>
          <button class="viz-btn ${this.visualizerMode === 'matrix' ? 'active' : ''}" @click=${() => this.visualizerMode = 'matrix'}>Matrix Waterfall</button>
        </div>

        ${tool ? html`
          <div class="focus">
            <div class="focus-head">
              <span>${tool.icon}</span><span>${tool.label}</span>
              <span class="spacer"></span>
              <button class="focus-close" @click=${this._closeTool}>✕ Close (Esc)</button>
            </div>
            <div class="focus-body">
              ${this._loadingTool ? html`<div class="focus-loading">Loading ${tool.label}…</div>` : this._toolView}
            </div>
          </div>
        ` : null}

        <div class="dock">
          ${msgs.length ? html`
            <div class="transcript">
              ${msgs.map((m) => html`<chat-message class="msg ${m.role}" .msg=${m}></chat-message>`)}
            </div>` : null}
          ${thinking.get() ? html`<div class="thinking">DEEP is thinking…</div>` : null}
          <div class="composer">
            <input
              .value=${this._draft}
              placeholder="Talk to DEEP…"
              @input=${(e: Event) => (this._draft = (e.target as HTMLInputElement).value)}
              @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this._send(); } }}
            />
            <button class="send" title="Send" @click=${this._send}>➤</button>
          </div>
        </div>
      </div>

      <tool-dock .selected=${this._openTool} @tool-select=${(e: CustomEvent<string>) => this._selectTool(e.detail)}></tool-dock>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "deep-console": DeepConsole; }
}
