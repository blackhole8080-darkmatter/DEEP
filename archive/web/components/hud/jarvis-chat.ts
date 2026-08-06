// <jarvis-chat> — Bottom-right: JARVIS command input bar
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { thinking, isStreaming } from "../../core/store";
import { socket } from "../../core/ws";

@customElement("jarvis-chat")
export class JarvisChat extends SignalWatcher(LitElement) {
  @property({ type: String }) mode = "idle";
  @state() private _value = "";
  @state() private _history: string[] = [];
  @state() private _histIdx = -1;

  static styles = css`
    :host { display:flex; flex-direction:column; height:100%; --j-cyan:#00e5ff; }
    .c-header {
      display:flex; align-items:center; justify-content:space-between;
      padding:6px 12px 5px; border-bottom:1px solid rgba(0,229,255,0.1); flex-shrink:0;
    }
    .c-title { font-family:"Rajdhani",monospace; font-size:0.6rem; font-weight:700; letter-spacing:0.28em; text-transform:uppercase; color:rgba(0,229,255,0.45); }
    .c-status {
      font-family:monospace; font-size:0.55rem; letter-spacing:0.1em;
      color:var(--j-cyan); text-shadow:0 0 8px var(--j-cyan);
    }
    .c-status.busy { animation:c-blink 0.7s ease-in-out infinite; }
    @keyframes c-blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .c-body { flex:1; display:flex; align-items:center; gap:8px; padding:0 12px; }
    .c-prompt {
      font-family:"Rajdhani",monospace; font-size:1rem; font-weight:700;
      color:var(--j-cyan); text-shadow:0 0 10px var(--j-cyan); flex-shrink:0;
    }
    .c-input {
      flex:1; background:transparent; border:none; outline:none;
      font-family:"JetBrains Mono",monospace; font-size:0.78rem;
      color:rgba(220,245,255,0.9); caret-color:var(--j-cyan);
      letter-spacing:0.04em;
    }
    .c-input::placeholder { color:rgba(0,229,255,0.25); font-style:italic; }
    .c-input:disabled::placeholder { opacity:0.5; }
    .c-btn {
      flex-shrink:0; width:28px; height:28px; border-radius:3px;
      border:1px solid rgba(0,229,255,0.3);
      background:rgba(0,229,255,0.08);
      color:var(--j-cyan); font-size:0.8rem; cursor:pointer;
      display:grid; place-items:center;
      transition:background 0.15s, box-shadow 0.15s, transform 0.1s;
    }
    .c-btn:hover { background:rgba(0,229,255,0.18); box-shadow:0 0 12px rgba(0,229,255,0.4); }
    .c-btn:active { transform:scale(0.9); }
    .c-btn:disabled { opacity:0.25; cursor:not-allowed; }

    .c-hints { display:flex; gap:14px; padding:4px 12px 6px; flex-shrink:0; }
    .hint { font-family:monospace; font-size:0.5rem; letter-spacing:0.06em; color:rgba(0,229,255,0.22); }
    .hint span { color:rgba(0,229,255,0.5); }
  `;

  private _send(): void {
    const text = this._value.trim();
    if (!text || thinking.get() || isStreaming.get()) return;
    this._history = [text, ...this._history.slice(0, 19)];
    this._histIdx = -1;
    this._value = "";
    socket.send({ type: "chat", content: text });
  }

  private _onKeyDown(e: KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this._send(); return; }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      const i = Math.min(this._histIdx + 1, this._history.length - 1);
      this._histIdx = i; this._value = this._history[i] ?? "";
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const i = Math.max(this._histIdx - 1, -1);
      this._histIdx = i; this._value = i === -1 ? "" : this._history[i];
    }
  }

  render() {
    const busy = thinking.get() || isStreaming.get();
    return html`
      <div class="c-header">
        <span class="c-title">◈ COMMAND</span>
        <span class="c-status ${busy ? "busy" : ""}">${busy ? "⬡ PROCESSING..." : "⬡ READY"}</span>
      </div>
      <div class="c-body">
        <span class="c-prompt">&gt;_</span>
        <input class="c-input" type="text"
          .value=${this._value}
          placeholder="${busy ? "DEEP is processing..." : "Enter command..."}"
          ?disabled=${busy}
          @input=${(e: InputEvent) => { this._value = (e.target as HTMLInputElement).value; }}
          @keydown=${this._onKeyDown}
          autocomplete="off" spellcheck="false"
        />
        <button class="c-btn" ?disabled=${busy || !this._value.trim()} @click=${this._send} title="Send">⏎</button>
      </div>
      <div class="c-hints">
        <span class="hint"><span>Enter</span> send</span>
        <span class="hint"><span>↑↓</span> history</span>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-chat": JarvisChat; } }
