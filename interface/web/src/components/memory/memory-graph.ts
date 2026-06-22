// <memory-graph> — advanced knowledge-graph visualization.
//
// Pulls the enriched graph from /api/knowledge/vault (entities carry pagerank /
// community / betweenness; edges carry a `kind`: relation | semantic | gnn |
// suggestion). Runs a continuous force simulation in an SVG with a neon-FUI
// aesthetic: nodes glow by importance, cluster-coloured by detected community,
// edges styled by kind. Drag nodes, hover for detail, focus a neighbourhood,
// run the GraphSAGE GNN to overlay predicted links, and read derived inferences
// in the side rail.
import { LitElement, html, css, svg, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Entity {
  id: string; name: string; type: string;
  description?: string; context?: string[];
  pagerank?: number; community?: number; betweenness?: number; link_count?: number;
}
interface Rel { source: string; target: string; relation: string; kind?: string; confidence?: number; }
interface Node extends Entity {
  x: number; y: number; vx: number; vy: number; deg: number; fixed?: boolean;
}
interface Edge { s: Node; t: Node; relation: string; kind: string; confidence: number; }
interface Inference { type: string; text: string; score: number; subjects: string[]; }

const TYPE_COLOR: Record<string, string> = {
  technology: "var(--ds-periwinkle)",
  topic: "var(--ds-lilac)",
  concept: "var(--ds-sky)",
  person: "var(--ds-amber)",
  project: "var(--ds-coral)",
  organization: "var(--ds-iris)",
  place: "var(--ds-mint)",
  preference: "var(--ds-mint)",
};
// Distinct hues for community clusters (cluster-colouring mode).
const COMMUNITY_COLOR = [
  "#7c93ff", "#56c596", "#e0a35a", "#e5736a", "#5ec8e5",
  "#b58cff", "#9a8cff", "#f5b942", "#00e5ff", "#ff6ad5",
];

@customElement("memory-graph")
export class MemoryGraph extends LitElement {
  @state() private nodes: Node[] = [];
  @state() private edges: Edge[] = [];
  @state() private query = "";
  @state() private focusedId: string | null = null;
  @state() private hover: Node | null = null;
  @state() private stats: Record<string, unknown> = {};
  @state() private inferences: Inference[] = [];
  @state() private colorMode: "community" | "type" = "community";
  @state() private showSemantic = true;
  @state() private busy = "";
  @state() private loading = true;

  private raf = 0;
  private alpha = 1;          // simulation "temperature"
  private drag: Node | null = null;
  private readonly W = 960;
  private readonly H = 620;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
    void this.loadInferences();
  }
  disconnectedCallback(): void { super.disconnectedCallback(); cancelAnimationFrame(this.raf); }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      const d = await (await fetch("/api/knowledge/vault?limit=220")).json();
      const ents: Entity[] = d.entities ?? [];
      const rels: Rel[] = d.relationships ?? [];
      this.stats = d.stats ?? {};
      const deg: Record<string, number> = {};
      for (const r of rels) { deg[r.source] = (deg[r.source] ?? 0) + 1; deg[r.target] = (deg[r.target] ?? 0) + 1; }
      const byId = new Map<string, Node>();
      this.nodes = ents.map((e, i) => {
        const a = (i / Math.max(1, ents.length)) * Math.PI * 2;
        const rad = 120 + ((e.pagerank ?? 0) > 0 ? 0 : (i % 5) * 30);
        const n: Node = {
          ...e,
          x: this.W / 2 + Math.cos(a) * (rad + 80),
          y: this.H / 2 + Math.sin(a) * (rad + 40),
          vx: 0, vy: 0, deg: deg[e.id] ?? 0,
        };
        byId.set(e.id, n); return n;
      });
      this.edges = rels
        .map((r) => {
          const s = byId.get(r.source), t = byId.get(r.target);
          return s && t ? { s, t, relation: r.relation, kind: r.kind ?? "relation", confidence: r.confidence ?? 0.6 } : null;
        })
        .filter((e): e is Edge => !!e);
      this.alpha = 1;
      this.run();
    } catch { /* ignore */ }
    this.loading = false;
  }

  private async loadInferences(): Promise<void> {
    try {
      const d = await (await fetch("/api/knowledge/inferences?limit=7&connections=true")).json();
      this.inferences = d.inferences ?? [];
    } catch { /* ignore */ }
  }

  private async runGnn(): Promise<void> {
    this.busy = "Running GraphSAGE…";
    try {
      const d = await (await fetch("/api/knowledge/gnn?epochs=50", { method: "POST" })).json();
      const links: { source: string; target: string; score: number }[] = d.predicted_links ?? [];
      const byId = new Map(this.nodes.map((n) => [n.id, n]));
      const fresh: Edge[] = [];
      for (const p of links) {
        const s = byId.get(p.source), t = byId.get(p.target);
        if (s && t) fresh.push({ s, t, relation: "predicted", kind: "gnn", confidence: p.score });
      }
      this.edges = [...this.edges.filter((e) => e.kind !== "gnn"), ...fresh];
      this.alpha = Math.max(this.alpha, 0.4);
      this.run();
      this.busy = `GNN linked ${fresh.length} predicted pairs`;
    } catch { this.busy = "GNN unavailable"; }
    setTimeout(() => { this.busy = ""; }, 3200);
  }

  /** Continuous force sim with cooling; reheats on interaction. */
  private run(): void {
    cancelAnimationFrame(this.raf);
    const step = () => {
      const N = this.nodes;
      const a = Math.max(this.alpha, 0.02);
      for (let i = 0; i < N.length; i++) {
        for (let j = i + 1; j < N.length; j++) {
          const p = N[i], q = N[j];
          let dx = p.x - q.x, dy = p.y - q.y;
          let d2 = dx * dx + dy * dy || 0.01;
          const f = (1700 / d2) * a;
          const d = Math.sqrt(d2); dx /= d; dy /= d;
          p.vx += dx * f; p.vy += dy * f; q.vx -= dx * f; q.vy -= dy * f;
        }
      }
      for (const e of this.edges) {
        const rest = e.kind === "semantic" ? 130 : e.kind === "gnn" ? 150 : 88;
        let dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const k = e.kind === "relation" ? 0.012 : 0.005;
        const f = (d - rest) * k * a;
        dx /= d; dy /= d;
        e.s.vx += dx * f; e.s.vy += dy * f; e.t.vx -= dx * f; e.t.vy -= dy * f;
      }
      for (const n of N) {
        if (n === this.drag) { n.vx = 0; n.vy = 0; continue; }
        n.vx += (this.W / 2 - n.x) * 0.0016 * a;
        n.vy += (this.H / 2 - n.y) * 0.0016 * a;
        n.vx *= 0.86; n.vy *= 0.86;
        n.x = Math.max(24, Math.min(this.W - 24, n.x + n.vx));
        n.y = Math.max(24, Math.min(this.H - 24, n.y + n.vy));
      }
      this.alpha *= 0.992;
      this.requestUpdate();
      this.raf = requestAnimationFrame(step);
    };
    this.raf = requestAnimationFrame(step);
  }

  // ── geometry helpers ──────────────────────────────────────────────────────
  private toSvg(ev: PointerEvent): { x: number; y: number } {
    const svgEl = this.renderRoot.querySelector("svg") as SVGSVGElement | null;
    if (!svgEl) return { x: 0, y: 0 };
    const pt = svgEl.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const ctm = svgEl.getScreenCTM(); if (!ctm) return { x: 0, y: 0 };
    const p = pt.matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y };
  }
  private onDown(n: Node, ev: PointerEvent): void {
    ev.stopPropagation();
    this.drag = n; n.fixed = true;
    (ev.target as Element).setPointerCapture?.(ev.pointerId);
  }
  private onMove(ev: PointerEvent): void {
    if (!this.drag) return;
    const p = this.toSvg(ev); this.drag.x = p.x; this.drag.y = p.y;
    this.alpha = Math.max(this.alpha, 0.25); this.requestUpdate();
  }
  private onUp(): void { if (this.drag) this.drag.fixed = false; this.drag = null; }

  private nodeColor(n: Node): string {
    if (this.colorMode === "community" && n.community !== undefined)
      return COMMUNITY_COLOR[n.community % COMMUNITY_COLOR.length];
    return TYPE_COLOR[n.type] ?? "var(--ds-text-muted)";
  }
  private nodeRadius(n: Node): number {
    const pr = (n.pagerank ?? 0) * 1400;
    return Math.max(5, Math.min(22, 5 + n.deg * 1.5 + pr));
  }
  private dim(id: string): boolean {
    const q = this.query.toLowerCase();
    if (this.focusedId) {
      if (id === this.focusedId) return false;
      return !this.edges.some((e) => (e.s.id === this.focusedId && e.t.id === id) || (e.t.id === this.focusedId && e.s.id === id));
    }
    if (q) { const n = this.nodes.find((x) => x.id === id); return !!n && !n.name.toLowerCase().includes(q); }
    return false;
  }

  static styles = css`
    :host { display: grid; grid-template-columns: 1fr 260px; gap: var(--ds-space-4);
      padding: var(--ds-space-4); max-width: 1320px; margin: 0 auto; color: var(--ds-text); }
    @media (max-width: 880px) { :host { grid-template-columns: 1fr; } .rail { order: -1; } }

    .main { display: grid; gap: var(--ds-space-3); min-width: 0; }
    .bar { display: flex; align-items: center; gap: var(--ds-space-3); flex-wrap: wrap; }
    .bar h2 { font-size: var(--ds-text-xl); margin: 0; letter-spacing: var(--ds-tracking-wide);
      background: linear-gradient(90deg, var(--ds-white), var(--ds-periwinkle));
      -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .bar .s { color: var(--ds-text-muted); font-size: var(--ds-text-xs); font-family: var(--ds-font-mono); }
    .spacer { flex: 1; }
    input {
      padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2);
      color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-sm); width: 200px; transition: border-color var(--ds-dur-fast), box-shadow var(--ds-dur-fast);
    }
    input:focus { outline: none; border-color: var(--ds-border-accent); box-shadow: var(--ds-glow); }

    button { font: inherit; font-size: var(--ds-text-xs); cursor: pointer; color: var(--ds-text-soft);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill);
      padding: var(--ds-space-2) var(--ds-space-3); transition: all var(--ds-dur-fast); white-space: nowrap; }
    button:hover { color: var(--ds-text); border-color: var(--ds-border-accent); box-shadow: var(--ds-glow); }
    button.on { color: var(--ds-on-accent); background: var(--ds-accent); border-color: transparent; }
    button.gnn { color: var(--ds-accent); border-color: var(--ds-border-accent); }
    button.gnn:hover { background: rgba(var(--ds-periwinkle-rgb), 0.12); }

    .canvas { position: relative; background:
        radial-gradient(120% 90% at 50% 0%, rgba(var(--ds-periwinkle-rgb),0.10), transparent 60%),
        radial-gradient(80% 80% at 80% 100%, rgba(154,140,255,0.08), transparent 55%),
        var(--ds-charcoal-900);
      border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden;
      box-shadow: var(--ds-elev-3), inset 0 0 60px rgba(0,0,0,0.4); }
    svg { width: 100%; height: auto; display: block; touch-action: none; }
    text { font-family: var(--ds-font-sans); fill: var(--ds-text-soft); pointer-events: none; }
    circle { cursor: grab; }
    circle:active { cursor: grabbing; }

    .tip { position: absolute; pointer-events: none; max-width: 240px; z-index: 5;
      background: var(--ds-glass); backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-strong); border-radius: var(--ds-radius-md);
      padding: var(--ds-space-2) var(--ds-space-3); box-shadow: var(--ds-elev-3);
      transform: translate(-50%, calc(-100% - 14px)); transition: opacity var(--ds-dur-fast); }
    .tip h4 { margin: 0 0 2px; font-size: var(--ds-text-sm); }
    .tip .meta { font-size: var(--ds-text-xs); color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .tip p { margin: 4px 0 0; font-size: var(--ds-text-xs); color: var(--ds-text-soft); line-height: 1.4; }

    .legend { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; font-size: var(--ds-text-xs); color: var(--ds-text-muted); align-items: center; }
    .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
    .legend .edge { width: 18px; height: 0; border-top: 2px solid; margin-right: 4px; display: inline-block; vertical-align: middle; }

    .rail { display: grid; gap: var(--ds-space-3); align-content: start; }
    .card { background: var(--ds-surface-1); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md); padding: var(--ds-space-3); }
    .card h3 { margin: 0 0 var(--ds-space-2); font-size: var(--ds-text-sm); color: var(--ds-text-soft);
      display: flex; align-items: center; gap: 6px; }
    .card h3::before { content: ""; width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .infer { display: grid; gap: var(--ds-space-2); }
    .infer .row { font-size: var(--ds-text-xs); line-height: 1.4; padding: var(--ds-space-2);
      background: var(--ds-surface-2); border-radius: var(--ds-radius-sm); border-left: 2px solid var(--ds-border-strong); }
    .infer .row.habit { border-left-color: var(--ds-periwinkle); }
    .infer .row.connection { border-left-color: var(--ds-sky); }
    .infer .row.hub { border-left-color: var(--ds-amber); }
    .infer .row.stale { border-left-color: var(--ds-text-muted); }
    .infer .tag { font-family: var(--ds-font-mono); font-size: 10px; text-transform: uppercase;
      letter-spacing: 0.05em; color: var(--ds-text-muted); }
    .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-2); }
    .metrics .m { background: var(--ds-surface-2); border-radius: var(--ds-radius-sm); padding: var(--ds-space-2); }
    .metrics .m b { display: block; font-size: var(--ds-text-lg); font-family: var(--ds-font-mono); color: var(--ds-text); }
    .metrics .m span { font-size: 10px; color: var(--ds-text-muted); }
    .toast { position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
      background: var(--ds-glass); border: 1px solid var(--ds-border-accent); color: var(--ds-text);
      padding: var(--ds-space-2) var(--ds-space-4); border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-xs); box-shadow: var(--ds-glow); backdrop-filter: blur(var(--ds-blur-md)); }
    .empty { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
  `;

  private edgeStroke(kind: string): string {
    if (kind === "gnn") return "var(--ds-accent)";
    if (kind === "semantic") return "var(--ds-lilac)";
    if (kind === "suggestion" || kind === "suggested") return "var(--ds-sky)";
    return "var(--ds-border-strong)";
  }

  render() {
    const g = (this.stats["graph"] ?? {}) as Record<string, number>;
    const tipNode = this.hover;
    return html`
      <div class="main">
        <div class="bar">
          <h2>Memory Graph</h2>
          <span class="s">${(this.stats["entities"] as number) ?? this.nodes.length} nodes · ${this.edges.length} links</span>
          <span class="spacer"></span>
          <button class=${this.colorMode === "community" ? "on" : ""}
            @click=${() => { this.colorMode = this.colorMode === "community" ? "type" : "community"; }}>
            ${this.colorMode === "community" ? "◍ Clusters" : "◐ Types"}
          </button>
          <button class=${this.showSemantic ? "on" : ""} @click=${() => { this.showSemantic = !this.showSemantic; }}>~ Semantic</button>
          <button class="gnn" @click=${() => this.runGnn()}>⚡ Run GNN</button>
          <input placeholder="Search…" @input=${(e: Event) => { this.query = (e.target as HTMLInputElement).value; this.focusedId = null; }} />
        </div>

        <div class="canvas">
          <svg viewBox="0 0 ${this.W} ${this.H}"
            @pointermove=${(e: PointerEvent) => this.onMove(e)}
            @pointerup=${() => this.onUp()} @pointerleave=${() => this.onUp()}
            @click=${(e: Event) => { if ((e.target as Element).tagName === "svg") this.focusedId = null; }}>
            <defs>
              <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="3.2" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            ${this.edges
              .filter((e) => this.showSemantic || e.kind !== "semantic")
              .map((e) => {
                const faded = this.dim(e.s.id) || this.dim(e.t.id);
                const base = e.kind === "relation" ? 0.34 : e.kind === "gnn" ? 0.7 : 0.18;
                const dash = e.kind === "semantic" ? "4 5" : e.kind === "gnn" ? "1 6" : "0";
                return svg`<line x1=${e.s.x} y1=${e.s.y} x2=${e.t.x} y2=${e.t.y}
                  stroke=${this.edgeStroke(e.kind)} stroke-width=${e.kind === "gnn" ? 1.6 : 1}
                  stroke-dasharray=${dash}
                  opacity=${faded ? 0.04 : base}></line>`;
              })}

            ${this.nodes.map((n) => {
              const r = this.nodeRadius(n);
              const faded = this.dim(n.id);
              const isHub = (n.pagerank ?? 0) * 1400 > 6 || n.deg >= 4;
              return svg`
                <circle cx=${n.x} cy=${n.y} r=${r}
                  fill=${this.nodeColor(n)}
                  filter=${isHub && !faded ? "url(#glow)" : nothing}
                  opacity=${faded ? 0.1 : 0.94}
                  stroke=${this.focusedId === n.id ? "var(--ds-white)" : "transparent"} stroke-width="1.5"
                  @pointerdown=${(e: PointerEvent) => this.onDown(n, e)}
                  @pointerenter=${() => { this.hover = n; }}
                  @pointerleave=${() => { if (this.hover === n) this.hover = null; }}
                  @click=${(e: Event) => { e.stopPropagation(); this.focusedId = this.focusedId === n.id ? null : n.id; }}></circle>
                ${(n.deg >= 2 || this.focusedId === n.id || isHub) && !faded
                  ? svg`<text x=${n.x + r + 3} y=${n.y + 3} font-size=${isHub ? 11 : 9}>${n.name}</text>`
                  : ""}
              `;
            })}
          </svg>

          ${tipNode ? html`
            <div class="tip" style=${`left:${(tipNode.x / this.W) * 100}%; top:${(tipNode.y / this.H) * 100}%`}>
              <h4>${tipNode.name}</h4>
              <div class="meta">${tipNode.type}${tipNode.community !== undefined ? ` · cluster ${tipNode.community}` : ""} · ${tipNode.deg} links</div>
              ${tipNode.description ? html`<p>${tipNode.description}</p>` : tipNode.context?.[0] ? html`<p>${tipNode.context[0]}</p>` : nothing}
            </div>` : nothing}

          ${this.busy ? html`<div class="toast">${this.busy}</div>` : nothing}
          ${this.loading ? html`<div class="toast">Loading memory…</div>` : nothing}
        </div>

        <div class="legend">
          ${this.colorMode === "type"
            ? Object.entries(TYPE_COLOR).map(([t, c]) => html`<span><i style="background:${c}"></i>${t}</span>`)
            : html`<span class="empty">Coloured by detected community · node size = PageRank importance</span>`}
          <span class="spacer"></span>
          <span><i class="edge" style="border-color:var(--ds-border-strong)"></i>fact</span>
          <span><i class="edge" style="border-color:var(--ds-lilac);border-top-style:dashed"></i>semantic</span>
          <span><i class="edge" style="border-color:var(--ds-accent);border-top-style:dotted"></i>GNN</span>
        </div>
      </div>

      <div class="rail">
        <div class="card">
          <h3>Network</h3>
          <div class="metrics">
            <div class="m"><b>${(this.stats["entities"] as number) ?? "—"}</b><span>entities</span></div>
            <div class="m"><b>${(this.stats["relationships"] as number) ?? "—"}</b><span>relations</span></div>
            <div class="m"><b>${g["communities"] ?? "—"}</b><span>clusters</span></div>
            <div class="m"><b>${g["density"] !== undefined ? (g["density"] as number).toFixed(3) : "—"}</b><span>density</span></div>
          </div>
        </div>
        <div class="card">
          <h3>Inferences</h3>
          <div class="infer">
            ${this.inferences.length
              ? this.inferences.map((i) => html`
                  <div class="row ${i.type}">
                    <span class="tag">${i.type}</span><br />${i.text}
                  </div>`)
              : html`<span class="empty">No inferences yet — teach DEEP more and they'll appear.</span>`}
          </div>
        </div>
      </div>
    `;
  }
}
