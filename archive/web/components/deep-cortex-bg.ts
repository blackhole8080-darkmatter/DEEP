// <deep-cortex-bg> — DEEP's JARVIS-style HUD brain interface.
// Technical, holographic, angular. Circuit-trace synapses, rotating ring nodes,
// corner data panels, central DEEP core, hex grid background, targeting brackets.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

export type BrainStatus = "idle" | "active" | "speaking" | "thinking" | "warning" | "indexing";
export type BrainState = Partial<Record<string, BrainStatus>>;

// HUD color palette — saturated neon against deep space
const C = {
  idle:     "#00ff88", // green
  active:   "#00e5ff", // cyan
  speaking: "#ff00aa", // magenta
  thinking: "#ffaa00", // amber
  warning:  "#ff3333", // red
  indexing: "#aa66ff", // violet
  grid:     "rgba(0, 200, 255, 0.06)",
  panel:    "rgba(0, 20, 40, 0.45)",
  text:     "rgba(200, 230, 255, 0.9)",
  dim:      "rgba(100, 140, 180, 0.35)",
};

const STATUS_HUE: Record<BrainStatus, number> = {
  idle: 150, active: 185, speaking: 320, thinking: 40, warning: 0, indexing: 270,
};

interface NodeDef {
  key: string; label: string; nx: number; ny: number;
  ring: number; // ring tier: 0=inner, 1=mid, 2=outer
}

// Radial HUD layout — nodes orbit in concentric rings around central DEEP core
const NODES: NodeDef[] = [
  { key: "reasoning",  label: "REASONING",  nx: 0.50, ny: 0.28, ring: 0 },
  { key: "chat",       label: "CHAT",       nx: 0.35, ny: 0.38, ring: 1 },
  { key: "agents",     label: "AGENTS",     nx: 0.65, ny: 0.38, ring: 1 },
  { key: "memory",     label: "MEMORY",     nx: 0.22, ny: 0.55, ring: 2 },
  { key: "voice",      label: "VOICE",      nx: 0.40, ny: 0.60, ring: 2 },
  { key: "research",   label: "RESEARCH",   nx: 0.60, ny: 0.60, ring: 2 },
  { key: "security",   label: "SECURITY",   nx: 0.78, ny: 0.55, ring: 2 },
  { key: "system",     label: "SYSTEM",     nx: 0.30, ny: 0.75, ring: 2 },
  { key: "network",    label: "NETWORK",    nx: 0.50, ny: 0.78, ring: 2 },
  { key: "predictive", label: "PREDICTIVE", nx: 0.70, ny: 0.75, ring: 2 },
];

// Circuit-trace edges (organized by ring connections)
const EDGES: [string, string][] = [
  ["reasoning", "chat"], ["reasoning", "agents"], ["reasoning", "memory"],
  ["chat", "voice"], ["chat", "memory"],
  ["agents", "research"], ["agents", "security"], ["agents", "predictive"],
  ["memory", "system"], ["memory", "research"],
  ["voice", "system"], ["voice", "network"],
  ["research", "network"], ["research", "predictive"],
  ["security", "network"], ["security", "system"],
  ["system", "network"], ["network", "predictive"],
];

interface RNode extends NodeDef {
  x: number; y: number;
  level: number; target: number;
  angle: number; // orbital angle
  ringR: number; // actual pixel radius from center
}
interface Packet { from: number; to: number; t: number; speed: number; hue: number; }
interface Blip { x: number; y: number; t: number; hue: number; }
interface Glitch { x: number; y: number; w: number; h: number; t: number; }
@customElement("deep-cortex-bg")
export class DeepCortexBg extends LitElement {
  @property({ attribute: false }) brainState: BrainState = {};
  @property({ attribute: false }) cognitiveState: "idle" | "thinking" | "speaking" | "alert" = "idle";

  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private dpr = 1;
  private lastDraw = 0;
  private reduced = false;
  private w = 0; private h = 0;
  private t = 0;
  private nodes: RNode[] = [];
  private idx: Record<string, number> = {};
  private packets: Packet[] = [];
  private blips: Blip[] = [];
  private glitches: Glitch[] = [];
  private mouse = { x: -9999, y: -9999 };
  private hover = -1;
  private corePulse = 0;
  private rotAngle = 0;

  static styles = css`
    :host { display: block; position: fixed; inset: 0; z-index: 0; pointer-events: none; }
    canvas { width: 100%; height: 100%; display: block; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.addEventListener("mousemove", this._onMouse, { passive: true });
    window.addEventListener("resize", this._resize);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    window.removeEventListener("mousemove", this._onMouse);
    window.removeEventListener("resize", this._resize);
  }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d", { alpha: true })!;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this._resize();
    this.nodes = NODES.map((n, i) => {
      this.idx[n.key] = i;
      return { ...n, x: 0, y: 0, level: 0.15, target: 0.15, angle: 0, ringR: 0 };
    });
    this._layout();
    if (this.reduced) { this._applyState(); this._draw(performance.now()); }
    else this.raf = requestAnimationFrame(this._loop);
  }

  updated(): void { this._applyState(); }

  private _onMouse = (e: MouseEvent) => { this.mouse.x = e.clientX; this.mouse.y = e.clientY; };

  private _resize = () => {
    if (!this.canvas) return;
    this.w = this.canvas.clientWidth; this.h = this.canvas.clientHeight;
    this.canvas.width = this.w * this.dpr; this.canvas.height = this.h * this.dpr;
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this._layout();
  };

  private _layout() {
    const cx = this.w * 0.5, cy = this.h * 0.52;
    const baseR = Math.min(this.w, this.h) * 0.32;
    for (const n of this.nodes) {
      // Convert normalized position to polar-ish layout around center
      const dx = (n.nx - 0.5) * 2; const dy = (n.ny - 0.5) * 2;
      n.angle = Math.atan2(dy, dx);
      n.ringR = baseR * (0.35 + n.ring * 0.32);
      n.x = cx + Math.cos(n.angle) * n.ringR;
      n.y = cy + Math.sin(n.angle) * n.ringR * 0.85; // slight vertical compression for oval shape
    }
  }

  private _status(key: string): BrainStatus {
    const s = this.brainState[key];
    if (s) return s;
    if (key === "chat") {
      if (this.cognitiveState === "speaking") return "speaking";
      if (this.cognitiveState === "thinking") return "active";
    }
    if (key === "reasoning" && this.cognitiveState === "thinking") return "thinking";
    return "idle";
  }

  private _applyState() {
    if (!this.nodes.length) return;
    for (const n of this.nodes) {
      const st = this._status(n.key);
      const tgt = st === "idle" ? 0.12 : 1;
      if (tgt > 0.5 && n.target <= 0.5) {
        const hue = STATUS_HUE[st];
        this.blips.push({ x: n.x, y: n.y, t: 0, hue });
        // Spawn data packets to connected neighbours
        const nbrs = EDGES.filter((e) => e[0] === n.key || e[1] === n.key);
        for (const nb of nbrs.slice(0, 3)) {
          const other = nb[0] === n.key ? nb[1] : nb[0];
          const a = this.idx[n.key], b = this.idx[other];
          if (a !== undefined && b !== undefined) {
            this.packets.push({ from: a, to: b, t: 0, speed: 0.025 + Math.random() * 0.02, hue });
          }
        }
      }
      n.target = tgt;
    }
  }

  private _activity(): number {
    let m = 0;
    for (const n of this.nodes) m = Math.max(m, n.target);
    return Math.max(m === 1 ? 1 : 0, this.packets.length || this.blips.length ? 1 : 0, this.hover >= 0 ? 0.5 : 0);
  }

  private _loop = (ts: number) => {
    this.raf = requestAnimationFrame(this._loop);
    const act = this._activity();
    const interval = act >= 1 ? 0 : act > 0.3 ? 33 : 100;
    if (ts - this.lastDraw < interval) return;
    this.lastDraw = ts; this.t = ts / 1000;
    this._draw(ts);
  };
  private _draw(_ts: number) {
    const ctx = this.ctx; if (!ctx) return;
    const w = this.w, h = this.h; const t = this.t;
    this.corePulse += 0.02;
    this.rotAngle += 0.003;

    ctx.clearRect(0, 0, w, h);

    // hover detect
    this.hover = -1; let best = 50 * 50;
    for (let i = 0; i < this.nodes.length; i++) {
      const d2 = (this.nodes[i].x - this.mouse.x) ** 2 + (this.nodes[i].y - this.mouse.y) ** 2;
      if (d2 < best) { best = d2; this.hover = i; }
    }

    this._drawBackground(ctx, w, h, t);
    this._drawHexGrid(ctx, w, h, t);
    this._drawOrbitRings(ctx, w, h, t);
    this._drawCircuitTraces(ctx, t);
    this._drawCore(ctx, w, h, t);
    this._drawNodes(ctx, t);
    this._drawPackets(ctx);
    this._drawBlips(ctx);
    this._drawCornerPanels(ctx, w, h, t);
    this._drawTargetingBrackets(ctx);
    this._drawScanSweep(ctx, w, h, t);
    this._drawVignette(ctx, w, h);

    // Occasional glitch
    if (!this.reduced && Math.random() < 0.01) {
      this.glitches.push({ x: Math.random() * w, y: Math.random() * h, w: 40 + Math.random() * 120, h: 2 + Math.random() * 6, t: 0 });
    }
    this._drawGlitches(ctx);
  }

  private _drawBackground(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
    // Deep space radial gradient
    const grad = ctx.createRadialGradient(w * 0.5, h * 0.5, 0, w * 0.5, h * 0.5, Math.max(w, h) * 0.8);
    grad.addColorStop(0, "#0a1020");
    grad.addColorStop(0.5, "#060a14");
    grad.addColorStop(1, "#020408");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Subtle starfield
    ctx.save();
    ctx.globalAlpha = 0.3;
    for (let i = 0; i < 80; i++) {
      const sx = (i * 137.5 + t * 2) % w;
      const sy = (i * 89.3 + Math.sin(t * 0.1 + i) * 3) % h;
      const sr = 0.5 + (i % 3) * 0.5;
      ctx.fillStyle = `rgba(180, 210, 255, ${0.2 + (i % 5) * 0.08})`;
      ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  private _drawHexGrid(ctx: CanvasRenderingContext2D, w: number, h: number, _t: number) {
    ctx.save();
    ctx.globalAlpha = 0.04;
    ctx.strokeStyle = C.grid;
    ctx.lineWidth = 0.5;
    const hexSize = 42;
    const cx = w * 0.5, cy = h * 0.52;
    for (let row = -8; row <= 8; row++) {
      for (let col = -12; col <= 12; col++) {
        const x = cx + col * hexSize * 1.5;
        const y = cy + row * hexSize * Math.sqrt(3) + (col % 2) * hexSize * Math.sqrt(3) / 2;
        const d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
        const fade = Math.max(0, 1 - d / (Math.max(w, h) * 0.45));
        if (fade < 0.01) continue;
        ctx.globalAlpha = 0.03 * fade;
        ctx.beginPath();
        for (let s = 0; s < 6; s++) {
          const ang = (s / 6) * Math.PI * 2 + Math.PI / 6;
          const hx = x + Math.cos(ang) * hexSize;
          const hy = y + Math.sin(ang) * hexSize;
          if (s === 0) ctx.moveTo(hx, hy); else ctx.lineTo(hx, hy);
        }
        ctx.closePath(); ctx.stroke();
      }
    }
    ctx.restore();
  }

  private _drawOrbitRings(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
    const cx = w * 0.5, cy = h * 0.52;
    const baseR = Math.min(w, h) * 0.32;
    const rings = [0.35, 0.67, 1.0];
    ctx.save();
    for (let i = 0; i < rings.length; i++) {
      const r = baseR * rings[i];
      const dash = [4 + i * 3, 12 + i * 6];
      const offset = -(t * (8 + i * 4)) % (dash[0] + dash[1]);
      ctx.beginPath();
      ctx.ellipse(cx, cy, r, r * 0.85, 0, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 180, 255, ${0.04 + i * 0.015})`;
      ctx.lineWidth = 0.8;
      ctx.setLineDash(dash);
      ctx.lineDashOffset = offset;
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.restore();
  }

  private _drawCircuitTraces(ctx: CanvasRenderingContext2D, _t: number) {
    for (const [ak, bk] of EDGES) {
      const a = this.nodes[this.idx[ak]], b = this.nodes[this.idx[bk]];
      const lvl = Math.max(a.level, b.level);
      const lit = lvl > 0.3;
      const stA = this._status(ak), stB = this._status(bk);
      const hue = STATUS_HUE[a.level >= b.level ? stA : stB];
      const col = lit ? `hsla(${hue}, 85%, 55%, ${0.15 + lvl * 0.35})` : "rgba(0, 100, 160, 0.04)";

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      // Circuit-style elbow connector
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      if (Math.abs(a.x - b.x) > Math.abs(a.y - b.y)) {
        ctx.lineTo(mx, a.y); ctx.lineTo(mx, b.y); ctx.lineTo(b.x, b.y);
      } else {
        ctx.lineTo(a.x, my); ctx.lineTo(b.x, my); ctx.lineTo(b.x, b.y);
      }
      ctx.strokeStyle = col;
      ctx.lineWidth = lit ? 1.5 + lvl * 2.5 : 0.6;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (lit) {
        ctx.shadowBlur = 10 + lvl * 15;
        ctx.shadowColor = `hsla(${hue}, 80%, 50%, ${0.4 + lvl * 0.4})`;
      } else {
        ctx.shadowBlur = 0;
      }
      ctx.stroke(); ctx.shadowBlur = 0;
    }
  }
  private _drawCore(ctx: CanvasRenderingContext2D, w: number, h: number, _t: number) {
    const cx = w * 0.5, cy = h * 0.52;
    const pulse = 1 + Math.sin(this.corePulse) * 0.08;
    const r = 22 * pulse;

    // Outer rotating ring
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.rotAngle);
    ctx.beginPath();
    for (let i = 0; i < 32; i++) {
      const a1 = (i / 32) * Math.PI * 2;
      const a2 = ((i + 0.5) / 32) * Math.PI * 2;
      const rr = r + 14 + (i % 3) * 3;
      ctx.moveTo(Math.cos(a1) * rr, Math.sin(a1) * rr);
      ctx.lineTo(Math.cos(a2) * rr, Math.sin(a2) * rr);
    }
    ctx.strokeStyle = "rgba(0, 200, 255, 0.25)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // Inner counter-rotating ring
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-this.rotAngle * 1.5);
    ctx.beginPath(); ctx.arc(0, 0, r + 8, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(0, 180, 230, 0.15)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 10]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    // Core glow
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 3);
    glow.addColorStop(0, "rgba(0, 200, 255, 0.15)");
    glow.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(cx, cy, r * 3, 0, Math.PI * 2); ctx.fill();

    // Core orb
    const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    core.addColorStop(0, "rgba(200, 245, 255, 0.95)");
    core.addColorStop(0.4, "rgba(0, 200, 255, 0.7)");
    core.addColorStop(1, "rgba(0, 80, 150, 0.2)");
    ctx.fillStyle = core;
    ctx.shadowBlur = 25;
    ctx.shadowColor = "rgba(0, 200, 255, 0.5)";
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    // DEEP label
    ctx.font = "700 11px 'Courier New', monospace";
    ctx.fillStyle = "rgba(200, 245, 255, 0.85)";
    ctx.textAlign = "center";
    ctx.fillText("DEEP", cx, cy + r + 18);
    ctx.textAlign = "left";
  }

  private _drawNodes(ctx: CanvasRenderingContext2D, t: number) {
    for (let i = 0; i < this.nodes.length; i++) {
      const n = this.nodes[i];
      n.level += (n.target - n.level) * 0.08;
      const st = this._status(n.key);
      const hue = STATUS_HUE[st];
      const lit = n.level > 0.3;
      const r = (6 + n.level * 10);
      const hover = this.hover === i;

      // Outer ring (rotating segments)
      ctx.save();
      ctx.translate(n.x, n.y);
      ctx.rotate(t * 0.3 + i * 2.1);
      ctx.beginPath();
      for (let s = 0; s < 8; s++) {
        const a1 = (s / 8) * Math.PI * 2;
        const a2 = ((s + 0.3) / 8) * Math.PI * 2;
        const rr = r + 10 + n.level * 6;
        ctx.arc(0, 0, rr, a1, a2);
      }
      ctx.strokeStyle = `hsla(${hue}, 70%, 60%, ${0.15 + n.level * 0.3})`;
      ctx.lineWidth = 1.2;
      if (lit) {
        ctx.shadowBlur = 8 + n.level * 12;
        ctx.shadowColor = `hsla(${hue}, 80%, 50%, ${0.3 + n.level * 0.4})`;
      }
      ctx.stroke(); ctx.shadowBlur = 0;
      ctx.restore();

      // Inner ring (counter-rotating)
      ctx.save();
      ctx.translate(n.x, n.y);
      ctx.rotate(-t * 0.5 + i * 1.7);
      ctx.beginPath(); ctx.arc(0, 0, r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = `hsla(${hue}, 60%, 50%, ${0.1 + n.level * 0.2})`;
      ctx.lineWidth = 0.8;
      ctx.setLineDash([3, 7]);
      ctx.stroke(); ctx.setLineDash([]);
      ctx.restore();

      // Node glow
      const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 4);
      glow.addColorStop(0, `hsla(${hue}, 80%, 60%, ${0.1 + n.level * 0.15})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(n.x, n.y, r * 4, 0, Math.PI * 2); ctx.fill();

      // Core dot
      const core = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r);
      core.addColorStop(0, `hsla(${hue}, 95%, 80%, ${0.7 + n.level * 0.3})`);
      core.addColorStop(1, `hsla(${hue}, 80%, 40%, ${0.2 + n.level * 0.2})`);
      ctx.fillStyle = core;
      ctx.shadowBlur = 12 + n.level * 18;
      ctx.shadowColor = `hsla(${hue}, 90%, 50%, ${0.4 + n.level * 0.5})`;
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;

      // Label
      ctx.font = hover ? "700 10px 'Courier New', monospace" : "600 9px 'Courier New', monospace";
      ctx.fillStyle = hover ? `hsla(${hue}, 80%, 80%, 0.95)` : `hsla(${hue}, 60%, 70%, ${0.5 + n.level * 0.4})`;
      ctx.textAlign = "center";
      ctx.fillText(n.label, n.x, n.y - r - 14);
      ctx.textAlign = "left";

      // Status bar below
      if (lit || hover) {
        const bw = 40, bh = 3;
        const bx = n.x - bw / 2, by = n.y + r + 10;
        ctx.fillStyle = "rgba(0, 40, 60, 0.6)";
        ctx.fillRect(bx, by, bw, bh);
        ctx.fillStyle = `hsla(${hue}, 80%, 55%, 0.85)`;
        ctx.fillRect(bx, by, bw * n.level, bh);
      }
    }
  }

  private _drawPackets(ctx: CanvasRenderingContext2D) {
    for (const p of this.packets) {
      p.t += p.speed;
      if (p.t >= 1) continue;
      const a = this.nodes[p.from], b = this.nodes[p.to];
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      let x: number, y: number;
      if (Math.abs(a.x - b.x) > Math.abs(a.y - b.y)) {
        if (p.t < 0.5) { x = a.x + (mx - a.x) * (p.t * 2); y = a.y; }
        else { x = mx + (b.x - mx) * ((p.t - 0.5) * 2); y = b.y; }
      } else {
        if (p.t < 0.5) { x = a.x; y = a.y + (my - a.y) * (p.t * 2); }
        else { x = b.x; y = my + (b.y - my) * ((p.t - 0.5) * 2); }
      }
      const alpha = 1 - p.t;
      ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${p.hue}, 95%, 70%, ${alpha})`;
      ctx.shadowBlur = 10 * alpha;
      ctx.shadowColor = `hsla(${p.hue}, 90%, 50%, ${alpha * 0.7})`;
      ctx.fill(); ctx.shadowBlur = 0;
    }
    this.packets = this.packets.filter((p) => p.t < 1);
  }

  private _drawBlips(ctx: CanvasRenderingContext2D) {
    for (const b of this.blips) {
      b.t += 0.045;
      if (b.t >= 1) continue;
      const r = b.t * 55;
      const alpha = (1 - b.t) * 0.6;
      ctx.beginPath(); ctx.arc(b.x, b.y, r, 0, Math.PI * 2);
      ctx.strokeStyle = `hsla(${b.hue}, 85%, 65%, ${alpha})`;
      ctx.lineWidth = 1.8;
      ctx.shadowBlur = 20 * (1 - b.t);
      ctx.shadowColor = `hsla(${b.hue}, 80%, 50%, ${alpha})`;
      ctx.stroke(); ctx.shadowBlur = 0;
    }
    this.blips = this.blips.filter((b) => b.t < 1);
  }
  private _drawCornerPanels(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
    const pad = 24;
    const corners = [
      { x: pad, y: pad, w: 140, h: 80, align: "left" },
      { x: w - pad - 140, y: pad, w: 140, h: 80, align: "right" },
      { x: pad, y: h - pad - 60, w: 120, h: 40, align: "left" },
      { x: w - pad - 120, y: h - pad - 40, w: 120, h: 40, align: "right" },
    ];
    for (let i = 0; i < corners.length; i++) {
      const c = corners[i];
      ctx.save();
      ctx.globalAlpha = 0.35;
      ctx.fillStyle = C.panel;
      ctx.fillRect(c.x, c.y, c.w, c.h);
      // Corner brackets
      ctx.strokeStyle = "rgba(0, 180, 255, 0.5)";
      ctx.lineWidth = 1.2;
      const bl = 10;
      ctx.beginPath();
      if (c.align === "left") {
        ctx.moveTo(c.x, c.y + c.h); ctx.lineTo(c.x, c.y + c.h - bl); ctx.lineTo(c.x + bl, c.y + c.h);
        ctx.moveTo(c.x, c.y); ctx.lineTo(c.x, c.y + bl); ctx.lineTo(c.x + bl, c.y);
      } else {
        ctx.moveTo(c.x + c.w, c.y + c.h); ctx.lineTo(c.x + c.w, c.y + c.h - bl); ctx.lineTo(c.x + c.w - bl, c.y + c.h);
        ctx.moveTo(c.x + c.w, c.y); ctx.lineTo(c.x + c.w, c.y + bl); ctx.lineTo(c.x + c.w - bl, c.y);
      }
      ctx.stroke();
      ctx.globalAlpha = 0.6;
      ctx.font = "500 8px 'Courier New', monospace";
      ctx.fillStyle = C.dim;
      if (i === 0) { ctx.fillText("SYS_STATUS", c.x + 6, c.y + 14); ctx.fillText("ONLINE", c.x + 6, c.y + 28); }
      if (i === 1) { ctx.fillText("NET_LINK", c.x + 6, c.y + 14); ctx.fillText("SECURE", c.x + 6, c.y + 28); }
      if (i === 2) { ctx.fillText("CPU  " + Math.floor(10 + Math.sin(t) * 5) + "%", c.x + 6, c.y + 14); }
      if (i === 3) { ctx.fillText("MEM  " + Math.floor(30 + Math.cos(t * 0.7) * 8) + "%", c.x + 6, c.y + 14); }
      ctx.restore();
    }
  }

  private _drawTargetingBrackets(ctx: CanvasRenderingContext2D) {
    if (this.hover < 0) return;
    const n = this.nodes[this.hover];
    const st = this._status(n.key);
    const hue = STATUS_HUE[st];
    const r = 20 + n.level * 12;
    ctx.save();
    ctx.strokeStyle = `hsla(${hue}, 80%, 60%, 0.7)`;
    ctx.lineWidth = 1.2;
    ctx.shadowBlur = 12;
    ctx.shadowColor = `hsla(${hue}, 80%, 50%, 0.5)`;
    const bl = 12;
    // Top-left
    ctx.beginPath();
    ctx.moveTo(n.x - r - 4, n.y - r + bl); ctx.lineTo(n.x - r - 4, n.y - r - 4); ctx.lineTo(n.x - r + bl, n.y - r - 4);
    // Top-right
    ctx.moveTo(n.x + r + 4, n.y - r + bl); ctx.lineTo(n.x + r + 4, n.y - r - 4); ctx.lineTo(n.x + r - bl, n.y - r - 4);
    // Bottom-left
    ctx.moveTo(n.x - r - 4, n.y + r - bl); ctx.lineTo(n.x - r - 4, n.y + r + 4); ctx.lineTo(n.x - r + bl, n.y + r + 4);
    // Bottom-right
    ctx.moveTo(n.x + r + 4, n.y + r - bl); ctx.lineTo(n.x + r + 4, n.y + r + 4); ctx.lineTo(n.x + r - bl, n.y + r + 4);
    ctx.stroke();
    // Crosshair center dot
    ctx.fillStyle = `hsla(${hue}, 90%, 70%, 0.9)`;
    ctx.beginPath(); ctx.arc(n.x, n.y, 2, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  private _drawScanSweep(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
    if (this.reduced) return;
    const y = ((t * 35) % (h + 60)) - 30;
    ctx.save();
    ctx.globalAlpha = 0.04;
    ctx.fillStyle = "rgba(0, 200, 255, 0.25)";
    ctx.fillRect(0, y, w, 1.2);
    ctx.globalAlpha = 0.015;
    ctx.fillRect(0, y - 4, w, 10);
    ctx.restore();
  }

  private _drawVignette(ctx: CanvasRenderingContext2D, w: number, h: number) {
    const grad = ctx.createRadialGradient(w * 0.5, h * 0.5, Math.min(w, h) * 0.25, w * 0.5, h * 0.5, Math.max(w, h) * 0.75);
    grad.addColorStop(0, "rgba(0,0,0,0)");
    grad.addColorStop(1, "rgba(0,0,0,0.55)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  private _drawGlitches(ctx: CanvasRenderingContext2D) {
    for (const g of this.glitches) {
      g.t += 0.08;
      if (g.t >= 1) continue;
      ctx.save();
      ctx.globalAlpha = (1 - g.t) * 0.25;
      ctx.fillStyle = `rgba(0, 200, 255, ${0.3 + Math.random() * 0.3})`;
      ctx.fillRect(g.x, g.y, g.w, g.h);
      ctx.restore();
    }
    this.glitches = this.glitches.filter((g) => g.t < 1);
  }

  render() {
    return html`<canvas></canvas>`;
  }
}
