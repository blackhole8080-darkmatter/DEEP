// <thought-stream> — Ambient vertical stream of symbols & fragments
// representing DEEP's live consciousness. Symbols flow upward like bubbles.
// Color and speed vary with cognitive load. Very low opacity, purely ambient.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface ThoughtBubble {
  x: number;
  y: number;
  speed: number;
  symbol: string;
  hue: number;
  alpha: number;
  size: number;
  trail: { x: number; y: number; a: number }[];
}

const SYMBOLS = ["◊", "◈", "◉", "◆", "◐", "◑", "◎", "◊", "◈", "◉", "◆", "◇", "○", "●"];

@customElement("thought-stream")
export class ThoughtStream extends LitElement {
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private bubbles: ThoughtBubble[] = [];
  private dpr = 1;

  @state() public cognitiveLoad: "idle" | "thinking" | "speaking" = "idle";

  static styles = css`
    :host { display: block; position: fixed; right: 0; top: 0; bottom: 0; width: 80px; z-index: 1; pointer-events: none; }
    canvas { width: 100%; height: 100%; display: block; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
  }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    this.dpr = Math.min(window.devicePixelRatio, 2);
    this._resize();
    this._loop();
    window.addEventListener("resize", this._resize);
  }

  private _resize = () => {
    if (!this.canvas) return;
    this.canvas.width = this.canvas.clientWidth * this.dpr;
    this.canvas.height = this.canvas.clientHeight * this.dpr;
    this.ctx?.scale(this.dpr, this.dpr);
  };

  private _spawn() {
    const rate = this.cognitiveLoad === "thinking" ? 0.15 : this.cognitiveLoad === "speaking" ? 0.08 : 0.03;
    if (Math.random() < rate) {
      const w = this.canvas?.clientWidth || 80;
      const h = this.canvas?.clientHeight || 600;
      this.bubbles.push({
        x: Math.random() * w,
        y: h + 10,
        speed: 0.3 + Math.random() * 0.8 + (this.cognitiveLoad === "thinking" ? 0.5 : 0),
        symbol: SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
        hue: this.cognitiveLoad === "thinking" ? 185 : this.cognitiveLoad === "speaking" ? 300 : 210,
        alpha: 0.1 + Math.random() * 0.2,
        size: 8 + Math.random() * 10,
        trail: [],
      });
    }
  }

  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    const w = this.canvas?.clientWidth || 80;
    const h = this.canvas?.clientHeight || 600;
    const ctx = this.ctx;
    if (!ctx) return;

    ctx.clearRect(0, 0, w, h);
    this._spawn();

    for (const b of this.bubbles) {
      b.y -= b.speed;
      b.x += Math.sin(b.y * 0.02) * 0.3;
      b.alpha -= 0.0008;

      // Trail
      b.trail.push({ x: b.x, y: b.y, a: b.alpha });
      if (b.trail.length > 8) b.trail.shift();

      // Draw trail
      for (let i = 0; i < b.trail.length - 1; i++) {
        const t = b.trail[i];
        ctx.beginPath();
        ctx.arc(t.x, t.y, b.size * 0.15 * (i / b.trail.length), 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${b.hue}, 70%, 65%, ${t.a * 0.3 * (i / b.trail.length)})`;
        ctx.fill();
      }

      // Draw symbol
      ctx.font = `${b.size}px var(--ds-font-mono, monospace)`;
      ctx.fillStyle = `hsla(${b.hue}, 80%, 70%, ${b.alpha})`;
      ctx.textAlign = "center";
      ctx.fillText(b.symbol, b.x, b.y);
    }

    this.bubbles = this.bubbles.filter((b) => b.y > -20 && b.alpha > 0);
  };

  render() {
    return html`<canvas></canvas>`;
  }
}
