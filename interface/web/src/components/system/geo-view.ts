// <geo-view> — the machine's network-reported precise location: an
// equirectangular coordinate map with a glowing pin at lat/lon, plus city,
// region, country, coordinates and public IP. Offline (no map tiles).
import { LitElement, html, css, svg } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchGeo, type GeoSelf } from "../../core/api";
import "../primitives/ds-panel";

@customElement("geo-view")
export class GeoView extends LitElement {
  @state() private geo: GeoSelf | null = null;
  @state() private err = "";

  connectedCallback(): void {
    super.connectedCallback();
    void fetchGeo().then((g) => (this.geo = g)).catch((e) => (this.err = String(e)));
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 980px; margin: 0 auto; align-content: start; }
    .map { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .grat { stroke: var(--ds-border); stroke-width: 0.5; fill: none; }
    .pin { fill: var(--ds-danger); }
    .pulse { fill: var(--ds-danger); opacity: 0.4; animation: ping 2s ease-out infinite; transform-origin: center; transform-box: fill-box; }
    @keyframes ping { 0% { transform: scale(1); opacity: 0.5; } 100% { transform: scale(4); opacity: 0; } }
    .rows { display: grid; gap: 0; }
    .row { display: flex; justify-content: space-between; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); text-transform: uppercase; font-size: var(--ds-text-xs); letter-spacing: var(--ds-tracking-wide); }
    .row b { font-family: var(--ds-font-mono); }
    .big { font-size: var(--ds-text-2xl); font-weight: 700; }
    .note { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
    .muted { color: var(--ds-text-muted); }
  `;

  render() {
    if (this.err) return html`<ds-panel heading="Location"><span class="muted">${this.err}</span></ds-panel>`;
    const g = this.geo;
    const W = 720, H = 360;
    // equirectangular projection
    const px = g ? ((g.lon + 180) / 360) * W : 0;
    const py = g ? ((90 - g.lat) / 180) * H : 0;
    const grat = [];
    for (let lon = -150; lon <= 150; lon += 30) { const x = ((lon + 180) / 360) * W; grat.push(svg`<line class="grat" x1=${x} y1="0" x2=${x} y2=${H}></line>`); }
    for (let lat = -60; lat <= 60; lat += 30) { const y = ((90 - lat) / 180) * H; grat.push(svg`<line class="grat" x1="0" y1=${y} x2=${W} y2=${y}></line>`); }
    return html`
      <ds-panel heading="Precise location · network-reported">
        <div class="map">
          <svg viewBox="0 0 ${W} ${H}">
            <rect width=${W} height=${H} fill="var(--ds-surface-1)"></rect>
            ${grat}
            <line class="grat" x1="0" y1=${H / 2} x2=${W} y2=${H / 2} stroke="var(--ds-border-strong)"></line>
            ${g ? svg`
              <circle class="pulse" cx=${px} cy=${py} r="5"></circle>
              <circle class="pin" cx=${px} cy=${py} r="5"></circle>
              <text x=${px + 9} y=${py + 4} fill="var(--ds-text)" font-size="12" font-family="var(--ds-font-mono)">${g.city}, ${g.country}</text>
            ` : ""}
          </svg>
        </div>
        ${g ? html`<div class="big" style="margin-top:var(--ds-space-3);color:var(--ds-accent)">${g.city}, ${g.regionName}</div>` : ""}
      </ds-panel>

      ${g ? html`
        <ds-panel heading="Coordinates & network">
          <div class="rows">
            <div class="row"><span class="k">country</span><b>${g.country}</b></div>
            <div class="row"><span class="k">region</span><b>${g.regionName}</b></div>
            <div class="row"><span class="k">latitude</span><b>${g.lat}°</b></div>
            <div class="row"><span class="k">longitude</span><b>${g.lon}°</b></div>
            <div class="row"><span class="k">public IP</span><b>${g.query}</b></div>
            ${g.isp ? html`<div class="row"><span class="k">ISP</span><b>${g.isp}</b></div>` : ""}
          </div>
          <p class="note">Derived from the public IP DEEP currently exits through — reflects your VPN/network egress, not GPS.</p>
        </ds-panel>
      ` : html`<ds-panel heading="Coordinates"><span class="muted">locating…</span></ds-panel>`}
    `;
  }
}
