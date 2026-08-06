// <ops-view> — operations dashboard: AI provider health, network security
// posture, and the knowledge base. Pure views over existing /api endpoints.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchProviderHealth, fetchKnowledgeList, type ProviderHealth } from "../../core/api";
import "../primitives/ds-panel";
import "../primitives/ds-button";

interface SecurityStatus {
  status: string;
  summary: { total: number; trusted: number; unknown: number; suspicious: number; recent_events: number };
  local_ip: string;
  gateway: string;
  interface: string;
  active_connections: number;
  listening_ports: number[];
  last_scan: string;
}
interface KnowledgeStats {
  entities: number;
  relationships: number;
  entity_types: Record<string, number>;
  most_connected: { name: string; connections: number }[];
}

@customElement("ops-view")
export class OpsView extends LitElement {
  @state() private providers: ProviderHealth | null = null;
  @state() private security: SecurityStatus | null = null;
  @state() private kstats: KnowledgeStats | null = null;
  @state() private docs: { source: string; chunks: number }[] = [];

  connectedCallback(): void {
    super.connectedCallback();
    void this.refresh();
  }

  private async refresh(): Promise<void> {
    void fetchProviderHealth().then((d) => (this.providers = d)).catch(() => {});
    void fetch("/api/security/status").then((r) => r.json()).then((d) => (this.security = d)).catch(() => {});
    void fetch("/api/knowledge/stats").then((r) => r.json()).then((d) => (this.kstats = d)).catch(() => {});
    void fetchKnowledgeList().then((d) => (this.docs = d.documents)).catch(() => {});
  }

  static styles = css`
    :host {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: var(--ds-space-4);
      padding: var(--ds-space-5);
      max-width: 1100px;
      margin: 0 auto;
      align-content: start;
    }
    .row {
      display: flex; justify-content: space-between; align-items: center;
      gap: var(--ds-space-3); padding: var(--ds-space-2) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
    .ok { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .bad { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .warn { color: var(--ds-warning); }
    .danger-text { color: var(--ds-danger); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag {
      padding: 1px 8px; border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-xs); color: var(--ds-text-soft);
      font-family: var(--ds-font-mono);
    }
  `;

  render() {
    const p = this.providers, s = this.security, k = this.kstats;
    return html`
      <ds-panel heading="AI providers">
        ${p
          ? p.providers.map(
              (pr) => html`
                <div class="row">
                  <span class="k"><span class="dot ${pr.ok ? "ok" : "bad"}"></span>${pr.provider}</span>
                  <span class=${pr.ok ? "muted" : "danger-text"}>${pr.detail}</span>
                </div>
              `,
            )
          : html`<span class="muted">loading…</span>`}
        <div slot="actions"><ds-button size="sm" @click=${() => void this.refresh()}>refresh</ds-button></div>
      </ds-panel>

      <ds-panel heading="Network security">
        ${s
          ? html`
              <div class="row"><span class="k">devices</span>
                <b>${s.summary.total} total · ${s.summary.trusted} trusted ·
                <span class=${s.summary.suspicious ? "danger-text" : ""}>${s.summary.suspicious} suspicious</span></b></div>
              <div class="row"><span class="k">interface</span><b>${s.interface} · ${s.local_ip}</b></div>
              <div class="row"><span class="k">gateway</span><b>${s.gateway}</b></div>
              <div class="row"><span class="k">active connections</span><b>${s.active_connections}</b></div>
              <div class="row"><span class="k">listening ports</span>
                <span class="tags">${(s.listening_ports ?? []).slice(0, 10).map((pt) => html`<span class="tag">${pt}</span>`)}</span></div>
            `
          : html`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Knowledge graph">
        ${k
          ? html`
              <div class="row"><span class="k">entities</span><b>${k.entities}</b></div>
              <div class="row"><span class="k">relationships</span><b>${k.relationships}</b></div>
              <div class="row"><span class="k">types</span>
                <span class="tags">${Object.entries(k.entity_types).map(([t, n]) => html`<span class="tag">${t} ${n}</span>`)}</span></div>
              <div class="row"><span class="k">most connected</span>
                <b>${(k.most_connected ?? []).slice(0, 3).map((m) => m.name).join(" · ")}</b></div>
            `
          : html`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Ingested documents">
        ${this.docs.length
          ? this.docs.map(
              (d) => html`<div class="row"><span class="k">${d.source}</span><b>${d.chunks} chunks</b></div>`,
            )
          : html`<span class="muted">No documents ingested yet — drop a file into the chat.</span>`}
      </ds-panel>
    `;
  }
}
