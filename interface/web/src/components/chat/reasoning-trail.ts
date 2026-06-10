// <reasoning-trail> — the live grounding trail for the current turn: routing
// decisions, symbolic/oracle verifications, tool calls/results, model hops.
// Collapsible; auto-shows while steps stream in.
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

export interface Step { t: string; [k: string]: unknown; }

const ICONS: Record<string, string> = {
  model: "◇",
  route: "⇢",
  symbolic: "∑",
  oracle: "⚛",
  thinking: "…",
  tool_call: "⚙",
  tool_result: "✓",
  final: "●",
};

function describe(s: Step): string {
  switch (s.t) {
    case "route": return `routed: ${s.reason ?? ""} → ${s.model ?? ""}`;
    case "symbolic": return `verified by ${s.engine ?? "sympy"} (${s.kind}): ${s.result}`;
    case "oracle": return `${s.domain} oracle: ${s.result ?? s.element ?? ""}`;
    case "tool_call": return `tool: ${s.tool}`;
    case "tool_result": return `result from ${s.tool}: ${String(s.result ?? "").slice(0, 80)}`;
    case "model": return `model: ${s.model ?? "?"} (loop ${s.loop ?? 1})`;
    case "thinking": return String(s.text ?? "").slice(0, 100);
    default: return s.t;
  }
}

@customElement("reasoning-trail")
export class ReasoningTrail extends LitElement {
  @property({ attribute: false }) steps: Step[] = [];
  @state() private open = true;

  static styles = css`
    :host { display: block; }
    .trail {
      border: 1px solid var(--ds-border);
      border-left: 2px solid var(--ds-accent);
      border-radius: var(--ds-radius-md);
      background: var(--ds-glass-thin);
      -webkit-backdrop-filter: blur(var(--ds-blur-sm));
      backdrop-filter: blur(var(--ds-blur-sm));
      font-family: var(--ds-font-mono);
      font-size: var(--ds-text-xs);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    header {
      display: flex; align-items: center; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-3);
      color: var(--ds-text-muted);
      cursor: pointer;
      user-select: none;
      letter-spacing: var(--ds-tracking-wide);
      text-transform: uppercase;
      font-size: 0.62rem;
    }
    header:hover { color: var(--ds-text-soft); }
    ul { list-style: none; margin: 0; padding: 0 var(--ds-space-3) var(--ds-space-2); display: grid; gap: 3px; }
    li { display: flex; gap: var(--ds-space-2); color: var(--ds-text-soft); }
    li .ic { color: var(--ds-accent); width: 14px; text-align: center; }
    li.verify { color: var(--ds-success); }
    li.verify .ic { color: var(--ds-success); }
    @keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  `;

  render() {
    if (!this.steps.length) return html``;
    return html`
      <div class="trail">
        <header @click=${() => (this.open = !this.open)}>
          <span>${this.open ? "▾" : "▸"}</span>
          <span>reasoning · ${this.steps.length} step${this.steps.length > 1 ? "s" : ""}</span>
        </header>
        ${this.open
          ? html`<ul>
              ${this.steps.map(
                (s) => html`
                  <li class=${s.t === "symbolic" || s.t === "oracle" ? "verify" : ""}>
                    <span class="ic">${ICONS[s.t] ?? "·"}</span>
                    <span>${describe(s)}</span>
                  </li>
                `,
              )}
            </ul>`
          : ""}
      </div>
    `;
  }
}
