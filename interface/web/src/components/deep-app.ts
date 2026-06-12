// <deep-app> — the application shell.
// Phase 2: state now lives in the signal store (core/store.ts); this component
// is a pure view over it via SignalWatcher. Includes a minimal chat probe to
// prove the full reactive pipeline (send → stream → render) before Phase 3
// builds the real chat surface.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { initStore, connection, activeModel } from "../core/store";
import { fetchStatus } from "../core/api";
import { skin, cycleSkin } from "../core/theme";
import "../core/commands";
import "./chat/deep-chat";        // chat is the default route → eager
import "./command-palette";
import type { CommandPalette } from "./command-palette";

// Heavy secondary views are code-split: their bundles load on first visit.
const lazyView: Record<string, () => Promise<unknown>> = {
  gallery: () => import("./gallery"),
  science: () => import("./science/science-view"),
  ops: () => import("./ops/ops-view"),
  agents: () => import("./ops/agents-view"),
  network: () => import("./ops/network-view"),
  audit: () => import("./ops/audit-view"),
  memory: () => import("./memory/memory-graph"),
  system: () => import("./system/system-monitor"),
  geo: () => import("./system/geo-view"),
  calc: () => import("./science/calc-view"),
};

@customElement("deep-app")
export class DeepApp extends SignalWatcher(LitElement) {
  @state() private route = location.hash.slice(1) || "home";
  @state() private status = "—";

  private onHash = () => {
    const next = location.hash.slice(1) || "home";
    void lazyView[next]?.(); // preload the view's bundle if it's code-split
    // Smooth cross-fade between views where supported.
    const doc = document as Document & { startViewTransition?: (cb: () => void) => void };
    if (doc.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      doc.startViewTransition(() => { this.route = next; });
    } else {
      this.route = next;
    }
  };
  private onGlobalKey = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      (this.renderRoot.querySelector("command-palette") as CommandPalette | null)?.toggle();
    }
  };

  connectedCallback(): void {
    super.connectedCallback();
    initStore();
    void fetchStatus().then((s) => (this.status = s.deep)).catch(() => (this.status = "offline"));
    void lazyView[this.route]?.(); // load the initial view if it's not chat
    window.addEventListener("hashchange", this.onHash);
    window.addEventListener("keydown", this.onGlobalKey);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("hashchange", this.onHash);
    window.removeEventListener("keydown", this.onGlobalKey);
  }

  private renderRoute() {
    switch (this.route) {
      case "gallery": return html`<ds-gallery></ds-gallery>`;
      case "science": return html`<science-view></science-view>`;
      case "calc": return html`<calc-view></calc-view>`;
      case "memory": return html`<memory-graph></memory-graph>`;
      case "network": return html`<network-view></network-view>`;
      case "system": return html`<system-monitor></system-monitor>`;
      case "geo": return html`<geo-view></geo-view>`;
      case "audit": return html`<audit-view></audit-view>`;
      case "ops": return html`<ops-view></ops-view>`;
      case "agents": return html`<agents-view></agents-view>`;
      default: return html`<deep-chat></deep-chat>`;
    }
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
    .kbd {
      padding: 2px 7px;
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-xs);
      font-size: 0.65rem;
      cursor: default;
      color: var(--ds-text-soft);
      background: none;
      font-family: var(--ds-font-mono);
    }
    button.theme { cursor: pointer; transition: all var(--ds-dur-fast) var(--ds-ease-out); }
    button.theme:hover { color: var(--ds-accent); border-color: var(--ds-border-accent); box-shadow: var(--ds-glow); }
    nav { display: flex; flex-wrap: wrap; }

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
          <a href="#calc">calc</a>
          <a href="#science">science</a>
          <a href="#memory">memory</a>
          <a href="#system">system</a>
          <a href="#geo">geo</a>
          <a href="#network">network</a>
          <a href="#audit">audit</a>
          <a href="#ops">ops</a>
          <a href="#agents">agents</a>
        </nav>
        <span class="meta">${this.status} · ${activeModel.get()}</span>
        <button class="kbd theme" title="Toggle theme (calm / neon)" @click=${() => cycleSkin()}>
          ${skin.get() === "neon" ? "◖ neon" : "◗ calm"}
        </button>
        <span class="meta kbd" title="Command palette">⌘K</span>
      </header>
      <main>
        ${this.renderRoute()}
      </main>
      <command-palette></command-palette>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "deep-app": DeepApp;
  }
}
