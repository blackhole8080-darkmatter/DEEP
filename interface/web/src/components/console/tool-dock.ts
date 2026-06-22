// <tool-dock> — DEEP's primary tool launcher: a floating, glassmorphic bottom
// dock of compact icon pills (macOS-dock style) that holds ALL tools from
// TOOL_REGISTRY. Hovering magnifies the focused pill and its neighbours and
// reveals a label tooltip. Clicking emits `tool-select` (detail = tool id),
// exactly like the old elements-panel — so the console wiring is unchanged.
//
// Adding a tool to DEEP is still just appending one entry to TOOL_REGISTRY;
// this dock updates automatically, with subtle separators between groups.
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { TOOL_REGISTRY, type ToolDef } from "../../core/tool-registry";

const GROUP_ORDER = ["intelligence", "system", "personal", "core"] as const;

@customElement("tool-dock")
export class ToolDock extends LitElement {
  @property() selected = "";
  @state() private _hover = -1;

  static styles = css`
    :host {
      display: block;
      pointer-events: none;
    }

    .dock {
      position: relative;
      isolation: isolate;
      pointer-events: auto;
      display: inline-flex;
      align-items: flex-end;
      gap: 6px;
      padding: 10px 14px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(16,20,40,0.5), rgba(10,12,26,0.66));
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid transparent;
      box-shadow:
        0 18px 50px rgba(0,0,0,0.5),
        0 0 50px rgba(140,160,255,0.10),
        inset 0 1px 0 rgba(255,255,255,0.08);
      max-width: 92vw;
      overflow: visible;
    }
    /* Animated iridescent gradient border */
    .dock::before {
      content: "";
      position: absolute; inset: 0;
      border-radius: inherit;
      padding: 1.4px;
      background: linear-gradient(120deg,
        #a8edea, #8fd3ff, #b8a6ff, #ff9ed8, #ffd6a5, #a8edea);
      background-size: 320% 320%;
      animation: irid-border 9s ease infinite;
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      pointer-events: none;
      z-index: -1;
      opacity: 0.8;
    }
    /* Holographic sheen sweep across the glass */
    .dock::after {
      content: "";
      position: absolute; inset: 0;
      border-radius: inherit;
      background: linear-gradient(115deg,
        transparent 30%, rgba(255,255,255,0.10) 48%, rgba(184,166,255,0.12) 54%, transparent 70%);
      background-size: 280% 100%;
      animation: irid-sheen 7s linear infinite;
      pointer-events: none;
      z-index: -1;
      mix-blend-mode: screen;
    }
    @keyframes irid-border {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    @keyframes irid-sheen {
      0% { background-position: 180% 0; }
      100% { background-position: -80% 0; }
    }

    .sep {
      width: 1px;
      align-self: center;
      height: 26px;
      margin: 0 4px;
      background: linear-gradient(180deg, transparent, rgba(184,166,255,0.4), transparent);
      flex: 0 0 auto;
    }

    .pill {
      position: relative;
      flex: 0 0 auto;
      width: 44px; height: 44px;
      border: 1px solid transparent;
      border-radius: 14px;
      background: rgba(255,255,255,0.04);
      color: rgba(210,235,255,0.82);
      cursor: pointer;
      display: grid; place-items: center;
      transform-origin: bottom center;
      transform: scale(var(--s, 1)) translateY(var(--ty, 0));
      transition:
        transform 0.18s cubic-bezier(0.22,1,0.36,1),
        background 0.16s ease,
        border-color 0.16s ease,
        box-shadow 0.16s ease;
    }
    .pill:hover { background: rgba(184,166,255,0.12); border-color: rgba(184,166,255,0.35); }
    .pill.on {
      background: rgba(143,211,255,0.16);
      border-color: rgba(184,166,255,0.55);
      box-shadow: 0 0 24px rgba(143,211,255,0.3), 0 0 36px rgba(255,158,216,0.16), inset 0 0 12px rgba(184,166,255,0.14);
    }
    .pill.on::after {
      content: "";
      position: absolute; bottom: -7px; left: 50%; transform: translateX(-50%);
      width: 14px; height: 4px; border-radius: 999px;
      background: linear-gradient(90deg, #8fd3ff, #b8a6ff, #ff9ed8);
      box-shadow: 0 0 10px rgba(184,166,255,0.8);
    }

    .icon {
      font-size: 1.15rem; line-height: 1;
      background: linear-gradient(135deg, #b6f0ff, #9fb8ff, #d9b3ff, #ffb3e6);
      background-size: 200% 200%;
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent; color: transparent;
      filter: drop-shadow(0 0 8px rgba(143,211,255,0.45));
      animation: irid-icon 9s ease infinite;
    }
    .pill.on .icon { filter: drop-shadow(0 0 12px rgba(184,166,255,0.9)); }
    @keyframes irid-icon {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    /* Hover label tooltip */
    .tip {
      position: absolute;
      bottom: calc(100% + 12px);
      left: 50%; transform: translateX(-50%) translateY(6px);
      padding: 5px 12px;
      border-radius: 9px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.66rem; letter-spacing: 0.12em; text-transform: uppercase;
      white-space: nowrap;
      color: #eaffff;
      background: rgba(10,14,28,0.92);
      border: 1px solid rgba(184,166,255,0.35);
      box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 16px rgba(143,211,255,0.18);
      opacity: 0; pointer-events: none;
      transition: opacity 0.15s ease, transform 0.15s ease;
    }
    .pill:hover .tip { opacity: 1; transform: translateX(-50%) translateY(0); }
    .tip::after {
      content: "";
      position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
      border: 5px solid transparent; border-top-color: rgba(184,166,255,0.35);
    }

    @media (prefers-reduced-motion: reduce) {
      .pill { transition: background 0.16s ease, border-color 0.16s ease; transform: none !important; }
    }
  `;

  private _select(t: ToolDef) {
    this.dispatchEvent(new CustomEvent("tool-select", { detail: t.id, bubbles: true, composed: true }));
  }

  // macOS-style magnification: hovered pill grows most, neighbours taper off.
  private _scale(i: number): number {
    if (this._hover < 0) return 1;
    const d = Math.abs(i - this._hover);
    if (d === 0) return 1.5;
    if (d === 1) return 1.28;
    if (d === 2) return 1.12;
    return 1;
  }
  // Lift magnified pills slightly so they don't clip the dock's top edge.
  private _lift(i: number): number {
    if (this._hover < 0) return 0;
    const d = Math.abs(i - this._hover);
    if (d === 0) return -8;
    if (d === 1) return -4;
    if (d === 2) return -1;
    return 0;
  }

  render() {
    // Order tools by group so separators are meaningful.
    const ordered = [...TOOL_REGISTRY].sort(
      (a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group)
    );
    return html`
      <div class="dock" @pointerleave=${() => (this._hover = -1)}>
        ${ordered.map((t, i) => {
          const prev = ordered[i - 1];
          const sep = prev && prev.group !== t.group ? html`<div class="sep"></div>` : null;
          return html`
            ${sep}
            <button
              class="pill ${this.selected === t.id ? "on" : ""}"
              style="--s:${this._scale(i)}; --ty:${this._lift(i)}px"
              @pointerenter=${() => (this._hover = i)}
              @click=${() => this._select(t)}
              aria-label=${t.label}
            >
              <span class="icon">${t.icon}</span>
              <span class="tip">${t.label}</span>
            </button>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "tool-dock": ToolDock; }
}
