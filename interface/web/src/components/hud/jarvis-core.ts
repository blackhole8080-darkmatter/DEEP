// <jarvis-core> — Central JARVIS orb with spinning arc rings and radar sweep
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { BrainState } from "../deep-cortex-bg";

@customElement("jarvis-core")
export class JarvisCore extends LitElement {
  @property({ type: String }) state: string = "idle";
  @property({ type: Object }) brainState: BrainState = {};

  @state() private _angle = 0;
  @state() private _radarAngle = 0;
  @state() private _pulseR = 0;
  @state() private _statusText = "SYSTEMS NOMINAL";

  private _raf = 0;
  private _t = 0;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      position: relative;
      overflow: hidden;
      --j-cyan: #00e5ff;
    }

    .header {
      position: absolute;
      top: 0; left: 0; right: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      border-bottom: 1px solid rgba(0,229,255,0.12);
      z-index: 2;
    }
    .h-title {
      font-family: "Rajdhani", monospace;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.3em;
      text-transform: uppercase;
      color: rgba(0,229,255,0.55);
    }
    .h-status {
      font-family: "JetBrains Mono", monospace;
      font-size: 0.6rem;
      letter-spacing: 0.1em;
      color: var(--j-cyan);
      text-shadow: 0 0 10px var(--j-cyan);
      animation: j-flicker 4s ease-in-out infinite;
    }

    canvas {
      display: block;
      position: relative;
      z-index: 1;
    }

    .state-pill {
      position: absolute;
      bottom: 16px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 5px 16px;
      background: rgba(0,18,32,0.9);
      border: 1px solid rgba(0,229,255,0.25);
      border-radius: 20px;
      white-space: nowrap;
      z-index: 2;
    }
    .pill-dot {
      width: 5px; height: 5px; border-radius: 50%;
      background: var(--j-cyan);
      box-shadow: 0 0 8px var(--j-cyan);
      animation: j-pulse-dot 1.5s ease-in-out infinite;
    }
    .pill-text {
      font-family: "Rajdhani", monospace;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--j-cyan);
      text-shadow: 0 0 10px var(--j-cyan);
    }

    @keyframes j-flicker {
      0%,100%{opacity:1}45%{opacity:1}50%{opacity:0.6}55%{opacity:1}90%{opacity:1}92%{opacity:0.75}94%{opacity:1}
    }
    @keyframes j-pulse-dot {
      0%,100%{opacity:1;box-shadow:0 0 8px var(--j-cyan)}
      50%{opacity:0.4;box-shadow:0 0 3px var(--j-cyan)}
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

  firstUpdated(): void {
    this._drawLoop();
  }

  private _loop = (): void => {
    this._raf = requestAnimationFrame(this._loop);
    this._t += 0.016;
    const speed = this.state === "thinking" ? 2.5 : this.state === "speaking" ? 1.8 : 1;
    this._angle = (this._angle + speed * 0.4) % 360;
    this._radarAngle = (this._radarAngle + speed * 1.2) % 360;
    this._pulseR = 0.5 + Math.sin(this._t * 2) * 0.5;
    this._statusText =
      this.state === "thinking" ? "PROCESSING QUERY" :
      this.state === "speaking" ? "GENERATING RESPONSE" :
      this.state === "listening" ? "LISTENING..." :
      "SYSTEMS NOMINAL";
    this._drawLoop();
  };

  private _drawLoop(): void {
    const canvas = this.renderRoot?.querySelector("canvas") as HTMLCanvasElement | null;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const dpr = Math.min(devicePixelRatio, 2);
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;
    if (canvas.width !== W * dpr || canvas.height !== H * dpr) {
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.scale(dpr, dpr);
    }
    if (W === 0 || H === 0) return;

    const cx = W / 2, cy = H / 2;
    const CYAN = "#00e5ff";
    const CYAN2 = "rgba(0,229,255,";

    ctx.clearRect(0, 0, W, H);

    // ── Background radial fade ──
    const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(W, H) * 0.55);
    bg.addColorStop(0, "rgba(0,40,70,0.35)");
    bg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    const ang = (deg: number) => (deg - 90) * Math.PI / 180;

    // ── Outer orbit ring ──
    ctx.beginPath();
    ctx.arc(cx, cy, 160, 0, Math.PI * 2);
    ctx.strokeStyle = CYAN2 + "0.06)";
    ctx.lineWidth = 1;
    ctx.stroke();

    // ── Rotating dashed arc rings ──
    const rings = [
      { r: 160, dash: [8, 12], speed: 1, w: 1.2, alpha: 0.35 },
      { r: 130, dash: [4, 18], speed: -0.7, w: 1, alpha: 0.25 },
      { r: 100, dash: [12, 8], speed: 1.3, w: 1.5, alpha: 0.45 },
      { r: 70,  dash: [3, 10], speed: -1.5, w: 1, alpha: 0.3  },
    ];
    rings.forEach((ring, i) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(ang(this._angle * (i % 2 === 0 ? 1 : -1) * ring.speed + i * 45));
      ctx.translate(-cx, -cy);
      ctx.beginPath();
      ctx.arc(cx, cy, ring.r, 0, Math.PI * 2);
      ctx.setLineDash(ring.dash);
      ctx.strokeStyle = CYAN2 + ring.alpha + ")";
      ctx.lineWidth = ring.w;
      ctx.shadowColor = CYAN;
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;
      ctx.restore();
    });

    // ── Radar sweep (filled arc sector + glow line) ──
    ctx.save();
    ctx.translate(cx, cy);
    const sweepR = ang(this._radarAngle);
    const sweepSpan = Math.PI * 0.35; // ~63°
    // Filled translucent sector
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, 160, sweepR, sweepR + sweepSpan);
    ctx.closePath();
    const secGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, 160);
    secGrad.addColorStop(0, CYAN2 + "0.22)");
    secGrad.addColorStop(1, CYAN2 + "0.02)");
    ctx.fillStyle = secGrad;
    ctx.fill();
    // Leading glow line
    const sx = Math.cos(sweepR) * 160;
    const sy = Math.sin(sweepR) * 160;
    const lg2 = ctx.createLinearGradient(0, 0, sx, sy);
    lg2.addColorStop(0, CYAN2 + "0.8)");
    lg2.addColorStop(1, CYAN2 + "0.1)");
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(sx, sy);
    ctx.strokeStyle = lg2;
    ctx.lineWidth = 1.5;
    ctx.shadowColor = CYAN;
    ctx.shadowBlur = 14;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();

    // ── Radar blip dots ──
    const blips = [
      { a: 45,  r: 90  },
      { a: 130, r: 140 },
      { a: 210, r: 70  },
      { a: 310, r: 120 },
    ];
    blips.forEach(b => {
      const ba = ang(b.a + this._radarAngle * 0.1);
      const bx = cx + Math.cos(ba) * b.r;
      const by = cy + Math.sin(ba) * b.r;
      const pulse = 0.5 + Math.sin(this._t * 3 + b.a) * 0.5;
      ctx.beginPath();
      ctx.arc(bx, by, 3 * pulse, 0, Math.PI * 2);
      ctx.fillStyle = CYAN;
      ctx.shadowColor = CYAN;
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    });

    // ── Core orb ──
    const coreR = 38 + this._pulseR * 4;
    const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 2.5);
    coreGrad.addColorStop(0, "rgba(180,240,255,0.9)");
    coreGrad.addColorStop(0.3, CYAN2 + "0.7)");
    coreGrad.addColorStop(0.7, CYAN2 + "0.2)");
    coreGrad.addColorStop(1, CYAN2 + "0)");
    ctx.beginPath();
    ctx.arc(cx, cy, coreR * 2.5, 0, Math.PI * 2);
    ctx.fillStyle = coreGrad;
    ctx.fill();

    // Bright core
    ctx.beginPath();
    ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
    ctx.fillStyle = CYAN2 + "0.15)";
    ctx.shadowColor = CYAN;
    ctx.shadowBlur = 30;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Core ring
    ctx.beginPath();
    ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
    ctx.strokeStyle = CYAN;
    ctx.lineWidth = 1.5;
    ctx.shadowColor = CYAN;
    ctx.shadowBlur = 20;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // ── Crosshair lines ──
    const cr = 160;
    [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dx, dy]) => {
      const lg = ctx.createLinearGradient(cx, cy, cx + dx * cr, cy + dy * cr);
      lg.addColorStop(0, CYAN2 + "0.4)");
      lg.addColorStop(1, CYAN2 + "0)");
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + dx * cr, cy + dy * cr);
      ctx.strokeStyle = lg;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    });

    // ── Tick marks on outer ring ──
    for (let i = 0; i < 36; i++) {
      const ta = ang(i * 10);
      const isLong = i % 9 === 0;
      const r1 = 160; const r2 = r1 - (isLong ? 12 : 5);
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ta) * r1, cy + Math.sin(ta) * r1);
      ctx.lineTo(cx + Math.cos(ta) * r2, cy + Math.sin(ta) * r2);
      ctx.strokeStyle = CYAN2 + (isLong ? "0.6" : "0.2") + ")";
      ctx.lineWidth = isLong ? 1.5 : 0.8;
      ctx.stroke();
    }
  }

  render() {
    return html`
      <div class="header">
        <span class="h-title">◈ DEEP // CORE</span>
        <span class="h-status">${this._statusText}</span>
      </div>
      <canvas style="width:100%;height:100%;"></canvas>
      <div class="state-pill">
        <span class="pill-dot"></span>
        <span class="pill-text">${this.state.toUpperCase()}</span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "jarvis-core": JarvisCore; }
}
