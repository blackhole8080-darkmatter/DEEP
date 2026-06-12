// <spark-line> — a tiny live time-series sparkline (SVG area + line).
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("spark-line")
export class SparkLine extends LitElement {
  @property({ attribute: false }) data: number[] = [];
  @property({ type: Number }) max = 100;
  @property() color = "var(--ds-accent)";
  @property({ type: Number }) height = 48;

  static styles = css`
    :host { display: block; }
    svg { width: 100%; height: 100%; display: block; }
  `;

  render() {
    const W = 200, H = this.height;
    const d = this.data.slice(-60);
    if (d.length < 2) return html`<svg viewBox="0 0 ${W} ${H}"></svg>`;
    const max = this.max || Math.max(...d, 1);
    const step = W / (d.length - 1);
    const pts = d.map((v, i) => `${(i * step).toFixed(1)},${(H - (Math.min(v, max) / max) * H).toFixed(1)}`);
    const line = pts.join(" ");
    const area = `0,${H} ${line} ${W},${H}`;
    const uid = Math.random().toString(36).slice(2, 7);
    return html`
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="g${uid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color=${this.color} stop-opacity="0.32" />
            <stop offset="100%" stop-color=${this.color} stop-opacity="0" />
          </linearGradient>
        </defs>
        <polygon points=${area} fill="url(#g${uid})" />
        <polyline points=${line} fill="none" stroke=${this.color} stroke-width="1.5"
          vector-effect="non-scaling-stroke" stroke-linejoin="round" />
      </svg>
    `;
  }
}
