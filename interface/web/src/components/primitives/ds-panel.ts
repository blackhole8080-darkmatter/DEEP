// <ds-panel> — surface container with optional header. glass | solid variants.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("ds-panel")
export class DsPanel extends LitElement {
  @property() heading = "";
  @property() variant: "solid" | "glass" = "solid";

  static styles = css`
    :host { display: block; }
    section {
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      overflow: hidden;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    /* Default panels are now lightly translucent so the living-brain background
       shows through — deeper fill + small blur keeps text readable (no heavy
       blur here; that's reserved for sidebar/topbar to keep compositing cheap). */
    .solid {
      background: var(--ds-glass-deep);
      -webkit-backdrop-filter: blur(var(--ds-blur-sm));
      backdrop-filter: blur(var(--ds-blur-sm));
      border-color: var(--ds-border-glass);
    }
    .glass {
      background: var(--ds-glass-light);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
      border-color: var(--ds-border-glass);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--ds-space-3) var(--ds-space-4);
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      font-weight: 600;
      letter-spacing: var(--ds-tracking-wide);
      color: var(--ds-text-soft);
      text-transform: uppercase;
    }
    .body { padding: var(--ds-space-4); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { section { animation: none; } }
  `;

  render() {
    return html`
      <section class=${this.variant}>
        ${this.heading
          ? html`<header><span>${this.heading}</span><slot name="actions"></slot></header>`
          : ""}
        <div class="body"><slot></slot></div>
      </section>
    `;
  }
}
