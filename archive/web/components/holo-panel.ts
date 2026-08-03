// <holo-panel> — Reusable sci-fi panel with holographic HUD aesthetics.
// Features: glowing corner brackets, marching border, scan-line sweep,
// glitch entry animation, and active-pulse ripple on content updates.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("holo-panel")
export class HoloPanel extends LitElement {
  @property({ type: String }) title = "";
  @property({ type: String }) accent: "cyan" | "violet" | "green" | "amber" | "red" = "cyan";
  @property({ type: Boolean }) scanLine = true;
  @property({ type: Boolean }) glitchEntry = true;
  @property({ type: Number }) pulseOnUpdate = 0;

  private _version = 0;

  static styles = css`
    :host { display: block; }
    .panel {
      position: relative;
      background:
        radial-gradient(ellipse at 20% 20%, rgba(var(--glow-rgb), 0.03), transparent 50%),
        radial-gradient(ellipse at 80% 80%, rgba(var(--glow-rgb), 0.03), transparent 50%),
        var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      padding: var(--ds-space-4);
      overflow: hidden;
      transition: box-shadow 0.3s ease;
    }
    .panel::before {
      content: "";
      position: absolute; inset: 0;
      border-radius: var(--ds-radius-lg);
      padding: 1px;
      background: linear-gradient(135deg, transparent 40%, rgba(var(--glow-rgb), 0.15), transparent 60%);
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      animation: border-flow 6s linear infinite;
    }

    /* Corner brackets */
    .corner {
      position: absolute;
      width: 12px; height: 12px;
      border-color: rgba(var(--glow-rgb), 0.5);
      pointer-events: none;
      transition: all 0.3s ease;
    }
    .corner.tl { top: 4px; left: 4px; border-top: 2px solid; border-left: 2px solid; border-top-left-radius: 3px; }
    .corner.tr { top: 4px; right: 4px; border-top: 2px solid; border-right: 2px solid; border-top-right-radius: 3px; }
    .corner.bl { bottom: 4px; left: 4px; border-bottom: 2px solid; border-left: 2px solid; border-bottom-left-radius: 3px; }
    .corner.br { bottom: 4px; right: 4px; border-bottom: 2px solid; border-right: 2px solid; border-bottom-right-radius: 3px; }
    .panel:hover .corner {
      width: 18px; height: 18px;
      border-color: rgba(var(--glow-rgb), 0.9);
      box-shadow: 0 0 6px rgba(var(--glow-rgb), 0.4);
    }

    /* Title bar */
    .title-bar {
      display: flex; align-items: center; gap: var(--ds-space-2);
      margin-bottom: var(--ds-space-3);
    }
    .title-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: rgb(var(--glow-rgb));
      box-shadow: 0 0 6px rgb(var(--glow-rgb));
      animation: dot-breathe 2s ease-in-out infinite;
    }
    .title-text {
      font-size: var(--ds-text-xs);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
      color: var(--ds-text-soft);
      font-weight: 600;
    }

    /* Scan line */
    .scan-line {
      position: absolute;
      left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(var(--glow-rgb), 0.15), transparent);
      animation: scan-sweep 5s ease-in-out infinite;
      pointer-events: none;
    }

    /* Active pulse ripple */
    .pulse-ring {
      position: absolute;
      border-radius: var(--ds-radius-lg);
      border: 1px solid rgba(var(--glow-rgb), 0.4);
      opacity: 0;
      pointer-events: none;
    }
    .pulse-ring.active {
      animation: pulse-expand 0.8s ease-out forwards;
    }

    /* Glitch entry */
    @keyframes glitch-in {
      0% { opacity: 0; transform: translateX(-8px) skewX(3deg); filter: hue-rotate(30deg); }
      20% { opacity: 0.3; transform: translateX(4px) skewX(-2deg); }
      40% { opacity: 0.6; transform: translateX(-2px) skewX(1deg); }
      60% { opacity: 0.8; transform: translateX(1px); filter: hue-rotate(0deg); }
      100% { opacity: 1; transform: none; filter: none; }
    }
    .glitch-in {
      animation: glitch-in 0.5s var(--ds-ease-out) both;
    }

    @keyframes border-flow {
      0% { background-position: 0% 50%; }
      100% { background-position: 200% 50%; }
    }
    @keyframes scan-sweep {
      0%, 100% { top: 0; opacity: 0; }
      10% { opacity: 1; }
      90% { opacity: 1; }
      50% { top: 100%; }
    }
    @keyframes dot-breathe {
      0%, 100% { opacity: 0.6; transform: scale(1); }
      50% { opacity: 1; transform: scale(1.2); }
    }
    @keyframes pulse-expand {
      0% { inset: 0; opacity: 0.5; }
      100% { inset: -12px; opacity: 0; border-width: 0.5px; }
    }
  `;

  updated(changed: Map<string, unknown>): void {
    if (changed.has("pulseOnUpdate") && this.pulseOnUpdate > 0) {
      this._version++;
      const ring = this.renderRoot.querySelector(".pulse-ring") as HTMLElement | null;
      if (ring) {
        ring.classList.remove("active");
        void ring.offsetWidth; // force reflow
        ring.classList.add("active");
      }
    }
  }

  private _rgbForAccent(): string {
    switch (this.accent) {
      case "violet": return "155, 140, 255"; // --ds-iris
      case "green": return "0, 255, 209";    // --ds-neon-green
      case "amber": return "255, 193, 7";    // --ds-warning-ish
      case "red": return "239, 68, 68";      // --ds-danger
      default: return "0, 229, 255";         // --ds-accent cyan
    }
  }

  render() {
    const rgb = this._rgbForAccent();
    return html`
      <style>
        :host { --glow-rgb: ${rgb}; }
      </style>
      <div class="panel ${this.glitchEntry ? "glitch-in" : ""}">
        <span class="corner tl"></span>
        <span class="corner tr"></span>
        <span class="corner bl"></span>
        <span class="corner br"></span>
        ${this.scanLine ? html`<div class="scan-line"></div>` : ""}
        <div class="pulse-ring" data-v="${this._version}"></div>
        ${this.title ? html`
          <div class="title-bar">
            <span class="title-dot"></span>
            <span class="title-text">${this.title}</span>
          </div>
        ` : ""}
        <slot></slot>
      </div>
    `;
  }
}
