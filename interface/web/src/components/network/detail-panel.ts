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
    :host { display: block; font-family: var(--ds-font-mono, monospace); }
    .panel { 
      background: rgba(2, 4, 8, 0.6); 
      padding: 20px; 
      height: 100%; 
      overflow-y: auto; 
      color: rgba(0, 229, 255, 0.8);
    }
    .header { 
      display: flex; align-items: center; gap: 12px; margin-bottom: 24px; 
      padding-bottom: 12px; border-bottom: 1px solid rgba(0, 229, 255, 0.2);
    }
    .layer-badge { 
      padding: 4px 10px; border-radius: 2px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
      border: 1px solid currentColor;
    }
    .layer-lan { color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .layer-wifi { color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
    .layer-bluetooth { color: #8b5cf6; background: rgba(139, 92, 246, 0.1); }
    .layer-vpn { color: var(--ds-accent); background: rgba(0, 229, 255, 0.1); }
    .layer-internet { color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .layer-dns { color: #d946ef; background: rgba(217, 70, 239, 0.1); }
    .layer-ai { color: #3b82f6; background: rgba(59, 130, 246, 0.1); }
    
    .section { margin-bottom: 24px; }
    .section-title { font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 0.2em; margin-bottom: 12px; }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .meta-item { 
      background: rgba(0, 0, 0, 0.5); 
      border: 1px solid rgba(0, 229, 255, 0.15);
      padding: 10px; border-radius: 2px; font-size: 0.8rem; 
    }
    .meta-item .k { font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }
    .meta-item .v { color: var(--ds-accent); word-break: break-all; }
    
    .inference { 
      background: rgba(0, 0, 0, 0.5); padding: 12px; border-radius: 2px; margin-bottom: 8px; 
      border: 1px solid rgba(0, 229, 255, 0.15); border-left: 3px solid var(--ds-accent); 
    }
    .inference .conf { font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; }
    .inference .text { font-size: 0.8rem; color: var(--ds-accent); margin-top: 6px; }
    
    .analysis-result { background: #000; border: 1px solid var(--ds-accent); padding: 16px; border-radius: 2px; font-size: 0.8rem; color: var(--ds-accent); white-space: pre-wrap; box-shadow: inset 0 0 15px rgba(0, 229, 255, 0.1); }
    .muted { color: rgba(255,255,255,0.3); font-size: 0.8rem; font-style: italic; }
    
    button { 
      background: transparent; color: var(--ds-accent); border: 1px solid var(--ds-accent); 
      padding: 6px 12px; border-radius: 2px; font-size: 0.7rem; font-family: var(--ds-font-mono, monospace);
      text-transform: uppercase; letter-spacing: 0.15em; cursor: pointer; transition: all 0.2s;
    }
    button:hover:not(:disabled) { background: var(--ds-accent); color: #000; box-shadow: 0 0 15px var(--ds-accent); }
    button:disabled { opacity: 0.5; cursor: not-allowed; border-color: rgba(0, 229, 255, 0.3); color: rgba(0, 229, 255, 0.5); }
    
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(0, 229, 255, 0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 229, 255, 0.6); }
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
