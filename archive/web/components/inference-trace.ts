// <inference-trace> — Visual reasoning pathway for chat view.
// When DEEP thinks, an organic neural path animates from input → reasoning → output.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface TraceNode {
  x: number; y: number;
  label: string;
  lit: boolean;
  hue: number;
}

@customElement("inference-trace")
export class InferenceTrace extends LitElement {
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private time = 0;
  private dpr = 1;

  @state() public phase: "idle" | "perceive" | "recall" | "reason" | "generate" | "complete" = "idle";

  private nodes: TraceNode[] = [
    { x: 40, y: 50, label: "Input", lit: false, hue: 45 },
    { x: 120, y: 30, label: "Recall", lit: false, hue: 270 },
    { x: 200, y: 50, label: "Reason", lit: false, hue: 185 },
    { x: 280, y: 30, label: "Generate", lit: false, hue: 300 },
    { x: 360, y: 50, label: "Output", lit: false, hue: 140 },
  ];

  static styles = css`
    :host { display: block; width: 100%; height: 64px; position: relative; }
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
    // Scale nodes to canvas width
    const w = this.canvas.clientWidth || 400;
    const scale = w / 400;
    for (const n of this.nodes) { n.x = [40, 120, 200, 280, 360][this.nodes.indexOf(n)] * scale; }
  };

  private _phaseToIndex(): number {
    switch (this.phase) {
      case "perceive": return 1;
      case "recall": return 2;
      case "reason": return 3;
      case "generate": return 4;
      case "complete": return 5;
      default: return 0;
    }
  }

  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    this.time++;
    const w = this.canvas?.clientWidth || 400;
    const h = this.canvas?.clientHeight || 64;
    const ctx = this.ctx;
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    const phaseIdx = this._phaseToIndex();
    const progress = this.phase === "idle" ? 0 : Math.min(1, (this.time % 120) / 120);

    // Update lit state
    for (let i = 0; i < this.nodes.length; i++) {
      this.nodes[i].lit = i <= phaseIdx || (i === phaseIdx && progress > 0.3);
    }

    // Draw connections
    for (let i = 0; i < this.nodes.length - 1; i++) {
      const a = this.nodes[i], b = this.nodes[i + 1];
      const isActive = i < phaseIdx;
      const isCurrent = i === phaseIdx;

      ctx.beginPath();
      const mx = (a.x + b.x) / 2;
      const my = Math.min(a.y, b.y) - 20;
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(mx, my, b.x, b.y);
      ctx.strokeStyle = isActive
        ? `hsla(${a.hue}, 70%, 55%, 0.5)`
        : isCurrent
          ? `hsla(${a.hue}, 70%, 55%, ${0.15 + Math.sin(this.time * 0.05) * 0.1})`
          : `hsla(${a.hue}, 30%, 40%, 0.08)`;
      ctx.lineWidth = isActive ? 2 : isCurrent ? 1.5 : 1;
      ctx.shadowBlur = isActive ? 6 : 0;
      ctx.shadowColor = `hsla(${a.hue}, 70%, 55%, 0.4)`;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Traveling pulse on active edge
      if (isCurrent && this.phase !== "idle") {
        const t = (this.time * 0.008) % 1;
        const px = (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * mx + t * t * b.x;
        const py = (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * my + t * t * b.y;
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${a.hue}, 90%, 75%, ${1 - t * 0.5})`;
        ctx.shadowBlur = 8;
        ctx.shadowColor = `hsla(${a.hue}, 90%, 75%, 0.5)`;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    // Draw nodes
    for (const n of this.nodes) {
      const r = n.lit ? 6 : 4;
      const alpha = n.lit ? 0.9 : 0.25;

      // Glow
      if (n.lit) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 2.5, 0, Math.PI * 2);
        const g = ctx.createRadialGradient(n.x, n.y, r * 0.5, n.x, n.y, r * 2.5);
        g.addColorStop(0, `hsla(${n.hue}, 80%, 60%, 0.15)`);
        g.addColorStop(1, `hsla(${n.hue}, 80%, 60%, 0)`);
        ctx.fillStyle = g;
        ctx.fill();
      }

      // Core
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${n.hue}, 80%, 65%, ${alpha})`;
      ctx.shadowBlur = n.lit ? 10 : 0;
      ctx.shadowColor = `hsla(${n.hue}, 80%, 65%, 0.5)`;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Label
      ctx.font = `500 ${n.lit ? 10 : 9}px var(--ds-font-mono, monospace)`;
      ctx.fillStyle = n.lit ? `hsla(${n.hue}, 70%, 85%, ${alpha})` : `hsla(${n.hue}, 30%, 60%, ${alpha})`;
      ctx.textAlign = "center";
      ctx.fillText(n.label, n.x, n.y + r + 12);
    }
  };

  render() {
    return html`<canvas></canvas>`;
  }
}
