// <intel-stats-view> — the operations-center statistics board.
//
// Reads /api/intel/stats and renders the global threat picture: how fast CISA
// is adding actively-exploited CVEs, the current botnet C2 population, and the
// health of every upstream source.
//
// A feed that is down renders as "unavailable", never as zero. On a security
// board those are opposite claims, and conflating them is how an outage gets
// read as an all-clear.
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";

interface KevStats {
  available: boolean;
  catalog_version?: string;
  total?: number;
  added_7d?: number;
  added_30d?: number;
  added_90d?: number;
  remediation_overdue?: number;
  remediation_due_14d?: number;
  ransomware_linked?: number;
  top_vendors?: { vendor: string; count: number }[];
  latest?: {
    cve: string; vendor: string; product: string; name: string;
    added: string; due: string; ransomware: boolean;
  }[];
}

interface BotnetStats {
  available: boolean;
  active_c2_servers?: number;
  families?: { family: string; count: number }[];
  top_countries?: { country_code: string; count: number }[];
}

interface SourceRow {
  id: string; name: string; category: string; auth: string;
  configured: boolean; env_var: string | null; docs_url: string;
}

interface Stats {
  generated_at: string;
  kev: KevStats;
  botnet: BotnetStats;
  anonymity: { available: boolean; tor_exit_nodes?: number };
  sources: {
    total: number; keyless: number; key_required: number;
    key_configured: number; available_now: number; sources: SourceRow[];
  };
  degraded: Record<string, string>;
}

const REFRESH_MS = 5 * 60 * 1000;

@customElement("intel-stats-view")
export class IntelStatsView extends LitElement {
  @state() private stats: Stats | null = null;
  @state() private error = "";
  @state() private loading = true;

  private timer = 0;

  static styles = css`
    :host { display: block; height: 100%; overflow-y: auto; padding: 4px 2px 20px; }

    h3 {
      margin: 22px 0 10px;
      font-size: 0.7rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.55;
      font-weight: 600;
    }
    h3:first-of-type { margin-top: 6px; }

    .tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }
    .tile {
      border: 1px solid rgba(120, 200, 230, 0.16);
      border-radius: 8px;
      background: rgba(120, 200, 230, 0.045);
      padding: 12px 14px;
    }
    .tile .value {
      font-size: 1.6rem;
      font-variant-numeric: tabular-nums;
      line-height: 1.1;
      font-family: var(--ds-font-mono, monospace);
    }
    .tile .label {
      margin-top: 5px;
      font-size: 0.68rem;
      opacity: 0.62;
      letter-spacing: 0.04em;
    }
    .tile.alert { border-color: rgba(255, 140, 140, 0.4); background: rgba(255, 120, 120, 0.07); }
    .tile.alert .value { color: rgba(255, 165, 165, 0.95); }
    .tile.warn { border-color: rgba(255, 210, 130, 0.35); }
    .tile.warn .value { color: rgba(255, 215, 150, 0.95); }
    .tile.muted .value { opacity: 0.35; font-size: 1rem; }

    table { width: 100%; border-collapse: collapse; font-size: 0.74rem; }
    th, td {
      text-align: left;
      padding: 5px 8px;
      border-bottom: 1px solid rgba(120, 200, 230, 0.09);
      vertical-align: top;
    }
    th { opacity: 0.5; font-weight: 500; text-transform: uppercase; font-size: 0.63rem; letter-spacing: 0.08em; }
    td.mono { font-family: var(--ds-font-mono, monospace); white-space: nowrap; }
    .scroll-x { overflow-x: auto; }

    .pill {
      display: inline-block;
      border-radius: 3px;
      padding: 1px 6px;
      font-size: 0.62rem;
      letter-spacing: 0.04em;
    }
    .pill.live { background: rgba(120, 240, 180, 0.16); color: rgba(160, 250, 200, 0.95); }
    .pill.gated { background: rgba(255, 210, 130, 0.14); color: rgba(255, 220, 160, 0.9); }
    .pill.ransom { background: rgba(255, 130, 130, 0.16); color: rgba(255, 170, 170, 0.95); }

    .note { font-size: 0.72rem; opacity: 0.55; margin: 8px 0 0; }
    .banner {
      border: 1px solid rgba(255, 180, 120, 0.35);
      background: rgba(255, 170, 110, 0.07);
      border-radius: 6px;
      padding: 9px 12px;
      font-size: 0.73rem;
      margin-bottom: 4px;
    }
    .banner ul { margin: 6px 0 0; padding-left: 18px; }
    .state { padding: 24px; opacity: 0.6; font-size: 0.8rem; }
    a { color: rgba(150, 210, 255, 0.85); }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
    this.timer = window.setInterval(() => void this.load(), REFRESH_MS);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.timer);
  }

  private async load(): Promise<void> {
    try {
      const r = await fetch("/api/intel/stats");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      this.stats = (await r.json()) as Stats;
      this.error = "";
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.loading = false;
    }
  }

  private tile(value: unknown, label: string, tone: "" | "alert" | "warn" = "") {
    const missing = value === undefined || value === null;
    return html`
      <div class="tile ${missing ? "muted" : tone}">
        <div class="value">${missing ? "unavailable" : value}</div>
        <div class="label">${label}</div>
      </div>
    `;
  }

  render() {
    if (this.loading) return html`<div class="state">Loading global intelligence…</div>`;
    if (!this.stats) return html`<div class="state">Could not reach the intel layer: ${this.error}</div>`;

    const { kev, botnet, anonymity, sources, degraded } = this.stats;
    const degradedKeys = Object.keys(degraded ?? {});

    return html`
      ${degradedKeys.length
        ? html`
            <div class="banner">
              <strong>${degradedKeys.length} source(s) degraded</strong> — figures below
              are computed only from feeds that answered.
              <ul>
                ${degradedKeys.map((k) => html`<li>${k}: ${degraded[k]}</li>`)}
              </ul>
            </div>
          `
        : nothing}

      <h3>Actively exploited (CISA KEV)</h3>
      <div class="tiles">
        ${this.tile(kev.total, "catalog entries")}
        ${this.tile(kev.added_7d, "added, last 7 days", (kev.added_7d ?? 0) > 5 ? "warn" : "")}
        ${this.tile(kev.added_30d, "added, last 30 days")}
        ${this.tile(kev.remediation_overdue, "remediation overdue", "alert")}
        ${this.tile(kev.remediation_due_14d, "due within 14 days", "warn")}
        ${this.tile(kev.ransomware_linked, "ransomware-linked", "alert")}
      </div>

      ${kev.available && kev.latest?.length
        ? html`
            <h3>Newest KEV entries</h3>
            <div class="scroll-x">
              <table>
                <thead>
                  <tr><th>CVE</th><th>Vendor</th><th>Product</th><th>Added</th><th>Remediate by</th><th></th></tr>
                </thead>
                <tbody>
                  ${kev.latest.slice(0, 12).map(
                    (v) => html`
                      <tr>
                        <td class="mono">${v.cve}</td>
                        <td>${v.vendor}</td>
                        <td>${v.product}</td>
                        <td class="mono">${v.added}</td>
                        <td class="mono">${v.due}</td>
                        <td>${v.ransomware ? html`<span class="pill ransom">ransomware</span>` : nothing}</td>
                      </tr>
                    `,
                  )}
                </tbody>
              </table>
            </div>
          `
        : nothing}

      <h3>Botnet infrastructure &amp; anonymity</h3>
      <div class="tiles">
        ${this.tile(botnet.active_c2_servers, "active C2 servers", "alert")}
        ${this.tile(anonymity.tor_exit_nodes, "Tor exit nodes")}
        ${this.tile(botnet.families?.[0]?.family, "top malware family")}
      </div>
      ${botnet.available && botnet.families?.length
        ? html`
            <p class="note">
              Families:
              ${botnet.families.slice(0, 6).map((f) => `${f.family} (${f.count})`).join(", ")}
            </p>
          `
        : nothing}

      <h3>Source health</h3>
      <div class="tiles">
        ${this.tile(`${sources.available_now}/${sources.total}`, "sources available")}
        ${this.tile(sources.keyless, "keyless (no signup)")}
        ${this.tile(`${sources.key_configured}/${sources.key_required}`, "keyed sources configured")}
      </div>
      <div class="scroll-x">
        <table>
          <thead><tr><th>Source</th><th>Category</th><th>Status</th><th>Docs</th></tr></thead>
          <tbody>
            ${sources.sources.map(
              (s) => html`
                <tr>
                  <td>${s.name}</td>
                  <td>${s.category}</td>
                  <td>
                    ${s.configured
                      ? html`<span class="pill live">live</span>`
                      : html`<span class="pill gated">set ${s.env_var}</span>`}
                  </td>
                  <td><a href=${s.docs_url} target="_blank" rel="noreferrer noopener">docs</a></td>
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>

      <p class="note">Generated ${new Date(this.stats.generated_at).toLocaleString()} · refreshes every 5 minutes.</p>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "intel-stats-view": IntelStatsView;
  }
}
