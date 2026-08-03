// <jarvis-orbs> — Drifting holographic metric orbs with Lissajous paths
// 6 glowing spheres drift independently. Click to expand gauge.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Orb {
  id: number;
  label: string;
  unit: string;
  value: number;
  color: string;
  // Lissajous parameters
  ax: number; ay: number;   // amplitude (px)
  fx: number; fy: number;   // frequency
  px: number; py: number;   // phase offset (rad)
  cx: number; cy: number;   // center (vw/vh fraction 0-1)
  speed: number;
  expanded: boolean;
}

let _uid = 0;
function makeOrb(label: string, unit: string, value: number, cx: number, cy: number, color = "#00e5ff"): Orb {
  return {
    id: _uid++, label, unit, value, color,
    ax: 60 + Math.random() * 80, ay: 40 + Math.random() * 60,
    fx: 1 + Math.random() * 2, fy: 1 + Math.random() * 2.5,
    px: Math.random() * Math.PI * 2, py: Math.random() * Math.PI * 2,
    cx, cy, speed: 0.18 + Math.random() * 0.22,
    expanded: false,
  };
}

const INITIAL_ORBS: Orb[] = [
  makeOrb("CPU",     "%",   34, 0.5,  0.3,  "#00e5ff"),
  makeOrb("MEM",     "GB",  6.1, 0.72, 0.55, "#00ffd1"),
  makeOrb("NET",     "MB/s",12, 0.3,  0.65, "#00e5ff"),
  makeOrb("LATENCY", "ms",  4,  0.55, 0.78, "#80f0ff"),
  makeOrb("AGENTS",  "",    4,  0.25, 0.42, "#00e5ff"),
  makeOrb("TEMP",    "°C",  52, 0.78, 0.35, "#00ffd1"),
];

@customElement("jarvis-orbs")
export class JarvisOrbs extends LitElement {
  @state() private _orbs: Orb[] = INITIAL_ORBS.map(o => ({ ...o }));
  @state() private _t = 0;

  private _raf = 0;
  private _dataTimer = 0;

  static styles = css`
    :host { display: block; position: absolute; inset: 0; pointer-events: none; }

    .orb-wrap {
      position: absolute;
      pointer-events: auto;
      cursor: pointer;
      transform-style: preserve-3d;
      will-change: transform;
      transition: transform 0.2s ease;
    }
    .orb-wrap:hover .orb-sphere { transform: scale(1.3); }

    .orb-sphere {
      width: 52px; height: 52px;
      border-radius: 50%;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      position: relative;
      transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1);
    }

    /* Core radial glow */
    .orb-sphere::before {
      content: ""; position: absolute; inset: 0;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 30%,
        rgba(180,245,255,0.55) 0%,
        var(--orb-color, #00e5ff) 35%,
        rgba(0,229,255,0.08) 70%,
        transparent 100%);
      box-shadow:
        0 0 18px var(--orb-color, #00e5ff),
        0 0 40px rgba(0,229,255,0.3),
        inset 0 1px 3px rgba(255,255,255,0.4);
    }
    /* Specular highlight */
    .orb-sphere::after {
      content: ""; position: absolute;
      top: 10px; left: 13px; width: 14px; height: 8px;
      border-radius: 50%;
      background: rgba(255,255,255,0.55);
      filter: blur(2px);
    }

    .orb-label {
      font-family: "Rajdhani", monospace;
      font-size: 0.52rem; font-weight: 700;
      letter-spacing: 0.14em; color: rgba(0,0,0,0.8);
      text-shadow: none; position: relative; z-index: 1;
      line-height: 1; margin-top: 2px;
    }
    .orb-val {
      font-family: "JetBrains Mono", monospace;
      font-size: 0.65rem; font-weight: 700;
      color: rgba(0,0,0,0.9); position: relative; z-index: 1;
      line-height: 1;
    }

    /* Trail */
    .orb-trail {
      position: absolute; border-radius: 50%;
      background: radial-gradient(circle, var(--orb-color, #00e5ff) 0%, transparent 70%);
      opacity: 0.12;
      animation: orb-trail-fade 0.8s ease-out forwards;
      pointer-events: none;
    }
    @keyframes orb-trail-fade { to { opacity: 0; transform: scale(2); } }

    /* Expanded popup */
    .orb-expand {
      position: absolute; top: 58px; left: 50%;
      transform: translateX(-50%);
      background: rgba(0,12,26,0.92);
      border: 1px solid rgba(0,229,255,0.35);
      border-radius: 6px; padding: 8px 14px;
      backdrop-filter: blur(20px);
      white-space: nowrap; z-index: 10;
      box-shadow: 0 0 24px rgba(0,229,255,0.2);
      animation: orb-pop-in 0.2s cubic-bezier(0.34,1.56,0.64,1);
    }
    @keyframes orb-pop-in {
      from { opacity: 0; transform: translateX(-50%) scale(0.7); }
      to   { opacity: 1; transform: translateX(-50%) scale(1); }
    }
    .exp-label {
      font-family: "Rajdhani", monospace;
      font-size: 0.62rem; font-weight: 700; letter-spacing: 0.2em;
      color: rgba(0,229,255,0.6); display: block; margin-bottom: 4px;
    }
    .exp-val {
      font-family: "JetBrains Mono", monospace;
      font-size: 1.1rem; font-weight: 700;
      color: #00e5ff; text-shadow: 0 0 12px #00e5ff;
    }
    .exp-bar {
      margin-top: 6px; height: 3px; width: 100px;
      background: rgba(0,229,255,0.12); border-radius: 2px; overflow: hidden;
    }
    .exp-fill {
      height: 100%; background: #00e5ff;
      box-shadow: 0 0 6px #00e5ff;
      border-radius: 2px;
      transition: width 0.6s ease;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._raf = requestAnimationFrame(this._loop);
    this._dataTimer = window.setInterval(() => {
      this._orbs = this._orbs.map(o => ({
        ...o,
        value: Math.max(1, Math.min(99, o.value + (Math.random() - 0.48) * 6)),
      }));
    }, 1800);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this._raf);
    clearInterval(this._dataTimer);
  }

  private _loop = (): void => {
    this._t += 0.016;
    this._raf = requestAnimationFrame(this._loop);
    this._updatePositions();
  };

  private _updatePositions(): void {
    // Trigger re-render by updating positions array
    this._orbs = this._orbs.map(o => ({ ...o }));
  }

  private _getPos(o: Orb): { x: number; y: number } {
    // Lissajous path centered at (cx, cy) * viewport
    const W = window.innerWidth;
    const H = window.innerHeight;
    const bx = o.cx * W;
    const by = o.cy * H;
    return {
      x: bx + o.ax * Math.sin(o.fx * this._t * o.speed + o.px),
      y: by + o.ay * Math.sin(o.fy * this._t * o.speed + o.py),
    };
  }

  private _toggleOrb(id: number): void {
    this._orbs = this._orbs.map(o =>
      o.id === id ? { ...o, expanded: !o.expanded } : { ...o, expanded: false }
    );
  }

  render() {
    return html`
      ${this._orbs.map(o => {
        const pos = this._getPos(o);
        const pct = Math.min(100, Math.max(0, o.value));
        return html`
          <div class="orb-wrap"
            style="
              left: ${pos.x - 26}px;
              top:  ${pos.y - 26}px;
              --orb-color: ${o.color};
            "
            @click=${() => this._toggleOrb(o.id)}
          >
            <div class="orb-sphere">
              <span class="orb-val">${Math.round(o.value)}</span>
              <span class="orb-label">${o.label}</span>
            </div>
            ${o.expanded ? html`
              <div class="orb-expand">
                <span class="exp-label">${o.label} ${o.unit ? `(${o.unit})` : ""}</span>
                <span class="exp-val">${o.value.toFixed(1)}<small style="font-size:0.6em;opacity:0.6"> ${o.unit}</small></span>
                <div class="exp-bar"><div class="exp-fill" style="width:${pct}%"></div></div>
              </div>
            ` : ""}
          </div>
        `;
      })}
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-orbs": JarvisOrbs; } }
