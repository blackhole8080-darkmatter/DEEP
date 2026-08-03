// <ds-field> — labeled text input. Emits `ds-input` (on input) and `ds-submit` (Enter).
import { LitElement, html, css } from "lit";
import { customElement, property, query } from "lit/decorators.js";

@customElement("ds-field")
export class DsField extends LitElement {
  @property() label = "";
  @property() placeholder = "";
  @property() value = "";
  @property() type = "text";

  @query("input") private input!: HTMLInputElement;

  static styles = css`
    :host { display: block; }
    label {
      display: block;
      margin-bottom: var(--ds-space-1);
      font-size: var(--ds-text-xs);
      letter-spacing: var(--ds-tracking-wide);
      text-transform: uppercase;
      color: var(--ds-text-muted);
    }
    input {
      width: 100%;
      padding: var(--ds-space-2) var(--ds-space-3);
      font-family: var(--ds-font-sans);
      font-size: var(--ds-text-sm);
      color: var(--ds-text);
      background: var(--ds-surface-2);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-sm);
      transition: border-color var(--ds-dur-fast) var(--ds-ease-out);
    }
    input::placeholder { color: var(--ds-text-faint); }
    input:hover { border-color: var(--ds-border-strong); }
    input:focus { outline: none; border-color: var(--ds-border-accent); box-shadow: var(--ds-focus-ring); }
  `;

  private onInput() {
    this.value = this.input.value;
    this.dispatchEvent(new CustomEvent("ds-input", { detail: this.value, bubbles: true, composed: true }));
  }

  private onKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      this.dispatchEvent(new CustomEvent("ds-submit", { detail: this.value, bubbles: true, composed: true }));
    }
  }

  render() {
    return html`
      ${this.label ? html`<label>${this.label}</label>` : ""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `;
  }
}
