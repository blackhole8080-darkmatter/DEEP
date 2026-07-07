// <topology-canvas> — Advanced force-directed multi-layer network topology
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface TopoNode {
  id: string; layer: string; node_type: string; label: string;
  metadata: Record<string, any>; x: number; y: number; last_seen: string;
  vx?: number; vy?: number; fx?: number; fy?: number;
  scrambleTime?: number;
}
interface TopoEdge {
  source: string; target: string; layer: string;
  relation: string; strength: number; metadata: Record<string, any>;
}
interface Packet {
  edge: TopoEdge; progress: number; speed: number; color: string;
}

interface AmbientParticle {
  x: number; y: number; vx: number; vy: number;
  size: number; color: string; alpha: number;
  phase: number; wobbleAmp: number; wobbleFreq: number;
}

const LAYER_Z: Record<string, number> = {
  lan: 0, wifi: 1, bluetooth: 1, vpn: 2, internet: 3, dns: 1, ai: 3, cross: 0,
};

const SCRAMBLE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";

const NEON_PALETTE = [
  "#00e5ff", "#ff00e5", "#39ff14", "#ffb300", "#bf5af2",
  "#00fff7", "#ff3d71", "#7aff3a", "#ffd54f", "#a78bfa",
];

@customElement("topology-canvas")
export class TopologyCanvas extends LitElement {
  @property({ type: Array }) nodes: TopoNode[] = [];
  @property({ type: Array }) edges: TopoEdge[] = [];
  @property({ type: Array }) visibleLayers: string[] = ["lan", "wifi", "bluetooth", "vpn", "internet", "dns", "ai", "cross"];
  @state() private hovered: string | null = null;
  @state() private selected: string | null = null;

  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private camera = { x: 0, y: 0, zoom: 1 };
  private isDragging = false;
  private time = 0;
  private sonarRadius = 0;
  private packets: Packet[] = [];
  private cameraVel = { x: 0, y: 0 };
  @state() private consoleLogs: string[] = [];
  private domHud!: HTMLElement;

  private dragNode: string | null = null;
  private lastMouse = { x: 0, y: 0 };

  private _colors: Record<string, string> = {};
  private _themeColors = { accent: "#00e5ff", threat: "#ef4444" };

  // Ambient neon particle system (screen space)
  private _ambientParticles: AmbientParticle[] = [];
  private _ambientInited = false;

  // Arrival ring effects
  private _arrivalRings: { x: number; y: number; color: string; t: number }[] = [];

  // Sonar glow intensification per node
  private _sonarGlow = new Map<string, number>();

  static styles = css`
    :host { display: block; width: 100%; height: 100%; position: relative; background: #030508; overflow: hidden; }
    canvas { width: 100%; height: 100%; display: block; cursor: crosshair; }
    canvas:active { cursor: grabbing; }

    .hud-overlay {
      position: absolute; top: 20px; left: 20px; pointer-events: none;
      font-family: var(--ds-font-mono, monospace); color: var(--ds-accent, #00e5ff);
      font-size: 10px; letter-spacing: 0.14em; opacity: 0.7;
      text-shadow: 0 0 6px rgba(0,229,255,0.4);
      line-height: 1.8; text-transform: uppercase;
    }

    .legend {
      position: absolute; bottom: 16px; left: 16px; display: flex; gap: 12px; flex-wrap: wrap;
      padding: 10px 16px;
      background: rgba(6,8,14,0.65);
      border: 1px solid rgba(255,255,255,0.06);
      border-left: 2px solid var(--ds-accent, #00e5ff);
      font-size: 10px; font-family: var(--ds-font-mono, monospace);
      text-transform: uppercase; letter-spacing: 0.14em;
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border-radius: 4px;
      box-shadow: 0 4px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .legend-item { display: flex; align-items: center; gap: 6px; color: rgba(255,255,255,0.6); }
    .dot { width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }

    .vignette {
      position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%);
      z-index: 9;
    }
    .packet-console {
      position: absolute; bottom: 80px; left: 20px;
      font-family: var(--ds-font-mono, monospace); font-size: 10px;
      color: rgba(0,229,255,0.65); pointer-events: none;
      text-shadow: 0 0 4px rgba(0,229,255,0.3);
      display: flex; flex-direction: column; gap: 3px; z-index: 100; width: 300px;
    }
    .dom-hud {
      position: absolute; pointer-events: none; display: none;
      background: rgba(4,6,12,0.85);
      border: 1px solid rgba(0,229,255,0.2);
      padding: 10px 14px;
      font-family: var(--ds-font-mono, monospace); font-size: 11px;
      color: rgba(0,229,255,0.9); z-index: 100;
      backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
      box-shadow: 0 0 20px rgba(0,229,255,0.08);
      border-left: 2px solid var(--ds-accent, #00e5ff);
      border-radius: 3px;
      transform: translate(25px, -50%); white-space: pre; line-height: 1.6;
    }
    .dom-hud.threat {
      border-color: rgba(239,68,68,0.3);
      border-left-color: var(--ds-danger, #ef4444);
      box-shadow: 0 0 20px rgba(239,68,68,0.12);
      color: #ff003c;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("resize", this._resize);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    window.removeEventListener("resize", this._resize);
  }

  private _nodeState = new Map<string, any>();

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    const style = getComputedStyle(document.body);
    this._colors = {
      lan: style.getPropertyValue('--ds-success').trim() || '#10b981',
      wifi: style.getPropertyValue('--ds-warning').trim() || '#f59e0b',
      bluetooth: style.getPropertyValue('--ds-iris').trim() || '#8b5cf6',
      vpn: style.getPropertyValue('--ds-info').trim() || '#00e5ff',
      internet: style.getPropertyValue('--ds-danger').trim() || '#ef4444',
      dns: style.getPropertyValue('--ds-coral').trim() || '#d946ef',
      ai: style.getPropertyValue('--ds-sky').trim() || '#3b82f6',
      cross: style.getPropertyValue('--ds-text-muted').trim() || '#94a3b8'
    };
    this._themeColors.accent = style.getPropertyValue('--ds-accent').trim() || '#00e5ff';
    this._themeColors.threat = style.getPropertyValue('--ds-danger').trim() || '#ef4444';

    this.domHud = this.renderRoot.querySelector('.dom-hud') as HTMLElement;

    this._resize();
    this._loop();
    this.canvas.addEventListener("mousedown", this._onDown);
    this.canvas.addEventListener("mousemove", this._onMove);
    this.canvas.addEventListener("mouseup", this._onUp);
    this.canvas.addEventListener("wheel", this._onWheel, { passive: false });
  }

  updated(changedProperties: Map<string, any>) {
    if (changedProperties.has("nodes") && this.nodes.length > 0) {
      const w = this.canvas?.clientWidth || 800;
      const h = this.canvas?.clientHeight || 400;

      for (const n of this.nodes) {
        const existing = this._nodeState.get(n.id);
        if (existing) {
          n.x = existing.x;
          n.y = existing.y;
          n.vx = existing.vx;
          n.vy = existing.vy;
          n.fx = existing.fx;
          n.fy = existing.fy;
          n.scrambleTime = existing.scrambleTime;
        } else {
          n.scrambleTime = 60 + Math.random() * 60;
          if (n.node_type === "gateway") {
            n.x = w / 2; n.y = h / 2; n.fx = w / 2; n.fy = h / 2;
          } else {
            const layerIndex = Object.keys(this._colors).indexOf(n.layer);
            const angle = (layerIndex / 7) * Math.PI * 2 + Math.random() * 0.5;
            const dist = 150 + Math.random() * 300;
            n.x = w / 2 + Math.cos(angle) * dist;
            n.y = h / 2 + Math.sin(angle) * dist;
            n.vx = 0; n.vy = 0;
          }
        }
        this._nodeState.set(n.id, n);
      }
    }
  }

  private _resize = () => {
    if (!this.canvas) return;
    const dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = this.canvas.clientWidth * dpr;
    this.canvas.height = this.canvas.clientHeight * dpr;
    this.ctx?.scale(dpr, dpr);
  };

  /* ─── Ambient Particle Init ─── */
  private _initAmbientParticles(w: number, h: number) {
    this._ambientParticles = [];
    for (let i = 0; i < 50; i++) {
      this._ambientParticles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.4 + (Math.random() > 0.5 ? 0.1 : -0.1),
        vy: (Math.random() - 0.5) * 0.4 + (Math.random() > 0.5 ? 0.1 : -0.1),
        size: 0.5 + Math.random() * 1.5,
        color: NEON_PALETTE[Math.floor(Math.random() * NEON_PALETTE.length)],
        alpha: 0.2 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
        wobbleAmp: 0.3 + Math.random() * 0.6,
        wobbleFreq: 0.01 + Math.random() * 0.02,
      });
    }
    this._ambientInited = true;
  }

  private _stepPhysics() {
    const visibleNodes = this.nodes.filter((n) => this.visibleLayers.includes(n.layer));
    const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));
    const visibleEdges = this.edges.filter((e) => this.visibleLayers.includes(e.layer) && nodeMap.has(e.source) && nodeMap.has(e.target));

    const cx = this.canvas?.clientWidth / 2 || 400;
    const cy = this.canvas?.clientHeight / 2 || 300;

    // Bi-Hemisphere Brain Gravity
    for (const n of this.nodes) {
      if (n.node_type === "gateway") {
        // Brain Stem / Corpus Callosum (Bottom center)
        n.x += (cx - n.x) * 0.1;
        n.y += ((cy + 100) - n.y) * 0.1;
      } else {
        // Assign hemispheres: Internal networks = Left Brain, External/AI = Right Brain
        const isLeftHemisphere = ["lan", "wifi", "bluetooth", "cross"].includes(n.layer);
        const targetX = isLeftHemisphere ? (cx - 160) : (cx + 160);
        const targetY = cy - 60; // Upper lobes

        // Gravitational pull toward hemisphere center
        n.vx = (n.vx || 0) + (targetX - n.x) * 0.0006;
        n.vy = (n.vy || 0) + (targetY - n.y) * 0.0006;

        // Longitudinal Fissure Repulsion (Force a gap down the middle of the brain)
        const distFromCenter = n.x - cx;
        if (Math.abs(distFromCenter) < 80 && Math.abs(distFromCenter) > 0.1) {
           const fissureForce = (80 - Math.abs(distFromCenter)) * 0.005;
           n.vx += (distFromCenter > 0 ? 1 : -1) * fissureForce;
        }
      }
    }

    const edgeCounts = new Map<string, number>();
    for (const e of visibleEdges) {
      edgeCounts.set(e.source, (edgeCounts.get(e.source) || 0) + 1);
      edgeCounts.set(e.target, (edgeCounts.get(e.target) || 0) + 1);
    }

    // Fast Barnes-Hut approximation (O(N^2) for small N is fine)
    for (let i = 0; i < visibleNodes.length; i++) {
      for (let j = i + 1; j < visibleNodes.length; j++) {
        const a = visibleNodes[i], b = visibleNodes[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        if (dx === 0 && dy === 0) { dx = (Math.random() - 0.5) * 10; dy = (Math.random() - 0.5) * 10; }
        const distSq = Math.max(100, dx * dx + dy * dy); // Prevent explosion when close
        const dist = Math.sqrt(distSq);
        const force = 20000 / distSq;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        const aMass = 1 + (edgeCounts.get(a.id) || 0) * 0.5;
        const bMass = 1 + (edgeCounts.get(b.id) || 0) * 0.5;
        if (a.fx == null) { a.vx = (a.vx || 0) - fx / aMass; a.vy = (a.vy || 0) - fy / aMass; }
        if (b.fx == null) { b.vx = (b.vx || 0) + fx / bMass; b.vy = (b.vy || 0) + fy / bMass; }
      }
    }

    for (const e of visibleEdges) {
      const a = nodeMap.get(e.source)!, b = nodeMap.get(e.target)!;
      let dx = b.x - a.x, dy = b.y - a.y;
      if (dx === 0 && dy === 0) { dx = 0.1; dy = 0.1; }
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const strength = e.strength ?? 0.5;
      const ideal = 120 + (1 - strength) * 60;
      const force = (dist - ideal) * 0.008 * strength;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      const aMass = 1 + (edgeCounts.get(a.id) || 0) * 0.5;
      const bMass = 1 + (edgeCounts.get(b.id) || 0) * 0.5;

      if (!Number.isNaN(fx) && !Number.isNaN(fy)) {
        if (a.fx == null) { a.vx = (a.vx || 0) + fx / aMass; a.vy = (a.vy || 0) + fy / aMass; }
        if (b.fx == null) { b.vx = (b.vx || 0) - fx / bMass; b.vy = (b.vy || 0) - fy / bMass; }
      }
    }

    // Use the already declared cx and cy from the top of the function
    for (const n of visibleNodes) {
      if (n.scrambleTime && n.scrambleTime > 0) n.scrambleTime--;
      if (n.fx != null) continue;
      n.vx = (n.vx || 0) + (cx - n.x) * 0.00005;
      n.vy = (n.vy || 0) + (cy - n.y) * 0.00005;
      n.vx *= 0.85; n.vy *= 0.85;

      // Speed limits to prevent chaotic leaping
      n.vx = Math.max(-25, Math.min(25, n.vx));
      n.vy = Math.max(-25, Math.min(25, n.vy));

      n.x += n.vx; n.y += n.vy;
    }

    if (Math.random() > 0.3 && visibleEdges.length > 0) {
      const edge = visibleEdges[Math.floor(Math.random() * visibleEdges.length)];
      const color = this._colors[edge.layer] || this._themeColors.accent;
      this.packets.push({ edge, progress: 0, speed: 0.015 + Math.random() * 0.025, color });

      const log = `[XFER] ${edge.source.substring(0,8)} >> ${edge.target.substring(0,8)} | ${(Math.random()*40).toFixed(1)}ms`;
      this.consoleLogs = [log, ...this.consoleLogs].slice(0, 10);
    }

    this.packets.forEach((p) => p.progress += p.speed);
    this.packets = this.packets.filter((p) => p.progress < 1);
  }

  /* ─── Draw Nodes ─── */
  private _drawNodes(ctx: CanvasRenderingContext2D, visibleNodes: TopoNode[], hoverNode: TopoNode | null, visibleEdges: TopoEdge[]) {
    const isSelectedMode = this.selected != null;
    const sorted = [...visibleNodes].sort((a, b) => (LAYER_Z[a.layer] || 0) - (LAYER_Z[b.layer] || 0));
    const now = Date.now();

    for (const n of sorted) {
      const isHover = n === hoverNode;
      const isSelected = n.id === this.selected;
      const isConnected = isSelectedMode ? visibleEdges.some(e => (e.source === this.selected && e.target === n.id) || (e.target === this.selected && e.source === n.id)) : false;

      // Focus Mode visual dampening
      if (isSelectedMode && !isSelected && !isConnected) {
        ctx.globalAlpha = 0.15;
      } else {
        ctx.globalAlpha = 1.0;
      }

      const nodeColor = this._colors[n.layer] || this._themeColors.accent;
      const finalColor = isHover || isSelected ? "#ffffff" : nodeColor;
      const threat = n.metadata?.risk === "high" || n.metadata?.trust === "blocked";

      // Pseudo-3D Parallax Depth
      const parallaxZ = 0.75 + (n.id.charCodeAt(n.id.length - 1) % 5) * 0.15;
      const scale = (isHover ? 1.4 : 1) * parallaxZ;

      let r = (n.node_type === "gateway" ? 14 : n.node_type === "compute" ? 10 : 7) * scale;
      if (threat) r += 2 * scale;

      // Sonar glow intensification
      const gw = visibleNodes.find(x => x.node_type === "gateway");
      let sonarIntensity = 0;
      if (gw && n !== gw) {
        const distToGw = Math.hypot(n.x - gw.x, n.y - gw.y);
        if (Math.abs(distToGw - this.sonarRadius) < 40) {
          sonarIntensity = 1 - (Math.abs(distToGw - this.sonarRadius) / 40);
        }
      }
      // Smooth the glow with interpolation
      const prevGlow = this._sonarGlow.get(n.id) || 0;
      const newGlow = prevGlow + (sonarIntensity - prevGlow) * 0.2;
      this._sonarGlow.set(n.id, newGlow);

      // ─── Gateway: concentric breathing rings ───
      if (n.node_type === "gateway") {
        const breathe1 = Math.sin(now / 1600) * 0.5 + 0.5; // 0..1
        const breathe2 = Math.sin(now / 2200 + 1) * 0.5 + 0.5;
        const ring1R = r * 2.5 + breathe1 * 12;
        const ring2R = r * 3.5 + breathe2 * 16;

        ctx.beginPath();
        ctx.arc(n.x, n.y, ring1R, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 229, 255, ${0.12 + breathe1 * 0.08})`;
        ctx.lineWidth = 1;
        ctx.shadowColor = "#00e5ff";
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0;

        ctx.beginPath();
        ctx.arc(n.x, n.y, ring2R, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 229, 255, ${0.06 + breathe2 * 0.06})`;
        ctx.lineWidth = 0.8;
        ctx.shadowColor = "#00e5ff";
        ctx.shadowBlur = 4;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Sonar double-ring
        const sonarAlpha = Math.max(0, (1 - this.sonarRadius / 1200)) * 0.5;
        const cosFade = sonarAlpha * (0.5 + 0.5 * Math.cos(this.sonarRadius * 0.003));
        if (cosFade > 0.005) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, this.sonarRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(0, 229, 255, ${cosFade})`;
          ctx.lineWidth = 1;
          ctx.stroke();

          ctx.beginPath();
          ctx.arc(n.x, n.y, this.sonarRadius + 4, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(0, 229, 255, ${cosFade * 0.6})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      } else if (threat) {
        // Threat pulsing halo
        const pulse = Math.sin(now / 300) * 0.5 + 0.5;
        const haloR = r * 3 + pulse * 8;
        const halo = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, haloR);
        halo.addColorStop(0, `rgba(239, 68, 68, ${0.25 + pulse * 0.15})`);
        halo.addColorStop(1, "rgba(239, 68, 68, 0)");
        ctx.beginPath();
        ctx.arc(n.x, n.y, haloR, 0, Math.PI * 2);
        ctx.fillStyle = halo;
        ctx.fill();
      }

      // Orbiting ring arcs for gateway/compute nodes
      if (n.node_type === "gateway" || n.node_type === "compute") {
        ctx.save();
        ctx.translate(n.x, n.y);
        ctx.rotate(this.time * (n.node_type === "gateway" ? 0.008 : -0.012));
        ctx.beginPath();
        ctx.arc(0, 0, r + 8, 0, Math.PI * 1.4);
        ctx.strokeStyle = nodeColor + "30";
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.restore();

        ctx.save();
        ctx.translate(n.x, n.y);
        ctx.rotate(this.time * (n.node_type === "gateway" ? -0.015 : 0.018));
        ctx.beginPath();
        ctx.arc(0, 0, r + 5, Math.PI * 0.5, Math.PI * 1.9);
        ctx.strokeStyle = nodeColor + "20";
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.restore();
      }

      // ─── Main node body ───
      // Sonar glow boost
      const glowBoost = newGlow * 14;
      const baseShadow = isHover ? 25 : 12;

      // Dark fill circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = threat ? "rgba(40,5,5,0.9)" : "rgba(8,10,18,0.9)";
      ctx.fill();

      // Neon stroke with glow
      ctx.shadowColor = threat ? "#ef4444" : nodeColor;
      ctx.shadowBlur = baseShadow + glowBoost;
      ctx.strokeStyle = threat ? "#ef4444" : nodeColor;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Inner core (40% radius)
      ctx.beginPath();
      ctx.arc(n.x, n.y, r * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = threat ? "#ef4444" : nodeColor;
      ctx.shadowColor = threat ? "#ef4444" : nodeColor;
      ctx.shadowBlur = 8 + glowBoost;
      ctx.fill();
      ctx.shadowBlur = 0;

      // ─── Hover / Selected: targeting reticle ───
      if (isSelected || isHover) {
        // Dashed orbit ring
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 1.8 + Math.sin(now / 200) * 1.5, 0, Math.PI * 2);
        ctx.strokeStyle = finalColor;
        ctx.lineWidth = 1 / this.camera.zoom;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Corner brackets
        const d = r * 2.5;
        const cornerLen = d * 0.3;
        ctx.beginPath();
        ctx.moveTo(n.x - d, n.y - d + cornerLen); ctx.lineTo(n.x - d, n.y - d); ctx.lineTo(n.x - d + cornerLen, n.y - d);
        ctx.moveTo(n.x + d - cornerLen, n.y - d); ctx.lineTo(n.x + d, n.y - d); ctx.lineTo(n.x + d, n.y - d + cornerLen);
        ctx.moveTo(n.x + d, n.y + d - cornerLen); ctx.lineTo(n.x + d, n.y + d); ctx.lineTo(n.x + d - cornerLen, n.y + d);
        ctx.moveTo(n.x - d + cornerLen, n.y + d); ctx.lineTo(n.x - d, n.y + d); ctx.lineTo(n.x - d, n.y + d - cornerLen);
        ctx.strokeStyle = finalColor;
        ctx.lineWidth = 1.5 / this.camera.zoom;
        ctx.stroke();
      }

      // ─── Label ───
      let label = n.label.toUpperCase();
      if (n.scrambleTime && n.scrambleTime > 0) {
        label = label.split('').map(c => Math.random() > 0.5 ? SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)] : c).join('');
      } else if (label.length > 18) {
        label = label.slice(0, 16) + "\u2026";
      }

      const fontSize = 10 / this.camera.zoom;
      ctx.font = `500 ${fontSize}px monospace`;
      ctx.textAlign = "center";
      const txtY = n.y + r + 22 / this.camera.zoom;

      // Glow shadow for text
      ctx.shadowColor = threat ? "#ef4444" : nodeColor;
      ctx.shadowBlur = 4;
      ctx.fillStyle = isHover || isSelected ? "#ffffff" : nodeColor;

      // Manual letter-spacing by drawing char by char
      const spacing = 1.5 / this.camera.zoom;
      const totalWidth = ctx.measureText(label).width + spacing * (label.length - 1);
      let charX = n.x - totalWidth / 2;
      for (let ci = 0; ci < label.length; ci++) {
        ctx.fillText(label[ci], charX, txtY);
        charX += ctx.measureText(label[ci]).width + spacing;
      }
      ctx.shadowBlur = 0;

      // Update DOM Holographic HUD position if hovered
      if (isHover && this.domHud) {
        const screenX = n.x * this.camera.zoom + this.camera.x;
        const screenY = n.y * this.camera.zoom + this.camera.y;
        this.domHud.style.display = 'block';
        this.domHud.style.left = `${screenX}px`;
        this.domHud.style.top = `${screenY}px`;

        const fullText = `> TARGET_LOCK: ${n.id}\n> IP_RESOLVE : ${n.metadata?.ip || 'UNKNOWN'}\n> SEC_STATUS : ${threat ? 'COMPROMISED' : 'ENCRYPTED'}`;

        // Typewriter animation
        if (!(n as any)._hoverStartTime) (n as any)._hoverStartTime = this.time;
        const framesHovered = (this.time - (n as any)._hoverStartTime) / 2;
        const visibleChars = Math.min(fullText.length, Math.floor(framesHovered));
        this.domHud.innerText = fullText.substring(0, visibleChars) + (Math.random() > 0.5 && visibleChars < fullText.length ? '_' : '');
        this.domHud.className = `dom-hud ${threat ? 'threat' : ''}`;
      } else if (!isHover && !(n as any)._hoverStartTime) {
        (n as any)._hoverStartTime = 0;
      }
    }

    // Hide DOM HUD if nothing hovered
    if (!hoverNode && this.domHud) {
      this.domHud.style.display = 'none';
    }
  }

  private _drawTargetReticule(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, color: string) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    const s = r + 8;
    const len = 6;
    ctx.beginPath();
    // Top Left
    ctx.moveTo(x - s, y - s + len); ctx.lineTo(x - s, y - s); ctx.lineTo(x - s + len, y - s);
    // Top Right
    ctx.moveTo(x + s - len, y - s); ctx.lineTo(x + s, y - s); ctx.lineTo(x + s, y - s + len);
    // Bottom Right
    ctx.moveTo(x + s, y + s - len); ctx.lineTo(x + s, y + s); ctx.lineTo(x + s - len, y + s);
    // Bottom Left
    ctx.moveTo(x - s + len, y + s); ctx.lineTo(x - s, y + s); ctx.lineTo(x - s, y + s - len);
    ctx.stroke();

    // Rotating inner dashed ring
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(this.time * 0.02);
    ctx.beginPath();
    ctx.arc(0, 0, r + 3, 0, Math.PI * 2);
    ctx.setLineDash([4, 6]);
    ctx.stroke();
    ctx.restore();
  }

  /* ─── Main Render Loop ─── */
  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    this.time += 1;
    this._stepPhysics();

    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    const ctx = this.ctx;
    const now = Date.now();

    // Kinetic Camera Inertia
    if (!this.isDragging) {
      this.camera.x += this.cameraVel.x;
      this.camera.y += this.cameraVel.y;
      this.cameraVel.x *= 0.9; // Friction
      this.cameraVel.y *= 0.9;
    }

    // ─── Clear with deep space background ───
    ctx.fillStyle = "#030508";
    ctx.fillRect(0, 0, w, h);

    // Subtle deep space vignette
    const vCx = w / 2;
    const vCy = h / 2;
    const vignette = ctx.createRadialGradient(vCx, vCy, w * 0.15, vCx, vCy, w * 0.85);
    vignette.addColorStop(0, "rgba(6,8,14,0)");
    vignette.addColorStop(0.6, "rgba(3,5,8,0.15)");
    vignette.addColorStop(1, "rgba(0,0,0,0.45)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, w, h);

    // ─── Atmospheric smoke clouds (3 colors: cyan, purple, warm amber) ───
    const s1x = w * 0.3 + Math.sin(this.time * 0.0015) * 180;
    const s1y = h * 0.35 + Math.cos(this.time * 0.001) * 120;
    const smoke1 = ctx.createRadialGradient(s1x, s1y, 0, s1x, s1y, w * 0.35);
    smoke1.addColorStop(0, "rgba(0, 200, 220, 0.025)");
    smoke1.addColorStop(1, "rgba(0, 200, 220, 0)");
    ctx.fillStyle = smoke1;
    ctx.fillRect(0, 0, w, h);

    const s2x = w * 0.7 + Math.cos(this.time * 0.001) * 200;
    const s2y = h * 0.55 + Math.sin(this.time * 0.002) * 150;
    const smoke2 = ctx.createRadialGradient(s2x, s2y, 0, s2x, s2y, w * 0.35);
    smoke2.addColorStop(0, "rgba(160, 80, 220, 0.02)");
    smoke2.addColorStop(1, "rgba(160, 80, 220, 0)");
    ctx.fillStyle = smoke2;
    ctx.fillRect(0, 0, w, h);

    const s3x = w * 0.5 + Math.sin(this.time * 0.0008 + 2) * 250;
    const s3y = h * 0.7 + Math.cos(this.time * 0.0012) * 180;
    const smoke3 = ctx.createRadialGradient(s3x, s3y, 0, s3x, s3y, w * 0.3);
    smoke3.addColorStop(0, "rgba(255, 180, 60, 0.018)");
    smoke3.addColorStop(1, "rgba(255, 180, 60, 0)");
    ctx.fillStyle = smoke3;
    ctx.fillRect(0, 0, w, h);

    // ─── Subtle slow-drifting dot grid ───
    const gridSize = 50;
    const driftX = (this.time * 0.08) % gridSize;
    const driftY = (this.time * 0.05) % gridSize;
    const gridCenterX = w / 2;
    const gridCenterY = h / 2;
    const gridMaxDist = Math.hypot(gridCenterX, gridCenterY);

    for (let gx = -gridSize; gx < w + gridSize; gx += gridSize) {
      for (let gy = -gridSize; gy < h + gridSize; gy += gridSize) {
        const dotX = gx + driftX;
        const dotY = gy + driftY;
        const distFromCenter = Math.hypot(dotX - gridCenterX, dotY - gridCenterY);
        const edgeFade = Math.max(0, 1 - distFromCenter / (gridMaxDist * 0.8));
        const dotAlpha = 0.08 * edgeFade * edgeFade;
        if (dotAlpha < 0.003) continue;

        ctx.beginPath();
        ctx.arc(dotX, dotY, 1, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(100, 140, 180, ${dotAlpha})`;
        ctx.fill();
      }
    }

    // ─── Ambient floating neon particles (SCREEN SPACE) ───
    if (!this._ambientInited) this._initAmbientParticles(w, h);

    for (const p of this._ambientParticles) {
      // Drift with sine-wave wobble
      p.x += p.vx + Math.sin(this.time * p.wobbleFreq + p.phase) * p.wobbleAmp * 0.1;
      p.y += p.vy + Math.cos(this.time * p.wobbleFreq * 0.7 + p.phase) * p.wobbleAmp * 0.1;

      // Wrap around edges
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;
      if (p.y < -10) p.y = h + 10;
      if (p.y > h + 10) p.y = -10;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    ctx.globalAlpha = 1;

    // ─── Camera Transform ───
    ctx.save();
    try {
      ctx.translate(this.camera.x, this.camera.y);
      ctx.scale(this.camera.zoom, this.camera.zoom);

      const visibleNodes = this.nodes.filter((n) => this.visibleLayers.includes(n.layer));
      const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));
      const visibleEdges = this.edges.filter((e) => this.visibleLayers.includes(e.layer) && nodeMap.has(e.source) && nodeMap.has(e.target));
      const isSelectedMode = this.selected != null;

    // Update Sonar Radius
    this.sonarRadius += 2.5;
    if (this.sonarRadius > w) this.sonarRadius = 0;

    // ─── Draw Edges ───
    for (const e of visibleEdges) {
      const a = nodeMap.get(e.source)!, b = nodeMap.get(e.target)!;
      const isConnectedToSelected = isSelectedMode && (e.source === this.selected || e.target === this.selected);

      // Focus mode dampening
      if (isSelectedMode && !isConnectedToSelected) {
        ctx.globalAlpha = 0.05;
      } else {
        ctx.globalAlpha = 1.0;
      }

      const isThreat = e.metadata?.threat_flag || e.layer === 'internet';
      const cA = this._colors[a.layer] || this._themeColors.accent;
      const cB = this._colors[b.layer] || this._themeColors.accent;

      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const nx = -dy / dist;
      const ny = dx / dist;
      const curve = Math.sin(a.x + b.y) * 45;

      const midX = (a.x + b.x) / 2 + nx * curve;
      const midY = (a.y + b.y) / 2 + ny * curve;

      // Gradient from source to target color
      const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      grad.addColorStop(0, cA + "AA");
      grad.addColorStop(1, cB + "AA");

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(midX, midY, b.x, b.y);

      // Clean thin stroke with subtle glow
      const lineW = e.strength > 0.7 ? 1.5 : 1;

      if (isThreat) {
        // Pulsing red glow for threat edges
        const threatPulse = Math.sin(now / 400) * 0.5 + 0.5;
        ctx.shadowColor = "#ef4444";
        ctx.shadowBlur = 2 + threatPulse * 6;
        ctx.strokeStyle = `rgba(239, 68, 68, ${0.6 + threatPulse * 0.3})`;
        ctx.lineWidth = lineW;
      } else {
        ctx.shadowColor = cA;
        ctx.shadowBlur = 4;
        ctx.strokeStyle = grad;
        ctx.lineWidth = lineW;
      }

      // Flowing dash animation
      ctx.setLineDash([3, 8]);
      ctx.lineDashOffset = -this.time * (0.8 + e.strength * 1.2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;
    }

    // ─── Packets ───
    for (const p of this.packets) {
      const a = nodeMap.get(p.edge.source), b = nodeMap.get(p.edge.target);
      if (!a || !b) continue;

      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const nx = -dy / dist;
      const ny = dx / dist;
      const curve = Math.sin(a.x + b.y) * 45;

      const cx_pt = (a.x + b.x) / 2 + nx * curve;
      const cy_pt = (a.y + b.y) / 2 + ny * curve;

      const t = p.progress;
      const mt = 1 - t;
      const px = mt * mt * a.x + 2 * mt * t * cx_pt + t * t * b.x;
      const py = mt * mt * a.y + 2 * mt * t * cy_pt + t * t * b.y;

      const tPrev = Math.max(0, t - 0.05);
      const mtP = 1 - tPrev;
      const prevX = mtP * mtP * a.x + 2 * mtP * tPrev * cx_pt + tPrev * tPrev * b.x;
      const prevY = mtP * mtP * a.y + 2 * mtP * tPrev * cy_pt + tPrev * tPrev * b.y;
      const angle = Math.atan2(py - prevY, px - prevX);

      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(angle);

      // Perfect 3px circle, bright white with strong colored glow
      ctx.beginPath();
      ctx.arc(0, 0, 3 / this.camera.zoom, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 18 / this.camera.zoom;
      ctx.fill();

      // Comet tail gradient line
      const tailLen = 50 * p.speed / this.camera.zoom;
      const tailGrad = ctx.createLinearGradient(0, 0, -tailLen, 0);
      tailGrad.addColorStop(0, p.color + "CC");
      tailGrad.addColorStop(1, p.color + "00");
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(-tailLen, 0);
      ctx.strokeStyle = tailGrad;
      ctx.lineWidth = 2 / this.camera.zoom;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Arrival: expanding ring that fades out (t > 0.9)
      if (t > 0.9) {
        const arrivalT = (t - 0.9) / 0.1; // 0..1
        const ringRadius = arrivalT * 20 / this.camera.zoom;
        const ringAlpha = (1 - arrivalT);
        ctx.beginPath();
        ctx.arc(0, 0, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = p.color;
        ctx.globalAlpha = ringAlpha * 0.8;
        ctx.lineWidth = 1.5 / this.camera.zoom;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 6 / this.camera.zoom;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.shadowBlur = 0;
      }
      ctx.restore();
    }

    ctx.globalAlpha = 1.0;

    // ─── Nodes ───
    const hoverNode = this.hovered ? nodeMap.get(this.hovered) || null : null;
    this._drawNodes(ctx, visibleNodes, hoverNode, visibleEdges);

    } catch (error) {
      console.error("Topology rendering error:", error);
    } finally {
      ctx.restore();
    }
  };

  private _worldPos(e: MouseEvent): { x: number; y: number } {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - this.camera.x) / this.camera.zoom,
      y: (e.clientY - rect.top - this.camera.y) / this.camera.zoom,
    };
  }

  private _hitTest(mx: number, my: number): string | null {
    for (const n of this.nodes) {
      if (!this.visibleLayers.includes(n.layer)) continue;
      const r = n.node_type === "gateway" ? 24 : n.layer === "ai" ? 18 : 10;
      if (Math.hypot(n.x - mx, n.y - my) < r + 8) return n.id;
    }
    return null;
  }

  private _onDown = (e: MouseEvent) => {
    const pos = this._worldPos(e);
    const hit = this._hitTest(pos.x, pos.y);
    if (hit) {
      this.isDragging = true; this.dragNode = hit; this.selected = hit;
      this.dispatchEvent(new CustomEvent("node-select", { detail: hit, bubbles: true, composed: true }));
    } else {
      this.isDragging = true; this.dragNode = null;
      this.lastMouse = { x: e.clientX, y: e.clientY };
    }
  };

  private _onMove = (e: MouseEvent) => {
    const pos = this._worldPos(e);
    if (this.isDragging && this.dragNode) {
      const n = this.nodes.find((x) => x.id === this.dragNode);
      if (n) { n.x = pos.x; n.y = pos.y; n.vx = 0; n.vy = 0; }
    } else if (this.isDragging) {
      const dx = e.clientX - this.lastMouse.x;
      const dy = e.clientY - this.lastMouse.y;
      this.camera.x += dx;
      this.camera.y += dy;
      this.cameraVel.x = dx;
      this.cameraVel.y = dy;
      this.lastMouse = { x: e.clientX, y: e.clientY };
    } else {
      this.hovered = this._hitTest(pos.x, pos.y);
    }
  };

  private _onUp = () => { this.isDragging = false; this.dragNode = null; };

  private _onWheel = (e: WheelEvent) => {
    e.preventDefault();
    const newZoom = Math.max(0.15, Math.min(5, this.camera.zoom - e.deltaY * 0.001));
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    this.camera.x = mx - (mx - this.camera.x) * (newZoom / this.camera.zoom);
    this.camera.y = my - (my - this.camera.y) * (newZoom / this.camera.zoom);
    this.camera.zoom = newZoom;
  };

  render() {
    return html`
      <div class="vignette"></div>
      <div class="hud-overlay">
        <div>SYS.OP // TOPOLOGY TRACE ACTIVE</div>
        <div>NODES: ${this.nodes.length}</div>
        <div style="color:var(--ds-danger, #ef4444)">THREATS DETECTED</div>
      </div>
      <div class="packet-console">
        ${this.consoleLogs.map(log => html`<div>${log}</div>`)}
      </div>
      <div class="dom-hud"></div>
      <canvas></canvas>
      <div class="legend">
        ${Object.entries(this._colors).map(([layer, color]) => html`
          <div class="legend-item">
            <span class="dot" style="background:${color}; box-shadow: 0 0 6px ${color}"></span>
            <span>${layer}</span>
          </div>
        `)}
      </div>
    `;
  }
}
