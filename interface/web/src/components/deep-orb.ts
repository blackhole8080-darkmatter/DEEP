// <deep-orb> — DEEP's living background: particle sphere + neural graph
// Reactive to connection state, voice amplitude, and AI thinking.
// Canvas 2D implementation (no Three.js dependency) for lightweight rendering.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Node {
  id: string; label: string; x: number; y: number; z: number;
  r: number; color: string; act: number;
}

interface ShootingStar {
  x: number; y: number; vx: number; vy: number;
  life: number; maxLife: number;
  tail: { x: number; y: number }[];
}

@customElement("deep-orb")
export class DeepOrb extends LitElement {
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private particles: Array<{
    x: number; y: number; z: number;
    vx: number; vy: number; vz: number;
    size: number; life: number; hue: number;
  }> = [];
  private nodes: Node[] = [];
  private stars: ShootingStar[] = [];
  private nebulaOffset = 0;
  private rotY = 0;
  private rotX = 0;
  private time = 0;
  private pulse = 0;
  private mouseX = 0;
  private mouseY = 0;
  private mouseActive = false;

  @state() private state: "idle" | "listening" | "thinking" | "speaking" = "idle";
  @state() private micAmp = 0;
  @state() private ttsAmp = 0;

  private _getStateColors() {
    const s = this.state;
    if (s === "listening") return { primary: "0,255,209", secondary: "0,229,255", hue: 160 };
    if (s === "thinking") return { primary: "255,61,240", secondary: "157,92,255", hue: 280 };
    if (s === "speaking") return { primary: "245,185,66", secondary: "255,122,26", hue: 35 };
    return { primary: "0,229,255", secondary: "124,147,255", hue: 190 };
  }

  static styles = css`
    :host { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
    canvas { width: 100%; height: 100%; display: block; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._initParticles();
    this._initNodes();
    window.addEventListener("resize", this._resize);
    window.addEventListener("mousemove", this._onMouseMove);
    window.addEventListener("mouseleave", this._onMouseLeave);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    window.removeEventListener("resize", this._resize);
    window.removeEventListener("mousemove", this._onMouseMove);
    window.removeEventListener("mouseleave", this._onMouseLeave);
  }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    this._resize();
    this._loop();
  }

  private _onMouseMove = (e: MouseEvent) => {
    this.mouseX = e.clientX;
    this.mouseY = e.clientY;
    this.mouseActive = true;
  };
  private _onMouseLeave = () => { this.mouseActive = false; };

  private _initParticles() {
    this.particles = Array.from({ length: 900 }, () => {
      const a = Math.random() * Math.PI * 2;
      const b = Math.random() * Math.PI;
      const d = 0.3 + Math.random() * 0.7;
      return {
        x: Math.sin(b) * Math.cos(a) * d,
        y: Math.sin(b) * Math.sin(a) * d,
        z: Math.cos(b) * d,
        vx: (Math.random() - 0.5) * 0.0003,
        vy: (Math.random() - 0.5) * 0.0003,
        vz: (Math.random() - 0.5) * 0.0003,
        size: 0.5 + Math.random() * 2,
        life: Math.random(),
        hue: Math.random() * 60,
      };
    });
  }

  private _initNodes() {
    const colors = ["#9bfff0", "#00ffd1", "#00b8e6", "#d946ef", "#f59e0b", "#10b981", "#a78bfa", "#f472b6"];
    const labels = ["BRAIN", "MEMORY", "KNOWLEDGE", "RESEARCH", "PREDICTIVE", "AGENTS", "SECURITY", "VOICE"];
    this.nodes = labels.map((label, i) => {
      const a = (i / labels.length) * Math.PI * 2;
      const b = Math.random() * Math.PI;
      const d = 0.5 + Math.random() * 0.4;
      return {
        id: label.toLowerCase(), label,
        x: Math.sin(b) * Math.cos(a) * d,
        y: Math.sin(b) * Math.sin(a) * d,
        z: Math.cos(b) * d,
        r: 2.5 + Math.random() * 2,
        color: colors[i % colors.length],
        act: Math.random() * 0.3,
      };
    });
  }

  private _spawnShootingStar(w: number, h: number) {
    const side = Math.floor(Math.random() * 4);
    let x = 0, y = 0, vx = 0, vy = 0;
    const speed = 4 + Math.random() * 6;
    switch (side) {
      case 0: x = Math.random() * w; y = -20; vx = (Math.random() - 0.5) * speed; vy = speed; break;
      case 1: x = w + 20; y = Math.random() * h; vx = -speed; vy = (Math.random() - 0.5) * speed; break;
      case 2: x = Math.random() * w; y = h + 20; vx = (Math.random() - 0.5) * speed; vy = -speed; break;
      case 3: x = -20; y = Math.random() * h; vx = speed; vy = (Math.random() - 0.5) * speed; break;
    }
    this.stars.push({ x, y, vx, vy, life: 1, maxLife: 30 + Math.random() * 40, tail: [] });
  }

  private _resize = () => {
    if (!this.canvas) return;
    const dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = this.canvas.clientWidth * dpr;
    this.canvas.height = this.canvas.clientHeight * dpr;
    this.ctx?.scale(dpr, dpr);
  };

  private _rot3D(x: number, y: number, z: number) {
    const cy = Math.cos(this.rotY), sy = Math.sin(this.rotY);
    const cx = Math.cos(this.rotX), sx = Math.sin(this.rotX);
    const x1 = x * cy - z * sy;
    const z1 = x * sy + z * cy;
    const y1 = y * cx - z1 * sx;
    const z2 = y * sx + z1 * cx;
    return { x: x1, y: y1, z: z2 };
  }

  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    const cx = w / 2;
    const cy = h / 2;
    const ctx = this.ctx;
    const t = (this.time += 1);

    // State-driven params
    const isListening = this.state === "listening";
    const isThinking = this.state === "thinking";
    const isSpeaking = this.state === "speaking";
    const isActive = isListening || isThinking || isSpeaking;

    const rotSpeedY = isThinking ? 0.004 : isListening ? 0.002 : 0.001;
    const rotSpeedX = isThinking ? 0.0015 : 0.0005;
    this.rotY += rotSpeedY;
    this.rotX += rotSpeedX;

    const drive = Math.max(this.micAmp * 0.5, this.ttsAmp * 0.5, isThinking ? 0.4 : isSpeaking ? 0.6 : 0);
    this.pulse = this.pulse * 0.92 + drive * 0.08;

    const baseR = Math.min(w, h) * 0.32;
    const r = baseR * (1 + this.pulse * 0.15);

    ctx.clearRect(0, 0, w, h);
    const colors = this._getStateColors();

    // ── Nebula fog (slow-moving radial clouds) ──
    this.nebulaOffset += 0.0003;
    const neb1 = ctx.createRadialGradient(
      cx + Math.sin(this.nebulaOffset) * w * 0.15,
      cy + Math.cos(this.nebulaOffset * 0.7) * h * 0.1,
      r * 0.3, cx, cy, r * 2.2
    );
    neb1.addColorStop(0, `rgba(${colors.primary},0.04)`);
    neb1.addColorStop(0.5, `rgba(${colors.secondary},0.02)`);
    neb1.addColorStop(1, "transparent");
    ctx.fillStyle = neb1;
    ctx.fillRect(0, 0, w, h);

    const neb2 = ctx.createRadialGradient(
      cx - Math.cos(this.nebulaOffset * 0.6) * w * 0.2,
      cy + Math.sin(this.nebulaOffset * 0.9) * h * 0.15,
      r * 0.2, cx, cy, r * 1.8
    );
    neb2.addColorStop(0, `rgba(${colors.secondary},0.03)`);
    neb2.addColorStop(1, "transparent");
    ctx.fillStyle = neb2;
    ctx.fillRect(0, 0, w, h);

    // ── 3D Particles with mouse reactivity ──
    const mouse3DX = this.mouseActive ? (this.mouseX - cx) / cx : 0;
    const mouse3DY = this.mouseActive ? (this.mouseY - cy) / cy : 0;

    const projParticles = this.particles.map((p) => {
      p.x += p.vx * (isThinking ? 4 : 1);
      p.y += p.vy * (isThinking ? 4 : 1);
      p.z += p.vz * (isThinking ? 4 : 1);
      p.life += 0.002;
      if (p.life > 1) p.life -= 1;

      const mDist = Math.sqrt((p.x - mouse3DX * 0.5) ** 2 + (p.y - mouse3DY * 0.5) ** 2);
      if (this.mouseActive && mDist < 0.4) {
        const repel = (0.4 - mDist) * 0.008;
        p.x += (p.x - mouse3DX * 0.5) * repel;
        p.y += (p.y - mouse3DY * 0.5) * repel;
      }

      const d = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z) || 1;
      const nx = (p.x / d) * r;
      const ny = (p.y / d) * r;
      const nz = (p.z / d) * r;
      const rp = this._rot3D(nx, ny, nz);
      const scale = 450 / (450 + rp.z);
      return { x: cx + rp.x * scale, y: cy + rp.y * scale, z: rp.z, scale, life: p.life, size: p.size, hue: p.hue };
    });

    projParticles.sort((a, b) => a.z - b.z);

    // ── Constellation lines ──
    const connDist = isActive ? 90 : 60;
    const maxConns = isActive ? 3 : 2;
    ctx.lineWidth = 0.5;
    for (let i = 0; i < projParticles.length; i++) {
      const a = projParticles[i];
      if (a.z < -r * 0.4) continue;
      let conns = 0;
      for (let j = i + 1; j < projParticles.length && conns < maxConns; j++) {
        const b = projParticles[j];
        if (b.z < -r * 0.4) continue;
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < connDist) {
          const lineAlpha = ((connDist - dist) / connDist) * ((a.z + r) / (2 * r)) * 0.2;
          ctx.strokeStyle = `rgba(${colors.primary},${lineAlpha})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
          conns++;
        }
      }
    }

    // ── Draw particles ──
    for (const p of projParticles) {
      const alpha = (p.z + r) / (2 * r);
      const size = (isListening ? 1.3 + this.micAmp * 3 : 0.8) * p.scale * p.size;
      const glowR = isThinking ? 6 : isSpeaking ? 5 : 3;
      const h = colors.hue + (p.hue * (isActive ? 1.5 : 0.5));
      ctx.beginPath();
      ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${h},85%,65%,${alpha * (0.5 + Math.sin(p.life * Math.PI * 2) * 0.3)})`;
      ctx.fill();
      if (alpha > 0.3) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, size * glowR, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${h},85%,65%,${alpha * 0.04})`;
        ctx.fill();
      }
    }

    // ── Neural Graph Nodes ──
    const nodePositions = this.nodes.map((n) => {
      const nr = r * 0.65;
      const rp = this._rot3D(n.x * nr, n.y * nr, n.z * nr);
      const scale = 400 / (400 + rp.z);
      return { ...n, sx: cx + rp.x * scale, sy: cy + rp.y * scale, sz: rp.z, scale };
    });

    // Draw links
    ctx.strokeStyle = `rgba(${colors.primary},0.08)`;
    ctx.lineWidth = 1;
    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        const a = nodePositions[i], b = nodePositions[j];
        if (a.sz > -40 && b.sz > -40) {
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          ctx.lineTo(b.sx, b.sy);
          ctx.stroke();
        }
      }
    }

    // Draw nodes
    for (const n of nodePositions) {
      if (n.sz < -r * 0.5) continue;
      const alpha = (n.sz + r) / (2 * r);
      const pulseR = n.r * n.scale * (1 + Math.sin(t * 0.04 + n.act * 10) * 0.2);
      ctx.beginPath();
      ctx.arc(n.sx, n.sy, pulseR, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.globalAlpha = alpha;
      ctx.fill();
      ctx.globalAlpha = 1;

      ctx.beginPath();
      ctx.arc(n.sx, n.sy, pulseR * 5, 0, Math.PI * 2);
      ctx.fillStyle = n.color + "14";
      ctx.fill();

      if (alpha > 0.35) {
        ctx.font = `500 ${9 * n.scale}px var(--ds-font-mono, monospace)`;
        ctx.fillStyle = `rgba(234,246,255,${alpha * 0.65})`;
        ctx.textAlign = "center";
        ctx.fillText(n.label, n.sx, n.sy - pulseR - 5 * n.scale);
      }
    }

    // ── Shooting stars ──
    if (Math.random() < (isActive ? 0.015 : 0.005)) {
      this._spawnShootingStar(w, h);
    }
    for (let i = this.stars.length - 1; i >= 0; i--) {
      const s = this.stars[i];
      s.tail.push({ x: s.x, y: s.y });
      if (s.tail.length > 8) s.tail.shift();
      s.x += s.vx; s.y += s.vy;
      s.life -= 1 / s.maxLife;
      if (s.life <= 0 || s.x < -50 || s.x > w + 50 || s.y < -50 || s.y > h + 50) {
        this.stars.splice(i, 1);
        continue;
      }
      ctx.lineWidth = 1.5;
      for (let j = 1; j < s.tail.length; j++) {
        const ta = s.tail[j - 1], tb = s.tail[j];
        const tailAlpha = (j / s.tail.length) * s.life * 0.8;
        ctx.strokeStyle = `rgba(${colors.primary},${tailAlpha})`;
        ctx.beginPath();
        ctx.moveTo(ta.x, ta.y);
        ctx.lineTo(tb.x, tb.y);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(s.x, s.y, 1.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${s.life * 0.9})`;
      ctx.fill();
    }

    // ── Data stream streaks ──
    if (isActive) {
      const streakCount = isThinking ? 3 : 1;
      for (let i = 0; i < streakCount; i++) {
        const sx = cx + (Math.random() - 0.5) * r * 1.5;
        const sy = cy + (Math.random() - 0.5) * r * 1.5;
        const ex = sx + (Math.random() - 0.5) * 60;
        const ey = sy + (Math.random() - 0.5) * 60;
        const grad = ctx.createLinearGradient(sx, sy, ex, ey);
        grad.addColorStop(0, `rgba(${colors.primary},0)`);
        grad.addColorStop(0.5, `rgba(${colors.primary},0.15)`);
        grad.addColorStop(1, `rgba(${colors.primary},0)`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }
    }

    // ── Center core glow ──
    const coreGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 0.45);
    coreGlow.addColorStop(0, `rgba(${colors.primary},0.22)`);
    coreGlow.addColorStop(0.5, `rgba(${colors.secondary},0.08)`);
    coreGlow.addColorStop(1, `rgba(${colors.primary},0)`);
    ctx.fillStyle = coreGlow;
    ctx.fillRect(cx - r * 0.45, cy - r * 0.45, r * 0.9, r * 0.9);

    // ── Scan line ──
    const scanY = ((t * 0.8) % (h + 100)) - 50;
    ctx.fillStyle = `rgba(${colors.primary},${0.03 + this.pulse * 0.04})`;
    ctx.fillRect(0, scanY, w, 1.5);
  };

  setState(s: "idle" | "listening" | "thinking" | "speaking") { this.state = s; }
  setMicAmp(v: number) { this.micAmp = v; }
  setTtsAmp(v: number) { this.ttsAmp = v; }

  render() {
    return html`<canvas></canvas>`;
  }
}
