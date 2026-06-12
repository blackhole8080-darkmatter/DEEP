// <research-view> — DEEP's live information intake: the daily news briefing,
// research-finding stream, and the indexed research-paper corpus by domain.
// This is the "carrying information from news + research papers, up to date" hub.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

interface Briefing { greeting: string; date: string; time: string; briefing: string; }
interface ResearchStats { topics: number; total_findings: number; unread_findings: number; last_24h: number; }
interface PaperStatus { total_papers: number; papers_by_domain: Record<string, number>; db_size_mb: number; last_updated: string; }

@customElement("research-view")
export class ResearchView extends LitElement {
  @state() private briefing: Briefing | null = null;
  @state() private stats: ResearchStats | null = null;
  @state() private papers: PaperStatus | null = null;
  @state() private speaking = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }
  private async load(): Promise<void> {
    void fetch("/api/briefing").then((r) => r.json()).then((d) => (this.briefing = d)).catch(() => {});
    void fetch("/api/research/stats").then((r) => r.json()).then((d) => (this.stats = d)).catch(() => {});
    void fetch("/knowledge/status").then((r) => r.json()).then((d) => (this.papers = d)).catch(() => {});
  }
  private async speak(): Promise<void> {
    this.speaking = true;
    try { await fetch("/api/briefing/speak", { method: "POST" }); toast("Speaking briefing…", "info"); }
    catch { toast("TTS unavailable", "danger"); }
    setTimeout(() => (this.speaking = false), 1500);
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .briefing { font-size: var(--ds-text-lg); line-height: 1.6; color: var(--ds-text); }
    .when { color: var(--ds-text-muted); font-size: var(--ds-text-sm); font-family: var(--ds-font-mono); margin-bottom: var(--ds-space-2); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); text-align: center; }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .stat.alert .v { color: var(--ds-warning); }
    .domains { display: grid; gap: var(--ds-space-2); }
    .dom { display: grid; grid-template-columns: 130px 1fr 50px; align-items: center; gap: var(--ds-space-3); font-size: var(--ds-text-sm); }
    .dom .bar { height: 8px; background: var(--ds-surface-3); border-radius: 4px; overflow: hidden; }
    .dom .bar > i { display: block; height: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .dom .n { font-family: var(--ds-font-mono); text-align: right; color: var(--ds-text-soft); }
    .meta { color: var(--ds-text-muted); font-size: var(--ds-text-xs); margin-top: var(--ds-space-2); }
    .muted { color: var(--ds-text-muted); }
  `;

  render() {
    const b = this.briefing, s = this.stats, p = this.papers;
    const total = p ? Object.values(p.papers_by_domain).reduce((a, c) => a + c, 0) || 1 : 1;
    return html`
      <ds-panel heading="Daily briefing · news">
        ${b ? html`
          <div class="when">${b.date} · ${b.time}</div>
          <p class="briefing">${b.briefing}</p>
          <div slot="actions"><ds-button size="sm" @click=${() => void this.speak()}>${this.speaking ? "🔊" : "speak"}</ds-button></div>
        ` : html`<span class="muted">loading briefing…</span>`}
      </ds-panel>

      <ds-panel heading="Research intake">
        ${s ? html`<div class="stats">
          <div class="stat"><div class="k">topics tracked</div><div class="v">${s.topics}</div></div>
          <div class="stat"><div class="k">findings</div><div class="v">${s.total_findings}</div></div>
          <div class="stat alert"><div class="k">unread</div><div class="v">${s.unread_findings}</div></div>
          <div class="stat"><div class="k">last 24h</div><div class="v">${s.last_24h}</div></div>
        </div>` : html`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Research paper corpus${p ? ` · ${p.total_papers} indexed` : ""}">
        ${p ? html`
          <div class="domains">
            ${Object.entries(p.papers_by_domain).sort((a, b2) => b2[1] - a[1]).map(([dom, n]) => html`
              <div class="dom">
                <span>${dom}</span>
                <span class="bar"><i style="width:${(n / total) * 100}%"></i></span>
                <span class="n">${n}</span>
              </div>
            `)}
          </div>
          <p class="meta">${p.db_size_mb?.toFixed?.(1) ?? p.db_size_mb} MB · updated ${new Date(p.last_updated).toLocaleString()}</p>
        ` : html`<span class="muted">loading corpus…</span>`}
      </ds-panel>
    `;
  }
}
