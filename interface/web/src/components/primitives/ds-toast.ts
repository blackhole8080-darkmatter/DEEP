// Toast system: call `toast("message", "success" | "danger" | "info")` from anywhere.
// A single <ds-toast-host> is auto-mounted on first use.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

export type ToastKind = "info" | "success" | "danger";
interface ToastItem { id: number; text: string; kind: ToastKind; }

let seq = 0;
let host: DsToastHost | null = null;

export function toast(text: string, kind: ToastKind = "info", ttlMs = 6000): void {
  if (!host) {
    host = document.createElement("ds-toast-host") as DsToastHost;
    document.body.appendChild(host);
  }
  host.push({ id: ++seq, text, kind }, ttlMs);
}

@customElement("ds-toast-host")
export class DsToastHost extends LitElement {
  @state() private items: ToastItem[] = [];

  push(item: ToastItem, ttlMs: number): void {
    this.items = [...this.items, item];
    setTimeout(() => this.dismiss(item.id), ttlMs);
  }

  private dismiss(id: number): void {
    this.items = this.items.filter((t) => t.id !== id);
  }

  static styles = css`
    :host {
      position: fixed;
      bottom: var(--ds-space-5);
      right: var(--ds-space-5);
      z-index: var(--ds-z-toast);
      display: flex;
      flex-direction: column;
      gap: var(--ds-space-2);
      max-width: 380px;
    }
    .toast {
      display: flex;
      align-items: center;
      gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-4);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-strong);
      border-radius: var(--ds-radius-md);
      box-shadow: var(--ds-elev-3);
      font-size: var(--ds-text-sm);
      animation: slide var(--ds-dur-base) var(--ds-ease-spring);
    }
    .info    { border-left: 2px solid var(--ds-info); }
    .success { border-left: 2px solid var(--ds-success); }
    .danger  { border-left: 2px solid var(--ds-danger); }
    .x { margin-left: auto; cursor: pointer; color: var(--ds-text-muted); border: 0; background: none; font-size: var(--ds-text-sm); }
    .x:hover { color: var(--ds-text); }
    @keyframes slide { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }
  `;

  render() {
    return html`${this.items.map(
      (t) => html`
        <div class="toast ${t.kind}">
          <span>${t.text}</span>
          <button class="x" @click=${() => this.dismiss(t.id)} aria-label="Dismiss">✕</button>
        </div>
      `,
    )}`;
  }
}
