// <system-monitor> — the live machine telemetry surface. Streams vitals into
// time-series charts, shows per-core load, connected displays (to scale),
// battery, uptime, GPU and OS — the precise "what this machine is doing" view.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchVitals, fetchSystemInfo, type SystemInfo } from "../../core/api";
import "../primitives/ds-panel";
import "../viz/spark-line";

function fmtUptime(s: number): string {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h ${m}m` : h ? `${h}h ${m}m` : `${m}m`;
}

@customElement("system-monitor")
export class SystemMonitor extends LitElement {
  @state() private info: SystemInfo | null = null;
  @state() private cpuHist: number[] = [];
  @state() private ramHist: number[] = [];
  @state() private netHist: number[] = [];
  @state() private cur = { cpu: 0, ram: 0, disk: 0, net: 0, ramUsed: 0, ramTotal: 0 };
  private vt?: ReturnType<typeof setInterval>;
  private it?: ReturnType<typeof setInterval>;

  connectedCallback(): void {
    super.connectedCallback();
    void this.tickVitals();
    void this.tickInfo();
    this.vt = setInterval(() => void this.tickVitals(), 2000);
    this.it = setInterval(() => void this.tickInfo(), 5000);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this.vt); clearInterval(this.it); }

  private async tickVitals(): Promise<void> {
    try {
      const v = await fetchVitals();
      this.cur = { cpu: v.cpu, ram: v.ram, disk: v.disk, net: v.net_recv_mbs + v.net_sent_mbs, ramUsed: v.ram_used_gb, ramTotal: v.ram_total_gb };
      this.cpuHist = [...this.cpuHist, v.cpu].slice(-60);
      this.ramHist = [...this.ramHist, v.ram].slice(-60);
      this.netHist = [...this.netHist, v.net_recv_mbs + v.net_sent_mbs].slice(-60);
    } catch { /* transient */ }
  }
  private async tickInfo(): Promise<void> {
    try { this.info = await fetchSystemInfo(); } catch { /* transient */ }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1100px; margin: 0 auto; align-content: start; }
    .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--ds-space-3); }
    .chart { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .chart .top { display: flex; justify-content: space-between; align-items: baseline; }
    .chart .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .chart .v { font-size: var(--ds-text-xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .cores { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: var(--ds-space-2); }
    .core { text-align: center; }
    .core .bar { height: 46px; background: var(--ds-surface-3); border-radius: var(--ds-radius-xs); position: relative; overflow: hidden; display: flex; align-items: flex-end; }
    .core .bar > i { width: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); transition: height var(--ds-dur-base) var(--ds-ease-out); }
    .core .n { font-size: 0.6rem; color: var(--ds-text-faint); font-family: var(--ds-font-mono); }
    .displays { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; align-items: flex-end; }
    .screen { border: 2px solid var(--ds-border-accent); border-radius: var(--ds-radius-sm); background: linear-gradient(135deg, rgba(var(--ds-periwinkle-rgb),0.12), transparent); display: grid; place-items: center; color: var(--ds-text-soft); font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); position: relative; box-shadow: var(--ds-elev-2); }
    .screen.primary { border-color: var(--ds-accent); box-shadow: var(--ds-glow); }
    .screen .badge { position: absolute; top: 4px; left: 6px; font-size: 0.55rem; color: var(--ds-accent); }
    .rows { display: grid; gap: 0; }
    .row { display: flex; justify-content: space-between; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .batt { display: inline-flex; align-items: center; gap: 6px; }
    .batt .cell { width: 30px; height: 13px; border: 1px solid var(--ds-text-soft); border-radius: 3px; position: relative; padding: 1px; }
    .batt .cell > i { display: block; height: 100%; border-radius: 1px; background: var(--ds-success); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;

  private chart(label: string, val: string, hist: number[], max: number, color: string) {
    return html`<div class="chart">
      <div class="top"><span class="k">${label}</span><span class="v">${val}</span></div>
      <spark-line .data=${hist} .max=${max} color=${color} .height=${44}></spark-line>
    </div>`;
  }

  private displayLayout() {
    const ds = this.info?.displays ?? [];
    if (!ds.length) return html`<span class="muted">no displays detected</span>`;
    const scale = 0.05;
    return html`<div class="displays">
      ${ds.map((d) => html`
        <div class="screen ${d.primary ? "primary" : ""}"
          style="width:${Math.max(60, d.width * scale)}px;height:${Math.max(36, d.height * scale)}px">
          ${d.primary ? html`<span class="badge">primary</span>` : ""}
          ${d.width}×${d.height}
        </div>
      `)}
    </div>`;
  }

  render() {
    const i = this.info, c = this.cur;
    return html`
      <ds-panel heading="Live usage">
        <div class="charts">
          ${this.chart("CPU", `${c.cpu.toFixed(0)}%`, this.cpuHist, 100, "var(--ds-accent)")}
          ${this.chart("Memory", `${c.ram.toFixed(0)}%`, this.ramHist, 100, "var(--ds-success)")}
          ${this.chart("Network MB/s", c.net.toFixed(2), this.netHist, Math.max(2, ...this.netHist), "var(--ds-info)")}
          <div class="chart">
            <div class="top"><span class="k">Disk</span><span class="v">${c.disk.toFixed(0)}%</span></div>
            <div style="margin-top:8px"><span class="muted">${c.ramUsed} / ${c.ramTotal} GB RAM used</span></div>
          </div>
        </div>
      </ds-panel>

      <ds-panel heading="Per-core load · ${i?.cores_logical ?? "?"} threads">
        ${i?.per_core?.length ? html`<div class="cores">
          ${i.per_core.map((p, n) => html`
            <div class="core">
              <div class="bar"><i style="height:${Math.max(2, p)}%"></i></div>
              <div class="n">${n}</div>
            </div>
          `)}
        </div>` : html`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Connected displays · ${i?.displays?.length ?? 0}">
        ${this.displayLayout()}
      </ds-panel>

      <ds-panel heading="Machine">
        ${i ? html`<div class="rows">
          <div class="row"><span class="k">hostname</span><b>${i.hostname}</b></div>
          <div class="row"><span class="k">OS</span><b>${i.os} · ${i.arch}</b></div>
          <div class="row"><span class="k">CPU</span><b>${i.cores_physical}c / ${i.cores_logical}t${i.cpu_freq_mhz ? ` · ${(i.cpu_freq_mhz / 1000).toFixed(1)} GHz` : ""}</b></div>
          <div class="row"><span class="k">uptime</span><b>${fmtUptime(i.uptime_s)}</b></div>
          ${i.battery ? html`<div class="row"><span class="k">battery</span>
            <b class="batt"><span class="cell"><i style="width:${i.battery.percent}%;background:${i.battery.percent < 20 ? "var(--ds-danger)" : "var(--ds-success)"}"></i></span>
              ${i.battery.percent}% ${i.battery.plugged ? "⚡" : ""}</b></div>` : ""}
        </div>` : html`<span class="muted">loading…</span>`}
      </ds-panel>
    `;
  }
}
