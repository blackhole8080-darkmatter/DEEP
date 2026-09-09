// <cybertech-world-view> — evidence-first intelligence world.
//
// This is intentionally a read-only vertical slice: it consumes /api/world,
// labels degraded/stale data, and never starts a scan or changes device state.
import { LitElement, html, css, svg, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Layer { id: string; label: string; description: string; count: number; enabled: boolean; }
interface WorldNode { id: string; layer: string; label: string; lat: number; lon: number; country: string; city: string; source: string; classification: string; severity: string; detail: Record<string, unknown>; }
interface WorldEvent { id: string; source: string; kind: string; severity: string; timestamp: string; summary: string; techniques: string[]; related_cves: string[]; }
interface WorldSnapshot {
  generated_at: string; layers: Layer[]; nodes: WorldNode[]; edges: unknown[]; events: WorldEvent[];
  sources: { id: string; label: string; category: string; available: boolean; reason: string }[];
  stats: { threat_nodes: number; security_events: number; graph_entities: number; graph_edges: number; available_sources: number; total_sources: number };
  degraded: Record<string, unknown>;
}

const EMPTY: WorldSnapshot = {
  generated_at: "", layers: [], nodes: [], edges: [], events: [], sources: [],
  stats: { threat_nodes: 0, security_events: 0, graph_entities: 0, graph_edges: 0, available_sources: 0, total_sources: 0 },
  degraded: {},
};

@customElement("cybertech-world-view")
export class CybertechWorldView extends LitElement {
  @state() private snapshot: WorldSnapshot = EMPTY;
  @state() private enabled = new Set<string>(["threats", "local", "entities", "alerts"]);
  @state() private selected: WorldNode | null = null;
  @state() private loading = true;
  @state() private error = "";
  private timer = 0;

  static styles = css`
    :host { display: block; height: 100%; min-height: 520px; overflow: auto; color: var(--ds-text, #d9f4ff); font-family: var(--ds-font-sans, system-ui); background: #050a12; }
    .shell { min-height: 100%; display: grid; grid-template-rows: auto 1fr; }
    header { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-bottom: 1px solid rgba(0,229,255,.16); background: rgba(4,11,20,.82); }
    .title { font-family: var(--ds-font-mono, monospace); letter-spacing: .16em; text-transform: uppercase; color: #00e5ff; font-size: .8rem; }
    .subtitle { color: rgba(220,240,255,.55); font-size: .72rem; }
    .spacer { flex: 1; }
    .status { display: inline-flex; align-items: center; gap: 6px; color: rgba(150,240,200,.9); font: .68rem var(--ds-font-mono, monospace); text-transform: uppercase; }
    .status::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 9px currentColor; }
    .status.bad { color: #ff9c9c; }
    button { font: inherit; }
    .refresh { cursor: pointer; color: #9deeff; background: rgba(0,229,255,.08); border: 1px solid rgba(0,229,255,.25); border-radius: 6px; padding: 5px 9px; font-size: .7rem; }
    .refresh:hover { background: rgba(0,229,255,.18); }
    .layout { min-height: 0; display: grid; grid-template-columns: 188px minmax(360px, 1fr) 260px; }
    .rail, .dossier { padding: 16px; background: rgba(4,10,18,.78); }
    .rail { border-right: 1px solid rgba(0,229,255,.12); }
    .dossier { border-left: 1px solid rgba(0,229,255,.12); }
    .rail-title, .panel-title { color: rgba(0,229,255,.82); font: .68rem var(--ds-font-mono, monospace); letter-spacing: .14em; text-transform: uppercase; margin-bottom: 12px; }
    .layer { width: 100%; display: flex; align-items: center; gap: 8px; text-align: left; cursor: pointer; color: rgba(220,240,255,.7); background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 8px 7px; margin-bottom: 5px; }
    .layer:hover, .layer.on { color: #fff; background: rgba(0,229,255,.08); border-color: rgba(0,229,255,.22); }
    .layer.off { opacity: .42; }
    .layer-count { margin-left: auto; color: rgba(0,229,255,.82); font: .68rem var(--ds-font-mono, monospace); }
    .legend { margin-top: 22px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,.08); color: rgba(220,240,255,.48); font-size: .68rem; line-height: 1.5; }
    .map-panel { position: relative; min-height: 520px; overflow: hidden; background: radial-gradient(circle at 50% 45%, rgba(0,229,255,.09), transparent 44%), #050b14; }
    .map-panel::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: repeating-linear-gradient(0deg, transparent 0 31px, rgba(0,229,255,.035) 32px), repeating-linear-gradient(90deg, transparent 0 31px, rgba(0,229,255,.035) 32px); }
    .map { width: 100%; height: 100%; min-height: 520px; display: block; }
    .graticule { stroke: rgba(0,229,255,.16); stroke-width: .12; fill: none; }
    .land { fill: rgba(33,79,94,.22); stroke: rgba(100,220,230,.18); stroke-width: .25; }
    .node { cursor: pointer; stroke: rgba(255,255,255,.7); stroke-width: .18; }
    .node.high { fill: #ffb84d; } .node.critical { fill: #ff3d70; } .node.medium { fill: #00e5ff; } .node.low, .node.info { fill: #66e6b0; }
    .node:hover { stroke-width: .5; filter: drop-shadow(0 0 2px currentColor); }
    .map-label { position: absolute; left: 16px; top: 14px; color: rgba(220,240,255,.5); font: .66rem var(--ds-font-mono, monospace); text-transform: uppercase; letter-spacing: .12em; }
    .map-empty { position: absolute; inset: 0; display: grid; place-items: center; color: rgba(220,240,255,.46); text-align: center; padding: 40px; font-size: .85rem; }
    .stats { position: absolute; right: 14px; top: 12px; display: flex; gap: 10px; z-index: 2; }
    .stat { padding: 6px 8px; border: 1px solid rgba(0,229,255,.15); background: rgba(3,10,18,.68); border-radius: 5px; color: rgba(220,240,255,.58); font: .62rem var(--ds-font-mono, monospace); }
    .stat strong { color: #9deeff; font-size: .78rem; }
    .dossier-empty { color: rgba(220,240,255,.45); font-size: .78rem; line-height: 1.55; }
    .dossier h3 { margin: 0 0 12px; color: #fff; font: .86rem var(--ds-font-mono, monospace); overflow-wrap: anywhere; }
    .kv { display: grid; gap: 3px; margin: 0 0 12px; }
    .kv dt { color: rgba(220,240,255,.4); font-size: .64rem; text-transform: uppercase; letter-spacing: .08em; }
    .kv dd { margin: 0; color: rgba(220,240,255,.86); font: .72rem var(--ds-font-mono, monospace); overflow-wrap: anywhere; }
    .badge { display: inline-block; border: 1px solid rgba(255,184,77,.4); color: #ffca75; padding: 3px 6px; border-radius: 4px; font: .62rem var(--ds-font-mono, monospace); text-transform: uppercase; }
    .feed { border-top: 1px solid rgba(0,229,255,.12); padding: 12px 16px; background: rgba(3,8,15,.9); max-height: 190px; overflow: auto; }
    .event { display: grid; grid-template-columns: 66px 1fr; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,.05); font-size: .72rem; }
    .event-time { color: rgba(220,240,255,.38); font: .64rem var(--ds-font-mono, monospace); }
    .event-text { color: rgba(220,240,255,.76); }
    .event-text strong { color: #9deeff; font-weight: 500; }
    .degraded { color: #ffca75; font-size: .68rem; padding: 10px 16px; border-top: 1px solid rgba(255,184,77,.2); background: rgba(80,48,8,.18); }
    @media (max-width: 900px) { .layout { grid-template-columns: 150px 1fr; } .dossier { grid-column: 1 / -1; border-left: 0; border-top: 1px solid rgba(0,229,255,.12); } }
    @media (max-width: 620px) { .layout { grid-template-columns: 1fr; } .rail { border-right: 0; border-bottom: 1px solid rgba(0,229,255,.12); } .map-panel { min-height: 440px; } .map { min-height: 440px; } .stats { display: none; } }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
    this.timer = window.setInterval(() => void this.load(), 30_000);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.timer);
  }

  private async load(): Promise<void> {
    this.loading = true;
    this.error = "";
    try {
      const response = await fetch("/api/world?limit=160");
      if (!response.ok) throw new Error(`world API returned ${response.status}`);
      this.snapshot = (await response.json()) as WorldSnapshot;
    } catch (error) {
      this.error = error instanceof Error ? error.message : "Unable to load Cybertech World";
    } finally {
      this.loading = false;
    }
  }

  private toggle(id: string): void {
    const next = new Set(this.enabled);
    if (next.has(id)) next.delete(id); else next.add(id);
    this.enabled = next;
  }

  private point(node: WorldNode): { x: number; y: number } {
    return { x: 50 + node.lon / 3.6, y: 50 - node.lat / 1.8 };
  }

  private severityClass(node: WorldNode): string {
    return ["critical", "high", "medium", "low", "info"].includes(node.severity) ? node.severity : "info";
  }

  private formatTime(value: string): string {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value.slice(0, 16) : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  private renderMap() {
    const nodes = this.snapshot.nodes.filter((node) => this.enabled.has(node.layer));
    return svg`
      <svg class="map" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Cybertech World threat map">
        <path class="land" d="M8 31 L18 22 L29 25 L33 36 L27 45 L17 43 L11 51 L5 43 Z M37 20 L51 18 L62 24 L70 21 L82 27 L91 38 L84 49 L72 47 L65 57 L55 52 L48 63 L39 56 L35 43 Z M30 65 L39 69 L42 79 L37 90 L29 78 Z M69 60 L79 61 L87 71 L82 83 L71 78 Z"></path>
        ${Array.from({ length: 7 }, (_, i) => svg`<line class="graticule" x1="0" y1="${10 + i * 13.3}" x2="100" y2="${10 + i * 13.3}"></line>`)}
        ${Array.from({ length: 11 }, (_, i) => svg`<line class="graticule" x1="${i * 10}" y1="0" x2="${i * 10}" y2="100"></line>`)}
        ${nodes.map((node) => { const p = this.point(node); return svg`<circle class="node ${this.severityClass(node)}" cx="${p.x}" cy="${p.y}" r="${node.severity === "critical" ? 1.1 : .7}" @click=${() => (this.selected = node)}><title>${node.label} · ${node.source}</title></circle>`; })}
      </svg>
    `;
  }

  private renderDossier() {
    if (!this.selected) return html`<div class="dossier-empty">Select a sourced map entity to inspect its evidence, classification, and origin. No action is performed by selecting an entity.</div>`;
    const n = this.selected;
    return html`
      <h3>${n.label}</h3>
      <span class="badge">${n.severity} · ${n.classification}</span>
      <dl class="kv"><dt>Source</dt><dd>${n.source}</dd><dt>Location</dt><dd>${n.city || "—"}${n.city && n.country ? ", " : ""}${n.country || "—"}</dd><dt>Coordinates</dt><dd>${n.lat.toFixed(3)}, ${n.lon.toFixed(3)}</dd></dl>
      <div class="panel-title">Evidence fields</div>
      <dl class="kv">${Object.entries(n.detail).slice(0, 8).map(([key, value]) => html`<dt>${key.replaceAll("_", " ")}</dt><dd>${String(value ?? "—")}</dd>`)}</dl>
    `;
  }

  render() {
    const statusBad = Boolean(this.error) || Object.keys(this.snapshot.degraded).length > 0;
    return html`
      <div class="shell">
        <header><div class="title">DEEP // Cybertech World</div><div class="subtitle">read-only intelligence fusion</div><div class="spacer"></div><div class="status ${statusBad ? "bad" : ""}">${this.loading ? "syncing" : statusBad ? "degraded" : "live"}</div><button class="refresh" @click=${() => void this.load()}>Refresh</button></header>
        <div class="layout">
          <aside class="rail"><div class="rail-title">Layers</div>${this.snapshot.layers.map((layer) => html`<button class="layer ${this.enabled.has(layer.id) ? "on" : "off"}" @click=${() => this.toggle(layer.id)}><span>${this.enabled.has(layer.id) ? "◉" : "○"}</span><span>${layer.label}</span><span class="layer-count">${layer.count}</span></button>`)}<div class="legend">Counts are sourced from the current snapshot. Missing feeds remain degraded; they are never rendered as zero-risk.</div></aside>
          <main class="map-panel"><div class="map-label">global signal field · ${this.snapshot.generated_at ? this.formatTime(this.snapshot.generated_at) : "waiting"}</div><div class="stats"><div class="stat"><strong>${this.snapshot.stats.threat_nodes}</strong><br>threat nodes</div><div class="stat"><strong>${this.snapshot.stats.security_events}</strong><br>events</div><div class="stat"><strong>${this.snapshot.stats.available_sources}/${this.snapshot.stats.total_sources}</strong><br>sources</div></div>${this.renderMap()}${!this.loading && !this.snapshot.nodes.length ? html`<div class="map-empty">No geolocated threat nodes are available in the current snapshot.<br>The world is quiet or the upstream feeds are degraded.</div>` : nothing}</main>
          <aside class="dossier"><div class="panel-title">Entity dossier</div>${this.renderDossier()}</aside>
        </div>
        ${this.snapshot.events.length ? html`<section class="feed"><div class="panel-title">Live intelligence feed</div>${this.snapshot.events.slice(0, 12).map((event) => html`<div class="event"><span class="event-time">${this.formatTime(event.timestamp)}</span><span class="event-text"><strong>${event.severity.toUpperCase()}</strong> · ${event.summary} <small>(${event.source})</small></span></div>`)}</section>` : nothing}
        ${this.error ? html`<div class="degraded">${this.error}</div>` : Object.keys(this.snapshot.degraded).length ? html`<div class="degraded">Upstream limitations are visible: ${Object.keys(this.snapshot.degraded).join(", ")}. Inspect source health before treating the picture as complete.</div>` : nothing}
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "cybertech-world-view": CybertechWorldView; } }
