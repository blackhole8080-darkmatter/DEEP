// <memory-graph> — interactive knowledge-graph visualization. Pulls entities +
// relationships from /api/knowledge/vault and runs a small force simulation in
// an SVG. Search to filter, click a node to focus its neighbourhood.
import { LitElement, html, css, svg } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Entity { id: string; name: string; type: string; }
interface Rel { source: string; target: string; relation: string; }
interface Node extends Entity { x: number; y: number; vx: number; vy: number; deg: number; }

const TYPE_COLOR: Record<string, string> = {
  technology: "var(--ds-accent)",
  topic: "var(--ds-neon-violet, var(--ds-info))",
  concept: "var(--ds-success)",
  person: "var(--ds-warning)",
  project: "var(--ds-danger)",
};

@customElement("memory-graph")
export class MemoryGraph extends LitElement {
  @state() private nodes: Node[] = [];
  @state() private edges: { s: Node; t: Node; relation: string }[] = [];
  @state() private query = "";
  @state() private focus: string | null = null;
  @state() private stats: Record<string, number> = {};
  private raf = 0;
  private readonly W = 900;
  private readonly H = 560;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }
  disconnectedCallback(): void { super.disconnectedCallback(); cancelAnimationFrame(this.raf); }

  private async load(): Promise<void> {
    try {
      const d = await (await fetch("/api/knowledge/vault?limit=200")).json();
      const ents: Entity[] = d.entities ?? [];
      const rels: Rel[] = d.relationships ?? [];
      this.stats = d.stats ?? {};
      const deg: Record<string, number> = {};
      for (const r of rels) { deg[r.source] = (deg[r.source] ?? 0) + 1; deg[r.target] = (deg[r.target] ?? 0) + 1; }
      const byId = new Map<string, Node>();
      this.nodes = ents.map((e, i) => {
        const a = (i / ents.length) * Math.PI * 2;
        const n: Node = { ...e, x: this.W / 2 + Math.cos(a) * 200, y: this.H / 2 + Math.sin(a) * 160, vx: 0, vy: 0, deg: deg[e.id] ?? 0 };
        byId.set(e.id, n); return n;
      });
      this.edges = rels.map((r) => ({ s: byId.get(r.source)!, t: byId.get(r.target)!, relation: r.relation }))
        .filter((e) => e.s && e.t);
      this.simulate(220);
    } catch { /* ignore */ }
  }

  /** Tiny force sim: repulsion + spring + centering, run for n ticks then settle. */
  private simulate(ticks: number): void {
    const tick = () => {
      const N = this.nodes;
      for (let i = 0; i < N.length; i++) {
        for (let j = i + 1; j < N.length; j++) {
          const a = N[i], b = N[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          let d2 = dx * dx + dy * dy || 0.01;
          const f = 1400 / d2;
          const d = Math.sqrt(d2);
          dx /= d; dy /= d;
          a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
        }
      }
      for (const e of this.edges) {
        let dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (d - 90) * 0.01;
        dx /= d; dy /= d;
        e.s.vx += dx * f; e.s.vy += dy * f; e.t.vx -= dx * f; e.t.vy -= dy * f;
      }
      for (const n of this.nodes) {
        n.vx += (this.W / 2 - n.x) * 0.002;
        n.vy += (this.H / 2 - n.y) * 0.002;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x = Math.max(20, Math.min(this.W - 20, n.x + n.vx));
        n.y = Math.max(20, Math.min(this.H - 20, n.y + n.vy));
      }
      this.requestUpdate();
      if (--ticks > 0) this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); max-width: 1000px; margin: 0 auto; }
    .bar { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .bar h2 { font-size: var(--ds-text-lg); margin: 0; }
    .bar .s { color: var(--ds-text-muted); font-size: var(--ds-text-sm); font-family: var(--ds-font-mono); }
    input {
      padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2);
      color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-sm); width: 220px;
    }
    input:focus { outline: none; border-color: var(--ds-border-accent); }
    .canvas { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    text { font-family: var(--ds-font-sans); fill: var(--ds-text-soft); pointer-events: none; }
    circle { cursor: pointer; transition: r var(--ds-dur-fast); }
    .legend { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
  `;

  private dim(id: string): boolean {
    const q = this.query.toLowerCase();
    const n = this.nodes.find((x) => x.id === id);
    if (this.focus) {
      if (id === this.focus) return false;
      return !this.edges.some((e) => (e.s.id === this.focus && e.t.id === id) || (e.t.id === this.focus && e.s.id === id));
    }
    if (q && n) return !n.name.toLowerCase().includes(q);
    return false;
  }

  render() {
    return html`
      <div class="bar">
        <h2>Memory graph</h2>
        <span class="s">${this.stats["total_entities"] ?? this.nodes.length} entities · ${this.edges.length} links</span>
        <input placeholder="Search entities…" @input=${(e: Event) => { this.query = (e.target as HTMLInputElement).value; this.focus = null; }} />
      </div>
      <div class="canvas">
        <svg viewBox="0 0 ${this.W} ${this.H}" @click=${(e: Event) => { if ((e.target as Element).tagName === "svg") this.focus = null; }}>
          ${this.edges.map((e) => svg`<line x1=${e.s.x} y1=${e.s.y} x2=${e.t.x} y2=${e.t.y}
            stroke="var(--ds-border-strong)" stroke-width="1"
            opacity=${this.dim(e.s.id) || this.dim(e.t.id) ? 0.05 : 0.35}></line>`)}
          ${this.nodes.map((n) => {
            const r = Math.min(5 + n.deg * 1.6, 16);
            const faded = this.dim(n.id);
            return svg`
              <circle cx=${n.x} cy=${n.y} r=${r}
                fill=${TYPE_COLOR[n.type] ?? "var(--ds-text-muted)"}
                opacity=${faded ? 0.12 : 0.92}
                @click=${() => (this.focus = this.focus === n.id ? null : n.id)}></circle>
              ${(n.deg >= 2 || this.focus === n.id) && !faded
                ? svg`<text x=${n.x + r + 2} y=${n.y + 3} font-size="9">${n.name}</text>`
                : ""}
            `;
          })}
        </svg>
      </div>
      <div class="legend">
        ${Object.entries(TYPE_COLOR).map(([t, c]) => html`<span><i style="background:${c}"></i>${t}</span>`)}
      </div>
    `;
  }
}
