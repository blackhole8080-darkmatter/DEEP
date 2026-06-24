// <stack-view> — DEEP's observability layer. Shows the live state of the two
// tiers DEEP actually owns: the model layer (which provider/model served each
// request, latency percentiles, fallthroughs) and the orchestration/tool layer
// (per-tool call counts, error rates, durations). Data from /api/telemetry.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { fetchTelemetry, type TelemetrySummary } from "../../core/api";
import "../primitives/ds-panel";
import "../primitives/ds-button";

@customElement("stack-view")
export class StackView extends LitElement {
  @state() private data: TelemetrySummary | null = null;
  @state() private loading = true;
  @state() private hours = 24;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try { this.data = await fetchTelemetry(this.hours); }
    catch (e) { this.data = { error: String(e) }; }
    this.loading = false;
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .muted { color: var(--ds-text-muted); }
    .stats { display: flex; gap: var(--ds-space-5); flex-wrap: wrap; margin-bottom: var(--ds-space-3); }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .v.warn { color: var(--ds-warning); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-soft); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    table { width: 100%; border-collapse: collapse; font-size: var(--ds-text-sm); }
    th, td { text-align: left; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); }
    th { color: var(--ds-text-soft); font-size: var(--ds-text-xs); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); font-weight: 500; }
    td { font-family: var(--ds-font-mono); }
    td.name { font-family: var(--ds-font-sans); }
    .num { text-align: right; }
    .err { color: var(--ds-danger); }
    select { background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); padding: 2px 8px; font-family: var(--ds-font-mono); }
  `;

  private stat(k: string, v: unknown, warn = false) {
    return html`<div class="stat"><div class="v ${warn ? "warn" : ""}">${v ?? "—"}</div><div class="k">${k}</div></div>`;
  }

  render() {
    const d = this.data;
    const llm = d?.llm, tools = d?.tools;
    return html`
      <ds-panel heading="DEEP stack telemetry · model + orchestration layers">
        <div class="head">
          <span class="muted">${this.loading ? "loading…" : `last ${this.hours}h`}</span>
          <div style="display:flex;gap:var(--ds-space-2);align-items:center">
            <select @change=${(e: Event) => { this.hours = +(e.target as HTMLSelectElement).value; void this.load(); }}>
              <option value="1">1h</option><option value="24" selected>24h</option><option value="168">7d</option>
            </select>
            <ds-button @click=${() => void this.load()}>refresh</ds-button>
          </div>
        </div>
        ${d?.error ? html`<div class="err">${d.error}</div>` : ""}
      </ds-panel>

      <ds-panel heading="Model layer · LLM routing">
        ${llm && llm.total_calls ? html`
          <div class="stats">
            ${this.stat("calls", llm.total_calls)}
            ${this.stat("ok", llm.ok)}
            ${this.stat("fallthroughs", llm.fallthroughs, llm.fallthroughs > 0)}
            ${this.stat("p50", llm.p50_ms != null ? `${llm.p50_ms}ms` : "—")}
            ${this.stat("~tokens", (llm.est_tokens ?? 0).toLocaleString())}
            ${this.stat("~cost", `$${(llm.est_cost_usd ?? 0).toFixed(4)}`)}
          </div>
          <table>
            <tr><th>provider:model</th><th class="num">calls</th><th class="num">ok</th><th class="num">p50</th><th class="num">~tok</th><th class="num">~cost</th></tr>
            ${llm.providers.map((p) => html`<tr>
              <td>${p.provider}</td><td class="num">${p.calls}</td>
              <td class="num ${p.ok < p.calls ? "err" : ""}">${p.ok}</td>
              <td class="num">${p.p50_ms ?? "—"}</td>
              <td class="num">${(p.tokens ?? 0).toLocaleString()}</td>
              <td class="num">$${(p.cost ?? 0).toFixed(4)}</td>
            </tr>`)}
          </table>
          <div class="muted" style="margin-top:var(--ds-space-2);font-size:var(--ds-text-xs)">Tokens & cost are estimates (~4 chars/token × published rates), not billed figures.</div>
        ` : html`<span class="muted">No LLM calls recorded yet — send a chat message.</span>`}
      </ds-panel>

      <ds-panel heading="Orchestration layer · tool calls">
        ${tools && tools.total_calls ? html`
          <div class="stats">
            ${this.stat("calls", tools.total_calls)}
            ${this.stat("errors", tools.errors, tools.errors > 0)}
          </div>
          <table>
            <tr><th>tool</th><th class="num">calls</th><th class="num">errors</th><th class="num">p50</th><th class="num">p95</th></tr>
            ${tools.by_tool.map((t) => html`<tr>
              <td class="name">${t.name}</td><td class="num">${t.calls}</td>
              <td class="num ${t.errors ? "err" : ""}">${t.errors}</td>
              <td class="num">${t.p50_ms ?? "—"}</td><td class="num">${t.p95_ms ?? "—"}</td>
            </tr>`)}
          </table>
        ` : html`<span class="muted">No tool calls recorded yet — ask DEEP something that uses a tool.</span>`}
      </ds-panel>
    `;
  }
}
