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
import { GROUPS, groupForRoute } from "../core/nav";
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
  projects: () => import("./knowledge/projects-view"),
  research: () => import("./knowledge/research-view"),
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

  private renderSubnav() {
    const g = groupForRoute(this.route);
    if (!g) return ""; // chat / home → no sub-nav
    return html`
      <div class="subnav">
        <span class="grp-label">${g.label}</span>
        ${g.tabs.map((t) => html`
          <a href="#${t.route}" class="tab ${this.route === t.route ? "on" : ""}">${t.label}</a>
        `)}
      </div>
    `;
  }

  private renderRoute() {
    switch (this.route) {
      case "gallery": return html`<ds-gallery></ds-gallery>`;
      case "science": return html`<science-view></science-view>`;
      case "calc": return html`<calc-view></calc-view>`;
      case "projects": return html`<projects-view></projects-view>`;
      case "research": return html`<research-view></research-view>`;
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
    :host { display: grid; grid-template-rows: auto auto 1fr; height: 100%; }
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
    /* group-level nav (primary) */
    nav.groups { display: flex; gap: var(--ds-space-1); }
    .grp {
      padding: var(--ds-space-1) var(--ds-space-4);
      border-radius: var(--ds-radius-pill);
      color: var(--ds-text-muted);
      font-size: var(--ds-text-sm);
      font-weight: 500;
      text-decoration: none;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .grp:hover { color: var(--ds-text); background: var(--ds-surface-2); }
    .grp.on { color: var(--ds-on-accent); background: var(--ds-accent); box-shadow: var(--ds-glow); }
    /* tab-level nav (secondary) */
    .subnav {
      display: flex; align-items: center; gap: var(--ds-space-1);
      padding: var(--ds-space-2) var(--ds-space-5);
      border-bottom: 1px solid var(--ds-border);
      background: var(--ds-glass-thin);
      overflow-x: auto;
    }
    .grp-label {
      font-size: var(--ds-text-xs); text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide); color: var(--ds-text-faint);
      margin-right: var(--ds-space-3); white-space: nowrap;
    }
    .tab {
      padding: 3px var(--ds-space-3);
      border-radius: var(--ds-radius-sm);
      color: var(--ds-text-muted);
      font-size: var(--ds-text-sm);
      text-decoration: none; white-space: nowrap;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .tab:hover { color: var(--ds-accent); }
    .tab.on { color: var(--ds-accent); background: rgba(var(--ds-periwinkle-rgb), 0.14); }
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
    nav.groups { flex-wrap: nowrap; flex-shrink: 0; }
    header { flex-wrap: nowrap; }
    .logo { white-space: nowrap; }
    @media (max-width: 640px) { .meta { display: none; } }

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
        <nav class="groups">
          <a href="#home" class="grp ${this.route === "home" ? "on" : ""}">chat</a>
          ${GROUPS.map((g) => {
            const active = groupForRoute(this.route)?.id === g.id;
            return html`<a href="#${g.tabs[0].route}" class="grp ${active ? "on" : ""}">${g.label}</a>`;
          })}
        </nav>
        <span class="spacer"></span>
        <span class="meta">${this.status} · ${activeModel.get()}</span>
        <button class="kbd theme" title="Toggle theme (calm / neon)" @click=${() => cycleSkin()}>
          ${skin.get() === "neon" ? "◖ neon" : "◗ calm"}
        </button>
        <span class="meta kbd" title="Command palette">⌘K</span>
      </header>
      ${this.renderSubnav()}
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
