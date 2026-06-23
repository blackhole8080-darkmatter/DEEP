// <connection-map> — connection geography. Geolocates the machine's live
// established outbound connections (public remote IPs) and plots one pin per
// peer on an offline equirectangular map, color-coded by risk flag
// (hosting/proxy), with a sortable peer list. No map tiles, no GPS — derived
// from psutil connections + ip-api, server-side.
import { LitElement, html, css, svg } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchNetworkGeo, type GeoPeer } from "../../core/api";
import "../primitives/ds-panel";
import "../primitives/ds-button";

@customElement("connection-map")
export class ConnectionMap extends LitElement {
  @state() private peers: GeoPeer[] = [];
  @state() private elevated = 0;
  @state() private countries: string[] = [];
  @state() private loading = true;
  @state() private err = "";
  @state() private selected: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading = true; this.err = "";
    try {
      const r = await fetchNetworkGeo();
      if (r.error) this.err = r.error;
      this.peers = r.peers ?? [];
      this.elevated = r.elevated ?? 0;
      this.countries = r.countries ?? [];
    } catch (e) { this.err = String(e); }
    this.loading = false;
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
    .label { fill: var(--ds-text); font-size: 10px; font-family: var(--ds-font-mono); }
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
          <ds-button @click=${() => void this.load()}>${this.loading ? "…" : "rescan"}</ds-button>
        </div>
        ${this.err ? html`<div class="muted">${this.err}</div>` : ""}
        <div class="map" style="margin-top:var(--ds-space-3)">
          <svg viewBox="0 0 ${W} ${H}">
            <rect width=${W} height=${H} fill="var(--ds-surface-1)"></rect>
            ${grat}
            <line class="grat" x1="0" y1=${H / 2} x2=${W} y2=${H / 2} stroke="var(--ds-border-strong)"></line>
            ${this.peers.map((p) => {
              const cls = this.pinClass(p);
              const isSel = this.selected === p.ip;
              return svg`<circle class="pin ${cls} ${isSel ? "sel" : ""}" cx=${sx(p.lon)} cy=${sy(p.lat)} r=${isSel ? 6 : 4}
                @click=${() => { this.selected = p.ip; }}><title>${p.ip} — ${p.city}, ${p.country} (${p.isp})</title></circle>`;
            })}
          </svg>
        </div>
        <div class="legend">
          <span><i style="background:var(--ds-info)"></i>direct</span>
          <span><i style="background:var(--ds-warning)"></i>hosting / cloud</span>
          <span><i style="background:var(--ds-danger)"></i>proxy / VPN</span>
        </div>
      </ds-panel>

      <ds-panel heading="Peers · ${this.peers.length}">
        ${this.peers.length ? html`
          <div class="rows">
            ${this.peers.map((p) => html`
              <div class="row ${this.selected === p.ip ? "sel" : ""}" @click=${() => { this.selected = p.ip; }}>
                <div>
                  <div class="loc">${p.city || "?"}, ${p.country || "?"} ${p.proxy ? html`<span class="flag prox">PROXY</span>` : p.hosting ? html`<span class="flag host">HOSTING</span>` : ""}</div>
                  <div class="isp">${p.isp} · ${p.asn}</div>
                  <div class="ip">${p.ip}</div>
                </div>
                <div class="ip">${p.connections}×</div>
              </div>
            `)}
          </div>
        ` : html`<span class="muted">${this.loading ? "locating…" : "No public outbound connections found."}</span>`}
      </ds-panel>
    `;
  }
}
