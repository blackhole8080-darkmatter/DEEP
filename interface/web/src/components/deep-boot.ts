// <deep-boot> — DEEP startup sequence overlay
// Shows for ~2.5s on first visit, then auto-fades. Matches legacy HUD boot feel.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

@customElement("deep-boot")
export class DeepBoot extends LitElement {
  @state() private visible = true;
  @state() private progress = 0;
  private raf = 0;
  private start = performance.now();

  static styles = css`
    :host {
      position: fixed; inset: 0; z-index: 100;
      display: grid; place-items: center;
      background: #000205;
      transition: opacity 1s ease, visibility 1s;
    }
    :host(.fade) { opacity: 0; visibility: hidden; pointer-events: none; }
    .wrap { display: grid; gap: 28px; text-align: center; position: relative; }
    .ring-wrap {
      position: relative;
      width: 140px; height: 140px;
      margin: 0 auto;
      display: grid; place-items: center;
    }
    .ring-svg {
      position: absolute; inset: 0;
      transform: rotate(-90deg);
    }
    .ring-track { fill: none; stroke: rgba(0,229,255,0.06); stroke-width: 2; }
    .ring-fill {
      fill: none; stroke: var(--ds-accent, #00e5ff); stroke-width: 2;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.1s linear;
      filter: drop-shadow(0 0 4px var(--ds-accent, #00e5ff));
    }
    .logo {
      font-size: 2.4rem; font-weight: 700; letter-spacing: 0.12em;
      color: #eaf6ff; text-shadow: 0 0 40px rgba(0,229,255,0.35);
      animation: text-glow 2s ease-in-out infinite;
    }
    .om { color: var(--ds-accent, #00e5ff); margin-right: 8px; }
    .tagline {
      font-size: 0.72rem; letter-spacing: 0.28em; color: rgba(234,246,255,0.45);
      text-transform: uppercase;
    }
    .bar-wrap {
      width: 220px; height: 3px; margin: 8px auto 0;
      background: rgba(0,229,255,0.08); border-radius: 2px; overflow: hidden;
    }
    .bar {
      height: 100%; width: 0%;
      background: linear-gradient(90deg, rgba(0,229,255,0.6), rgba(0,255,209,0.8));
      border-radius: 2px; transition: width 0.1s linear;
      box-shadow: 0 0 12px rgba(0,229,255,0.3);
    }
    .status {
      font-size: 0.65rem; font-family: var(--ds-font-mono, monospace);
      color: rgba(234,246,255,0.35); letter-spacing: 0.08em;
      min-height: 1.2em;
    }
    .ready-flash {
      position: absolute; inset: 0;
      background: radial-gradient(circle at center, rgba(0,229,255,0.15), transparent 60%);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.4s ease;
    }
    :host(.ready) .ready-flash { opacity: 1; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._loop();
  }

  private _loop = () => {
    const elapsed = performance.now() - this.start;
    this.progress = Math.min(100, (elapsed / 3800) * 100);
    if (elapsed > 3500 && elapsed < 4000) {
      this.classList.add("ready");
    }
    if (elapsed > 4000) {
      this.classList.add("fade");
      setTimeout(() => { this.visible = false; }, 1000);
      return;
    }
    this.raf = requestAnimationFrame(this._loop);
  };

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
  }

  render() {
    if (!this.visible) return html``;
    const c = 2 * Math.PI * 66;
    const dash = `${c * (this.progress / 100)} ${c}`;
    const statuses = [
      "INITIALISING NEURAL SUBSTRATE...",
      "LOADING KNOWLEDGE GRAPH...",
      "WARMING EMBEDDING MODEL...",
      "CALIBRATING PREDICTIVE ENGINE...",
      "ESTABLISHING SECURE UPLINK...",
      "MOUNTING VOICE INTERFACE...",
      "COALESCING INTELLIGENCE CORE...",
      "SYSTEM READY",
    ];
    const idx = Math.min(statuses.length - 1, Math.floor((this.progress / 100) * statuses.length));
    return html`
      <div class="wrap">
        <div class="ring-wrap">
          <svg class="ring-svg" viewBox="0 0 140 140">
            <circle class="ring-track" cx="70" cy="70" r="66" />
            <circle class="ring-fill" cx="70" cy="70" r="66" stroke-dasharray="${dash}" />
          </svg>
          <div class="logo"><span class="om">ॐ</span></div>
        </div>
        <div class="tagline">Dynamic · Empathic · Execution · Processor</div>
        <div class="bar-wrap"><div class="bar" style="width:${this.progress}%"></div></div>
        <div class="status">${statuses[idx]}</div>
        <div class="ready-flash"></div>
      </div>
    `;
  }
}
