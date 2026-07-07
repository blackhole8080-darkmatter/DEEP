// <dashboard-view> — Command-center dashboard overview (new default home)
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface SystemVital {
  label: string;
  value: string;
  spark: number[];
  status: "good" | "warn" | "critical";
}

interface RecentEvent {
  time: string;
  type: "info" | "warn" | "alert" | "success";
  message: string;
}

@customElement("dashboard-view")
export class DashboardView extends LitElement {
  @state() private vitals: SystemVital[] = [
    { label: "CPU CORE 0", value: "12.4%", spark: Array.from({length: 40}, () => Math.random() * 30 + 10), status: "good" },
    { label: "SYS RAM", value: "32.1 GB", spark: Array.from({length: 40}, () => Math.random() * 10 + 40), status: "good" },
    { label: "NET I/O", value: "402 Mbps", spark: Array.from({length: 40}, () => Math.random() * 50 + 20), status: "good" },
    { label: "THREAT", value: "SECURE", spark: Array.from({length: 40}, () => Math.random() * 5), status: "good" },
  ];
  private _interval: any;

  connectedCallback() {
    super.connectedCallback();
    this._interval = setInterval(() => this._tick(), 1000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this._interval);
  }

  private _tick() {
    this.vitals = this.vitals.map(v => {
      const nextVal = v.spark[v.spark.length - 1] + (Math.random() - 0.5) * 15;
      const next = [...v.spark.slice(1), Math.max(0, Math.min(100, nextVal))];
      let val = v.value;
      if (v.label.includes("CPU")) val = next[next.length - 1].toFixed(1) + "%";
      else if (v.label.includes("RAM")) val = (next[next.length - 1] / 2).toFixed(1) + " GB";
      else if (v.label.includes("NET")) val = Math.abs(next[next.length - 1] * 10).toFixed(0) + " Mbps";
      return { ...v, spark: next, value: val };
    });
  }
  @state() private events: RecentEvent[] = [
    { time: "14:32", type: "success", message: "Network scan completed — 24 devices found" },
    { time: "14:28", type: "info", message: "Agent 'Alpha-7' started analysis task" },
    { time: "14:15", type: "warn", message: "Unrecognized device joined LAN: 192.168.1.44" },
    { time: "13:52", type: "info", message: "Knowledge graph synced — 520 entities" },
    { time: "13:30", type: "success", message: "Voice assistant model loaded" },
    { time: "12:45", type: "alert", message: "Critical update available: security patch" },
  ];

  static styles = css`
    :host {
      display: grid;
      gap: var(--ds-space-4);
      padding: var(--ds-space-5);
      overflow-y: auto;
      height: 100%;
    }

    /* ── Top HUD row ── */
    .hud {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--ds-space-3);
    }
    .hud-card {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      padding: var(--ds-space-4);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s var(--ds-ease-out), box-shadow 0.2s var(--ds-ease-out);
    }
    .hud-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--ds-elev-2), 0 0 20px rgba(var(--ds-periwinkle-rgb), 0.08);
    }
    .hud-card::after {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--ds-accent), transparent);
      opacity: 0.25;
    }
    .hud-label {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-faint);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
      margin-bottom: var(--ds-space-2);
    }
    .hud-value {
      font-size: var(--ds-text-2xl);
      font-weight: 700;
      color: var(--ds-text);
      font-family: var(--ds-font-mono);
      animation: text-glow 3s ease-in-out infinite;
    }
    .hud-value.warn { color: var(--ds-warning); }
    .hud-value.critical { color: var(--ds-danger); }

    /* Telemetry Graphs */
    .telemetry-svg {
      width: 100%; height: 50px;
      margin-top: var(--ds-space-2);
      overflow: visible;
    }
    .telemetry-line {
      fill: none;
      stroke-width: 1.5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .telemetry-area {
      opacity: 0.15;
    }
    .telemetry-grid {
      stroke: rgba(0, 229, 255, 0.15);
      stroke-width: 1;
    }

    /* ── Middle row ── */
    .mid {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: var(--ds-space-4);
    }
    @media (max-width: 900px) { .mid { grid-template-columns: 1fr; } }

    .panel {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      padding: var(--ds-space-4);
      position: relative;
    }
    .panel::after {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--ds-accent), transparent);
      opacity: 0.25;
    }
    .panel-title {
      font-size: var(--ds-text-sm);
      color: var(--ds-text-soft);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
      margin-bottom: var(--ds-space-3);
      display: flex; align-items: center; gap: var(--ds-space-2);
    }
    .panel-title .dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent);
      box-shadow: 0 0 6px var(--ds-accent);
    }

    /* ── Activity rings ── */
    .rings {
      display: flex; gap: var(--ds-space-4);
      justify-content: center;
      padding: var(--ds-space-3) 0;
    }
    .ring-wrap {
      display: flex; flex-direction: column; align-items: center; gap: var(--ds-space-2);
    }
    .ring-svg {
      width: 80px; height: 80px;
      transform: rotate(-90deg);
    }
    .ring-track { fill: none; stroke: var(--ds-surface-3); stroke-width: 6; }
    .ring-fill {
      fill: none; stroke: var(--ds-accent); stroke-width: 6;
      stroke-linecap: round;
      transition: stroke-dashoffset 1s var(--ds-ease-out);
      filter: drop-shadow(0 0 4px var(--ds-accent));
    }
    .ring-label {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
      text-align: center;
    }

    /* ── Event feed ── */
    .feed {
      display: flex; flex-direction: column; gap: var(--ds-space-2);
      max-height: 280px;
      overflow-y: auto;
    }
    .event {
      display: flex; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-3);
      border-radius: var(--ds-radius-sm);
      background: var(--ds-surface-1);
      border-left: 2px solid transparent;
      font-size: var(--ds-text-sm);
      animation: fade-up 0.3s var(--ds-ease-out) both;
    }
    .event.info  { border-left-color: var(--ds-info); }
    .event.warn  { border-left-color: var(--ds-warning); }
    .event.alert { border-left-color: var(--ds-danger); }
    .event.success { border-left-color: var(--ds-success); }
    .event-time {
      color: var(--ds-text-faint);
      font-family: var(--ds-font-mono);
      font-size: var(--ds-text-xs);
      white-space: nowrap;
    }
    .event-msg { color: var(--ds-text-soft); }

    /* ── Quick actions ── */
    .actions {
      display: flex; gap: var(--ds-space-3);
      flex-wrap: wrap;
    }
    .action-btn {
      display: inline-flex; align-items: center; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-4);
      border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border-accent);
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      color: var(--ds-accent);
      font-size: var(--ds-text-sm);
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s var(--ds-ease-out);
    }
    .action-btn:hover {
      background: rgba(var(--ds-periwinkle-rgb), 0.15);
      box-shadow: 0 0 16px rgba(var(--ds-periwinkle-rgb), 0.2);
      transform: translateY(-1px);
    }

    .greeting {
      font-size: var(--ds-text-2xl);
      font-weight: 600;
      color: var(--ds-text);
      margin-bottom: var(--ds-space-1);
      animation: text-glow 3s ease-in-out infinite;
    }
    .subgreeting {
      font-size: var(--ds-text-sm);
      color: var(--ds-text-muted);
      margin-bottom: var(--ds-space-4);
    }
  `;

  private _ringCircumference = 2 * Math.PI * 34;

  private _ringDash(percent: number) {
    const c = this._ringCircumference;
    return `${c * (1 - percent)} ${c}`;
  }

  private _getColor(status: string) {
    if (status === 'critical') return '#ef4444';
    if (status === 'warn') return '#eab308';
    return '#00e5ff';
  }

  private _renderGraph(spark: number[], color: string) {
    const min = Math.max(0, Math.min(...spark) - 5);
    const max = Math.max(...spark) + 5;
    const range = max - min || 1;
    const w = 200; const h = 50;
    const step = w / (spark.length - 1);
    
    const points = spark.map((val, i) => `${(i * step).toFixed(1)},${(h - ((val - min) / range) * h).toFixed(1)}`).join(" ");
    
    return html`
      <svg class="telemetry-svg" viewBox="0 -5 ${w} ${h + 10}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="grad-${color.replace('#','')}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <path class="telemetry-area" d="M 0,${h} L ${points.split(' ')[0]} L ${points} L ${w},${h} Z" fill="url(#grad-${color.replace('#','')})"></path>
        <polyline class="telemetry-line" points="${points}" style="stroke: ${color}; filter: drop-shadow(0 0 4px ${color})"></polyline>
        <line x1="0" y1="${h/2}" x2="${w}" y2="${h/2}" class="telemetry-grid" stroke-dasharray="2,4" />
        <line x1="0" y1="${h}" x2="${w}" y2="${h}" class="telemetry-grid" stroke-dasharray="2,4" />
      </svg>
    `;
  }

  render() {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning, Aryan" : hour < 18 ? "Good afternoon, Aryan" : "Good evening, Aryan";
    return html`
      <div class="greeting">${greeting}</div>
      <div class="subgreeting">DEEP is online and monitoring your systems.</div>

      <div class="hud">
        ${this.vitals.map((v, i) => html`
          <holo-panel title="${v.label}" accent="cyan" .pulseOnUpdate=${i}>
            <div class="hud-value ${v.status}">${v.value}</div>
            ${this._renderGraph(v.spark, this._getColor(v.status))}
          </holo-panel>
        `)}
      </div>

      <div class="mid">
        <holo-panel title="System Activity" accent="green">
          <div class="rings">
            ${[
              { label: "Agents", pct: Math.max(0.1, this.vitals[0].spark[39] / 100), color: "var(--ds-accent)" },
              { label: "Security", pct: Math.max(0.1, 1 - (this.vitals[3].spark[39] / 10)), color: "var(--ds-success)" },
              { label: "Queue", pct: Math.max(0.05, this.vitals[2].spark[39] / 100), color: "var(--ds-warning)" },
            ].map((r) => html`
              <div class="ring-wrap">
                <svg class="ring-svg" viewBox="0 0 80 80">
                  <circle class="ring-track" cx="40" cy="40" r="34" />
                  <circle class="ring-fill" cx="40" cy="40" r="34"
                    stroke-dasharray="${this._ringDash(r.pct)}"
                    style="stroke:${r.color}" />
                </svg>
                <div class="ring-label">${r.label}<br/><strong>${Math.round(r.pct * 100)}%</strong></div>
              </div>
            `)}
          </div>
          <div class="actions">
            <button class="action-btn" @click=${() => location.hash = "network"}>◉ Scan Network</button>
            <button class="action-btn" @click=${() => location.hash = "home"}>◆ Open Chat</button>
            <button class="action-btn" @click=${() => location.hash = "agents"}>✦ Launch Agent</button>
            <button class="action-btn" @click=${() => location.hash = "system"}>⚙ System Check</button>
          </div>
        </holo-panel>

        <holo-panel title="Live Events" accent="violet">
          <div class="feed">
            ${this.events.map((e, i) => html`
              <div class="event ${e.type}" style="animation-delay:${i * 0.05}s">
                <span class="event-time">${e.time}</span>
                <span class="event-msg">${e.message}</span>
              </div>
            `)}
          </div>
        </holo-panel>
      </div>
    `;
  }
}
