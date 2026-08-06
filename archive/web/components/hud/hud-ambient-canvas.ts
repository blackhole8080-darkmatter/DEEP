// <hud-ambient-canvas> — Layer 1 ambient particle field
// 200 lightweight dots drifting in parallax. Reacts to mouse as "wind."
// Auto-degrades to 100 particles if FPS drops below 45 for 3 frames.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { particleBudget } from "../../core/perf";

// JARVIS cyan palette — strictly cyan/teal/white
const NEON_COLORS = [
  { r: 0,   g: 229, b: 255 }, // cyan (primary)
  { r: 0,   g: 229, b: 255 }, // cyan (weighted)
  { r: 0,   g: 229, b: 255 }, // cyan (weighted)
  { r: 0,   g: 255, b: 209 }, // teal
  { r: 120, g: 240, b: 255 }, // light cyan
  { r: 255, g: 255, b: 255 }, // white spark
];

interface Particle {
  x: number; y: number;
  vx: number; vy: number;
  size: number;
  alpha: number;
  depth: number;
  color: { r: number; g: number; b: number };
  twinkle: number;   // phase for alpha oscillation
  isStar: boolean;   // larger glow node
}

@customElement("hud-ambient-canvas")
export class HudAmbientCanvas extends LitElement {
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private particles: Particle[] = [];

  @state() private _count = particleBudget();   // 200 high-end, 80 low-end
  private _degraded = false;
  private _lastTime = 0;
  private _lowFpsCount = 0;

  private _mouseX = -9999;
  private _mouseY = -9999;

  static styles = css`
    :host {
      position: absolute;
      inset: 0;
      z-index: 1;
      pointer-events: none;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }
    :host([degraded]) canvas {
      image-rendering: pixelated;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._initParticles();
    window.addEventListener("mousemove", this._onMouseMove);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    window.removeEventListener("mousemove", this._onMouseMove);
  }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    this._resize();
    this._loop();
  }

  private _onMouseMove = (e: MouseEvent) => {
    this._mouseX = e.clientX;
    this._mouseY = e.clientY;
  };

  private _initParticles() {
    this.particles = Array.from({ length: this._count }, (_, i) => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      size: 0.6 + Math.random() * 2.2,
      alpha: 0.25 + Math.random() * 0.55,
      depth: 0.25 + Math.random() * 0.75,
      color: NEON_COLORS[Math.floor(Math.random() * NEON_COLORS.length)],
      twinkle: Math.random() * Math.PI * 2,
      isStar: i < Math.floor(this._count * 0.06), // 6% are stars
    }));
  }

  private _resize = () => {
    if (!this.canvas) return;
    const dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = this.canvas.clientWidth * dpr;
    this.canvas.height = this.canvas.clientHeight * dpr;
    // setTransform (not scale) — scale() compounds on every resize, progressively
    // zooming the field; setTransform resets the matrix each time.
    this.ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  private _checkFps(now: number): void {
    const delta = now - this._lastTime;
    this._lastTime = now;
    // 22.2ms = ~45fps
    if (delta > 22.2) {
      this._lowFpsCount++;
    } else {
      this._lowFpsCount = 0;
    }
    if (this._lowFpsCount > 3 && !this._degraded) {
      this._degraded = true;
      // Cap, don't raise — a low-tier device already starts below 100.
      this._count = Math.min(this._count, 100);
      this.setAttribute("degraded", "");
    }
  }

  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    const now = performance.now();
    this._checkFps(now);

    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    const ctx = this.ctx;

    // Deep void trail fade
    ctx.fillStyle = "rgba(3, 4, 10, 0.18)";
    ctx.fillRect(0, 0, w, h);

    const activeParticles = this.particles.slice(0, this._count);

    // Draw connection lines between nearby particles first (behind particles)
    const connectionDist = 90;
    for (let i = 0; i < Math.min(activeParticles.length, 80); i++) {
      const a = activeParticles[i];
      for (let j = i + 1; j < Math.min(activeParticles.length, 80); j++) {
        const b = activeParticles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < connectionDist) {
          const opacity = (1 - dist / connectionDist) * 0.12;
          const { r, g, bl: blC } = { r: a.color.r, g: a.color.g, bl: a.color.b };
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(${r},${g},${blC},${opacity})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    for (let i = 0; i < this._count; i++) {
      const p = this.particles[i];
      if (!p) continue;

      // Mouse wind force
      const dx = p.x - this._mouseX;
      const dy = p.y - this._mouseY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 220 && this._mouseX > 0) {
        const force = (1 / (dist + 1)) * 0.4 * p.depth;
        p.vx += (dx / dist) * force;
        p.vy += (dy / dist) * force;
      }

      // Apply velocity with depth parallax
      p.x += p.vx * p.depth;
      p.y += p.vy * p.depth;

      // Friction
      p.vx *= 0.97;
      p.vy *= 0.97;

      // Gentle ambient drift
      p.vx += (Math.random() - 0.5) * 0.018;
      p.vy += (Math.random() - 0.5) * 0.018;

      // Twinkle
      p.twinkle += 0.025 + p.depth * 0.01;
      const twinkAlpha = p.alpha * (0.55 + Math.sin(p.twinkle) * 0.45);

      // Wrap around edges
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      const { r, g, b: pb } = p.color;
      const r2 = p.size * p.depth;

      if (p.isStar) {
        // Star: large glow halo + bright core
        const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r2 * 7);
        halo.addColorStop(0,   `rgba(${r},${g},${pb},${twinkAlpha * 0.9})`);
        halo.addColorStop(0.3, `rgba(${r},${g},${pb},${twinkAlpha * 0.4})`);
        halo.addColorStop(1,   `rgba(${r},${g},${pb},0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r2 * 7, 0, Math.PI * 2);
        ctx.fillStyle = halo;
        ctx.fill();
        // Bright core
        ctx.beginPath();
        ctx.arc(p.x, p.y, r2 * 1.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${twinkAlpha})`;
        ctx.fill();
      } else {
        // Regular particle: inner glow + core dot
        const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r2 * 3.5);
        grd.addColorStop(0,   `rgba(${r},${g},${pb},${twinkAlpha * 0.7})`);
        grd.addColorStop(1,   `rgba(${r},${g},${pb},0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r2 * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();
        // Core
        ctx.beginPath();
        ctx.arc(p.x, p.y, r2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${pb},${Math.min(1, twinkAlpha * 1.4)})`;
        ctx.fill();
      }
    }
  };

  render() {
    return html`<canvas></canvas>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hud-ambient-canvas": HudAmbientCanvas;
  }
}
