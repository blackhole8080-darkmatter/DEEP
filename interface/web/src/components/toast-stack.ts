// <toast-stack> — Slide-in notification toasts replacing deep-predictive
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface Toast {
  id: number;
  title: string;
  body: string;
  type: "info" | "success" | "warn" | "alert";
  action?: { label: string; href: string };
}

let nextId = 1;

@customElement("toast-stack")
export class ToastStack extends LitElement {
  @state() private toasts: Toast[] = [];

  static styles = css`
    :host {
      position: fixed;
      top: 16px; right: 16px;
      z-index: 3000;
      display: flex; flex-direction: column;
      gap: 10px;
      max-width: 340px;
      pointer-events: none;
    }
    .toast {
      pointer-events: auto;
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-lg));
      -webkit-backdrop-filter: blur(var(--ds-blur-lg));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md);
      padding: var(--ds-space-3) var(--ds-space-4);
      box-shadow: var(--ds-elev-3);
      animation: toast-in 0.35s var(--ds-ease-out) both;
      position: relative;
      overflow: hidden;
    }
    .toast.out { animation: toast-out 0.3s var(--ds-ease-out) both; }
    .toast::before {
      content: "";
      position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    }
    .toast.info::before  { background: var(--ds-info); box-shadow: 0 0 6px var(--ds-info); }
    .toast.success::before { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .toast.warn::before  { background: var(--ds-warning); box-shadow: 0 0 6px var(--ds-warning); }
    .toast.alert::before { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .toast-title {
      font-size: var(--ds-text-sm); font-weight: 600;
      color: var(--ds-text-soft);
      margin-bottom: 2px;
    }
    .toast-body {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
      line-height: 1.4;
    }
    .toast-action {
      margin-top: var(--ds-space-2);
      display: inline-block;
      font-size: var(--ds-text-xs);
      color: var(--ds-accent);
      text-decoration: none;
      font-weight: 500;
      cursor: pointer;
    }
    .toast-action:hover { text-decoration: underline; }
    .toast-close {
      position: absolute; top: 6px; right: 8px;
      background: none; border: none; color: var(--ds-text-faint);
      font-size: 14px; cursor: pointer; line-height: 1;
    }
    .toast-close:hover { color: var(--ds-text); }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    // Demo toasts for preview
    setTimeout(() => this._push({ title: "DEEP Online", body: "Voice assistant connected and ready.", type: "success" }), 1200);
    setTimeout(() => this._push({ title: "Network Scan Complete", body: "24 devices discovered. 1 unknown flagged.", type: "info", action: { label: "Review →", href: "#network" } }), 3500);
  }

  private _push(t: Omit<Toast, "id">) {
    const toast = { ...t, id: nextId++ };
    this.toasts = [...this.toasts, toast];
    setTimeout(() => this._remove(toast.id), 6000);
  }

  private _remove(id: number) {
    const el = this.renderRoot.querySelector(`[data-id="${id}"]`) as HTMLElement | null;
    if (el) el.classList.add("out");
    setTimeout(() => {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    }, 350);
  }

  render() {
    return html`
      ${this.toasts.map((t) => html`
        <div class="toast ${t.type}" data-id="${t.id}">
          <button class="toast-close" @click=${() => this._remove(t.id)}>×</button>
          <div class="toast-title">${t.title}</div>
          <div class="toast-body">${t.body}</div>
          ${t.action ? html`<a class="toast-action" href="${t.action.href}">${t.action.label}</a>` : ""}
        </div>
      `)}
    `;
  }
}
