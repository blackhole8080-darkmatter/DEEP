// <elements-panel> — the right-side tool rail. Renders TOOL_REGISTRY grouped by
// category; clicking a tool emits `tool-select` (detail = tool id). Adding a tool
// to DEEP is just appending to TOOL_REGISTRY — this panel updates automatically.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { TOOL_REGISTRY, type ToolDef } from "../../core/tool-registry";

const GROUP_LABEL: Record<string, string> = {
  intelligence: "Intelligence",
  system: "System",
  personal: "Personal",
  core: "Core",
};

@customElement("elements-panel")
export class ElementsPanel extends LitElement {
  @property() selected = "";

  static styles = css`
    :host {
      display: block; height: 100%; overflow-y: auto;
      pointer-events: auto;
      background: linear-gradient(180deg, rgba(8,14,24,0.55), rgba(6,10,18,0.7));
      backdrop-filter: blur(18px) saturate(140%);
      -webkit-backdrop-filter: blur(18px) saturate(140%);
      border-left: 1px solid rgba(0,229,255,0.16);
      box-shadow: -8px 0 40px rgba(0,0,0,0.4), inset 1px 0 0 rgba(0,229,255,0.08);
      padding: var(--ds-space-4, 16px) var(--ds-space-3, 12px);
      font-family: var(--ds-font-sans, system-ui);
    }
    .title {
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.7rem; letter-spacing: 0.28em; text-transform: uppercase;
      color: rgba(0,229,255,0.85); text-shadow: 0 0 12px rgba(0,229,255,0.4);
      margin: 0 0 var(--ds-space-4, 16px) 4px;
    }
    .group { margin-bottom: var(--ds-space-4, 16px); }
    .group-label {
      font-size: 0.62rem; letter-spacing: 0.18em; text-transform: uppercase;
      color: rgba(200,230,255,0.35); margin: 0 0 6px 6px;
    }
    .tool {
      display: flex; align-items: center; gap: 12px;
      padding: 9px 12px; margin-bottom: 4px;
      border-radius: 10px; cursor: pointer;
      color: rgba(210,235,255,0.82);
      border: 1px solid transparent;
      transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
    }
    .tool:hover {
      background: rgba(0,229,255,0.07);
      border-color: rgba(0,229,255,0.25);
      transform: translateX(-3px);
      box-shadow: 0 0 20px rgba(0,229,255,0.12);
    }
    .tool[aria-selected="true"] {
      background: rgba(0,229,255,0.12);
      border-color: rgba(0,229,255,0.45);
      box-shadow: 0 0 24px rgba(0,229,255,0.2);
      color: #eaffff;
    }
    .icon {
      width: 26px; height: 26px; flex-shrink: 0;
      display: grid; place-items: center;
      font-size: 1rem; border-radius: 7px;
      background: rgba(0,229,255,0.08);
      color: var(--j-cyan, #00e5ff);
      text-shadow: 0 0 10px rgba(0,229,255,0.5);
    }
    .label { font-size: 0.86rem; font-weight: 500; letter-spacing: 0.01em; }
  `;

  private _select(t: ToolDef) {
    this.dispatchEvent(new CustomEvent("tool-select", { detail: t.id, bubbles: true, composed: true }));
  }

  render() {
    const groups = ["intelligence", "system", "personal", "core"] as const;
    return html`
      <h2 class="title">Elements</h2>
      ${groups.map((g) => {
        const tools = TOOL_REGISTRY.filter((t) => t.group === g);
        if (!tools.length) return null;
        return html`
          <div class="group">
            <div class="group-label">${GROUP_LABEL[g]}</div>
            ${tools.map((t) => html`
              <div class="tool" role="button" tabindex="0"
                aria-selected=${this.selected === t.id}
                @click=${() => this._select(t)}
                @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); this._select(t); } }}>
                <span class="icon">${t.icon}</span>
                <span class="label">${t.label}</span>
              </div>
            `)}
          </div>
        `;
      })}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "elements-panel": ElementsPanel; }
}
