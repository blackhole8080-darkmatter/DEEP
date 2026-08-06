// <etis-hud> — ETIS Expert Technical Intelligence System HUD
// Terminal-aesthetic domain control panel: cyber, RF, physics, robotics, sandbox
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import "../primitives/ds-panel";
import "../primitives/ds-button";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DomainStatus {
  available: boolean;
  capabilities?: string[];
  error?: string;
  docker?: boolean;
  languages?: string[];
}

interface IntelItem {
  source: string;
  id: string;
  title: string;
  summary: string;
  published: string;
  severity: string;
  url: string;
  tags: string[];
  is_kev: boolean;
  cvss_score?: number;
}

interface CVERecord {
  cve_id: string;
  description: string;
  severity: string;
  cvss_score?: number;
  published: string;
  cwes: string[];
  affected_products: string[];
  references: string[];
  is_kev: boolean;
}

interface SandboxResult {
  exit_code: number;
  stdout: string;
  stderr: string;
  execution_time_ms: number;
  timed_out: boolean;
  runtime: string;
}

type ActivePanel = "overview" | "cyber" | "rf" | "physics" | "robotics" | "sandbox" | "intel";

// ── Component ─────────────────────────────────────────────────────────────────

@customElement("etis-hud")
export class ETISHud extends LitElement {
  // Panel state
  @state() private activePanel: ActivePanel = "overview";
  @state() private domains: Record<string, DomainStatus> = {};
  @state() private loading = false;
  @state() private error = "";

  // Intel feed
  @state() private intelItems: IntelItem[] = [];
  @state() private intelLoading = false;

  // CVE
  @state() private cveId = "";
  @state() private cveResult: CVERecord | null = null;
  @state() private cveSearchKeyword = "";
  @state() private cveSearchResults: CVERecord[] = [];

  // RF
  @state() private rfFreq = "2437000000";
  @state() private rfBw = "20000000";
  @state() private rfResult: any = null;
  @state() private wifiNetworks: any[] = [];
  @state() private bleDevices: any[] = [];

  // Physics
  @state() private physExpr = "";
  @state() private physVars = "";
  @state() private physResult: any = null;
  @state() private physSim = "pendulum";
  @state() private physSimResult: any = null;

  // Robotics
  @state() private robotModel = "ur5";
  @state() private robotAngles = "0,0,0,0,0,0";
  @state() private robotFkResult: any = null;
  @state() private robotTarget = "0.3,0.2,0.5";
  @state() private robotIkResult: any = null;

  // Sandbox
  @state() private sandboxCode = 'import sys, platform\nprint(f"Python {sys.version}")\nprint(f"Platform: {platform.system()}")\nprint("ETIS sandbox operational.")\nprint(2**64)';
  @state() private sandboxLang = "python";
  @state() private sandboxResult: SandboxResult | null = null;
  @state() private sandboxRunning = false;
  @state() private sandboxStatus: any = null;

  // Proto RE
  @state() private hexSamples = "";
  @state() private protoResult: any = null;

  connectedCallback() {
    super.connectedCallback();
    void this.loadStatus();
  }

  private async loadStatus() {
    this.loading = true;
    try {
      const res = await fetch("/api/etis/status");
      const data = await res.json();
      if (data.ok) this.domains = data.data.domains;
    } catch { this.error = "ETIS status unreachable"; }
    this.loading = false;
  }

  private async api(path: string, opts?: RequestInit): Promise<any> {
    const res = await fetch(`/api/etis${path}`, opts);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "API error");
    return data.data;
  }

  private async apiPost(path: string, body: any): Promise<any> {
    return this.api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  // ── Actions ──────────────────────────────────────────────────────────────────

  private async loadIntel() {
    this.intelLoading = true;
    try {
      const d = await this.api("/intel/feed?days_back=14");
      this.intelItems = d.items;
    } catch (e: any) { this.error = e.message; }
    this.intelLoading = false;
  }

  private async lookupCve() {
    if (!this.cveId.trim()) return;
    try {
      this.cveResult = await this.api(`/cve/${this.cveId.trim().toUpperCase()}`);
    } catch (e: any) { this.error = e.message; }
  }

  private async searchCve() {
    if (!this.cveSearchKeyword.trim()) return;
    try {
      const d = await this.apiPost("/cve/search", { keyword: this.cveSearchKeyword, min_cvss: 7.0, days_back: 30 });
      this.cveSearchResults = d.results;
    } catch (e: any) { this.error = e.message; }
  }

  private async identifyRfProtocol() {
    try {
      const d = await this.api(`/rf/protocol?center_freq=${this.rfFreq}&bandwidth=${this.rfBw}`);
      this.rfResult = d;
    } catch (e: any) { this.error = e.message; }
  }

  private async wifiScan() {
    try {
      const d = await this.apiPost("/rf/wifi/scan", {});
      this.wifiNetworks = d.networks;
    } catch (e: any) { this.error = e.message; }
  }

  private async bleScan() {
    try {
      const d = await this.apiPost("/rf/ble/scan", { duration: 8 });
      this.bleDevices = d.devices;
    } catch (e: any) { this.error = e.message; }
  }

  private async computePhysics() {
    if (!this.physExpr.trim()) return;
    let vars: Record<string, number> = {};
    try {
      if (this.physVars.trim()) {
        this.physVars.split(",").forEach((pair) => {
          const [k, v] = pair.trim().split("=");
          if (k && v) vars[k.trim()] = parseFloat(v.trim());
        });
      }
      this.physResult = await this.apiPost("/physics/compute", { expression: this.physExpr, variables: vars });
    } catch (e: any) { this.error = e.message; }
  }

  private async simulatePhysics() {
    try {
      this.physSimResult = await this.apiPost("/physics/simulate", { system: this.physSim, t_span: [0, 15] });
    } catch (e: any) { this.error = e.message; }
  }

  private async computeFk() {
    try {
      const angles = this.robotAngles.split(",").map(Number);
      this.robotFkResult = await this.apiPost("/robotics/fk", { joint_angles: angles, model: this.robotModel });
    } catch (e: any) { this.error = e.message; }
  }

  private async computeIk() {
    try {
      const pos = this.robotTarget.split(",").map(Number);
      this.robotIkResult = await this.apiPost("/robotics/ik", { target_pos: pos, model: this.robotModel });
    } catch (e: any) { this.error = e.message; }
  }

  private async runSandbox() {
    this.sandboxRunning = true;
    this.sandboxResult = null;
    try {
      this.sandboxResult = await this.apiPost("/sandbox/execute", {
        code: this.sandboxCode, language: this.sandboxLang, timeout: 30,
      });
    } catch (e: any) { this.error = e.message; }
    this.sandboxRunning = false;
  }

  private async checkSandboxStatus() {
    try { this.sandboxStatus = await this.api("/sandbox/status"); }
    catch (e: any) { this.error = e.message; }
  }

  private async analyzeProto() {
    const lines = this.hexSamples.trim().split("\n").map(s => s.trim()).filter(Boolean);
    if (!lines.length) return;
    try {
      this.protoResult = await this.apiPost("/protocols/binary-re", { hex_samples: lines });
    } catch (e: any) { this.error = e.message; }
  }

  // ── Styles ────────────────────────────────────────────────────────────────────

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
      font-family: var(--ds-font-mono, 'JetBrains Mono', 'Fira Code', monospace);
      background: var(--ds-bg, var(--ds-bg));
      color: var(--ds-text, var(--ds-text));
    }

    /* ── Top bar ── */
    .etis-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 20px;
      border-bottom: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-success) calc(0.03 * 100%), transparent);
      flex-shrink: 0;
    }
    .etis-logo {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 4px;
      color: var(--ds-success);
      text-shadow: 0 0 12px color-mix(in srgb, var(--ds-success) calc(0.6 * 100%), transparent);
    }
    .etis-subtitle {
      font-size: 10px;
      color: var(--ds-text-muted);
      letter-spacing: 1px;
    }
    .etis-status {
      margin-left: auto;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .domain-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--ds-text-muted);
      transition: all 0.3s;
    }
    .domain-dot.ok { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .domain-dot.err { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }

    /* ── Nav tabs ── */
    .etis-nav {
      display: flex;
      gap: 2px;
      padding: 8px 20px 0;
      border-bottom: 1px solid color-mix(in srgb, var(--ds-success) calc(0.1 * 100%), transparent);
      flex-shrink: 0;
      overflow-x: auto;
    }
    .tab {
      padding: 6px 14px;
      font-size: 10px;
      font-family: inherit;
      letter-spacing: 1.5px;
      cursor: pointer;
      border: none;
      background: transparent;
      color: var(--ds-text-soft);
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .tab:hover { color: var(--ds-info); }
    .tab.active {
      color: var(--ds-success);
      border-bottom-color: var(--ds-success);
      text-shadow: 0 0 8px color-mix(in srgb, var(--ds-success) calc(0.5 * 100%), transparent);
    }
    .tab .tab-icon { margin-right: 5px; }

    /* ── Content area ── */
    .etis-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    /* ── Error banner ── */
    .err-banner {
      background: color-mix(in srgb, var(--ds-danger) calc(0.1 * 100%), transparent);
      border: 1px solid color-mix(in srgb, var(--ds-danger) calc(0.4 * 100%), transparent);
      border-radius: 4px;
      padding: 8px 12px;
      font-size: 11px;
      color: var(--ds-danger);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .err-banner button {
      background: none; border: none; cursor: pointer; color: var(--ds-danger); font-size: 14px;
    }

    /* ── Cards / panels ── */
    .card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
      border-radius: 6px;
      padding: 14px 16px;
      transition: border-color 0.2s;
    }
    .card:hover { border-color: color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent); }
    .card-header {
      font-size: 10px;
      color: var(--ds-success);
      letter-spacing: 2px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .card-header::after {
      content: '';
      flex: 1;
      height: 1px;
      background: color-mix(in srgb, var(--ds-success) calc(0.1 * 100%), transparent);
    }

    /* ── Domain grid ── */
    .domain-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 10px;
    }
    .domain-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .domain-card:hover {
      border-color: color-mix(in srgb, var(--ds-info) calc(0.4 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-info) calc(0.04 * 100%), transparent);
    }
    .domain-card.active-domain {
      border-color: color-mix(in srgb, var(--ds-success) calc(0.5 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-success) calc(0.05 * 100%), transparent);
    }
    .domain-card.unavail {
      opacity: 0.45;
    }
    .dc-name {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: var(--ds-info);
      margin-bottom: 6px;
    }
    .dc-name .dc-icon { margin-right: 6px; }
    .dc-status {
      font-size: 10px;
      color: var(--ds-success);
    }
    .dc-status.err { color: var(--ds-danger); }
    .dc-caps {
      margin-top: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .dc-cap {
      font-size: 9px;
      padding: 1px 6px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 3px;
      color: var(--ds-text-soft);
      letter-spacing: 0.5px;
    }

    /* ── Terminal output ── */
    .term {
      background: var(--ds-surface-1);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 11px;
      line-height: 1.7;
      max-height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .term .ok { color: var(--ds-success); }
    .term .err { color: var(--ds-danger); }
    .term .warn { color: var(--ds-warning); }
    .term .dim { color: var(--ds-text-muted); }
    .term .hi { color: var(--ds-info); }
    .term .kev { color: var(--ds-danger); font-weight: 700; background: color-mix(in srgb, var(--ds-danger) calc(0.1 * 100%), transparent); padding: 1px 4px; border-radius: 2px; }

    /* ── Form inputs ── */
    .field-row {
      display: flex;
      gap: 8px;
      align-items: flex-end;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      min-width: 140px;
    }
    label {
      font-size: 9px;
      letter-spacing: 1.5px;
      color: var(--ds-text-soft);
    }
    input, select, textarea {
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      border-radius: 4px;
      color: var(--ds-text);
      font-family: inherit;
      font-size: 11px;
      padding: 6px 10px;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus {
      border-color: color-mix(in srgb, var(--ds-success) calc(0.45 * 100%), transparent);
      box-shadow: 0 0 0 2px color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
    }
    textarea {
      resize: vertical;
      min-height: 120px;
      line-height: 1.6;
    }
    select option { background: var(--ds-bg); }

    /* ── ETIS action buttons ── */
    .etis-btn {
      background: color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.3 * 100%), transparent);
      border-radius: 4px;
      color: var(--ds-success);
      font-family: inherit;
      font-size: 10px;
      letter-spacing: 1.5px;
      padding: 7px 16px;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .etis-btn:hover {
      background: color-mix(in srgb, var(--ds-success) calc(0.18 * 100%), transparent);
      box-shadow: 0 0 12px color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent);
    }
    .etis-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .etis-btn.danger {
      background: color-mix(in srgb, var(--ds-danger) calc(0.08 * 100%), transparent);
      border-color: color-mix(in srgb, var(--ds-danger) calc(0.3 * 100%), transparent);
      color: var(--ds-danger);
    }
    .etis-btn.blue {
      background: color-mix(in srgb, var(--ds-info) calc(0.08 * 100%), transparent);
      border-color: color-mix(in srgb, var(--ds-info) calc(0.3 * 100%), transparent);
      color: var(--ds-info);
    }

    /* ── Severity badges ── */
    .sev {
      display: inline-block;
      padding: 1px 7px;
      border-radius: 3px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1px;
    }
    .sev-CRITICAL { background: rgba(255,0,80,0.2); color: #ff0050; border: 1px solid rgba(255,0,80,0.4); }
    .sev-HIGH     { background: rgba(255,80,0,0.2); color: #ff5000; border: 1px solid rgba(255,80,0,0.4); }
    .sev-MEDIUM   { background: rgba(255,180,0,0.15); color: #ffb400; border: 1px solid rgba(255,180,0,0.3); }
    .sev-LOW      { background: rgba(0,200,80,0.1); color: #00c850; border: 1px solid rgba(0,200,80,0.2); }
    .sev-INFO     { background: rgba(0,180,255,0.1); color: #00b4ff; border: 1px solid rgba(0,180,255,0.2); }

    /* ── Intel feed ── */
    .intel-item {
      padding: 10px 12px;
      border: 1px solid rgba(255,255,255,0.05);
      border-left: 3px solid color-mix(in srgb, var(--ds-info) calc(0.4 * 100%), transparent);
      border-radius: 4px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .intel-item:hover { background: rgba(255,255,255,0.03); }
    .intel-item.kev { border-left-color: var(--ds-danger); background: color-mix(in srgb, var(--ds-danger) calc(0.04 * 100%), transparent); }
    .intel-item.critical { border-left-color: #ff0050; }
    .intel-item.high { border-left-color: #ff5000; }
    .intel-item-title { font-size: 11px; color: var(--ds-text); margin-bottom: 4px; line-height: 1.4; }
    .intel-item-meta { font-size: 9px; color: var(--ds-text-soft); display: flex; gap: 10px; flex-wrap: wrap; }
    .intel-item-meta .source { color: var(--ds-info); }

    /* ── Metric row ── */
    .metric-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 5px 0;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      font-size: 11px;
    }
    .metric-row:last-child { border-bottom: none; }
    .metric-label { color: var(--ds-text-soft); }
    .metric-value { color: var(--ds-text); font-family: inherit; }
    .metric-value.green { color: var(--ds-success); }
    .metric-value.red { color: var(--ds-danger); }
    .metric-value.blue { color: var(--ds-info); }
    .metric-value.amber { color: var(--ds-warning); }

    /* ── Tags ── */
    .tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
    .tag {
      font-size: 9px;
      padding: 1px 7px;
      border: 1px solid color-mix(in srgb, var(--ds-info) calc(0.2 * 100%), transparent);
      border-radius: 3px;
      color: var(--ds-info);
      letter-spacing: 0.5px;
    }

    /* ── 2-col layout ── */
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    @media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

    /* ── Spinner ── */
    .spin {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 1.5px solid color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent);
      border-top-color: var(--ds-success);
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      vertical-align: middle;
      margin-right: 6px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent); border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: color-mix(in srgb, var(--ds-success) calc(0.4 * 100%), transparent); }
  `;

  // ── Render helpers ────────────────────────────────────────────────────────────

  private _sev(s: string) {
    return html`<span class="sev sev-${s.toUpperCase()}">${s}</span>`;
  }

  private _cvss(score?: number) {
    if (!score) return nothing;
    const cls = score >= 9 ? "red" : score >= 7 ? "amber" : score >= 4 ? "blue" : "green";
    return html`<span class="metric-value ${cls}">CVSS ${score.toFixed(1)}</span>`;
  }

  private _termJson(obj: any) {
    if (!obj) return nothing;
    return html`<div class="term"><span class="hi">${JSON.stringify(obj, null, 2)}</span></div>`;
  }

  // ── Panel renderers ───────────────────────────────────────────────────────────

  private _renderOverview() {
    const domainMeta: Record<string, { icon: string; label: string; panel: ActivePanel }> = {
      cybersec: { icon: "🛡", label: "CYBERSEC", panel: "cyber" },
      rf: { icon: "📡", label: "RF / WIRELESS", panel: "rf" },
      protocols: { icon: "⚙", label: "PROTOCOLS", panel: "rf" },
      hardware: { icon: "🔬", label: "HARDWARE", panel: "rf" },
      physics: { icon: "⚛", label: "PHYSICS", panel: "physics" },
      robotics: { icon: "🤖", label: "ROBOTICS", panel: "robotics" },
      sandbox: { icon: "📦", label: "SANDBOX", panel: "sandbox" },
    };

    return html`
      <div class="card">
        <div class="card-header">ETIS OVERVIEW</div>
        <div class="domain-grid">
          ${Object.entries(domainMeta).map(([key, meta]) => {
            const d = this.domains[key];
            return html`
              <div class="domain-card ${d?.available ? "" : "unavail"}"
                   @click=${() => { if (d?.available) this.activePanel = meta.panel; }}>
                <div class="dc-name">
                  <span class="dc-icon">${meta.icon}</span>${meta.label}
                </div>
                <div class="dc-status ${d?.available ? "" : "err"}">
                  ${this.loading
                    ? html`<span class="spin"></span>loading`
                    : d?.available ? "● OPERATIONAL" : "○ UNAVAILABLE"
                  }
                </div>
                ${d?.capabilities ? html`
                  <div class="dc-caps">
                    ${d.capabilities.map(c => html`<span class="dc-cap">${c}</span>`)}
                  </div>
                ` : nothing}
              </div>
            `;
          })}
        </div>
      </div>

      <!-- Quick intel summary -->
      <div class="card">
        <div class="card-header">LIVE THREAT INTEL</div>
        ${this.intelItems.length
          ? html`
            <div style="font-size:11px; color:var(--ds-text-soft); margin-bottom:8px;">
              ${this.intelItems.filter(i => i.is_kev).length} KEV &nbsp;·&nbsp;
              ${this.intelItems.filter(i => i.severity === "CRITICAL").length} CRITICAL &nbsp;·&nbsp;
              ${this.intelItems.length} total items
            </div>
            ${this.intelItems.slice(0, 4).map(item => html`
              <div class="intel-item ${item.is_kev ? "kev" : item.severity?.toLowerCase()}">
                <div class="intel-item-title">${item.title}</div>
                <div class="intel-item-meta">
                  <span class="source">[${item.source}]</span>
                  <span>${item.published}</span>
                  ${this._sev(item.severity)}
                  ${item.is_kev ? html`<span class="kev">🔴 KEV</span>` : nothing}
                </div>
              </div>
            `)}
          `
          : html`
            <button class="etis-btn" @click=${() => { void this.loadIntel(); this.activePanel = "intel"; }}>
              LOAD INTEL FEED
            </button>
          `}
      </div>
    `;
  }

  private _renderCyber() {
    return html`
      <!-- CVE Lookup -->
      <div class="card">
        <div class="card-header">🛡 CVE LOOKUP</div>
        <div class="field-row">
          <div class="field">
            <label>CVE ID</label>
            <input .value=${this.cveId}
                   @input=${(e: any) => this.cveId = e.target.value}
                   placeholder="CVE-2024-3400"
                   @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") void this.lookupCve(); }}
            />
          </div>
          <button class="etis-btn" @click=${() => void this.lookupCve()}>LOOKUP</button>
        </div>
        ${this.cveResult ? html`
          <div class="term">
<span class="hi">[CVE] ${this.cveResult.cve_id}</span>
<span class="dim">Severity: </span><span class="${this.cveResult.severity?.toLowerCase() === "critical" ? "err" : "warn"}">${this.cveResult.severity}</span>  ${this._cvss(this.cveResult.cvss_score)}
<span class="dim">Published:</span> ${this.cveResult.published}
<span class="dim">KEV:      </span> ${this.cveResult.is_kev ? html`<span class="kev">YES — actively exploited in the wild!</span>` : html`<span class="ok">No</span>`}
<span class="dim">CWEs:     </span> ${(this.cveResult.cwes || []).join(", ") || "None"}
<span class="dim">Affected: </span> ${(this.cveResult.affected_products || []).slice(0, 4).join(", ")}
<span class="dim">Desc:     </span> ${this.cveResult.description}
          </div>
        ` : nothing}
      </div>

      <!-- CVE Search -->
      <div class="card">
        <div class="card-header">🔍 CVE SEARCH</div>
        <div class="field-row">
          <div class="field">
            <label>KEYWORD</label>
            <input .value=${this.cveSearchKeyword}
                   @input=${(e: any) => this.cveSearchKeyword = e.target.value}
                   placeholder="palo alto, cisco, apache..."
                   @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") void this.searchCve(); }}
            />
          </div>
          <button class="etis-btn" @click=${() => void this.searchCve()}>SEARCH NVD</button>
        </div>
        ${this.cveSearchResults.length ? html`
          <div class="term">
            ${this.cveSearchResults.map(r => html`
<span class="hi">${r.cve_id}</span>  ${this._cvss(r.cvss_score)}  ${r.is_kev ? html`<span class="kev">KEV</span>` : nothing}
<span class="dim">${r.description?.slice(0, 120)}…</span>

            `)}
          </div>
        ` : nothing}
      </div>

      <!-- OSINT Recon -->
      <div class="card">
        <div class="card-header">🕵 OSINT PASSIVE RECON</div>
        <div class="field-row">
          <div class="field">
            <label>TARGET (domain or IP)</label>
            <input id="osint-target" placeholder="example.com  or  1.2.3.4" />
          </div>
          <button class="etis-btn" @click=${async () => {
            const inp = this.shadowRoot!.querySelector("#osint-target") as HTMLInputElement;
            const target = inp.value.trim();
            if (!target) return;
            try {
              const d = await this.apiPost("/osint/recon", { target });
              const out = this.shadowRoot!.querySelector("#osint-out") as HTMLElement;
              if (out) out.textContent = JSON.stringify(d, null, 2);
            } catch (e: any) { this.error = e.message; }
          }}>RECON</button>
        </div>
        <div id="osint-out" class="term" style="display:block;"></div>
      </div>

      <!-- Exploit lookup -->
      <div class="card">
        <div class="card-header">💥 EXPLOIT SEARCH</div>
        <div class="field-row">
          <div class="field">
            <label>CVE ID</label>
            <input id="exploit-cve" placeholder="CVE-2024-3400" />
          </div>
          <button class="etis-btn danger" @click=${async () => {
            const inp = this.shadowRoot!.querySelector("#exploit-cve") as HTMLInputElement;
            const cve = inp.value.trim().toUpperCase();
            if (!cve) return;
            try {
              const d = await this.apiPost("/exploit/search", { cve_id: cve });
              const out = this.shadowRoot!.querySelector("#exploit-out") as HTMLElement;
              if (out) out.textContent = JSON.stringify(d.exploits, null, 2);
            } catch (e: any) { this.error = e.message; }
          }}>SEARCH EXPLOITS</button>
        </div>
        <div id="exploit-out" class="term" style="display:block;"></div>
      </div>
    `;
  }

  private _renderRF() {
    return html`
      <!-- Protocol ID -->
      <div class="card">
        <div class="card-header">📡 RF PROTOCOL IDENTIFIER</div>
        <div class="field-row">
          <div class="field">
            <label>CENTER FREQ (Hz)</label>
            <input .value=${this.rfFreq}
                   @input=${(e: any) => this.rfFreq = e.target.value}
                   placeholder="2437000000" />
          </div>
          <div class="field">
            <label>BANDWIDTH (Hz)</label>
            <input .value=${this.rfBw}
                   @input=${(e: any) => this.rfBw = e.target.value}
                   placeholder="20000000" />
          </div>
          <button class="etis-btn" @click=${() => void this.identifyRfProtocol()}>IDENTIFY</button>
        </div>
        ${this.rfResult ? html`
          <div class="term">
            ${this.rfResult.matches?.map((m: any, i: number) => html`
<span class="${i === 0 ? "ok" : "dim"}">[${Math.round(m.confidence * 100)}%] ${m.protocol}</span>
<span class="dim">    Modulation: ${m.modulation}  |  BW: ${(m.bandwidth_khz || 0).toFixed(0)} kHz</span>
<span class="dim">    Use: ${m.typical_use}</span>
${m.security_notes ? html`<span class="warn">    ⚠ ${m.security_notes}</span>` : nothing}

            `)}
          </div>
        ` : nothing}
      </div>

      <!-- WiFi scan -->
      <div class="card">
        <div class="card-header">📶 WIFI DEEP SCAN</div>
        <div class="field-row">
          <button class="etis-btn blue" @click=${() => void this.wifiScan()}>SCAN NEARBY NETWORKS</button>
        </div>
        ${this.wifiNetworks.length ? html`
          <div class="term">
            ${this.wifiNetworks.map(n => html`
<span class="hi">${n.ssid || "(hidden)"}</span>  <span class="dim">${n.bssid}</span>  ch<span class="ok">${n.channel}</span>  <span class="${n.signal_strength > -60 ? "ok" : "warn"}">${n.signal_strength} dBm</span>  <span class="dim">${n.security}</span>
            `)}
          </div>
        ` : nothing}
      </div>

      <!-- BLE scan -->
      <div class="card">
        <div class="card-header">🔵 BLUETOOTH / BLE ENUMERATION</div>
        <div class="field-row">
          <button class="etis-btn blue" @click=${() => void this.bleScan()}>SCAN BLE DEVICES (8s)</button>
        </div>
        ${this.bleDevices.length ? html`
          <div class="term">
            ${this.bleDevices.map(d => html`
<span class="hi">${d.address}</span>  <span class="dim">${d.name || "(no name)"}</span>  ${d.rssi} dBm  ~${(d.distance_m || 0).toFixed(1)}m${d.is_airtag ? html`  <span class="warn">🍎 AirTag</span>` : nothing}
            `)}
          </div>
        ` : nothing}
      </div>

      <!-- Binary Protocol RE -->
      <div class="card">
        <div class="card-header">🔬 BINARY PROTOCOL REVERSE ENGINEERING</div>
        <div class="field-row">
          <div class="field" style="flex:1">
            <label>HEX SAMPLES (one per line)</label>
            <textarea .value=${this.hexSamples}
                      @input=${(e: any) => this.hexSamples = e.target.value}
                      placeholder="AABB0001000B48656C6C6F0000CDEF&#10;AABB0002000648692100FFEE"></textarea>
          </div>
        </div>
        <div class="field-row">
          <button class="etis-btn" @click=${() => void this.analyzeProto()}>ANALYZE PROTOCOL</button>
        </div>
        ${this.protoResult ? html`
          <div class="term">
<span class="hi">Protocol: ${this.protoResult.description}</span>
Entropy: ${(this.protoResult.entropy || 0).toFixed(2)} bits/byte  |  Confidence: ${Math.round((this.protoResult.confidence || 0) * 100)}%
Encrypted: ${this.protoResult.is_encrypted}  |  Magic: ${this.protoResult.has_magic}  |  Checksum: ${this.protoResult.has_checksum}
Header: ${this.protoResult.header_size}B

Fields:
${(this.protoResult.fields || []).map((f: any) => `  @${f.offset}+${f.size}B [${f.type}]: ${f.description}`).join("\n")}

${(this.protoResult.security_issues || []).length ? html`<span class="err">Security Issues:\n${(this.protoResult.security_issues || []).map((i: string) => `  ⚠ ${i}`).join("\n")}</span>` : nothing}
          </div>
        ` : nothing}
      </div>
    `;
  }

  private _renderPhysics() {
    return html`
      <!-- Symbolic / numeric compute -->
      <div class="card">
        <div class="card-header">⚛ PHYSICS COMPUTATION</div>
        <div class="field-row">
          <div class="field" style="flex:2">
            <label>EXPRESSION</label>
            <input .value=${this.physExpr}
                   @input=${(e: any) => this.physExpr = e.target.value}
                   placeholder="plasma_frequency, lorentz_force, E = m*c**2, ..."
                   @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") void this.computePhysics(); }}
            />
          </div>
          <div class="field">
            <label>VARIABLES (k=v, ...)</label>
            <input .value=${this.physVars}
                   @input=${(e: any) => this.physVars = e.target.value}
                   placeholder="n=1e18, B=0.5" />
          </div>
          <button class="etis-btn" @click=${() => void this.computePhysics()}>COMPUTE</button>
        </div>
        ${this.physResult ? this._termJson(this.physResult) : nothing}
      </div>

      <!-- ODE Simulation -->
      <div class="card">
        <div class="card-header">🌀 SYSTEM SIMULATION</div>
        <div class="field-row">
          <div class="field">
            <label>SYSTEM</label>
            <select .value=${this.physSim} @change=${(e: any) => this.physSim = e.target.value}>
              <option value="pendulum">Pendulum</option>
              <option value="lorenz">Lorenz Attractor</option>
              <option value="harmonic_oscillator">Harmonic Oscillator</option>
              <option value="plasma_wave">Plasma Wave</option>
            </select>
          </div>
          <button class="etis-btn" @click=${() => void this.simulatePhysics()}>SIMULATE [0, 15s]</button>
        </div>
        ${this.physSimResult ? html`
          <div class="term">
<span class="hi">[SIM] ${this.physSim}</span>
Time steps: ${(this.physSimResult.t || []).length}
Final state: ${JSON.stringify((this.physSimResult.y || []).map((c: number[]) => c[c.length - 1]?.toFixed(4)))}
${this.physSimResult.plot_url ? html`<span class="ok">Plot: <a href="${this.physSimResult.plot_url}" target="_blank">${this.physSimResult.plot_url}</a></span>` : nothing}
          </div>
        ` : nothing}
      </div>

      <!-- Constants lookup -->
      <div class="card">
        <div class="card-header">🔭 PHYSICAL CONSTANTS</div>
        <div class="field-row">
          <div class="field">
            <label>CONSTANT NAME</label>
            <input id="const-name" placeholder="speed_of_light, planck_constant, ..."
                   @keydown=${async (e: KeyboardEvent) => {
                     if (e.key !== "Enter") return;
                     const inp = e.target as HTMLInputElement;
                     try {
                       const d = await this.api(`/physics/constant/${inp.value.trim()}`);
                       const out = this.shadowRoot!.querySelector("#const-out") as HTMLElement;
                       if (out) out.textContent = `${d.name}: ${d.value} ${d.unit}\n${d.description || ""}`;
                     } catch (ex: any) { this.error = ex.message; }
                   }}
            />
          </div>
          <button class="etis-btn" @click=${async () => {
            const inp = this.shadowRoot!.querySelector("#const-name") as HTMLInputElement;
            const name = inp.value.trim();
            if (!name) return;
            try {
              const d = await this.api(`/physics/constant/${name}`);
              const out = this.shadowRoot!.querySelector("#const-out") as HTMLElement;
              if (out) out.textContent = `${d.name}: ${d.value} ${d.unit}\n${d.description || ""}`;
            } catch (ex: any) { this.error = ex.message; }
          }}>LOOKUP</button>
        </div>
        <div id="const-out" class="term" style="display:block;min-height:0;"></div>
      </div>
    `;
  }

  private _renderRobotics() {
    return html`
      <div class="two-col">
        <!-- FK -->
        <div class="card">
          <div class="card-header">🤖 FORWARD KINEMATICS</div>
          <div class="field-row">
            <div class="field">
              <label>MODEL</label>
              <select .value=${this.robotModel} @change=${(e: any) => this.robotModel = e.target.value}>
                <option value="ur5">UR5 (6-DOF)</option>
                <option value="puma560">PUMA 560</option>
              </select>
            </div>
          </div>
          <div class="field-row">
            <div class="field">
              <label>JOINT ANGLES (rad, comma sep)</label>
              <input .value=${this.robotAngles}
                     @input=${(e: any) => this.robotAngles = e.target.value}
                     placeholder="0,0,0,0,0,0" />
            </div>
            <button class="etis-btn" @click=${() => void this.computeFk()}>COMPUTE FK</button>
          </div>
          ${this.robotFkResult ? html`
            <div class="term">
<span class="hi">[FK] ${this.robotModel.toUpperCase()}</span>
Position:
  x = <span class="ok">${this.robotFkResult.position?.x?.toFixed(4)}m</span>
  y = <span class="ok">${this.robotFkResult.position?.y?.toFixed(4)}m</span>
  z = <span class="ok">${this.robotFkResult.position?.z?.toFixed(4)}m</span>
Manipulability: ${this.robotFkResult.manipulability?.toFixed(4)}
Singularity: ${this.robotFkResult.singularity ? html`<span class="err">⚠ YES</span>` : html`<span class="ok">No</span>`}
            </div>
          ` : nothing}
        </div>

        <!-- IK -->
        <div class="card">
          <div class="card-header">🎯 INVERSE KINEMATICS</div>
          <div class="field-row">
            <div class="field">
              <label>TARGET POSITION (x,y,z in m)</label>
              <input .value=${this.robotTarget}
                     @input=${(e: any) => this.robotTarget = e.target.value}
                     placeholder="0.3,0.2,0.5" />
            </div>
            <button class="etis-btn" @click=${() => void this.computeIk()}>COMPUTE IK</button>
          </div>
          ${this.robotIkResult ? html`
            <div class="term">
<span class="hi">[IK] ${this.robotModel.toUpperCase()}</span>
Target:   (${this.robotIkResult.target?.x?.toFixed(3)}, ${this.robotIkResult.target?.y?.toFixed(3)}, ${this.robotIkResult.target?.z?.toFixed(3)})m
Achieved: (${this.robotIkResult.achieved?.x?.toFixed(4)}, ${this.robotIkResult.achieved?.y?.toFixed(4)}, ${this.robotIkResult.achieved?.z?.toFixed(4)})m
Error:    <span class="${this.robotIkResult.error_mm < 1 ? "ok" : "warn"}">${this.robotIkResult.error_mm?.toFixed(3)} mm</span>

Joint angles (deg):
${(this.robotIkResult.joint_angles_deg || []).map((a: number, i: number) => `  J${i + 1}: ${a.toFixed(2)}°`).join("\n")}
            </div>
          ` : nothing}
        </div>
      </div>

      <!-- Trajectory -->
      <div class="card">
        <div class="card-header">📈 CUBIC TRAJECTORY PLANNER</div>
        <div class="field-row">
          <div class="field">
            <label>START ANGLES (rad)</label>
            <input id="traj-start" placeholder="0,0,0,0,0,0" />
          </div>
          <div class="field">
            <label>END ANGLES (rad)</label>
            <input id="traj-end" placeholder="1.57,0.5,-1.0,0,0,0" />
          </div>
          <div class="field" style="max-width:100px">
            <label>DURATION (s)</label>
            <input id="traj-dur" placeholder="3.0" />
          </div>
          <button class="etis-btn" @click=${async () => {
            const s = (this.shadowRoot!.querySelector("#traj-start") as HTMLInputElement).value.split(",").map(Number);
            const e2 = (this.shadowRoot!.querySelector("#traj-end") as HTMLInputElement).value.split(",").map(Number);
            const dur = parseFloat((this.shadowRoot!.querySelector("#traj-dur") as HTMLInputElement).value || "3");
            try {
              const d = await this.apiPost("/robotics/trajectory", { q_start: s, q_end: e2, duration: dur });
              const out = this.shadowRoot!.querySelector("#traj-out") as HTMLElement;
              if (out) out.textContent = `Duration: ${d.duration_s}s  |  ${d.n_points} waypoints\nMax vel (rad/s): ${(d.max_velocities || []).map((v: number) => v.toFixed(3)).join(", ")}`;
            } catch (ex: any) { this.error = ex.message; }
          }}>GENERATE</button>
        </div>
        <div id="traj-out" class="term" style="display:block;min-height:0;"></div>
      </div>
    `;
  }

  private _renderSandbox() {
    return html`
      <div class="card">
        <div class="card-header">📦 ISOLATED CODE SANDBOX</div>

        ${this.sandboxStatus ? html`
          <div class="metric-row">
            <span class="metric-label">ISOLATION</span>
            <span class="metric-value ${this.sandboxStatus.docker_available ? "green" : "amber"}">
              ${this.sandboxStatus.isolation?.toUpperCase()}
            </span>
          </div>
          <div class="metric-row">
            <span class="metric-label">SECURITY</span>
            <span class="metric-value blue" style="font-size:10px">${this.sandboxStatus.security}</span>
          </div>
          <div class="metric-row" style="margin-bottom:12px">
            <span class="metric-label">LANGUAGES</span>
            <span class="metric-value">${(this.sandboxStatus.languages || []).join(" · ")}</span>
          </div>
        ` : html`
          <div style="margin-bottom:12px">
            <button class="etis-btn blue" @click=${() => void this.checkSandboxStatus()}>CHECK STATUS</button>
          </div>
        `}

        <div class="field-row">
          <div class="field">
            <label>LANGUAGE</label>
            <select .value=${this.sandboxLang} @change=${(e: any) => this.sandboxLang = e.target.value}>
              <option value="python">Python 3</option>
              <option value="bash">Bash</option>
              <option value="node">Node.js</option>
            </select>
          </div>
        </div>

        <div style="margin-bottom:10px">
          <label>CODE</label>
          <textarea .value=${this.sandboxCode}
                    @input=${(e: any) => this.sandboxCode = e.target.value}
                    style="width:100%;min-height:160px;margin-top:4px;box-sizing:border-box;"></textarea>
        </div>

        <div class="field-row">
          <button class="etis-btn"
                  ?disabled=${this.sandboxRunning}
                  @click=${() => void this.runSandbox()}>
            ${this.sandboxRunning ? html`<span class="spin"></span>EXECUTING...` : "▶ EXECUTE"}
          </button>
          <button class="etis-btn" style="margin-left:auto"
                  @click=${() => this.sandboxCode = ""}>CLEAR</button>
        </div>

        ${this.sandboxResult ? html`
          <div class="term">
<span class="dim">[SANDBOX] exit=${this.sandboxResult.exit_code}  time=${this.sandboxResult.execution_time_ms.toFixed(0)}ms  runtime=${this.sandboxResult.runtime}</span>
<span class="dim">─────────── stdout ───────────</span>
<span class="${this.sandboxResult.exit_code === 0 ? "ok" : "err"}">${this.sandboxResult.stdout || "(no output)"}</span>
${this.sandboxResult.stderr ? html`<span class="dim">─────────── stderr ───────────</span>
<span class="err">${this.sandboxResult.stderr}</span>` : nothing}
${this.sandboxResult.timed_out ? html`<span class="err">⚠ TIMED OUT</span>` : nothing}
          </div>
        ` : nothing}
      </div>
    `;
  }

  private _renderIntel() {
    return html`
      <div class="card">
        <div class="card-header">📰 LIVE THREAT INTELLIGENCE FEED</div>
        <div class="field-row">
          <button class="etis-btn" ?disabled=${this.intelLoading} @click=${() => void this.loadIntel()}>
            ${this.intelLoading ? html`<span class="spin"></span>FETCHING...` : "REFRESH FEED"}
          </button>
          <span style="font-size:10px;color:var(--ds-text-soft);margin-left:auto">${this.intelItems.length} items loaded</span>
        </div>
        ${this.intelItems.map(item => html`
          <div class="intel-item ${item.is_kev ? "kev" : item.severity?.toLowerCase()}"
               @click=${() => window.open(item.url, "_blank")}>
            <div class="intel-item-title">${item.title}</div>
            <div class="intel-item-meta">
              <span class="source">[${item.source}]</span>
              <span>${item.published}</span>
              ${this._sev(item.severity)}
              ${item.cvss_score ? html`<span>CVSS ${item.cvss_score.toFixed(1)}</span>` : nothing}
              ${item.is_kev ? html`<span class="kev">🔴 KEV</span>` : nothing}
            </div>
            ${item.summary ? html`<div style="font-size:10px;color:var(--ds-text-soft);margin-top:5px">${item.summary.slice(0, 150)}…</div>` : nothing}
            ${(item.tags || []).length ? html`
              <div class="tag-row">${item.tags.slice(0, 6).map(t => html`<span class="tag">${t}</span>`)}</div>
            ` : nothing}
          </div>
        `)}
        ${!this.intelItems.length && !this.intelLoading ? html`
          <div class="term"><span class="dim">No intel loaded — click REFRESH FEED.</span></div>
        ` : nothing}
      </div>
    `;
  }

  // ── Main render ───────────────────────────────────────────────────────────────

  render() {
    const tabs: { id: ActivePanel; label: string; icon: string }[] = [
      { id: "overview", label: "OVERVIEW", icon: "◉" },
      { id: "cyber",    label: "CYBER",    icon: "🛡" },
      { id: "rf",       label: "RF / PROTO", icon: "📡" },
      { id: "physics",  label: "PHYSICS",  icon: "⚛" },
      { id: "robotics", label: "ROBOTICS", icon: "🤖" },
      { id: "sandbox",  label: "SANDBOX",  icon: "📦" },
      { id: "intel",    label: "INTEL",    icon: "📰" },
    ];

    return html`
      <!-- Header -->
      <div class="etis-header">
        <div class="etis-logo">ETIS</div>
        <div class="etis-subtitle">EXPERT TECHNICAL INTELLIGENCE SYSTEM</div>
        <div class="etis-status">
          ${Object.entries(this.domains).map(([, d]) => html`
            <div class="domain-dot ${d.available ? "ok" : "err"}"
                 title="${d.available ? "operational" : d.error || "unavailable"}"></div>
          `)}
          <button class="etis-btn" style="padding:3px 10px;font-size:9px"
                  @click=${() => void this.loadStatus()}>↻</button>
        </div>
      </div>

      <!-- Tab bar -->
      <div class="etis-nav">
        ${tabs.map(t => html`
          <button class="tab ${this.activePanel === t.id ? "active" : ""}"
                  @click=${() => this.activePanel = t.id}>
            <span class="tab-icon">${t.icon}</span>${t.label}
          </button>
        `)}
      </div>

      <!-- Error banner -->
      ${this.error ? html`
        <div class="err-banner" style="margin:8px 20px 0">
          ⚠ ${this.error}
          <button @click=${() => this.error = ""}>✕</button>
        </div>
      ` : nothing}

      <!-- Panel body -->
      <div class="etis-body">
        ${this.activePanel === "overview" ? this._renderOverview() : nothing}
        ${this.activePanel === "cyber"    ? this._renderCyber()    : nothing}
        ${this.activePanel === "rf"       ? this._renderRF()       : nothing}
        ${this.activePanel === "physics"  ? this._renderPhysics()  : nothing}
        ${this.activePanel === "robotics" ? this._renderRobotics() : nothing}
        ${this.activePanel === "sandbox"  ? this._renderSandbox()  : nothing}
        ${this.activePanel === "intel"    ? this._renderIntel()    : nothing}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "etis-hud": ETISHud; }
}
