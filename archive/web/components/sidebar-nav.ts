// <sidebar-nav> — Collapsible left sidebar with live badge counts
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { connection } from "../core/store";

interface NavItem {
  route: string;
  label: string;
  icon: string;
  badge?: number;
}

const ITEMS: NavItem[] = [
  { route: "dashboard", label: "Dashboard", icon: "◈" },
  { route: "home", label: "Chat", icon: "◆" },
  { route: "network", label: "Network", icon: "◎" },
  { route: "ops", label: "Operations", icon: "◉" },
  { route: "agents", label: "Agents", icon: "✦" },
  { route: "memory", label: "Memory", icon: "◐" },
  { route: "research", label: "Research", icon: "◑" },
  { route: "science", label: "Science", icon: "✹" },
  { route: "system", label: "System", icon: "⚙" },
];

@customElement("sidebar-nav")
export class SidebarNav extends LitElement {
  @state() private collapsed = false;
  @state() private activeRoute = "dashboard";

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      background: var(--ds-glass-deep);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-right: 1px solid var(--ds-border-glow);
      height: 100%;
      transition: width 0.3s var(--ds-ease-out);
      overflow: hidden;
      z-index: 50;
    }
    :host(.collapsed) { width: 52px; }
    :host(:not(.collapsed)) { width: 180px; }

    .logo {
      display: flex; align-items: center; gap: 8px;
      padding: 14px 14px 10px;
      font-weight: 700; font-size: var(--ds-text-lg);
      letter-spacing: 0.08em;
      color: var(--ds-text);
      white-space: nowrap;
    }
    .logo .icon {
      width: 28px; height: 28px; border-radius: 6px;
      display: grid; place-items: center;
      background: var(--ds-accent);
      color: var(--ds-on-accent);
      font-size: 14px; flex-shrink: 0;
      box-shadow: var(--ds-glow);
    }
    .logo .txt {
      animation: text-glow 3s ease-in-out infinite;
    }
    :host(.collapsed) .logo .txt { display: none; }

    .divider {
      height: 1px; margin: 6px 12px;
      background: var(--ds-border);
    }

    nav {
      display: flex; flex-direction: column; gap: 2px;
      padding: 0 8px; flex: 1;
    }
    a {
      display: flex; align-items: center; gap: 10px;
      padding: 8px 10px;
      border-radius: var(--ds-radius-sm);
      color: var(--ds-text-muted);
      text-decoration: none;
      font-size: var(--ds-text-sm);
      font-weight: 500;
      transition: all 0.15s ease;
      position: relative;
      white-space: nowrap;
    }
    a:hover {
      color: var(--ds-text-soft);
      background: var(--ds-surface-2);
    }
    a.on {
      color: var(--ds-accent);
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      box-shadow: inset 3px 0 0 var(--ds-accent);
    }
    a.on:hover {
      background: rgba(var(--ds-periwinkle-rgb), 0.12);
      box-shadow: inset 3px 0 0 var(--ds-accent), inset 3px 0 12px rgba(var(--ds-periwinkle-rgb), 0.2);
    }

    .ico {
      width: 22px; height: 22px;
      display: grid; place-items: center;
      font-size: 13px; flex-shrink: 0;
    }
    .lbl { flex: 1; }
    :host(.collapsed) .lbl { display: none; }

    .badge {
      min-width: 18px; height: 18px; border-radius: 9px;
      background: var(--ds-danger);
      color: #fff;
      font-size: 10px; font-weight: 600;
      display: grid; place-items: center;
      padding: 0 5px;
      box-shadow: 0 0 6px rgba(229,115,106,0.4);
      animation: neon-pulse 2s ease-in-out infinite;
    }
    :host(.collapsed) .badge {
      position: absolute; top: 4px; right: 4px;
      min-width: 8px; height: 8px; padding: 0;
      font-size: 0;
    }

    .toggle {
      padding: 10px 14px;
      display: flex; align-items: center; justify-content: flex-end;
      cursor: pointer;
      color: var(--ds-text-faint);
      font-size: 12px;
      transition: color 0.15s ease;
    }
    .toggle:hover { color: var(--ds-accent); }
    :host(.collapsed) .toggle { justify-content: center; }

    .status {
      padding: 10px 14px;
      font-size: var(--ds-text-xs);
      color: var(--ds-text-faint);
      font-family: var(--ds-font-mono);
      white-space: nowrap;
    }
    .status .dot {
      display: inline-block; width: 6px; height: 6px;
      border-radius: 50%; margin-right: 6px;
      background: var(--ds-danger);
      vertical-align: middle;
    }
    .status .dot.open { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    :host(.collapsed) .status { display: none; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.activeRoute = location.hash.slice(1) || "dashboard";
    window.addEventListener("hashchange", () => {
      this.activeRoute = location.hash.slice(1) || "dashboard";
    });
  }

  private _toggle = () => {
    this.collapsed = !this.collapsed;
    this.classList.toggle("collapsed", this.collapsed);
  };

  private _navigate = (e: Event, route: string) => {
    e.preventDefault();
    location.hash = route;
  };

  render() {
    const conn = connection.get();
    return html`
      <div class="logo">
        <div class="icon">◉</div>
        <span class="txt">DEEP</span>
      </div>
      <div class="divider"></div>
      <nav>
        ${ITEMS.map((item) => html`
          <a
            href="#${item.route}"
            class="${this.activeRoute === item.route || (this.activeRoute === "home" && item.route === "home") ? "on" : ""}"
            @click=${(e: Event) => this._navigate(e, item.route)}
            title="${item.label}"
          >
            <span class="ico">${item.icon}</span>
            <span class="lbl">${item.label}</span>
            ${item.badge ? html`<span class="badge">${item.badge}</span>` : ""}
          </a>
        `)}
      </nav>
      <div class="status">
        <span class="dot ${conn === "open" ? "open" : ""}"></span>
        ${conn === "open" ? "ONLINE" : "OFFLINE"}
      </div>
      <div class="toggle" @click=${this._toggle} title="Toggle sidebar">
        ${this.collapsed ? "▸" : "◂"}
      </div>
    `;
  }
}
