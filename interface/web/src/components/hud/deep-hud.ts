// <deep-hud> — JARVIS Floating AI HUD
// Cinematic: absolute-positioned panels at independent Z-depths, global mouse
// parallax (±15° tilt), per-panel bob oscillation, ambient orbs, floating labels.
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { BrainState } from "../deep-cortex-bg";
import { type HudMode } from "./hud-layout-engine";
import { qualityTier } from "../../core/perf";
import "./hud-ambient-canvas";
import "./jarvis-core";
import "./jarvis-telemetry";
import "./jarvis-stream";
import "./jarvis-chat";
import "./jarvis-radar";
import "./jarvis-systems";
import "./jarvis-orbs";
import "./jarvis-floating-labels";

@customElement("deep-hud")
export class DeepHud extends LitElement {
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String, reflect: true }) mode: HudMode = "idle";
  @property({ type: Object }) brainState: BrainState = {};

  @state() private _clock = "";
  @state() private _mx = 0; // –1 … +1
  @state() private _my = 0;

  private _clockTimer = 0;

  private _tickClock = () => {
    const d = new Date();
    this._clock = d.toLocaleTimeString("en-US", { hour12: false });
  };

  private _onMouseMove = (e: MouseEvent) => {
    this._mx = (e.clientX / window.innerWidth  - 0.5) * 2;
    this._my = (e.clientY / window.innerHeight - 0.5) * 2;
    // Push values into CSS custom properties on host for child consumption
    (this.renderRoot as ShadowRoot).host?.setAttribute(
      "style",
      `--mx:${this._mx.toFixed(3)};--my:${this._my.toFixed(3)}`
    );
  };

  connectedCallback(): void {
    super.connectedCallback();
    this.setAttribute("data-quality", qualityTier());
    this._tickClock();
    this._clockTimer = window.setInterval(this._tickClock, 1000);
    window.addEventListener("mousemove", this._onMouseMove, { passive: true });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this._clockTimer);
    window.removeEventListener("mousemove", this._onMouseMove);
  }

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      z-index: 50;
      pointer-events: none;
      font-family: "Rajdhani", "JetBrains Mono", monospace;
      /* JARVIS cyan tokens */
      --j-cyan:  #00e5ff;
      --j-cyan2: #00b8d9;
      --j-dark:  #020912;
      --j-panel: rgba(0,14,28,0.78);
      /* Parallax inputs (set via JS) */
      --mx: 0;
      --my: 0;
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.7s ease, visibility 0.7s ease;
      /* 3-D stage */
      perspective: 1100px;
      perspective-origin: 50% 45%;
    }
    :host([active]) { opacity: 1; visibility: visible; }

    /* Mode accent shifts */
    :host([mode="thinking"])  { --j-cyan: #bf40ff; --j-cyan2: #8020cc; }
    :host([mode="speaking"])  { --j-cyan: #ffb300; --j-cyan2: #cc7000; }
    :host([mode="alert"])     { --j-cyan: #ff2d55; --j-cyan2: #cc0033; }
    :host([mode="listening"]) { --j-cyan: #00ffd1; --j-cyan2: #00b899; }

    /* ── Full-screen dark void background ── */
    .j-bg {
      position: absolute; inset: 0;
      background: radial-gradient(ellipse 110% 110% at 50% 50%,
        #010c1a 0%, #020912 55%, #000407 100%);
      pointer-events: none;
    }
    .j-grid {
      position: absolute; inset: 0; pointer-events: none;
      opacity: 0.055;
      background-image:
        linear-gradient(var(--j-cyan) 1px, transparent 1px),
        linear-gradient(90deg, var(--j-cyan) 1px, transparent 1px);
      background-size: 52px 52px;
      mask-image: radial-gradient(ellipse 90% 90% at 50% 50%, black 30%, transparent 75%);
      -webkit-mask-image: radial-gradient(ellipse 90% 90% at 50% 50%, black 30%, transparent 75%);
    }
    .j-scanlines {
      position: absolute; inset: 0; pointer-events: none;
      background: repeating-linear-gradient(
        to bottom,
        transparent 0px, transparent 3px,
        rgba(0,229,255,0.012) 3px, rgba(0,229,255,0.012) 4px
      );
    }
    hud-ambient-canvas {
      position: absolute; inset: 0; pointer-events: none; z-index: 1;
    }
    .j-vignette {
      position: absolute; inset: 0; pointer-events: none; z-index: 2;
      background: radial-gradient(ellipse 80% 80% at 50% 50%,
        transparent 28%, rgba(0,0,0,0.82) 100%);
    }

    /* ── Corner accent brackets ── */
    .j-corner {
      position: absolute; width: 68px; height: 68px;
      border-color: var(--j-cyan); pointer-events: none; z-index: 6;
      opacity: 0.65; transition: border-color 1s ease, box-shadow 1s ease;
    }
    .j-corner::after {
      content: ""; position: absolute; width: 7px; height: 7px;
      border-radius: 50%; background: var(--j-cyan);
      box-shadow: 0 0 12px var(--j-cyan), 0 0 24px var(--j-cyan);
      animation: j-dot-pulse 2s ease-in-out infinite;
    }
    .j-corner.tl { top: 18px; left: 18px; border-top: 1.5px solid; border-left: 1.5px solid; }
    .j-corner.tl::after { top: -3.5px; left: -3.5px; }
    .j-corner.tr { top: 18px; right: 18px; border-top: 1.5px solid; border-right: 1.5px solid; }
    .j-corner.tr::after { top: -3.5px; right: -3.5px; }
    .j-corner.bl { bottom: 18px; left: 18px; border-bottom: 1.5px solid; border-left: 1.5px solid; }
    .j-corner.bl::after { bottom: -3.5px; left: -3.5px; }
    .j-corner.br { bottom: 18px; right: 18px; border-bottom: 1.5px solid; border-right: 1.5px solid; }
    .j-corner.br::after { bottom: -3.5px; right: -3.5px; }

    /* ── Status pill ── */
    .j-statusbar {
      position: absolute; top: 16px; left: 50%;
      transform: translateX(-50%);
      z-index: 10;
      display: flex; align-items: center; gap: 18px;
      padding: 7px 28px;
      background: rgba(0,10,22,0.88);
      border: 1px solid rgba(0,229,255,0.28);
      border-radius: 32px;
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.07),
        0 0 36px rgba(0,229,255,0.14),
        0 2px 20px rgba(0,0,0,0.7),
        inset 0 1px 0 rgba(0,229,255,0.12);
      white-space: nowrap; pointer-events: none;
      transition: border-color 0.8s ease, box-shadow 0.8s ease;
    }
    .j-sb-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--j-cyan);
      box-shadow: 0 0 10px var(--j-cyan), 0 0 20px var(--j-cyan);
      animation: j-dot-pulse 1.8s ease-in-out infinite;
      flex-shrink: 0;
      transition: background 0.8s ease;
    }
    .j-sb-clock {
      font-size: 1.05rem; font-weight: 700; letter-spacing: 0.18em;
      color: rgba(210,245,255,0.95);
      text-shadow: 0 0 14px rgba(0,229,255,0.45);
    }
    .j-sb-sep {
      width: 1px; height: 18px;
      background: linear-gradient(to bottom, transparent, rgba(0,229,255,0.35), transparent);
    }
    .j-sb-label {
      font-size: 0.7rem; font-weight: 700; letter-spacing: 0.28em;
      text-transform: uppercase; color: var(--j-cyan);
      text-shadow: 0 0 12px var(--j-cyan);
      transition: color 0.8s ease, text-shadow 0.8s ease;
    }
    .j-sb-label.dim { color: rgba(0,229,255,0.3); text-shadow: none; font-weight: 400; }

    /* ══════════════════════════════════════════
       FLOATING PANEL SYSTEM
       Each panel is absolutely positioned with
       its own Z-depth and bob timing.
    ══════════════════════════════════════════ */
    .j-panel {
      position: absolute;
      background: linear-gradient(
        135deg,
        rgba(0,18,36,0.85) 0%,
        rgba(0,10,22,0.92) 100%
      );
      backdrop-filter: blur(32px) saturate(200%) brightness(1.1);
      -webkit-backdrop-filter: blur(32px) saturate(200%) brightness(1.1);
      border: 1px solid rgba(0,229,255,0.2);
      border-radius: 6px;
      overflow: hidden;
      pointer-events: auto;
      /* Holographic multi-layer shadow */
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.07),
        0 8px 48px rgba(0,0,0,0.8),
        0 0 80px rgba(0,229,255,0.05),
        inset 0 1px 0 rgba(0,229,255,0.1),
        inset 0 0 40px rgba(0,10,30,0.5);
      transform-style: preserve-3d;
      will-change: transform;
      transition:
        box-shadow 0.25s ease,
        border-color 0.8s ease;
    }

    /* Holographic top-edge light leak */
    .j-panel::before {
      content: ""; position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg,
        var(--j-cyan) 0%,
        rgba(0,229,255,0.5) 35%,
        rgba(120,240,255,0.2) 65%,
        transparent 100%);
      z-index: 1;
    }
    /* Top-right corner chamfer glow */
    .j-panel::after {
      content: ""; position: absolute;
      top: 0; right: 0; width: 28px; height: 28px;
      background: linear-gradient(225deg, rgba(0,229,255,0.35) 0%, transparent 65%);
    }

    /* Animated rim overlay */
    .j-panel-rim {
      position: absolute; inset: -1px; border-radius: inherit; padding: 1px;
      background: conic-gradient(
        from 0deg,
        transparent 0deg,
        rgba(0,229,255,0.7) 55deg,
        rgba(120,240,255,0.3) 90deg,
        transparent 140deg,
        rgba(0,229,255,0.25) 230deg,
        transparent 290deg
      );
      animation: j-rim-spin 12s linear infinite;
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      mask-composite: exclude;
      pointer-events: none; opacity: 0.5;
    }

    /* ── Panel positions & individual Z-depths + bob phases ── */

    /* LEFT panel — telemetry */
    .j-left {
      left: 18px; top: 60px;
      width: 308px;
      bottom: 18px;
      animation: j-bob-a 5.5s ease-in-out infinite;
      transform:
        translateZ(24px)
        rotateY(calc(var(--mx) * -12deg))
        rotateX(calc(var(--my) * 6deg));
    }
    .j-left:hover {
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.18),
        0 20px 80px rgba(0,0,0,0.9),
        0 0 120px rgba(0,229,255,0.1),
        inset 0 1px 0 rgba(0,229,255,0.18);
      border-color: rgba(0,229,255,0.42);
    }

    /* CENTER panel — core orb */
    .j-center {
      left: 344px; right: 344px;
      top: 60px; bottom: 18px;
      animation: j-bob-b 6.2s ease-in-out infinite;
      transform:
        translateZ(64px)
        rotateY(calc(var(--mx) * -15deg))
        rotateX(calc(var(--my) * 8deg));
    }
    .j-center:hover {
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.22),
        0 28px 100px rgba(0,0,0,0.9),
        0 0 160px rgba(0,229,255,0.12),
        inset 0 1px 0 rgba(0,229,255,0.2);
      border-color: rgba(0,229,255,0.5);
    }

    /* RIGHT panel — systems */
    .j-right {
      right: 18px; top: 60px;
      width: 308px;
      bottom: 162px;
      animation: j-bob-c 4.8s ease-in-out infinite;
      transform:
        translateZ(32px)
        rotateY(calc(var(--mx) * -12deg))
        rotateX(calc(var(--my) * 6deg));
    }
    .j-right:hover {
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.18),
        0 20px 80px rgba(0,0,0,0.9),
        0 0 120px rgba(0,229,255,0.1),
        inset 0 1px 0 rgba(0,229,255,0.18);
      border-color: rgba(0,229,255,0.42);
    }

    /* BOTTOM-LEFT panel — data stream */
    .j-bottom-left {
      left: 18px; right: 344px;
      bottom: 18px; height: 130px;
      animation: j-bob-d 7s ease-in-out infinite;
      transform:
        translateZ(16px)
        rotateY(calc(var(--mx) * -10deg))
        rotateX(calc(var(--my) * 5deg));
    }

    /* BOTTOM-RIGHT panel — chat */
    .j-bottom-right {
      right: 18px; left: calc(100% - 326px);
      bottom: 18px; height: 130px;
      animation: j-bob-e 5.8s ease-in-out infinite;
      transform:
        translateZ(48px)
        rotateY(calc(var(--mx) * -14deg))
        rotateX(calc(var(--my) * 7deg));
    }
    .j-bottom-right:hover {
      box-shadow:
        0 0 0 1px rgba(0,229,255,0.2),
        0 24px 80px rgba(0,0,0,0.9),
        0 0 100px rgba(0,229,255,0.1),
        inset 0 1px 0 rgba(0,229,255,0.18);
      border-color: rgba(0,229,255,0.45);
    }

    /* ── Floating bob keyframes (each panel unique) ── */
    @keyframes j-bob-a {
      0%, 100% { margin-top: 0px; }
      50%       { margin-top: 10px; }
    }
    @keyframes j-bob-b {
      0%, 100% { margin-top: 0px; }
      40%       { margin-top: -12px; }
      80%       { margin-top: 6px; }
    }
    @keyframes j-bob-c {
      0%, 100% { margin-top: 4px; }
      55%       { margin-top: -8px; }
    }
    @keyframes j-bob-d {
      0%, 100% { margin-bottom: 0px; }
      45%       { margin-bottom: 8px; }
    }
    @keyframes j-bob-e {
      0%, 100% { margin-bottom: 2px; }
      35%       { margin-bottom: -10px; }
      70%       { margin-bottom: 6px; }
    }

    /* Panel enter animation */
    @keyframes j-panel-enter {
      from { opacity: 0; transform: translateZ(-40px) scale(0.97); }
      to   { opacity: 1; }
    }
    .j-panel { animation-fill-mode: both; }
    .j-left        { animation: j-panel-enter 0.6s 0.1s cubic-bezier(0.22,1,0.36,1) both, j-bob-a 5.5s 0.7s ease-in-out infinite; }
    .j-center      { animation: j-panel-enter 0.6s 0.0s cubic-bezier(0.22,1,0.36,1) both, j-bob-b 6.2s 0.6s ease-in-out infinite; }
    .j-right       { animation: j-panel-enter 0.6s 0.2s cubic-bezier(0.22,1,0.36,1) both, j-bob-c 4.8s 0.3s ease-in-out infinite; }
    .j-bottom-left { animation: j-panel-enter 0.6s 0.3s cubic-bezier(0.22,1,0.36,1) both, j-bob-d 7.0s 1.2s ease-in-out infinite; }
    .j-bottom-right{ animation: j-panel-enter 0.6s 0.25s cubic-bezier(0.22,1,0.36,1) both, j-bob-e 5.8s 0.9s ease-in-out infinite; }

    /* Ambient orbs layer */
    jarvis-orbs {
      position: absolute; inset: 0; pointer-events: none; z-index: 3;
    }

    /* Floating labels layer */
    jarvis-floating-labels {
      position: absolute; inset: 0; pointer-events: none; z-index: 3;
    }

    /* ── Shared keyframes ── */
    @keyframes j-dot-pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.35; }
    }
    @keyframes j-rim-spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }

    /* Low-quality fallback */
    :host([data-quality="low"]) .j-panel {
      backdrop-filter: none; -webkit-backdrop-filter: none;
      background: rgba(0,12,26,0.97);
      animation: none; transform: none;
    }
    :host([data-quality="low"]) .j-panel { transform: none !important; }
  `;

  render() {
    const mode = this.mode.toUpperCase();
    return html`
      <div class="j-bg"></div>
      <div class="j-grid"></div>
      <div class="j-scanlines"></div>
      <hud-ambient-canvas></hud-ambient-canvas>
      <div class="j-vignette"></div>

      <!-- Corner brackets -->
      <div class="j-corner tl"></div>
      <div class="j-corner tr"></div>
      <div class="j-corner bl"></div>
      <div class="j-corner br"></div>

      <!-- Ambient drifting orbs -->
      <jarvis-orbs></jarvis-orbs>

      <!-- Floating info labels -->
      <jarvis-floating-labels .mode=${this.mode}></jarvis-floating-labels>

      <!-- Status pill -->
      <div class="j-statusbar">
        <span class="j-sb-dot"></span>
        <span class="j-sb-clock">${this._clock}</span>
        <span class="j-sb-sep"></span>
        <span class="j-sb-label">J.A.R.V.I.S — DEEP</span>
        <span class="j-sb-sep"></span>
        <span class="j-sb-label">MODE: ${mode}</span>
        <span class="j-sb-sep"></span>
        <span class="j-sb-label dim">⌘K COMMAND</span>
      </div>

      <!-- Floating panels -->
      <div class="j-panel j-left">
        <div class="j-panel-rim"></div>
        <jarvis-telemetry .mode=${this.mode}></jarvis-telemetry>
      </div>

      <div class="j-panel j-center">
        <div class="j-panel-rim"></div>
        <jarvis-core .state=${this.mode} .brainState=${this.brainState}></jarvis-core>
      </div>

      <div class="j-panel j-right">
        <div class="j-panel-rim"></div>
        <jarvis-systems .mode=${this.mode}></jarvis-systems>
      </div>

      <div class="j-panel j-bottom-left">
        <div class="j-panel-rim"></div>
        <jarvis-stream></jarvis-stream>
      </div>

      <div class="j-panel j-bottom-right">
        <div class="j-panel-rim"></div>
        <jarvis-chat .mode=${this.mode}></jarvis-chat>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "deep-hud": DeepHud; }
}

