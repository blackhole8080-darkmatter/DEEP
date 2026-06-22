// <calc-view> — interactive graphing calculator + symbolic/science compute.
// Plots y = f(x) client-side on an SVG with axes; the compute box routes
// natural-language math/science to the live engine (/api/science/compute).
import { LitElement, html, css, svg } from "lit";
import { customElement, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { mathSolve, scienceCompute } from "../../core/api";
import { katexStyles, renderTeX } from "../../core/math";
import "../primitives/ds-panel";
import "../primitives/ds-button";

// Restricted math-expression compiler: x → number, common Math fns allowed.
function compile(expr: string): ((x: number) => number) | null {
  const cleaned = expr
    .replace(/\^/g, "**")
    .replace(/\b(sin|cos|tan|asin|acos|atan|sqrt|abs|log|log2|log10|exp|sign|floor|ceil|round|cbrt|sinh|cosh|tanh)\b/g, "Math.$1")
    .replace(/\bpi\b/gi, "Math.PI")
    .replace(/\be\b/g, "Math.E")
    .replace(/\bln\b/g, "Math.log");
  if (/[^0-9x+\-*/().,%\sMathPIE_a-z]/i.test(cleaned)) return null;
  try {
    // eslint-disable-next-line no-new-func
    const f = new Function("x", `"use strict"; return (${cleaned});`) as (x: number) => number;
    if (typeof f(1) !== "number" || Number.isNaN(f(1)) && Number.isNaN(f(0.5))) { /* allow */ }
    return f;
  } catch { return null; }
}

@customElement("calc-view")
export class CalcView extends LitElement {
  @state() private expr = "sin(x) * x";
  @state() private xmin = -10;
  @state() private xmax = 10;
  @state() private error = "";
  @state() private computeQ = "derivative of x^3 + 2x";
  @state() private computeOut = "";
  @state() private computeTeX = "";       // rendered LaTeX (display mode)
  @state() private computeTeXExpr = "";    // rendered LaTeX of the input expression
  @state() private computing = false;

  static styles = [katexStyles, css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .controls { display: flex; gap: var(--ds-space-2); align-items: center; flex-wrap: wrap; }
    input { padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); }
    input.fn { flex: 1; min-width: 200px; }
    input.rng { width: 64px; }
    .eq { color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .plot { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .axis { stroke: var(--ds-border-strong); stroke-width: 1; }
    .grid { stroke: var(--ds-border); stroke-width: 0.5; }
    .curve { fill: none; stroke: var(--ds-accent); stroke-width: 2; filter: drop-shadow(0 0 4px var(--ds-accent)); }
    .err { color: var(--ds-danger); font-size: var(--ds-text-sm); }
    .compute textarea { width: 100%; min-height: 44px; resize: vertical; background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); padding: var(--ds-space-3); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); }
    .out { margin-top: var(--ds-space-3); padding: var(--ds-space-3); background: var(--ds-surface-2); border-left: 2px solid var(--ds-accent); border-radius: var(--ds-radius-sm); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); white-space: pre-wrap; }
    .chips { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; margin-top: var(--ds-space-2); }
    .chip { padding: 2px 10px; border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); color: var(--ds-text-soft); cursor: pointer; font-family: var(--ds-font-mono); }
    .chip:hover { border-color: var(--ds-border-accent); color: var(--ds-accent); }
    .tex-block { margin-top: var(--ds-space-3); padding: var(--ds-space-3) var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border-accent); border-radius: var(--ds-radius-md); overflow-x: auto; }
    .tex-block .katex { color: var(--ds-text); font-size: 1.25em; }
    .tex-expr { color: var(--ds-text-muted); margin-bottom: var(--ds-space-2); padding-bottom: var(--ds-space-2); border-bottom: 1px dashed var(--ds-border); }
    .tex-expr .katex { font-size: 1em; }
    .tex-error { color: var(--ds-danger); font-family: var(--ds-font-mono); }
  `];

  private plot() {
    const W = 720, H = 380;
    const f = compile(this.expr);
    if (!f) { this.error = "invalid expression"; return svg``; }
    const xmin = this.xmin, xmax = this.xmax;
    const N = 480;
    const xs: number[] = [], ys: number[] = [];
    for (let i = 0; i <= N; i++) {
      const x = xmin + (i / N) * (xmax - xmin);
      let y = NaN;
      try { y = f(x); } catch { /* skip */ }
      xs.push(x); ys.push(y);
    }
    const finite = ys.filter((y) => Number.isFinite(y));
    if (!finite.length) { this.error = "no finite values in range"; return svg``; }
    this.error = "";
    let ymin = Math.min(...finite), ymax = Math.max(...finite);
    if (ymin === ymax) { ymin -= 1; ymax += 1; }
    const pad = (ymax - ymin) * 0.08; ymin -= pad; ymax += pad;
    const sx = (x: number) => ((x - xmin) / (xmax - xmin)) * W;
    const sy = (y: number) => H - ((y - ymin) / (ymax - ymin)) * H;
    // build path, breaking on non-finite / jumps (asymptotes)
    let dpath = "";
    let pen = false;
    for (let i = 0; i <= N; i++) {
      const y = ys[i];
      if (!Number.isFinite(y) || sy(y) < -H || sy(y) > 2 * H) { pen = false; continue; }
      dpath += `${pen ? "L" : "M"}${sx(xs[i]).toFixed(1)},${sy(y).toFixed(1)} `;
      pen = true;
    }
    const x0 = sx(0), y0 = sy(0);
    const grids = [];
    for (let gx = Math.ceil(xmin); gx <= xmax; gx++) grids.push(svg`<line class="grid" x1=${sx(gx)} y1="0" x2=${sx(gx)} y2=${H}></line>`);
    return svg`
      <svg viewBox="0 0 ${W} ${H}">
        ${grids}
        ${y0 >= 0 && y0 <= H ? svg`<line class="axis" x1="0" y1=${y0} x2=${W} y2=${y0}></line>` : ""}
        ${x0 >= 0 && x0 <= W ? svg`<line class="axis" x1=${x0} y1="0" x2=${x0} y2=${H}></line>` : ""}
        <path class="curve" d=${dpath}></path>
      </svg>`;
  }

  private async runCompute(): Promise<void> {
    this.computing = true;
    this.computeOut = "";
    this.computeTeX = "";
    this.computeTeXExpr = "";
    try {
      // Prefer the exact symbolic router; fall back to the broader NL engine.
      const m = await mathSolve(this.computeQ);
      if (m.ok && m.result) {
        this.computeOut = `${m.expression} = ${m.result}\n(${m.kind}, verified by ${m.engine})`;
        if (m.latex) this.computeTeX = renderTeX(m.latex, true);
        if (m.latex_expr) this.computeTeXExpr = renderTeX(m.latex_expr, true);
      } else {
        const r = await scienceCompute(this.computeQ);
        this.computeOut = r.verbal || JSON.stringify(r.result ?? r, null, 1);
        if (r.latex) this.computeTeX = renderTeX(r.latex, true);
      }
    } catch (e) { this.computeOut = "compute failed: " + String(e); }
    this.computing = false;
  }

  render() {
    const examples = ["sin(x) * x", "x^2 - 4", "1/x", "exp(-x*x)", "tan(x)", "sqrt(abs(x))"];
    const computeEx = ["solve x^2 - 5x + 6 = 0", "integrate x^2", "factor x^2 - 9", "what is 2^20"];
    return html`
      <ds-panel heading="Graphing calculator">
        <div class="controls">
          <span class="eq">y =</span>
          <input class="fn" .value=${this.expr} @input=${(e: Event) => { this.expr = (e.target as HTMLInputElement).value; }} />
          <span class="eq">x ∈ [</span>
          <input class="rng" type="number" .value=${String(this.xmin)} @input=${(e: Event) => { this.xmin = +(e.target as HTMLInputElement).value; }} />
          <span class="eq">,</span>
          <input class="rng" type="number" .value=${String(this.xmax)} @input=${(e: Event) => { this.xmax = +(e.target as HTMLInputElement).value; }} />
          <span class="eq">]</span>
          <ds-button @click=${() => this.requestUpdate()}>plot</ds-button>
        </div>
        ${this.error ? html`<div class="err">${this.error}</div>` : ""}
        <div class="plot" style="margin-top:var(--ds-space-3)">${this.plot()}</div>
        <div class="chips">${examples.map((ex) => html`<span class="chip" @click=${() => { this.expr = ex; }}>${ex}</span>`)}</div>
      </ds-panel>

      <ds-panel heading="Symbolic & science compute · live engine">
        <div class="compute">
          <textarea .value=${this.computeQ} @input=${(e: Event) => { this.computeQ = (e.target as HTMLTextAreaElement).value; }}></textarea>
          <div class="chips">${computeEx.map((ex) => html`<span class="chip" @click=${() => { this.computeQ = ex; }}>${ex}</span>`)}</div>
          <div style="margin-top:var(--ds-space-2)"><ds-button variant="primary" @click=${() => void this.runCompute()}>${this.computing ? "computing…" : "compute"}</ds-button></div>
          ${this.computeTeX
            ? html`<div class="tex-block">
                ${this.computeTeXExpr ? html`<div class="tex-expr">${unsafeHTML(this.computeTeXExpr)}</div>` : ""}
                ${unsafeHTML(this.computeTeX)}
              </div>`
            : ""}
          ${this.computeOut ? html`<div class="out">${this.computeOut}</div>` : ""}
        </div>
      </ds-panel>
    `;
  }
}
