// <deep-welcome> — Welcome screen with prompt chips
// Shown when chat is empty. Matches legacy HUD welcome experience.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const CHIPS = [
  "Scan network",
  "Research latest AI papers",
  "Show my projects",
  "What can you do?",
  "Check my finances",
  "Check my email",
];

@customElement("deep-welcome")
export class DeepWelcome extends LitElement {
  @state() private dismissed = false;

  static styles = css`
    :host { display: grid; place-items: center; height: 100%; }
    .wrap { text-align: center; max-width: 520px; padding: var(--ds-space-5); }
    .sub { font-size: var(--ds-text-xl); font-weight: 600; color: var(--ds-text); margin-bottom: var(--ds-space-2); }
    .hint { font-size: var(--ds-text-sm); color: var(--ds-text-muted); margin-bottom: var(--ds-space-5); }
    .chips { display: flex; flex-wrap: wrap; gap: var(--ds-space-2); justify-content: center; }
    .chip {
      padding: var(--ds-space-2) var(--ds-space-4);
      border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-1);
      color: var(--ds-text-soft);
      font-size: var(--ds-text-sm);
      cursor: pointer;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .chip:hover {
      border-color: var(--ds-border-accent);
      color: var(--ds-accent);
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      box-shadow: var(--ds-glow);
    }
  `;

  private onChip(text: string) {
    this.dispatchEvent(new CustomEvent("chip", { detail: text, bubbles: true, composed: true }));
    this.dismissed = true;
  }

  render() {
    if (this.dismissed) return html``;
    return html`
      <div class="wrap">
        <div class="sub">How can I help, Aryan?</div>
        <div class="hint">Ask anything, or pick a starting point below</div>
        <div class="chips">
          ${CHIPS.map((c) => html`<button class="chip" @click=${() => this.onChip(c)}>${c}</button>`)}
        </div>
      </div>
    `;
  }
}
