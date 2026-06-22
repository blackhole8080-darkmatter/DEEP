// <network-view> — DEEP Network Command Center
// Unified security dashboard: topology, devices, threats, scanner, WiFi.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { proximityFeed } from "../../core/store";
import {
  fetchSecurityStatus, fetchSecurityDevices, fetchSecurityEvents,
  fetchNetworkThreats, fetchWifiStatus, scanTarget,
  trustDevice, blockDevice, acknowledgeSecurityEvent,
  fetchNetworkGraph, fetchNetworkStats,
  type SecurityDevice, type SecurityStatus, type SecurityEvent, type Threat,
  type GraphData, type GraphNode,
} from "../../core/api";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";
import "../network/topology-canvas";
import "../network/detail-panel";

@customElement("network-view")
export class NetworkView extends SignalWatcher(LitElement) {
  @state() private status: SecurityStatus | null = null;
  @state() private devices: SecurityDevice[] = [];
  @state() private events: SecurityEvent[] = [];
  @state() private threats: Threat[] = [];
  @state() private aps: { ssid: string; bssid: string; channel: number; signal: number; rogue: boolean }[] = [];
  @state() private evilTwin = false;
  @state() private loading = true;
  @state() private filter = "all";
  @state() private scanIp = "";
  @state() private scanResult: any = null;
  @state() private scanLoading = false;
  @state() private graph: GraphData = { nodes: [], edges: [] };
  @state() private graphStats: any = null;
  @state() private selectedNode: GraphNode | null = null;
  private timer?: ReturnType<typeof setInterval>;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
    this.timer = setInterval(() => void this.load(), 8000);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this.timer); }

  private async load(): Promise<void> {
    try {
      const [s, d, e, t, w, g, gs] = await Promise.all([
        fetchSecurityStatus().catch(() => null),
        fetchSecurityDevices().catch(() => ({ devices: [] })),
        fetchSecurityEvents(20).catch(() => ({ events: [] })),
        fetchNetworkThreats(24).catch(() => ({ threats: [] })),
        fetchWifiStatus().catch(() => ({ aps: [], evil_twin_detected: false })),
        fetchNetworkGraph().catch(() => ({ nodes: [], edges: [] })),
        fetchNetworkStats().catch(() => null),
      ]);
      this.status = s;
      this.devices = d.devices;
      this.events = e.events;
      this.threats = t.threats;
      this.aps = w.aps;
      this.evilTwin = w.evil_twin_detected;
      this.graph = g;
      this.graphStats = gs;
    } catch { /* noop */ }
    this.loading = false;
  }

  private async act(mac: string, action: "trust" | "block"): Promise<void> {
    try {
      const fn = action === "trust" ? trustDevice : blockDevice;
      await fn(mac);
      toast(`Device ${action}ed`, action === "trust" ? "success" : "danger");
      void this.load();
    } catch { toast(`${action} failed`, "danger"); }
  }

  private async ackEvent(id: string): Promise<void> {
    try { await acknowledgeSecurityEvent(id); void this.load(); } catch { toast("Ack failed", "danger"); }
  }

  private async doScan(): Promise<void> {
    if (!this.scanIp.trim()) return;
    this.scanLoading = true;
    try { this.scanResult = await scanTarget(this.scanIp.trim()); }
    catch { toast("Scan failed", "danger"); }
    this.scanLoading = false;
  }

  private filteredDevices() {
    if (this.filter === "all") return this.devices;
    return this.devices.filter((d) => d.trust_status === this.filter);
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1200px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    /* Score header */
    .score-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: var(--ds-space-3); }
    .score-card { padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); text-align: center; }
    .score-card .num { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); }
    .score-card .num.ok { color: var(--ds-success); }
    .score-card .num.warn { color: var(--ds-warning); }
    .score-card .num.danger { color: var(--ds-danger); }
    .score-card .label { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); margin-top: var(--ds-space-1); }
    /* Topology */
    .topo-wrap { height: 320px; background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); overflow: hidden; }
    /* Tabs */
    .tabs { display: flex; gap: var(--ds-space-1); margin-bottom: var(--ds-space-3); }
    .tab { padding: var(--ds-space-1) var(--ds-space-3); border-radius: var(--ds-radius-pill); border: 1px solid var(--ds-border); background: none; color: var(--ds-text-muted); font-size: var(--ds-text-sm); cursor: pointer; }
    .tab.on { color: var(--ds-on-accent); background: var(--ds-accent); border-color: var(--ds-accent); }
    /* Device table */
    .dev-table { display: grid; gap: 1px; }
    .dev-row { display: grid; grid-template-columns: 1.2fr 1fr 1.2fr 0.9fr 0.8fr auto; gap: var(--ds-space-2); align-items: center; padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-1); font-size: var(--ds-text-sm); }
    .dev-row.head { font-size: var(--ds-text-xs); color: var(--ds-text-faint); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); background: none; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .trust-trusted { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .trust-unknown { background: var(--ds-warning); }
    .trust-suspicious, .trust-blocked { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .badge { padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; }
    .badge-trusted { background: rgba(16,185,129,0.12); color: var(--ds-success); }
    .badge-unknown { background: rgba(245,158,11,0.12); color: var(--ds-warning); }
    .badge-suspicious { background: rgba(239,68,68,0.12); color: var(--ds-danger); }
    .badge-blocked { background: rgba(220,38,38,0.12); color: #dc2626; }
    /* Events */
    .ev { display: flex; align-items: center; gap: var(--ds-space-2); padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .ev:last-child { border-bottom: 0; }
    .sev-critical { color: #ef4444; }
    .sev-warning { color: #f59e0b; }
    .sev-info { color: var(--ds-text-muted); }
    /* Scanner */
    .scan-row { display: flex; gap: var(--ds-space-2); }
    .scan-row input { flex: 1; padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); }
    /* WiFi */
    .ap { display: flex; justify-content: space-between; align-items: center; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .ap .rogue { color: #ef4444; font-weight: 600; }
    .evil-twin { padding: var(--ds-space-2) var(--ds-space-4); background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: var(--ds-radius-md); color: #ef4444; font-size: var(--ds-text-sm); text-align: center; }
  `;

  render() {
    if (this.loading) return html`<div class="muted">Loading network command center…</div>`;
    const s = this.status;
    const filtered = this.filteredDevices();
    const unack = this.events.filter((e) => !e.acknowledged);

    return html`
      <!-- Security Score Header -->
      <div class="score-row">
        <div class="score-card">
          <div class="num ${s ? (s.score >= 80 ? "ok" : s.score >= 50 ? "warn" : "danger") : ""}">${s?.score ?? "--"}</div>
          <div class="label">Security Score</div>
        </div>
        <div class="score-card"><div class="num ok">${s?.devices_trusted ?? 0}</div><div class="label">Trusted</div></div>
        <div class="score-card"><div class="num warn">${s?.devices_unknown ?? 0}</div><div class="label">Unknown</div></div>
        <div class="score-card"><div class="num danger">${s?.devices_suspicious ?? 0}</div><div class="label">Suspicious</div></div>
        <div class="score-card"><div class="num ${(s?.threats_24h ?? 0) > 0 ? "danger" : "ok"}">${s?.threats_24h ?? 0}</div><div class="label">Threats 24h</div></div>
      </div>

      <!-- Topology + Detail Panel -->
      <ds-panel heading="Network Topology · ${this.graph.nodes.length} nodes · ${this.graph.edges.length} edges">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);align-items:center;">
          <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);">${this.graphStats ? Object.entries(this.graphStats.nodes_by_layer).map(([l, c]) => `${l}:${c}`).join(" · ") : ""}</span>
          <ds-button size="sm" @click=${() => void this.load()}>refresh</ds-button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 320px;gap:var(--ds-space-3);height:400px;">
          <div class="topo-wrap" style="height:100%;">
            <topology-canvas
              .nodes=${this.graph.nodes}
              .edges=${this.graph.edges}
              @node-select=${(e: CustomEvent) => { this.selectedNode = this.graph.nodes.find((n) => n.id === e.detail) || null; }}
            ></topology-canvas>
          </div>
          <network-detail-panel
            .node=${this.selectedNode}
            style="height:100%;overflow:hidden;"
          ></network-detail-panel>
        </div>
      </ds-panel>

      <!-- Active Alerts -->
      ${unack.length > 0 ? html`
        <ds-panel heading="Active Alerts · ${unack.length}">
          ${unack.map((ev) => html`
            <div class="ev">
              <span class="sev-${ev.severity}">●</span>
              <span style="flex:1;">${ev.message}</span>
              <span class="muted" style="font-size:var(--ds-text-xs);">${new Date(ev.timestamp).toLocaleTimeString()}</span>
              <ds-button size="sm" @click=${() => void this.ackEvent(ev.id)}>ack</ds-button>
            </div>
          `)}
        </ds-panel>
      ` : ""}

      <!-- Device Inventory -->
      <ds-panel heading="Device Inventory · ${filtered.length}">
        <div slot="actions" class="tabs">
          ${["all", "trusted", "unknown", "suspicious"].map((f) => html`
            <button class="tab ${this.filter === f ? "on" : ""}" @click=${() => (this.filter = f)}>${f}</button>
          `)}
        </div>
        <div class="dev-table">
          <div class="dev-row head"><span>Device</span><span>IP</span><span>MAC / Vendor</span><span>Last seen</span><span>Status</span><span></span></div>
          ${filtered.length ? filtered.map((d) => html`
            <div class="dev-row">
              <span style="display:flex;align-items:center;gap:var(--ds-space-2);">
                <span class="dot trust-${d.trust_status}"></span>
                ${d.hostname || "Unknown"}${d.is_gateway ? " · GW" : ""}
              </span>
              <span class="muted">${d.ip}</span>
              <span class="muted">${d.mac}${d.vendor ? ` · ${d.vendor}` : ""}</span>
              <span class="muted">${new Date(d.last_seen).toLocaleTimeString()}</span>
              <span class="badge badge-${d.trust_status}">${d.trust_status}</span>
              <span style="display:flex;gap:var(--ds-space-1);">
                ${d.trust_status !== "trusted" ? html`<ds-button size="sm" @click=${() => void this.act(d.mac, "trust")}>trust</ds-button>` : ""}
                ${d.trust_status !== "blocked" ? html`<ds-button size="sm" variant="danger" @click=${() => void this.act(d.mac, "block")}>block</ds-button>` : ""}
              </span>
            </div>
          `) : html`<div class="dev-row"><span class="muted">No devices match this filter.</span></div>`}
        </div>
      </ds-panel>

      <!-- Threats -->
      <ds-panel heading="Recent Threats · ${this.threats.length}">
        ${this.threats.length ? this.threats.map((t) => html`
          <div class="ev">
            <span class="sev-critical">●</span>
            <span style="flex:1;">${t.type}</span>
            <span class="muted">${t.confidence.toFixed(0)}% confidence</span>
            <span class="muted">${new Date(t.detected_at).toLocaleString()}</span>
          </div>
        `) : html`<span class="muted">No threats detected in the last 24 hours.</span>`}
      </ds-panel>

      <!-- Scanner -->
      <ds-panel heading="Port Scanner">
        <div class="scan-row">
          <input type="text" placeholder="192.168.1.1" .value=${this.scanIp} @input=${(e: InputEvent) => (this.scanIp = (e.target as HTMLInputElement).value)} @keydown=${(e: KeyboardEvent) => e.key === "Enter" && void this.doScan()} />
          <ds-button @click=${() => void this.doScan()} ?disabled=${this.scanLoading}>${this.scanLoading ? "scanning…" : "scan"}</ds-button>
        </div>
        ${this.scanResult ? html`
          <pre style="margin-top:var(--ds-space-3);padding:var(--ds-space-3);background:var(--ds-surface-2);border-radius:var(--ds-radius-sm);font-size:var(--ds-text-xs);overflow:auto;">${JSON.stringify(this.scanResult, null, 2)}</pre>
        ` : ""}
      </ds-panel>

      <!-- WiFi / Evil Twin -->
      <ds-panel heading="WiFi Spectrum · ${this.aps.length} APs">
        ${this.evilTwin ? html`<div class="evil-twin">⚠ Evil Twin / Rogue AP detected!</div>` : ""}
        ${this.aps.map((ap) => html`
          <div class="ap">
            <span>${ap.ssid || "Hidden"} <span class="muted">ch${ap.channel}</span></span>
            <span class="muted">${ap.bssid}</span>
            <span>${ap.signal} dBm</span>
            ${ap.rogue ? html`<span class="rogue">ROGUE</span>` : ""}
          </div>
        `)}
        ${!this.aps.length ? html`<span class="muted">No WiFi data available.</span>` : ""}
      </ds-panel>

      <!-- Proximity -->
      <ds-panel heading="Proximity & RF · live">
        ${proximityFeed.get().length ? html`<div style="display:grid;gap:3px;font-family:var(--ds-font-mono);font-size:var(--ds-text-xs);max-height:200px;overflow:auto;">
          ${proximityFeed.get().map((e) => html`<div style="display:flex;gap:var(--ds-space-2);color:var(--ds-text-soft);"><span style="color:var(--ds-text-faint);">${e.time}</span><span>${e.label}</span></div>`)}
        </div>` : html`<span class="muted">Listening for nearby access points & proximity changes…</span>`}
      </ds-panel>
    `;
  }
}
