// <deep-chat> — the conversation surface: message history, live reasoning
// trail, thinking indicator, composer. Pure view over the signal store.
import { LitElement, html, css } from "lit";
import { customElement } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { messages, thinking, reasoningSteps, sendChat, isStreaming } from "../../core/store";
import "./chat-message";
import "./reasoning-trail";
import "./composer";
import "../inference-trace";

@customElement("deep-chat")
export class DeepChat extends SignalWatcher(LitElement) {
  static styles = css`
    :host {
      display: grid;
      grid-template-rows: 1fr auto;
      height: 100%;
      max-width: 820px;
      margin: 0 auto;
      width: 100%;
      padding: 0 var(--ds-space-4);
    }
    .scroll {
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: var(--ds-space-3);
      padding: var(--ds-space-5) var(--ds-space-1);
      scroll-behavior: smooth;
    }
    .empty {
      margin: auto;
      text-align: center;
      color: var(--ds-text-muted);
    }
    .empty h2 { color: var(--ds-text-soft); font-weight: 600; margin: 0 0 var(--ds-space-2); }
    .thinking {
      align-self: flex-start;
      display: inline-flex; gap: 5px;
      padding: var(--ds-space-3) var(--ds-space-4);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md);
    }
    .thinking span {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent);
      animation: pulse 1.2s ease-in-out infinite;
    }
    .thinking span:nth-child(2) { animation-delay: 0.15s; }
    .thinking span:nth-child(3) { animation-delay: 0.3s; }
    .composer-area { padding: var(--ds-space-3) 0 var(--ds-space-5); }
    @keyframes pulse { 0%, 100% { opacity: 0.25; } 50% { opacity: 1; } }
  `;

  updated(): void {
    const sc = this.renderRoot.querySelector(".scroll");
    if (sc) sc.scrollTop = sc.scrollHeight;
  }

  render() {
    const msgs = messages.get();
    const steps = reasoningSteps.get();
    const isThink = thinking.get();
    const isStream = isStreaming.get();
    let phase: "idle" | "perceive" | "recall" | "reason" | "generate" | "complete" = "idle";
    if (isThink) phase = "reason";
    else if (isStream) phase = "generate";
    else if (msgs.length > 0 && !isThink && !isStream) phase = "complete";
    return html`
      <inference-trace .phase=${phase}></inference-trace>
      <div class="scroll">
        ${msgs.length === 0
          ? html`<div class="empty">
              <h2>How can I help, Aryan?</h2>
              <p>Ask anything — drop an image for vision, or a document to absorb it.</p>
            </div>`
          : msgs.map((m) => html`<chat-message .msg=${m}></chat-message>`)}
        ${steps.length && (isThink || isStream)
          ? html`<reasoning-trail .steps=${steps}></reasoning-trail>`
          : ""}
        ${isThink
          ? html`<div class="thinking"><span></span><span></span><span></span></div>`
          : ""}
      </div>
      <div class="composer-area">
        <chat-composer
          @send=${(e: CustomEvent<{ text: string; image: string | null }>) =>
            sendChat(e.detail.text, e.detail.image)}
        ></chat-composer>
      </div>
    `;
  }
}
