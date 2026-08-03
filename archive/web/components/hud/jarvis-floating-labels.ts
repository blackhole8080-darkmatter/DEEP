// <jarvis-floating-labels> — Ambient holographic info tags drifting in empty space
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface Label {
  id: number;
  text: string;
  x: number;  // vw %
  y: number;  // vh %
  phase: number;
  speed: number;
  amp: number;
  delay: number;
  dim: boolean;
}

@customElement("jarvis-floating-labels")
export class JarvisFloatingLabels extends LitElement {
  @property({ type: String }) mode = "idle";
  @state() private _t = 0;
  @state() private _labels: Label[] = [
    { id: 0, text: "NEURAL LATENCY: 4ms",    x: 50,  y: 12,  phase: 0,    speed: 0.12, amp: 4,  delay: 0,   dim: false },
    { id: 1, text: "CONTEXT WINDOW: 82%",    x: 15,  y: 28,  phase: 1.2,  speed: 0.09, amp: 6,  delay: 200, dim: false },
    { id: 2, text: "UPTIME: 99.97%",          x: 82,  y: 22,  phase: 2.4,  speed: 0.11, amp: 5,  delay: 400, dim: false },
    { id: 3, text: "THREAT LEVEL: LOW",       x: 88,  y: 55,  phase: 0.8,  speed: 0.14, amp: 7,  delay: 100, dim: false },
    { id: 4, text: "AGENTS ACTIVE: 4",        x: 8,   y: 60,  phase: 3.1,  speed: 0.10, amp: 5,  delay: 300, dim: false },
    { id: 5, text: "MEMORY NODES: 8,241",     x: 50,  y: 88,  phase: 1.7,  speed: 0.13, amp: 6,  delay: 600, dim: false },
  ];

  private _raf = 0;

  static styles = css`
    :host { display: block; position: absolute; inset: 0; pointer-events: none; }

    .fl-tag {
      position: absolute;
      display: flex; align-items: center; gap: 6px;
      padding: 4px 12px 4px 8px;
      background: rgba(0,12,24,0.72);
      border: 1px solid rgba(0,229,255,0.18);
      border-radius: 2px;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      white-space: nowrap;
      animation: fl-enter 0.5s ease backwards;
      transition: opacity 0.4s ease;
    }
    .fl-tag::before {
      content: ""; width: 4px; height: 4px; border-radius: 50%;
      background: #00e5ff;
      box-shadow: 0 0 6px #00e5ff, 0 0 12px #00e5ff;
      flex-shrink: 0;
      animation: fl-dot 2s ease-in-out infinite;
    }
    .fl-tag::after {
      content: ""; position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, #00e5ff, rgba(0,229,255,0.2), transparent);
    }
    .fl-text {
      font-family: "JetBrains Mono", monospace;
      font-size: 0.58rem; letter-spacing: 0.08em;
      color: rgba(0,229,255,0.65);
      text-shadow: 0 0 8px rgba(0,229,255,0.3);
    }

    @keyframes fl-enter {
      from { opacity: 0; transform: translateX(-8px); }
      to   { opacity: 1; transform: none; }
    }
    @keyframes fl-dot {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.25; }
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._raf = requestAnimationFrame(this._loop);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this._raf);
  }

  private _loop = (): void => {
    this._t += 0.016;
    // Force render every ~10 frames to update positions
    if (Math.round(this._t * 60) % 10 === 0) this.requestUpdate();
    this._raf = requestAnimationFrame(this._loop);
  };

  private _getY(lbl: Label): number {
    return lbl.y + lbl.amp * Math.sin(this._t * lbl.speed + lbl.phase);
  }

  render() {
    return html`
      ${this._labels.map(lbl => html`
        <div class="fl-tag"
          style="
            left: ${lbl.x}%;
            top: ${this._getY(lbl)}%;
            transform: translateX(-50%);
            animation-delay: ${lbl.delay}ms;
            opacity: ${lbl.dim ? 0.1 : 0.9};
          "
        >
          <span class="fl-text">${lbl.text}</span>
        </div>
      `)}
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-floating-labels": JarvisFloatingLabels; } }
