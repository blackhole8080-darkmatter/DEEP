// <deep-app> — the application shell.
// Phase 2: state now lives in the signal store (core/store.ts); this component
// is a pure view over it via SignalWatcher. Includes a minimal chat probe to
// prove the full reactive pipeline (send → stream → render) before Phase 3
// builds the real chat surface.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import {
  initStore,
  connection,
  messages,
  thinking,
  sendChat,
  activeModel,
  lastTelemetry,
} from "../core/store";
import { fetchStatus } from "../core/api";
import "./gallery";
import "./primitives/ds-field";
import "./primitives/ds-button";

@customElement("deep-app")
export class DeepApp extends SignalWatcher(LitElement) {
  @state() private route = location.hash.slice(1) || "home";
  @state() private status = "—";
  @state() private draft = "";

  private onHash = () => { this.route = location.hash.slice(1) || "home"; };

  connectedCallback(): void {
    super.connectedCallback();
    initStore();
    void fetchStatus().then((s) => (this.status = s.deep)).catch(() => (this.status = "offline"));
    window.addEventListener("hashchange", this.onHash);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("hashchange", this.onHash);
  }

  private submit(): void {
    sendChat(this.draft);
    this.draft = "";
    const field = this.renderRoot.querySelector("ds-field");
    if (field) (field as HTMLElement & { value: string }).value = "";
  }

  static styles = css`
    :host { display: grid; grid-template-rows: auto 1fr; height: 100%; }
    header {
      display: flex; align-items: center; gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-5);
      border-bottom: 1px solid var(--ds-border);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
    }
    .logo { font-weight: 700; letter-spacing: 0.02em; }
    .dot { width: 8px; height: 8px; border-radius: var(--ds-radius-pill); background: var(--ds-danger); }
    .dot.open { background: var(--ds-success); box-shadow: 0 0 8px var(--ds-success); }
    .spacer { flex: 1; }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    nav a { color: var(--ds-text-muted); font-size: var(--ds-text-sm); text-decoration: none; margin-right: var(--ds-space-3); }
    nav a:hover { color: var(--ds-accent); }

    main { overflow: auto; }
    .probe {
      max-width: 720px; margin: 0 auto; padding: var(--ds-space-5);
      display: grid; gap: var(--ds-space-3);
    }
    .msgs { display: grid; gap: var(--ds-space-2); }
    .msg {
      padding: var(--ds-space-3) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      white-space: pre-wrap;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .user { background: rgba(var(--ds-periwinkle-rgb), 0.10); border-color: var(--ds-border-accent); justify-self: end; max-width: 85%; }
    .ai { background: var(--ds-surface-1); justify-self: start; max-width: 92%; }
    .ai.streaming::after { content: "▋"; color: var(--ds-accent); animation: blink 1s steps(1) infinite; }
    .row { display: flex; gap: var(--ds-space-2); align-items: end; }
    .row ds-field { flex: 1; }
    .hint { color: var(--ds-text-muted); font-size: var(--ds-text-xs); font-family: var(--ds-font-mono); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes blink { 50% { opacity: 0; } }
  `;

  render() {
    const conn = connection.get();
    return html`
      <header>
        <span class="dot ${conn === "open" ? "open" : ""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <nav>
          <a href="#home">chat</a>
          <a href="#gallery">gallery</a>
        </nav>
        <span class="meta">${this.status} · ${activeModel.get()}</span>
      </header>
      <main>
        ${this.route === "gallery"
          ? html`<ds-gallery></ds-gallery>`
          : html`
              <div class="probe">
                <div class="msgs">
                  ${messages.get().map(
                    (m) => html`
                      <div class="msg ${m.role} ${m.streaming ? "streaming" : ""}">
                        ${m.text}
                      </div>
                    `,
                  )}
                  ${thinking.get() ? html`<div class="msg ai">…</div>` : ""}
                </div>
                <div class="row">
                  <ds-field
                    placeholder="Message DEEP…"
                    @ds-input=${(e: CustomEvent<string>) => (this.draft = e.detail)}
                    @ds-submit=${() => this.submit()}
                  ></ds-field>
                  <ds-button variant="primary" @click=${() => this.submit()}>Send</ds-button>
                </div>
                <span class="hint">ws: ${conn} · last event: ${lastTelemetry.get() || "—"}</span>
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
