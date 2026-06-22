// <topology-canvas> — Force-directed multi-layer network topology
// Supports LAN, WiFi, Bluetooth, VPN, Internet, DNS, AI layers.
// Physics: repulsion + spring forces. Camera: pan, zoom, drag.
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface TopoNode {
  id: string; layer: string; node_type: string; label: string;
  metadata: Record<string, any>; x: number; y: number; last_seen: string;
  vx?: number; vy?: number; fx?: number; fy?: number;
}
interface TopoEdge {
  source: string; target: string; layer: string;
  relation: string; strength: number; metadata: Record<string, any>;
}

const LAYER_Z: Record<string, number> = {
  lan: 0, wifi: 1, bluetooth: 1, vpn: 2, internet: 3, dns: 1, ai: 3, cross: 0,
};

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
  private dragNode: string | null = null;
  private lastMouse = { x: 0, y: 0 };
  private time = 0;

  // Resolved theme colors
  private _colors: Record<string, string> = {};
  private _themeColors = { accent: "#00e5ff", threat: "#ef4444" };

  static styles = css`
    :host { display: block; width: 100%; height: 100%; position: relative; }
    canvas { width: 100%; height: 100%; display: block; border-radius: var(--ds-radius-md); cursor: grab; }
    canvas:active { cursor: grabbing; }
    .legend { position: absolute; bottom: 8px; left: 8px; display: flex; gap: 10px; flex-wrap: wrap; padding: 6px 10px; background: rgba(10,18,30,0.85); border-radius: 10px; border: 1px solid var(--ds-border); font-size: var(--ds-text-xs); }
    .legend-item { display: flex; align-items: center; gap: 4px; color: var(--ds-text-muted); }
    .dot { width: 7px; height: 7px; border-radius: 50%; }
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
    
    this._resize();
    this._initPositions();
    this._loop();
    this.canvas.addEventListener("mousedown", this._onDown);
    this.canvas.addEventListener("mousemove", this._onMove);
    this.canvas.addEventListener("mouseup", this._onUp);
    this.canvas.addEventListener("wheel", this._onWheel, { passive: false });
  }

  private _resize = () => {
    if (!this.canvas) return;
    const dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = this.canvas.clientWidth * dpr;
    this.canvas.height = this.canvas.clientHeight * dpr;
    this.ctx?.scale(dpr, dpr);
  };

  private _initPositions() {
    const w = this.canvas?.clientWidth || 800;
    const h = this.canvas?.clientHeight || 400;
    const gw = this.nodes.find((n) => n.node_type === "gateway");
    for (const n of this.nodes) {
      if (n.fx != null) continue;
      if (n.id === gw?.id) { n.x = w / 2; n.y = h / 2; n.fx = w / 2; n.fy = h / 2; continue; }
      const layerIndex = Object.keys(LAYER_COLORS).indexOf(n.layer);
      const angle = (layerIndex / 7) * Math.PI * 2 + Math.random() * 0.5;
      const dist = 120 + Math.random() * 180;
      n.x = w / 2 + Math.cos(angle) * dist;
      n.y = h / 2 + Math.sin(angle) * dist;
      n.vx = 0; n.vy = 0;
    }
  }

  private _stepPhysics() {
    const visibleNodes = this.nodes.filter((n) => this.visibleLayers.includes(n.layer));
    const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));
    const visibleEdges = this.edges.filter((e) => this.visibleLayers.includes(e.layer) && nodeMap.has(e.source) && nodeMap.has(e.target));

    for (let i = 0; i < visibleNodes.length; i++) {
      for (let j = i + 1; j < visibleNodes.length; j++) {
        const a = visibleNodes[i], b = visibleNodes[j];
        if (a.fx != null || b.fx != null) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 2500 / (dist * dist);
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        a.vx = (a.vx || 0) - fx; a.vy = (a.vy || 0) - fy;
        b.vx = (b.vx || 0) + fx; b.vy = (b.vy || 0) + fy;
      }
    }

    for (const e of visibleEdges) {
      const a = nodeMap.get(e.source)!, b = nodeMap.get(e.target)!;
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ideal = 90 + (1 - e.strength) * 60;
      const force = (dist - ideal) * 0.008 * e.strength;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      if (a.fx == null) { a.vx = (a.vx || 0) + fx; a.vy = (a.vy || 0) + fy; }
      if (b.fx == null) { b.vx = (b.vx || 0) - fx; b.vy = (b.vy || 0) - fy; }
    }

    const cx = this.canvas?.clientWidth / 2 || 400;
    const cy = this.canvas?.clientHeight / 2 || 200;
    for (const n of visibleNodes) {
      if (n.fx != null) continue;
      n.vx = (n.vx || 0) + (cx - n.x) * 0.0003;
      n.vy = (n.vy || 0) + (cy - n.y) * 0.0003;
      n.vx *= 0.88; n.vy *= 0.88;
      n.x += n.vx; n.y += n.vy;
    }
  }

  private _loop = () => {
    this.raf = requestAnimationFrame(this._loop);
    this.time += 1;
    this._stepPhysics();

    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(0,229,255,0.03)";
    ctx.lineWidth = 1;
    const gridSize = 40 * this.camera.zoom;
    const offsetX = this.camera.x % gridSize;
    const offsetY = this.camera.y % gridSize;
    for (let x = offsetX; x < w; x += gridSize) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = offsetY; y < h; y += gridSize) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    ctx.save();
    ctx.translate(this.camera.x, this.camera.y);
    ctx.scale(this.camera.zoom, this.camera.zoom);

    const visibleNodes = this.nodes.filter((n) => this.visibleLayers.includes(n.layer));
    const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));
    const visibleEdges = this.edges.filter((e) => this.visibleLayers.includes(e.layer) && nodeMap.has(e.source) && nodeMap.has(e.target));

    for (const e of visibleEdges) {
      const a = nodeMap.get(e.source)!, b = nodeMap.get(e.target)!;
      const isThreat = e.metadata?.threat_flag;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = isThreat ? "rgba(239,68,68,0.4)" : (this._colors[e.layer] || this._themeColors.accent) + "28";
      ctx.lineWidth = isThreat ? 2.5 : Math.max(0.5, e.strength * 1.5);
      if (e.layer === "vpn") { ctx.setLineDash([4, 4]); } else if (e.layer === "wifi") { ctx.setLineDash([2, 3]); } else { ctx.setLineDash([]); }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    if (visibleEdges.length > 0) {
      const t = (this.time * 0.008) % 1;
      const idx = Math.floor(this.time * 0.002) % visibleEdges.length;
      const e = visibleEdges[idx];
      const a = nodeMap.get(e.source)!, b = nodeMap.get(e.target)!;
      const px = a.x + (b.x - a.x) * t, py = a.y + (b.y - a.y) * t;
      ctx.beginPath(); ctx.arc(px, py, 2.5 / this.camera.zoom, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0,229,255,0.7)"; ctx.fill();
    }

    const sorted = [...visibleNodes].sort((a, b) => (LAYER_Z[a.layer] || 0) - (LAYER_Z[b.layer] || 0));
    for (const n of sorted) {
      const isHover = this.hovered === n.id;
      const isSelected = this.selected === n.id;
      const r = n.node_type === "gateway" ? 18 : n.layer === "ai" ? 12 : 8;
      const scale = isHover ? 1.4 : isSelected ? 1.2 : 1;
      const color = this._colors[n.layer] || this._themeColors.accent;
      const threat = n.metadata?.threat_type || n.metadata?.rogue;

      ctx.beginPath();
      ctx.arc(n.x, n.y, r * scale * 3, 0, Math.PI * 2);
      ctx.fillStyle = threat ? "rgba(239,68,68,0.12)" : color + "15";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(n.x, n.y, r * scale, 0, Math.PI * 2);
      ctx.fillStyle = threat ? this._themeColors.threat : color;
      ctx.fill();

      if (isSelected || isHover) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * scale + 3, 0, Math.PI * 2);
        ctx.strokeStyle = isSelected ? "rgba(0,229,255,0.6)" : "rgba(255,255,255,0.4)";
        ctx.lineWidth = 1.5; ctx.stroke();
      }

      const label = n.label.length > 14 ? n.label.slice(0, 12) + "…" : n.label;
      ctx.font = `${isHover ? 600 : 500} ${(isHover ? 11 : 9) / this.camera.zoom}px var(--ds-font-mono, monospace)`;
      ctx.fillStyle = isHover ? "#eaf6ff" : "rgba(234,246,255,0.55)";
      ctx.textAlign = "center";
      ctx.fillText(label, n.x, n.y + r * scale + 12 / this.camera.zoom);
    }

    ctx.restore();
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
      const r = n.node_type === "gateway" ? 18 : n.layer === "ai" ? 12 : 8;
      if (Math.hypot(n.x - mx, n.y - my) < r + 4) return n.id;
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
      this.camera.x += e.clientX - this.lastMouse.x;
      this.camera.y += e.clientY - this.lastMouse.y;
      this.lastMouse = { x: e.clientX, y: e.clientY };
    } else {
      this.hovered = this._hitTest(pos.x, pos.y);
      this.canvas.style.cursor = this.hovered ? "pointer" : "grab";
    }
  };

  private _onUp = () => { this.isDragging = false; this.dragNode = null; };

  private _onWheel = (e: WheelEvent) => {
    e.preventDefault();
    const newZoom = Math.max(0.2, Math.min(4, this.camera.zoom - e.deltaY * 0.001));
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    this.camera.x = mx - (mx - this.camera.x) * (newZoom / this.camera.zoom);
    this.camera.y = my - (my - this.camera.y) * (newZoom / this.camera.zoom);
    this.camera.zoom = newZoom;
  };

  render() {
    return html`
      <canvas></canvas>
      <div class="legend">
        ${Object.entries(this._colors).map(([layer, color]) => html`
          <div class="legend-item">
            <span class="dot" style="background:${color}"></span>
            <span>${layer}</span>
          </div>
        `)}
      </div>
    `;
  }
}
