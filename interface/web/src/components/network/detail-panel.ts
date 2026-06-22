// <network-detail-panel> — Slide-in panel showing node metadata, observations, and AI insights
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { fetchNetworkObservations, fetchNetworkInferences, analyseNetwork } from "../../core/api";

interface TopoNode {
  id: string; layer: string; node_type: string; label: string;
  metadata: Record<string, any>; x: number; y: number; last_seen: string;
}

@customElement("network-detail-panel")
export class NetworkDetailPanel extends LitElement {
  @property({ type: Object }) node: TopoNode | null = null;
  @property({ type: Boolean }) open = false;
  @property({ type: Array }) observations: any[] = [];
  @property({ type: Array }) inferences: any[] = [];
  @property({ type: Object }) analysis: any = null;
  @property({ type: Boolean }) loading = false;

  static styles = css`
    :host { display: block; }
    .panel { background: var(--ds-surface-1); border-left: 1px solid var(--ds-border); padding: var(--ds-space-4); height: 100%; overflow-y: auto; }
    .header { display: flex; align-items: center; gap: var(--ds-space-2); margin-bottom: var(--ds-space-3); }
    .layer-badge { padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; text-transform: uppercase; }
    .layer-lan { background: color-mix(in srgb, var(--ds-success) 12%, transparent); color: var(--ds-success); }
    .layer-wifi { background: color-mix(in srgb, var(--ds-warning) 12%, transparent); color: var(--ds-warning); }
    .layer-bluetooth { background: color-mix(in srgb, var(--ds-iris, var(--ds-iris, #8b5cf6)) 12%, transparent); color: var(--ds-iris, #8b5cf6); }
    .layer-vpn { background: color-mix(in srgb, var(--ds-info) 12%, transparent); color: var(--ds-info); }
    .layer-internet { background: color-mix(in srgb, var(--ds-danger) 12%, transparent); color: var(--ds-danger); }
    .layer-dns { background: color-mix(in srgb, var(--ds-coral, var(--ds-coral, #d946ef)) 12%, transparent); color: var(--ds-coral, #d946ef); }
    .layer-ai { background: color-mix(in srgb, var(--ds-sky, var(--ds-sky, #3b82f6)) 12%, transparent); color: var(--ds-sky, #3b82f6); }
    .section { margin-bottom: var(--ds-space-4); }
    .section-title { font-size: var(--ds-text-xs); color: var(--ds-text-faint); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); margin-bottom: var(--ds-space-2); }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-2); }
    .meta-item { background: var(--ds-surface-2); padding: var(--ds-space-2); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); }
    .meta-item .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; }
    .meta-item .v { color: var(--ds-text); font-family: var(--ds-font-mono); word-break: break-all; }
    .inference { background: var(--ds-surface-2); padding: var(--ds-space-3); border-radius: var(--ds-radius-sm); margin-bottom: var(--ds-space-2); border-left: 3px solid var(--ds-accent); }
    .inference .conf { font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .inference .text { font-size: var(--ds-text-sm); color: var(--ds-text); margin-top: var(--ds-space-1); }
    .analysis-result { background: var(--ds-surface-2); padding: var(--ds-space-3); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); color: var(--ds-text); white-space: pre-wrap; }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    button { background: var(--ds-accent); color: var(--ds-on-accent); border: none; padding: var(--ds-space-2) var(--ds-space-3); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
  `;

  updated(changedProperties: Map<string, any>) {
    if (changedProperties.has("node") && this.node) {
      void this._loadData();
    }
  }

  private async _loadData() {
    if (!this.node) return;
    this.loading = true;
    try {
      const [obs, inf] = await Promise.all([
        fetchNetworkObservations(this.node.id, undefined, 24).catch(() => ({ observations: [] })),
        fetchNetworkInferences(this.node.id, undefined, 10).catch(() => ({ inferences: [] })),
      ]);
      this.observations = obs.observations;
      this.inferences = inf.inferences;
    } catch { /* noop */ }
    this.loading = false;
  }

  private async _analyse() {
    if (!this.node) return;
    this.loading = true;
    try {
      const res = await analyseNetwork("device", this.node.id);
      this.analysis = res.analysis || res;
    } catch { /* noop */ }
    this.loading = false;
  }

  render() {
    if (!this.node) return html`<div class="panel"><span class="muted">Select a node to view details.</span></div>`;
    const n = this.node;
    const layerClass = `layer-${n.layer}`;

    return html`
      <div class="panel">
        <div class="header">
          <span class="layer-badge ${layerClass}">${n.layer}</span>
          <h3 style="margin:0;font-size:var(--ds-text-lg);">${n.label}</h3>
        </div>

        <div class="section">
          <div class="section-title">Metadata</div>
          <div class="meta-grid">
            <div class="meta-item"><div class="k">ID</div><div class="v">${n.id}</div></div>
            <div class="meta-item"><div class="k">Type</div><div class="v">${n.node_type}</div></div>
            ${Object.entries(n.metadata).map(([k, v]) => html`
              <div class="meta-item"><div class="k">${k}</div><div class="v">${typeof v === "object" ? JSON.stringify(v) : String(v)}</div></div>
            `)}
          </div>
        </div>

        <div class="section">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="section-title">AI Analysis</div>
            <button @click=${() => void this._analyse()} ?disabled=${this.loading}>${this.loading ? "Analysing…" : "Analyse"}</button>
          </div>
          ${this.analysis ? html`
            <div class="analysis-result">${this.analysis.explanation || JSON.stringify(this.analysis, null, 2)}</div>
          ` : html`<span class="muted">Click Analyse to generate AI insight.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Inferences · ${this.inferences.length}</div>
          ${this.inferences.length ? this.inferences.map((inf) => html`
            <div class="inference">
              <div class="conf">${inf.inference_type} · ${(inf.confidence * 100).toFixed(0)}% · ${new Date(inf.timestamp).toLocaleString()}</div>
              <div class="text">${inf.explanation}</div>
            </div>
          `) : html`<span class="muted">No inferences yet.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Observations · ${this.observations.length}</div>
          ${this.observations.length ? html`
            <div class="meta-grid">
              ${this.observations.slice(0, 6).map((o) => html`
                <div class="meta-item">
                  <div class="k">${o.metric}</div>
                  <div class="v">${o.value?.toFixed?.(2) ?? o.value}</div>
                </div>
              `)}
            </div>
          ` : html`<span class="muted">No observations in the last 24h.</span>`}
        </div>
      </div>
    `;
  }
}
