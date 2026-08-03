// <jarvis-telemetry> — Left panel: arc gauge rings for CPU/MEM/NET/GPU
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface Metric { label: string; value: number; max: number; unit: string; color: string; }

@customElement("jarvis-telemetry")
export class JarvisTelemetry extends LitElement {
  @property({ type: String }) mode = "idle";

  @state() private _metrics: Metric[] = [
    { label: "CPU",    value: 34, max: 100, unit: "%",  color: "#00e5ff" },
    { label: "MEMORY", value: 61, max: 100, unit: "%",  color: "#00e5ff" },
    { label: "NET I/O",value: 28, max: 100, unit: "MB", color: "#00e5ff" },
    { label: "GPU",    value: 18, max: 100, unit: "%",  color: "#00e5ff" },
    { label: "TEMP",   value: 52, max: 100, unit: "°C", color: "#00e5ff" },
  ];

  private _timer = 0;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      --j-cyan: #00e5ff;
    }
    .t-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 14px 8px;
      border-bottom: 1px solid rgba(0,229,255,0.1);
      flex-shrink: 0;
      position: relative; overflow: hidden;
    }
    /* Scan ticker line sweeping left to right */
    .t-header::after {
      content: "";
      position: absolute; bottom: 0; left: -100%; right: auto;
      width: 60%; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(0,229,255,0.7), transparent);
      animation: t-scan-ticker 3s linear infinite;
    }
    @keyframes t-scan-ticker {
      from { left: -60%; }
      to   { left: 160%; }
    }
    .t-title {
      font-family: "Rajdhani", monospace;
      font-size: 0.65rem; font-weight: 700; letter-spacing: 0.3em;
      text-transform: uppercase; color: rgba(0,229,255,0.55);
    }
    .t-live {
      font-family: monospace; font-size: 0.55rem; letter-spacing: 0.1em;
      color: var(--j-cyan); text-shadow: 0 0 8px var(--j-cyan);
      animation: t-blink 1.2s step-end infinite;
    }
    @keyframes t-blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .gauges { flex:1; display:flex; flex-direction:column; justify-content:center; gap:12px; padding:14px 14px; }

    .gauge-row { display:flex; align-items:center; gap:10px; }
    .g-label {
      font-family:"Rajdhani",monospace; font-size:0.62rem; font-weight:700;
      letter-spacing:0.18em; color:rgba(0,229,255,0.55);
      width:52px; flex-shrink:0;
    }
    .g-track {
      flex:1; height:4px; background:rgba(0,229,255,0.07);
      border-radius:3px; overflow:hidden; position:relative;
    }
    /* Liquid fill with shimmer sweep */
    .g-fill {
      height:100%; border-radius:3px;
      background: linear-gradient(90deg,
        rgba(0,180,220,0.6) 0%,
        #00e5ff 50%,
        rgba(120,240,255,0.9) 100%);
      background-size: 200% 100%;
      box-shadow: 0 0 10px #00e5ff, 0 0 20px rgba(0,229,255,0.3);
      transition: width 0.9s cubic-bezier(0.22,1,0.36,1);
      animation: g-shimmer 2.4s linear infinite;
      position:relative;
    }
    @keyframes g-shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    .g-fill::after {
      content:"";
      position:absolute; right:0; top:-3px;
      width:2px; height:10px;
      background:#fff;
      box-shadow:0 0 8px #00e5ff, 0 0 16px #00e5ff;
      border-radius:1px;
    }
    .g-val {
      font-family:"JetBrains Mono",monospace; font-size:0.66rem; font-weight:700;
      color:rgba(220,245,255,0.9); width:42px; text-align:right; flex-shrink:0;
      text-shadow: 0 0 8px rgba(0,229,255,0.4);
    }

    .arc-wrap {
      display:flex; justify-content:space-around; padding:8px 14px 12px;
      border-top:1px solid rgba(0,229,255,0.08); flex-shrink:0;
    }
    .arc-item { display:flex; flex-direction:column; align-items:center; gap:4px; }
    svg.arc-svg { overflow:visible; }
    .arc-label {
      font-family:"Rajdhani",monospace; font-size:0.55rem;
      letter-spacing:0.15em; color:rgba(0,229,255,0.4);
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._timer = window.setInterval(() => {
      this._metrics = this._metrics.map(m => ({
        ...m,
        value: Math.max(5, Math.min(95, m.value + (Math.random() - 0.48) * 8)),
      }));
    }, 1400);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this._timer); }

  private _arc(val: number, max: number, r: number) {
    const pct = val / max;
    const circ = 2 * Math.PI * r;
    return { circ, offset: circ * (1 - pct) };
  }

  render() {
    const mini = this._metrics.slice(0, 3);
    return html`
      <div class="t-header">
        <span class="t-title">◈ TELEMETRY</span>
        <span class="t-live">● LIVE</span>
      </div>
      <div class="gauges">
        ${this._metrics.map(m => html`
          <div class="gauge-row">
            <span class="g-label">${m.label}</span>
            <div class="g-track">
              <div class="g-fill" style="width:${m.value}%"></div>
            </div>
            <span class="g-val">${Math.round(m.value)}${m.unit}</span>
          </div>
        `)}
      </div>
      <div class="arc-wrap">
        ${mini.map(m => {
          const r = 20; const { circ, offset } = this._arc(m.value, m.max, r);
          return html`
            <div class="arc-item">
              <svg class="arc-svg" width="52" height="52" viewBox="0 0 52 52">
                <circle cx="26" cy="26" r="${r}" fill="none"
                  stroke="rgba(0,229,255,0.08)" stroke-width="4"/>
                <circle cx="26" cy="26" r="${r}" fill="none"
                  stroke="#00e5ff" stroke-width="4"
                  stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
                  stroke-linecap="round"
                  transform="rotate(-90 26 26)"
                  style="filter:drop-shadow(0 0 5px #00e5ff);transition:stroke-dashoffset 0.8s ease"/>
                <text x="26" y="30" text-anchor="middle"
                  font-family="Rajdhani,monospace" font-size="9" font-weight="700"
                  fill="rgba(220,245,255,0.9)">${Math.round(m.value)}</text>
              </svg>
              <span class="arc-label">${m.label}</span>
            </div>
          `;
        })}
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-telemetry": JarvisTelemetry; } }
