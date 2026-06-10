// <deep-app> — the application shell.
// Phase 0: proves the pipeline end-to-end (renders, connects to the live WS,
// shows connection state + live status). Grows into the full layout in Phase 4.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { socket, type DeepMessage } from "../core/ws";
import "./gallery";

@customElement("deep-app")
export class DeepApp extends LitElement {
  @state() private conn: "connecting" | "open" | "closed" = "closed";
  @state() private status = "—";
  @state() private model = "—";
  @state() private lastEvent = "";
  @state() private route = location.hash.slice(1) || "home";

  private off?: () => void;
  private onHash = () => { this.route = location.hash.slice(1) || "home"; };

  connectedCallback(): void {
    super.connectedCallback();
    this.off = socket.on((m) => this.onMessage(m));
    socket.connect();
    void this.fetchStatus();
    window.addEventListener("hashchange", this.onHash);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.off?.();
    socket.close();
    window.removeEventListener("hashchange", this.onHash);
  }

  private onMessage(m: DeepMessage): void {
    if (m.type === "_socket_open") this.conn = "open";
    else if (m.type === "_socket_close") this.conn = "closed";
    else this.lastEvent = m.type;
  }

  private async fetchStatus(): Promise<void> {
    try {
      const r = await fetch("/api/status");
      const d = await r.json();
      this.status = String(d.deep ?? "—");
      this.model = String(d.model ?? "—");
    } catch {
      this.status = "offline";
    }
  }

  static styles = css`
    :host {
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100%;
    }
    header {
      display: flex;
      align-items: center;
      gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-5);
      border-bottom: 1px solid var(--ds-border);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
    }
    .logo { font-weight: 700; letter-spacing: 0.02em; }
    .dot {
      width: 8px; height: 8px; border-radius: var(--ds-radius-pill);
      background: var(--ds-danger);
    }
    .dot.open { background: var(--ds-success); box-shadow: 0 0 8px var(--ds-success); }
    .spacer { flex: 1; }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    main {
      display: grid;
      place-items: center;
      padding: var(--ds-space-7);
    }
    .card {
      max-width: 520px;
      padding: var(--ds-space-6);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      animation: rise var(--ds-dur-slow) var(--ds-ease-spring);
    }
    h1 { margin: 0 0 var(--ds-space-2); font-size: var(--ds-text-2xl); }
    p { margin: var(--ds-space-2) 0; color: var(--ds-text-soft); }
    code { font-family: var(--ds-font-mono); color: var(--ds-accent); }
    @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  `;

  render() {
    return html`
      <header>
        <span class="dot ${this.conn === "open" ? "open" : ""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <span class="meta">${this.status} · ${this.model}</span>
      </header>
      <main style=${this.route === "gallery" ? "display:block;place-items:unset;overflow:auto" : ""}>
        ${this.route === "gallery"
          ? html`<ds-gallery></ds-gallery>`
          : html`
              <div class="card">
                <h1>Modern shell online</h1>
                <p>This is the new Vite + Lit frontend (Phase 1).</p>
                <p>WebSocket: <code>${this.conn}</code></p>
                <p>Last live event: <code>${this.lastEvent || "(none yet)"}</code></p>
                <p>Design system: <a href="#gallery" style="color:var(--ds-accent)">open the gallery</a></p>
              </div>
            `}
      </main>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "deep-app": DeepApp;
  }
}
