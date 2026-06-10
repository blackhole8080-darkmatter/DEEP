// <ds-gallery> — Phase 1 verification surface: renders every primitive in all
// variants so the design system can be eyeballed at /app#gallery.
import { LitElement, html, css } from "lit";
import { customElement } from "lit/decorators.js";
import "./primitives/ds-button";
import "./primitives/ds-panel";
import "./primitives/ds-field";
import { toast } from "./primitives/ds-toast";

@customElement("ds-gallery")
export class DsGallery extends LitElement {
  static styles = css`
    :host {
      display: grid;
      gap: var(--ds-space-5);
      padding: var(--ds-space-6);
      max-width: 860px;
      margin: 0 auto;
    }
    .row { display: flex; gap: var(--ds-space-3); align-items: center; flex-wrap: wrap; }
    h1 { font-size: var(--ds-text-xl); margin: 0; }
    .swatches { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    .sw {
      width: 72px; height: 48px;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      display: grid; place-items: end start;
      padding: 4px; font-size: 9px; color: var(--ds-text-muted);
      font-family: var(--ds-font-mono);
    }
  `;

  render() {
    return html`
      <h1>Design system gallery</h1>

      <ds-panel heading="Buttons">
        <div class="row">
          <ds-button variant="primary">Primary</ds-button>
          <ds-button>Ghost</ds-button>
          <ds-button variant="danger">Danger</ds-button>
          <ds-button variant="primary" size="sm">Small</ds-button>
          <ds-button disabled>Disabled</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Fields">
        <div class="row" style="align-items:end">
          <ds-field label="Name" placeholder="Type something…" style="flex:1"></ds-field>
          <ds-field label="Token" placeholder="••••" type="password" style="flex:1"></ds-field>
        </div>
      </ds-panel>

      <ds-panel heading="Toasts">
        <div class="row">
          <ds-button @click=${() => toast("Saved successfully", "success")}>Success</ds-button>
          <ds-button @click=${() => toast("Heads up — informational", "info")}>Info</ds-button>
          <ds-button variant="danger" @click=${() => toast("Something failed", "danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg", "--ds-surface-1", "--ds-surface-2", "--ds-surface-3", "--ds-accent", "--ds-success", "--ds-warning", "--ds-danger", "--ds-info"].map(
            (t) => html`<div class="sw" style="background: var(${t})">${t.slice(5)}</div>`,
          )}
        </div>
      </ds-panel>
    `;
  }
}
