// <security-timeline-view> — merged live feed for GET /api/security/timeline
// (core/security/security_timeline.py): raw device-level events + MITRE
// ATT&CK/CVE-enriched anomaly/threat correlations, one severity-scored list.
// Severity reads as form, not just a word — a left stripe + a chip — per
// the "encode state in form as well as number" rule for dashboards.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import "../primitives/ds-panel";

type Severity = "critical" | "high" | "medium" | "low" | "info";

interface Technique { id: string; name: string; tactics: string[]; detection: string; mitigation: string; }
interface RelatedCve { cve_id: string; severity: string | null; cvss_score: number | null; is_kev: boolean; description: string; }
interface TimelineItem {
  id: string; source: string; kind: string; severity: Severity; timestamp: string;
  summary: string; techniques: Technique[]; related_cves: RelatedCve[];
  device_mac: string | null; device_ip: string | null;
}
interface TimelineStats { total: number; by_severity: Record<string, number>; by_kind: Record<string, number>; }

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Info",
};

@customElement("security-timeline-view")
export class SecurityTimelineView extends LitElement {
  @state() private items: TimelineItem[] = [];
  @state() private stats: TimelineStats | null = null;
  @state() private minSeverity: Severity | "" = "";
  @state() private _expanded = new Set<string>();
  private timer?: ReturnType<typeof setInterval>;
  private _seen = new Set<string>();

  connectedCallback(): void {
    super.connectedCallback();
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), 6000);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this.timer); }

  // Guards against a real race: the poll interval can have an older
  // (e.g. unfiltered) request still in flight when a filter click fires a
  // newer one — if the older response resolves second, it would silently
  // overwrite the newer, correctly-filtered result. Only the response
  // matching the current generation is allowed to update `items`.
  private _reqGen = 0;

  private async refresh(): Promise<void> {
    const gen = ++this._reqGen;
    const q = this.minSeverity ? `?min_severity=${this.minSeverity}&limit=60` : "?limit=60";
    void fetch(`/api/security/timeline${q}`).then((r) => r.json())
      .then((d) => { if (gen === this._reqGen) this.items = d.timeline ?? []; }).catch(() => {});
    void fetch("/api/security/timeline/stats").then((r) => r.json())
      .then((d) => { this.stats = d; }).catch(() => {});
  }

  private toggle(id: string): void {
    const next = new Set(this._expanded);
    next.has(id) ? next.delete(id) : next.add(id);
    this._expanded = next;
  }

  private isNew(id: string): boolean {
    const fresh = !this._seen.has(id);
    this._seen.add(id);
    return fresh;
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }

    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .stat .v { font-size: var(--ds-text-xl); font-weight: 700; font-family: var(--ds-font-mono); font-variant-numeric: tabular-nums; }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .stat.critical .v, .stat.high .v { color: var(--ds-danger); }
    .stat.medium .v { color: var(--ds-warning); }
    .stat.low .v, .stat.info .v { color: var(--ds-info); }
    .stat.total .v { color: var(--ds-accent); }

    .filters { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    .filter-btn {
      padding: 3px 10px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs);
      font-family: var(--ds-font-mono); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); color: var(--ds-text-soft);
      cursor: pointer; transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .filter-btn:hover { border-color: var(--ds-border-strong); color: var(--ds-text); }
    .filter-btn.on { background: var(--ds-surface-3); border-color: var(--ds-border-accent); color: var(--ds-text); box-shadow: var(--ds-glow); }

    .list { display: grid; gap: 6px; }
    .row {
      display: grid; grid-template-columns: 4px 1fr auto; gap: var(--ds-space-3);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      overflow: hidden;
    }
    /* Only genuinely new rows animate in — the list re-renders every poll
       (6s), so animating every row unconditionally would flicker instead of
       reading as "alive". isNew() tracks what's already been seen. */
    .row.is-new { animation: fade-up var(--ds-dur-slow) var(--ds-ease-out); }
    @media (prefers-reduced-motion: reduce) { .row.is-new { animation: none; } }
    .row .stripe { background: var(--sev-color, var(--ds-text-faint)); }
    .row .main { padding: var(--ds-space-3) var(--ds-space-2); min-width: 0; cursor: pointer; }
    .row .head { display: flex; align-items: baseline; gap: var(--ds-space-2); flex-wrap: wrap; }
    .row .kind { font-weight: 600; font-size: var(--ds-text-sm); }
    .row .source { font-size: var(--ds-text-xs); color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .row .time { font-size: var(--ds-text-xs); color: var(--ds-text-faint); font-family: var(--ds-font-mono); margin-left: auto; }
    .row .summary { margin-top: 2px; font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .chip {
      padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: 0.66rem;
      font-family: var(--ds-font-mono); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      color: var(--sev-color, var(--ds-text-soft)); border: 1px solid var(--sev-color, var(--ds-border));
      background: color-mix(in srgb, var(--sev-color, transparent) 12%, transparent);
      align-self: center; margin-right: var(--ds-space-3);
    }
    .detail { grid-column: 1 / -1; padding: 0 var(--ds-space-3) var(--ds-space-3); display: grid; gap: var(--ds-space-2); }
    .tag-group { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag {
      padding: 1px 8px; border-radius: var(--ds-radius-sm); font-size: 0.68rem; font-family: var(--ds-font-mono);
      border: 1px solid var(--ds-border); color: var(--ds-text-soft);
    }
    .tag.technique { border-color: var(--ds-accent); color: var(--ds-accent); }
    .tag.cve { border-color: var(--ds-danger); color: var(--ds-danger); }
    .tag.kev { background: color-mix(in srgb, var(--ds-danger) 18%, transparent); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    .empty { padding: var(--ds-space-5); text-align: center; color: var(--ds-text-muted); }
  `;

  render() {
    const s = this.stats;
    return html`
      ${s ? html`
        <ds-panel heading="Live security timeline">
          <div class="stats">
            <div class="stat total"><div class="k">total</div><div class="v">${s.total}</div></div>
            ${SEVERITY_ORDER.filter((sev) => s.by_severity[sev]).map((sev) => html`
              <div class="stat ${sev}"><div class="k">${SEVERITY_LABEL[sev]}</div><div class="v">${s.by_severity[sev]}</div></div>
            `)}
          </div>
        </ds-panel>
      ` : html`<span class="muted">loading timeline…</span>`}

      <div class="filters">
        <button class="filter-btn ${this.minSeverity === "" ? "on" : ""}" @click=${() => { this.minSeverity = ""; void this.refresh(); }}>All</button>
        ${SEVERITY_ORDER.map((sev) => html`
          <button class="filter-btn ${this.minSeverity === sev ? "on" : ""}"
                  @click=${() => { this.minSeverity = sev; void this.refresh(); }}>${SEVERITY_LABEL[sev]}+</button>
        `)}
      </div>

      <div class="list">
        ${this.items.length === 0 ? html`<div class="empty">No security events yet — this feed lights up as anomaly/threat detection and network monitoring produce live signal.</div>` : null}
        ${this.items.map((item) => {
          const open = this._expanded.has(item.id);
          const hasDetail = item.techniques.length > 0 || item.related_cves.length > 0 || item.device_mac;
          const fresh = this.isNew(item.id);
          return html`
            <div class="row ${fresh ? "is-new" : ""}" style="--sev-color: var(--ds-${item.severity === "critical" || item.severity === "high" ? "danger" : item.severity === "medium" ? "warning" : "info"})">
              <div class="stripe"></div>
              <div class="main" @click=${() => hasDetail && this.toggle(item.id)}>
                <div class="head">
                  <span class="kind">${item.kind}</span>
                  <span class="source">${item.source}</span>
                  <span class="time">${this._fmtTime(item.timestamp)}</span>
                </div>
                <div class="summary">${item.summary}</div>
              </div>
              <span class="chip">${SEVERITY_LABEL[item.severity]}</span>
              ${open ? html`
                <div class="detail">
                  ${item.techniques.length ? html`
                    <div class="tag-group">
                      ${item.techniques.map((t) => html`<span class="tag technique" title=${t.detection}>${t.id} · ${t.name}</span>`)}
                    </div>
                  ` : null}
                  ${item.related_cves.length ? html`
                    <div class="tag-group">
                      ${item.related_cves.map((c) => html`<span class="tag cve ${c.is_kev ? "kev" : ""}">${c.cve_id}${c.is_kev ? " · KEV" : ""}</span>`)}
                    </div>
                  ` : null}
                  ${item.device_mac ? html`<div class="muted">Device: ${item.device_mac} ${item.device_ip ? `(${item.device_ip})` : ""}</div>` : null}
                </div>
              ` : null}
            </div>
          `;
        })}
      </div>
    `;
  }

  private _fmtTime(ts: string): string {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts.slice(11, 19) || ts;
      return d.toLocaleTimeString([], { hour12: false });
    } catch { return ts; }
  }
}

declare global {
  interface HTMLElementTagNameMap { "security-timeline-view": SecurityTimelineView; }
}
