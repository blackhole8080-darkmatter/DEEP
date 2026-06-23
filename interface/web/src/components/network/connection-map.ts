// <connection-map> — connection geography graph. Geolocates the machine's live
// established outbound connections (public remote IPs), plots the egress origin
// and draws an arc to each peer (color-coded by risk: direct/hosting/proxy),
// and attributes each peer to the local process(es) that opened it. Sortable
// peer list. Offline (no map tiles, no GPS) — derived from psutil connections
// + ip-api, server-side.
import { LitElement, html, css, svg } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchNetworkGeo, fetchInvestigate, type GeoPeer, type GeoOrigin, type Dossier } from "../../core/api";
import "../primitives/ds-panel";
import "../primitives/ds-button";

const REFRESH_MS = 15000;

@customElement("connection-map")
export class ConnectionMap extends LitElement {
  @state() private peers: GeoPeer[] = [];
  @state() private origin: GeoOrigin | null = null;
  @state() private elevated = 0;
  @state() private countries: string[] = [];
  @state() private loading = true;
  @state() private err = "";
  @state() private selected: string | null = null;
  @state() private dossier: Dossier | null = null;
  @state() private dossierLoading = false;
  @state() private auto = true;
  private timer: number | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
    this.startAuto();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.stopAuto();
  }

  private startAuto(): void {
    this.stopAuto();
    if (this.auto) this.timer = window.setInterval(() => { if (!this.loading) void this.load(); }, REFRESH_MS);
  }
  private stopAuto(): void {
    if (this.timer !== null) { clearInterval(this.timer); this.timer = null; }
  }
  private toggleAuto(): void {
    this.auto = !this.auto;
    this.startAuto();
  }

  private async load(): Promise<void> {
    this.loading = true; this.err = "";
    try {
      const r = await fetchNetworkGeo();
      if (r.error) this.err = r.error;
      this.peers = r.peers ?? [];
      this.origin = r.origin ?? null;
      this.elevated = r.elevated ?? 0;
      this.countries = r.countries ?? [];
      // Drop a stale selection if the peer is gone after a refresh.
      if (this.selected && !this.peers.some((p) => p.ip === this.selected)) {
        this.selected = null; this.dossier = null;
      }
    } catch (e) { this.err = String(e); }
    this.loading = false;
  }

  private async select(ip: string): Promise<void> {
    this.selected = ip;
    this.dossier = null;
    this.dossierLoading = true;
    try {
      this.dossier = await fetchInvestigate(ip);
    } catch (e) { this.dossier = { error: String(e) }; }
    this.dossierLoading = false;
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .count { font-family: var(--ds-font-mono); color: var(--ds-text-soft); font-size: var(--ds-text-sm); }
    .map { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .grat { stroke: var(--ds-border); stroke-width: 0.5; fill: none; }
    .pin { fill: var(--ds-info); cursor: pointer; transition: r var(--ds-dur-fast); }
    .pin.hosting { fill: var(--ds-warning); }
    .pin.proxy { fill: var(--ds-danger); }
    .pin.sel { stroke: var(--ds-text); stroke-width: 1.5; }
    .origin { fill: var(--ds-accent); stroke: var(--ds-bg); stroke-width: 1; }
    .origin-ring { fill: none; stroke: var(--ds-accent); opacity: 0.4; }
    .arc { fill: none; stroke: var(--ds-info); stroke-width: 0.6; opacity: 0.28; }
    .arc.hosting { stroke: var(--ds-warning); }
    .arc.proxy { stroke: var(--ds-danger); }
    .arc.sel { opacity: 0.9; stroke-width: 1.4; }
    .label { fill: var(--ds-text); font-size: 10px; font-family: var(--ds-font-mono); }
    .proc { color: var(--ds-accent); font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .legend { display: flex; gap: var(--ds-space-4); font-size: var(--ds-text-xs); color: var(--ds-text-soft); margin-top: var(--ds-space-2); }
    .legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
    .rows { display: grid; gap: 0; max-height: 320px; overflow-y: auto; }
    .row { display: grid; grid-template-columns: 1fr auto auto; gap: var(--ds-space-3); align-items: center; padding: var(--ds-space-2) var(--ds-space-1); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); cursor: pointer; }
    .row:hover, .row.sel { background: var(--ds-surface-2); }
    .row .loc { color: var(--ds-text); }
    .row .isp { color: var(--ds-text-soft); font-size: var(--ds-text-xs); }
    .row .ip { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .flag { font-size: var(--ds-text-xs); padding: 1px 6px; border-radius: var(--ds-radius-pill); }
    .flag.host { color: var(--ds-warning); border: 1px solid var(--ds-warning); }
    .flag.prox { color: var(--ds-danger); border: 1px solid var(--ds-danger); }
    .muted { color: var(--ds-text-muted); }
    .toggle { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); padding: 4px 10px; border-radius: var(--ds-radius-pill); border: 1px solid var(--ds-border); background: var(--ds-surface-2); color: var(--ds-text-muted); cursor: pointer; }
    .toggle.on { color: var(--ds-success); border-color: var(--ds-success); }
    .dossier .drow { display: flex; justify-content: space-between; gap: var(--ds-space-4); padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .dossier .dk { color: var(--ds-text-soft); text-transform: uppercase; font-size: var(--ds-text-xs); letter-spacing: var(--ds-tracking-wide); }
    .dossier .dv { font-family: var(--ds-font-mono); text-align: right; overflow-wrap: anywhere; }
    .dossier .sum { color: var(--ds-text); margin-bottom: var(--ds-space-2); }
    .dossier .sum.elevated { color: var(--ds-warning); }
  `;

  private pinClass(p: GeoPeer): string {
    return p.proxy ? "proxy" : p.hosting ? "hosting" : "";
  }

  render() {
    const W = 720, H = 360;
    const sx = (lon: number) => ((lon + 180) / 360) * W;
    const sy = (lat: number) => ((90 - lat) / 180) * H;
    const grat = [];
    for (let lon = -150; lon <= 150; lon += 30) grat.push(svg`<line class="grat" x1=${sx(lon)} y1="0" x2=${sx(lon)} y2=${H}></line>`);
    for (let lat = -60; lat <= 60; lat += 30) grat.push(svg`<line class="grat" x1="0" y1=${sy(lat)} x2=${W} y2=${sy(lat)}></line>`);

    return html`
      <ds-panel heading="Connection geography · live outbound peers">
        <div class="head">
          <span class="count">${this.loading
            ? "scanning connections…"
            : html`${this.peers.length} peer${this.peers.length === 1 ? "" : "s"} · ${this.countries.length} countr${this.countries.length === 1 ? "y" : "ies"}${this.elevated ? html` · <b style="color:var(--ds-warning)">${this.elevated} elevated</b>` : ""}`}</span>
          <div style="display:flex;gap:var(--ds-space-2);align-items:center">
            <button class="toggle ${this.auto ? "on" : ""}" @click=${() => this.toggleAuto()} title="Auto-refresh every 15s">${this.auto ? "● live" : "○ paused"}</button>
            <ds-button @click=${() => void this.load()}>${this.loading ? "…" : "rescan"}</ds-button>
          </div>
        </div>
        ${this.err ? html`<div class="muted">${this.err}</div>` : ""}
        <div class="map" style="margin-top:var(--ds-space-3)">
          <svg viewBox="0 0 ${W} ${H}">
            <rect width=${W} height=${H} fill="var(--ds-surface-1)"></rect>
            ${grat}
            <line class="grat" x1="0" y1=${H / 2} x2=${W} y2=${H / 2} stroke="var(--ds-border-strong)"></line>
            ${this.origin ? this.peers.map((p) => {
              const ox = sx(this.origin!.lon), oy = sy(this.origin!.lat);
              const px = sx(p.lon), py = sy(p.lat);
              // quadratic arc bowed upward, proportional to distance
              const mx = (ox + px) / 2, my = (oy + py) / 2 - Math.abs(px - ox) * 0.25 - 12;
              const isSel = this.selected === p.ip;
              return svg`<path class="arc ${this.pinClass(p)} ${isSel ? "sel" : ""}" d=${`M${ox},${oy} Q${mx},${my} ${px},${py}`}></path>`;
            }) : ""}
            ${this.peers.map((p) => {
              const cls = this.pinClass(p);
              const isSel = this.selected === p.ip;
              return svg`<circle class="pin ${cls} ${isSel ? "sel" : ""}" cx=${sx(p.lon)} cy=${sy(p.lat)} r=${isSel ? 6 : 4}
                @click=${() => void this.select(p.ip)}><title>${p.ip} — ${p.city}, ${p.country} (${p.isp})${p.processes.length ? " ← " + p.processes.join(", ") : ""}</title></circle>`;
            })}
            ${this.origin ? svg`
              <circle class="origin-ring" cx=${sx(this.origin.lon)} cy=${sy(this.origin.lat)} r="8"></circle>
              <circle class="origin" cx=${sx(this.origin.lon)} cy=${sy(this.origin.lat)} r="4"><title>egress · ${this.origin.city}, ${this.origin.country} (${this.origin.isp})</title></circle>
            ` : ""}
          </svg>
        </div>
        <div class="legend">
          ${this.origin ? html`<span><i style="background:var(--ds-accent)"></i>egress · ${this.origin.city}, ${this.origin.country}</span>` : ""}
          <span><i style="background:var(--ds-info)"></i>direct</span>
          <span><i style="background:var(--ds-warning)"></i>hosting / cloud</span>
          <span><i style="background:var(--ds-danger)"></i>proxy / VPN</span>
        </div>
      </ds-panel>

      <ds-panel heading="Peers · ${this.peers.length}">
        ${this.peers.length ? html`
          <div class="rows">
            ${this.peers.map((p) => html`
              <div class="row ${this.selected === p.ip ? "sel" : ""}" @click=${() => void this.select(p.ip)}>
                <div>
                  <div class="loc">${p.city || "?"}, ${p.country || "?"} ${p.proxy ? html`<span class="flag prox">PROXY</span>` : p.hosting ? html`<span class="flag host">HOSTING</span>` : ""}</div>
                  <div class="isp">${p.isp} · ${p.asn}</div>
                  <div class="ip">${p.ip}${p.processes.length ? html` · <span class="proc">${p.processes.join(", ")}</span>` : ""}</div>
                </div>
                <div class="ip">${p.connections}×</div>
              </div>
            `)}
          </div>
        ` : html`<span class="muted">${this.loading ? "locating…" : "No public outbound connections found."}</span>`}
      </ds-panel>

      ${this.selected ? html`
        <ds-panel heading="Dossier · ${this.selected}">
          ${this.dossierLoading
            ? html`<span class="muted">investigating…</span>`
            : this.dossier?.error
              ? html`<span class="muted">${this.dossier.error}</span>`
              : this.dossier
                ? html`
                    <div class="dossier">
                      ${this.dossier.summary ? html`<div class="sum ${this.dossier.risk === "elevated" ? "elevated" : ""}">${this.dossier.summary}</div>` : ""}
                      ${(this.dossier.findings ?? []).map((f) => html`<div class="drow"><span class="dk">${f.label}</span><span class="dv">${String(f.value)}</span></div>`)}
                    </div>`
                : html`<span class="muted">Select a peer for a full intelligence dossier.</span>`}
        </ds-panel>
      ` : ""}
    `;
  }
}
