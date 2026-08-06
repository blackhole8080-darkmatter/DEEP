// <deep-predictive> — Proactive suggestion banner
// Shows when DEEP predicts the user may want something. Legacy HUD parity.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

@customElement("deep-predictive")
export class DeepPredictive extends LitElement {
  @state() private visible = false;
  @state() private suggestion = "";
  @state() private reason = "";

  static styles = css`
    :host {
      position: fixed; top: 64px; left: 50%; transform: translateX(-50%);
      z-index: 30; max-width: 520px; width: 92vw;
      display: grid; gap: 0;
    }
    .banner {
      display: flex; align-items: center; gap: 12px;
      padding: 10px 16px;
      background: rgba(10,18,30,0.88);
      backdrop-filter: blur(16px) saturate(1.2);
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 14px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.35);
      animation: slideDown 0.35s var(--ds-ease-spring, ease);
    }
    .icon {
      width: 28px; height: 28px; border-radius: 50%;
      display: grid; place-items: center;
      background: rgba(0,229,255,0.1);
      color: var(--ds-accent, #00e5ff);
      font-size: 0.9rem; flex-shrink: 0;
    }
    .text { flex: 1; min-width: 0; }
    .label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.14em; color: var(--ds-accent, #00e5ff); }
    .sugg { font-size: 0.82rem; color: #eaf6ff; font-weight: 500; margin-top: 2px; }
    .reason { font-size: 0.65rem; color: rgba(234,246,255,0.4); margin-top: 1px; }
    .actions { display: flex; gap: 6px; flex-shrink: 0; }
    button {
      padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(0,229,255,0.2);
      background: none; color: #eaf6ff; font-size: 0.72rem; cursor: pointer;
      transition: all 0.15s;
    }
    button:hover { background: rgba(0,229,255,0.08); }
    button.yes { background: rgba(0,229,255,0.12); border-color: rgba(0,229,255,0.35); }
    button.yes:hover { background: rgba(0,229,255,0.22); }
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-12px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;

  show(suggestion: string, reason?: string) {
    this.suggestion = suggestion;
    this.reason = reason || "";
    this.visible = true;
  }

  hide() { this.visible = false; }

  private accept() {
    this.dispatchEvent(new CustomEvent("accept", { detail: this.suggestion, bubbles: true, composed: true }));
    this.hide();
  }

  private reject() {
    this.dispatchEvent(new CustomEvent("reject", { detail: this.suggestion, bubbles: true, composed: true }));
    this.hide();
  }

  render() {
    if (!this.visible) return html``;
    return html`
      <div class="banner">
        <div class="icon">ॐ</div>
        <div class="text">
          <div class="label">Predicted</div>
          <div class="sugg">${this.suggestion}</div>
          ${this.reason ? html`<div class="reason">${this.reason}</div>` : ""}
        </div>
        <div class="actions">
          <button class="yes" @click=${this.accept}>Yes</button>
          <button @click=${this.reject}>No</button>
        </div>
      </div>
    `;
  }
}
