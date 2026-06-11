// <network-view> — devices on the local network (wifi/bluetooth), system
// vitals, and a live proximity event feed (from WS telemetry). Trust/block
// actions hit the live security API.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { proximityFeed } from "../../core/store";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

interface Device {
  mac: string; ip: string; hostname: string | null; vendor: string | null;
  trust_status: string; is_gateway: boolean; last_seen: string;
}
interface Vitals { cpu: number; ram: number; disk: number; ram_used_gb: number; ram_total_gb: number; net_sent_mbs: number; net_recv_mbs: number; cores: number; }

@customElement("network-view")
export class NetworkView extends SignalWatcher(LitElement) {
  @state() private devices: Device[] = [];
  @state() private vitals: Vitals | null = null;
  private timer?: ReturnType<typeof setInterval>;

  connectedCallback(): void {
    super.connectedCallback();
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), 6000);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this.timer); }

  private async refresh(): Promise<void> {
    void fetch("/api/security/devices").then((r) => r.json()).then((d) => (this.devices = d.devices ?? [])).catch(() => {});
    void fetch("/api/vitals").then((r) => r.json()).then((d) => (this.vitals = d)).catch(() => {});
  }

  private async act(mac: string, action: "trust" | "block"): Promise<void> {
    try {
      const r = await fetch(`/api/security/${action}`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ mac }),
      });
      if (r.ok) { toast(`Device ${action}ed`, action === "trust" ? "success" : "danger"); void this.refresh(); }
      else toast(`${action} failed`, "danger");
    } catch { toast(`${action} failed`, "danger"); }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1100px; margin: 0 auto; align-content: start; }
    .vitals { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .bar { height: 4px; border-radius: 2px; background: var(--ds-surface-3); margin-top: 6px; overflow: hidden; }
    .bar > i { display: block; height: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .dev { display: grid; grid-template-columns: 1fr auto; gap: var(--ds-space-3); align-items: center; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .dev:last-child { border-bottom: none; }
    .dev .name { display: flex; align-items: center; gap: var(--ds-space-2); }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .trusted { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .unknown { background: var(--ds-warning); }
    .blocked, .suspicious { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .acts { display: flex; gap: var(--ds-space-1); }
    .feed { display: grid; gap: 3px; max-height: 220px; overflow-y: auto; font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .ev { color: var(--ds-text-soft); display: flex; gap: var(--ds-space-2); }
    .ev .t { color: var(--ds-text-faint); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;

  private statBar(label: string, val: number, suffix = "%") {
    return html`<div class="stat"><div class="k">${label}</div><div class="v">${val.toFixed(val < 10 ? 1 : 0)}${suffix}</div>
      ${suffix === "%" ? html`<div class="bar"><i style="width:${Math.min(val, 100)}%"></i></div>` : ""}</div>`;
  }

  render() {
    const v = this.vitals;
    return html`
      <ds-panel heading="System vitals">
        ${v ? html`<div class="vitals">
          ${this.statBar("CPU", v.cpu)}
          ${this.statBar("RAM", v.ram)}
          ${this.statBar("Disk", v.disk)}
          <div class="stat"><div class="k">RAM used</div><div class="v">${v.ram_used_gb}<span style="font-size:0.6em">/${v.ram_total_gb}GB</span></div></div>
          <div class="stat"><div class="k">Net ↓↑</div><div class="v" style="font-size:var(--ds-text-lg)">${v.net_recv_mbs.toFixed(2)}/${v.net_sent_mbs.toFixed(2)}</div></div>
          <div class="stat"><div class="k">Cores</div><div class="v">${v.cores}</div></div>
        </div>` : html`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Network devices · ${this.devices.length}">
        ${this.devices.length ? this.devices.map((d) => html`
          <div class="dev">
            <div class="name">
              <span class="dot ${d.trust_status}"></span>
              <span>${d.hostname || d.ip}${d.is_gateway ? " · gateway" : ""}</span>
              <span class="meta">${d.ip} · ${d.mac}${d.vendor ? ` · ${d.vendor}` : ""}</span>
            </div>
            <div class="acts">
              <ds-button size="sm" @click=${() => void this.act(d.mac, "trust")}>trust</ds-button>
              <ds-button size="sm" variant="danger" @click=${() => void this.act(d.mac, "block")}>block</ds-button>
            </div>
          </div>
        `) : html`<span class="muted">scanning…</span>`}
      </ds-panel>

      <ds-panel heading="Proximity & RF events · live">
        ${proximityFeed.get().length ? html`<div class="feed">
          ${proximityFeed.get().map((e) => html`<div class="ev"><span class="t">${e.time}</span><span>${e.label}</span></div>`)}
        </div>` : html`<span class="muted">Listening for nearby access points & proximity changes…</span>`}
      </ds-panel>
    `;
  }
}
