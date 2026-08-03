// <network-view> — DEEP Network Command Center
// Unified security dashboard: topology, devices, threats, scanner, WiFi.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
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
  @state() private activeTab: "devices" | "threats" | "scanner" | "wifi" = "devices";
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
    :host {
      display: flex; flex-direction: column;
      height: 100%; width: 100%;
      font-family: var(--ds-font-mono, monospace);
      background: #030508;
      color: rgba(220, 240, 255, 0.9);
      overflow: hidden;
    }

    /* ─── Hero: Full-bleed topology ─── */
    .hero {
      position: relative;
      flex: 1 1 55%;
      min-height: 340px;
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 0;
      border-bottom: 1px solid rgba(0, 229, 255, 0.1);
    }
    .topo-wrap {
      position: relative;
      overflow: hidden;
      background: #030508;
    }
    .topo-header {
      position: absolute; top: 0; left: 0; right: 0; z-index: 20;
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 24px;
      background: linear-gradient(to bottom, rgba(3,5,8,0.9) 0%, rgba(3,5,8,0) 100%);
      pointer-events: none;
    }
    .topo-title {
      font-size: 0.7rem; color: rgba(0,229,255,0.7);
      letter-spacing: 0.3em; text-transform: uppercase; font-weight: 600;
      text-shadow: 0 0 8px rgba(0,229,255,0.2);
    }
    .topo-stats {
      font-size: 0.6rem; color: rgba(0,229,255,0.5);
      letter-spacing: 0.15em; text-transform: uppercase;
    }
    .detail-sidebar {
      background: rgba(4, 8, 16, 0.7);
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border-left: 1px solid rgba(0, 229, 255, 0.1);
      overflow-y: auto;
    }

    /* ─── Score ribbon ─── */
    .score-ribbon {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 1px;
      background: rgba(0, 229, 255, 0.06);
      flex: 0 0 auto;
    }
    .score-cell {
      padding: 16px 20px;
      background: rgba(4, 8, 16, 0.85);
      display: flex; flex-direction: column; gap: 6px;
      position: relative; overflow: hidden;
      transition: background 0.3s;
    }
    .score-cell:hover {
      background: rgba(0, 229, 255, 0.04);
    }
    .score-cell::after {
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(0,229,255,0.15), transparent);
    }
    .score-val {
      font-size: 1.6rem; font-weight: 700; letter-spacing: -0.5px;
      text-shadow: 0 0 20px currentColor;
    }
    .score-val.ok { color: #00e5ff; }
    .score-val.warn { color: #f59e0b; }
    .score-val.danger { color: #ef4444; }
    .score-label {
      font-size: 0.6rem; color: rgba(255,255,255,0.4);
      text-transform: uppercase; letter-spacing: 0.2em;
    }

    /* ─── Lower panels ─── */
    .lower {
      flex: 1 1 45%;
      min-height: 0;
      display: flex; flex-direction: column;
      overflow: hidden;
    }

    /* ─── Tab bar ─── */
    .tab-bar {
      display: flex; gap: 0;
      background: rgba(4, 8, 16, 0.85);
      border-bottom: 1px solid rgba(0, 229, 255, 0.08);
      flex: 0 0 auto;
    }
    .tab-btn {
      padding: 10px 20px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.65rem; font-weight: 500;
      text-transform: uppercase; letter-spacing: 0.2em;
      color: rgba(0, 229, 255, 0.45);
      background: transparent;
      border: none; border-bottom: 2px solid transparent;
      cursor: pointer;
      transition: all 0.25s;
      position: relative;
    }
    .tab-btn:hover {
      color: rgba(0, 229, 255, 0.7);
      background: rgba(0, 229, 255, 0.03);
    }
    .tab-btn.active {
      color: #00e5ff;
      border-bottom-color: #00e5ff;
      text-shadow: 0 0 10px rgba(0,229,255,0.4);
    }
    .tab-btn .count {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 16px; height: 16px; padding: 0 4px;
      border-radius: 8px;
      background: rgba(0, 229, 255, 0.15);
      color: #00e5ff;
      font-size: 0.55rem; font-weight: 700;
      margin-left: 6px;
    }
    .tab-btn .count.danger {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    /* ─── Tab content ─── */
    .tab-content {
      flex: 1 1 auto;
      overflow-y: auto;
      padding: 16px 24px;
      background: rgba(3, 5, 8, 0.7);
    }

    /* ─── Device table ─── */
    .filter-row {
      display: flex; gap: 6px; margin-bottom: 12px;
    }
    .filter-btn {
      padding: 4px 12px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.12em;
      background: transparent;
      border: 1px solid rgba(0, 229, 255, 0.12);
      border-radius: 3px;
      color: rgba(0, 229, 255, 0.5);
      cursor: pointer;
      transition: all 0.2s;
    }
    .filter-btn:hover { border-color: rgba(0,229,255,0.3); color: rgba(0,229,255,0.8); }
    .filter-btn.on {
      color: #030508; background: #00e5ff; border-color: #00e5ff;
      font-weight: 700;
      box-shadow: 0 0 12px rgba(0,229,255,0.3);
    }

    .dev-grid { display: flex; flex-direction: column; gap: 2px; }
    .dev-header {
      display: grid;
      grid-template-columns: 1.5fr 1fr 1.5fr 0.8fr 0.7fr auto;
      gap: 12px; align-items: center;
      padding: 8px 14px;
      font-size: 0.6rem; color: rgba(0,229,255,0.6);
      text-transform: uppercase; letter-spacing: 0.2em;
      border-bottom: 1px solid rgba(0,229,255,0.12);
    }
    .dev-row {
      display: grid;
      grid-template-columns: 1.5fr 1fr 1.5fr 0.8fr 0.7fr auto;
      gap: 12px; align-items: center;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-left: 2px solid transparent;
      border-radius: 2px;
      font-size: 0.75rem;
      transition: all 0.2s;
    }
    .dev-row:hover {
      background: rgba(0, 229, 255, 0.04);
      border-left-color: #00e5ff;
    }
    .dev-name {
      display: flex; align-items: center; gap: 8px;
      font-weight: 600; color: rgba(255,255,255,0.85);
    }
    .status-dot {
      width: 6px; height: 6px; border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
      flex: none;
    }
    .status-dot.trusted { color: #00e5ff; background: #00e5ff; }
    .status-dot.unknown { color: #f59e0b; background: #f59e0b; }
    .status-dot.suspicious, .status-dot.blocked { color: #ef4444; background: #ef4444; }
    .dim { color: rgba(0, 229, 255, 0.4); font-size: 0.7rem; }

    .badge {
      padding: 3px 8px; border-radius: 2px;
      font-size: 0.55rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.12em;
      border: 1px solid currentColor; text-align: center;
    }
    .badge-trusted { color: #00e5ff; background: rgba(0,229,255,0.06); }
    .badge-unknown { color: #f59e0b; background: rgba(245,158,11,0.06); }
    .badge-suspicious { color: #ef4444; background: rgba(239,68,68,0.06); }
    .badge-blocked { color: #ef4444; background: rgba(239,68,68,0.1); box-shadow: 0 0 8px rgba(239,68,68,0.15); }

    .action-btn {
      padding: 3px 8px; font-size: 0.55rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.1em;
      font-family: var(--ds-font-mono, monospace);
      background: transparent; cursor: pointer;
      border: 1px solid; border-radius: 2px;
      transition: all 0.2s;
    }
    .action-btn.trust { color: #00e5ff; border-color: rgba(0,229,255,0.3); }
    .action-btn.trust:hover { background: rgba(0,229,255,0.1); border-color: #00e5ff; }
    .action-btn.block { color: #ef4444; border-color: rgba(239,68,68,0.3); }
    .action-btn.block:hover { background: rgba(239,68,68,0.1); border-color: #ef4444; }

    /* ─── Threat / event rows ─── */
    .threat-row {
      display: flex; align-items: center; gap: 14px;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-left: 2px solid rgba(239, 68, 68, 0.3);
      border-radius: 0 2px 2px 0;
      font-size: 0.75rem;
      margin-bottom: 2px;
      transition: all 0.2s;
    }
    .threat-row:hover {
      background: rgba(239, 68, 68, 0.04);
      border-left-color: #ef4444;
    }
    .threat-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #ef4444;
      box-shadow: 0 0 8px rgba(239,68,68,0.6);
      animation: threat-pulse 2s infinite;
      flex: none;
    }
    @keyframes threat-pulse {
      0%, 100% { box-shadow: 0 0 4px rgba(239,68,68,0.4); }
      50% { box-shadow: 0 0 12px rgba(239,68,68,0.8); }
    }

    .alert-banner {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 16px; margin-bottom: 12px;
      background: rgba(239, 68, 68, 0.06);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-left: 3px solid #ef4444;
      border-radius: 3px;
      color: #ef4444;
      font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.15em;
      animation: alert-glow 2s infinite;
    }
    @keyframes alert-glow {
      0%, 100% { box-shadow: inset 0 0 0 rgba(239,68,68,0); }
      50% { box-shadow: inset 0 0 20px rgba(239,68,68,0.08); }
    }

    /* ─── Scanner ─── */
    .scan-input-row { display: flex; gap: 10px; }
    .scan-input {
      flex: 1; padding: 10px 14px;
      background: rgba(0,0,0,0.5);
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 3px;
      color: #00e5ff;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.75rem;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .scan-input:focus {
      outline: none;
      border-color: rgba(0,229,255,0.5);
      box-shadow: 0 0 16px rgba(0,229,255,0.1);
    }
    .scan-btn {
      padding: 0 20px;
      background: #00e5ff; border: none; border-radius: 3px;
      color: #030508; font-weight: 700;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 0 12px rgba(0,229,255,0.2);
    }
    .scan-btn:hover { box-shadow: 0 0 24px rgba(0,229,255,0.4); }
    .scan-btn:disabled { opacity: 0.5; cursor: wait; }
    .scan-output {
      margin-top: 12px; padding: 14px;
      background: rgba(0,0,0,0.6);
      border: 1px solid rgba(0,229,255,0.12);
      border-left: 2px solid #00e5ff;
      border-radius: 3px;
      color: #00e5ff; font-size: 0.7rem;
      overflow: auto; max-height: 240px;
      white-space: pre-wrap;
      text-shadow: 0 0 4px rgba(0,229,255,0.15);
    }

    /* ─── WiFi / AP list ─── */
    .ap-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-radius: 2px;
      font-size: 0.75rem;
      margin-bottom: 2px;
      transition: background 0.2s;
    }
    .ap-row:hover { background: rgba(0,229,255,0.04); }
    .rogue-tag {
      color: #ef4444; font-weight: 700; font-size: 0.6rem;
      text-transform: uppercase; letter-spacing: 0.12em;
      text-shadow: 0 0 8px rgba(239,68,68,0.5);
      animation: threat-pulse 1s infinite;
    }

    .empty-state {
      padding: 24px; text-align: center;
      color: rgba(0,229,255,0.35);
      font-size: 0.7rem; letter-spacing: 0.15em;
      text-transform: uppercase;
    }

    .rescan-btn {
      pointer-events: auto;
      background: transparent;
      border: 1px solid rgba(0,229,255,0.25);
      color: rgba(0,229,255,0.6);
      padding: 4px 14px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.55rem; letter-spacing: 0.15em; text-transform: uppercase;
      cursor: pointer; border-radius: 3px;
      transition: all 0.2s;
    }
    .rescan-btn:hover {
      border-color: #00e5ff; color: #00e5ff;
      box-shadow: 0 0 12px rgba(0,229,255,0.15);
    }

    @media (max-width: 900px) {
      .hero { grid-template-columns: 1fr; }
      .detail-sidebar { display: none; }
      .score-ribbon { grid-template-columns: repeat(3, 1fr); }
    }
  `;

  render() {
    if (this.loading) return html`<div class="empty-state" style="padding:60px;">Initializing SYS.OP Trace...</div>`;
    const s = this.status;
    const filtered = this.filteredDevices();
    const unack = this.events.filter((e) => !e.acknowledged);

    return html`
      <!-- ═══ HERO: Full-bleed Topology ═══ -->
      <div class="hero">
        <div class="topo-wrap">
          <div class="topo-header">
            <span class="topo-title">// Global Topology Trace</span>
            <span style="display:flex;gap:16px;align-items:center;">
              <span class="topo-stats">${this.graphStats ? Object.entries(this.graphStats.nodes_by_layer).map(([l, c]) => `${l}:${c}`).join(" \u00b7 ") : ""}</span>
              <button class="rescan-btn" @click=${() => void this.load()}>Rescan</button>
            </span>
          </div>
          <topology-canvas
            .nodes=${this.graph.nodes}
            .edges=${this.graph.edges}
            @node-select=${(e: CustomEvent) => { this.selectedNode = this.graph.nodes.find((n) => n.id === e.detail) || null; }}
          ></topology-canvas>
        </div>
        <div class="detail-sidebar">
          <network-detail-panel .node=${this.selectedNode}></network-detail-panel>
        </div>
      </div>

      <!-- ═══ Score Ribbon ═══ -->
      <div class="score-ribbon">
        <div class="score-cell">
          <div class="score-val ${s ? (s.score >= 80 ? "ok" : s.score >= 50 ? "warn" : "danger") : ""}">${s?.score ?? "--"}</div>
          <div class="score-label">Trust Score</div>
        </div>
        <div class="score-cell">
          <div class="score-val ok">${s?.devices_trusted ?? 0}</div>
          <div class="score-label">Trusted</div>
        </div>
        <div class="score-cell">
          <div class="score-val warn">${s?.devices_unknown ?? 0}</div>
          <div class="score-label">Unknown</div>
        </div>
        <div class="score-cell">
          <div class="score-val danger">${s?.devices_suspicious ?? 0}</div>
          <div class="score-label">Suspicious</div>
        </div>
        <div class="score-cell">
          <div class="score-val ${(s?.threats_24h ?? 0) > 0 ? "danger" : "ok"}">${s?.threats_24h ?? 0}</div>
          <div class="score-label">Threats 24h</div>
        </div>
      </div>

      <!-- ═══ Lower: Tabbed Intelligence ═══ -->
      <div class="lower">
        <div class="tab-bar">
          <button class="tab-btn ${this.activeTab === "devices" ? "active" : ""}" @click=${() => this.activeTab = "devices"}>
            Devices <span class="count">${this.devices.length}</span>
          </button>
          <button class="tab-btn ${this.activeTab === "threats" ? "active" : ""}" @click=${() => this.activeTab = "threats"}>
            Threats ${this.threats.length > 0 ? html`<span class="count danger">${this.threats.length}</span>` : ""}
          </button>
          <button class="tab-btn ${this.activeTab === "scanner" ? "active" : ""}" @click=${() => this.activeTab = "scanner"}>
            Scanner
          </button>
          <button class="tab-btn ${this.activeTab === "wifi" ? "active" : ""}" @click=${() => this.activeTab = "wifi"}>
            RF Spectrum <span class="count">${this.aps.length}</span>
          </button>
        </div>

        <div class="tab-content">
          ${this.activeTab === "devices" ? this._renderDevices(filtered) : ""}
          ${this.activeTab === "threats" ? this._renderThreats(unack) : ""}
          ${this.activeTab === "scanner" ? this._renderScanner() : ""}
          ${this.activeTab === "wifi" ? this._renderWifi() : ""}
        </div>
      </div>
    `;
  }

  private _renderDevices(filtered: SecurityDevice[]) {
    return html`
      <div class="filter-row">
        ${["all", "trusted", "unknown", "suspicious"].map((f) => html`
          <button class="filter-btn ${this.filter === f ? "on" : ""}" @click=${() => (this.filter = f)}>${f}</button>
        `)}
      </div>
      <div class="dev-grid">
        <div class="dev-header">
          <span>Identity</span><span>IPv4</span><span>MAC / Vendor</span><span>Last Seen</span><span>Status</span><span>Actions</span>
        </div>
        ${filtered.length ? filtered.map((d) => html`
          <div class="dev-row">
            <div class="dev-name">
              <span class="status-dot ${d.trust_status}"></span>
              ${d.hostname || "Unknown_Client"}${d.is_gateway ? " [GW]" : ""}
            </div>
            <span class="dim">${d.ip}</span>
            <span class="dim">${d.mac}${d.vendor ? ` \u00b7 ${d.vendor}` : ""}</span>
            <span class="dim">${new Date(d.last_seen).toLocaleTimeString()}</span>
            <span class="badge badge-${d.trust_status}">${d.trust_status}</span>
            <span style="display:flex;gap:6px;">
              ${d.trust_status !== "trusted" ? html`<button class="action-btn trust" @click=${() => void this.act(d.mac, "trust")}>Trust</button>` : ""}
              ${d.trust_status !== "blocked" ? html`<button class="action-btn block" @click=${() => void this.act(d.mac, "block")}>Block</button>` : ""}
            </span>
          </div>
        `) : html`<div class="empty-state">No devices match current filter.</div>`}
      </div>
    `;
  }

  private _renderThreats(unack: SecurityEvent[]) {
    return html`
      ${unack.length > 0 ? html`
        <div class="alert-banner">\u26A0 ${unack.length} Unacknowledged Security Alert${unack.length > 1 ? "s" : ""}</div>
        ${unack.map((ev) => html`
          <div class="threat-row" style="border-left-color:#ef4444;">
            <span class="threat-dot"></span>
            <span style="flex:1;color:rgba(255,255,255,0.85);">${ev.message}</span>
            <span class="dim">${new Date(ev.timestamp).toLocaleTimeString()}</span>
            <button class="action-btn trust" @click=${() => void this.ackEvent(ev.id)}>ACK</button>
          </div>
        `)}
        <div style="height:16px;"></div>
      ` : ""}

      ${this.threats.length ? this.threats.map((t) => html`
        <div class="threat-row">
          <span class="threat-dot"></span>
          <span style="flex:1;color:#00e5ff;">${t.type}</span>
          <span class="dim">${t.confidence.toFixed(0)}% conf</span>
          <span class="dim">${new Date(t.detected_at).toLocaleTimeString()}</span>
        </div>
      `) : html`<div class="empty-state">No active threat vectors tracked. System secure.</div>`}
    `;
  }

  private _renderScanner() {
    return html`
      <div class="scan-input-row">
        <input class="scan-input" type="text" placeholder="Target IP or range..." .value=${this.scanIp}
          @input=${(e: InputEvent) => (this.scanIp = (e.target as HTMLInputElement).value)}
          @keydown=${(e: KeyboardEvent) => e.key === "Enter" && void this.doScan()} />
        <button class="scan-btn" @click=${() => void this.doScan()} ?disabled=${this.scanLoading}>
          ${this.scanLoading ? "Scanning..." : "Execute"}
        </button>
      </div>
      ${this.scanResult ? html`<div class="scan-output">${JSON.stringify(this.scanResult, null, 2)}</div>` : ""}
    `;
  }

  private _renderWifi() {
    return html`
      ${this.evilTwin ? html`<div class="alert-banner">CRITICAL: Evil Twin / Rogue AP Detected</div>` : ""}
      ${this.aps.length ? this.aps.map((ap) => html`
        <div class="ap-row">
          <span style="display:flex;gap:10px;align-items:center;">
            <span style="color:#00e5ff;font-weight:600;">${ap.ssid || "[HIDDEN_SSID]"}</span>
            <span class="dim">CH:${ap.channel}</span>
          </span>
          <span class="dim">${ap.bssid}</span>
          <span style="color:rgba(255,255,255,0.7);">${ap.signal} dBm</span>
          ${ap.rogue ? html`<span class="rogue-tag">Rogue</span>` : ""}
        </div>
      `) : html`<div class="empty-state">Awaiting RF telemetry...</div>`}
    `;
  }
}
