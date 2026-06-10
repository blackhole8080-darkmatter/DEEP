// <command-palette> — ⌘K overlay. Fuzzy-matches the command registry,
// keyboard-first (↑↓ navigate, Enter run, Esc close).
import { LitElement, html, css } from "lit";
import { customElement, state, query } from "lit/decorators.js";
import { matchCommands, type Command } from "../core/commands";

@customElement("command-palette")
export class CommandPalette extends LitElement {
  @state() private open = false;
  @state() private q = "";
  @state() private sel = 0;
  @query("input") private input!: HTMLInputElement;

  show(): void {
    this.open = true;
    this.q = "";
    this.sel = 0;
    requestAnimationFrame(() => this.input?.focus());
  }
  hide(): void { this.open = false; }
  toggle(): void { this.open ? this.hide() : this.show(); }

  static styles = css`
    .scrim {
      position: fixed; inset: 0;
      background: var(--ds-scrim);
      z-index: var(--ds-z-palette);
      display: grid;
      place-items: start center;
      padding-top: 14vh;
      animation: fade var(--ds-dur-fast) var(--ds-ease-out);
    }
    .box {
      width: min(560px, 92vw);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-lg));
      backdrop-filter: blur(var(--ds-blur-lg));
      border: 1px solid var(--ds-border-strong);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-4);
      overflow: hidden;
      animation: pop var(--ds-dur-base) var(--ds-ease-spring);
    }
    input {
      width: 100%;
      padding: var(--ds-space-4);
      border: 0; outline: 0; background: none;
      color: var(--ds-text);
      font-family: var(--ds-font-sans);
      font-size: var(--ds-text-base);
      border-bottom: 1px solid var(--ds-border);
    }
    input::placeholder { color: var(--ds-text-faint); }
    ul { list-style: none; margin: 0; padding: var(--ds-space-2); max-height: 320px; overflow-y: auto; }
    li {
      display: flex; align-items: center; justify-content: space-between;
      padding: var(--ds-space-2) var(--ds-space-3);
      border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-sm);
      cursor: pointer;
      color: var(--ds-text-soft);
    }
    li.sel { background: rgba(var(--ds-periwinkle-rgb), 0.14); color: var(--ds-text); }
    li .hint {
      font-family: var(--ds-font-mono);
      font-size: 0.62rem;
      color: var(--ds-text-faint);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
    }
    .none { padding: var(--ds-space-4); color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    @keyframes fade { from { opacity: 0; } }
    @keyframes pop { from { opacity: 0; transform: translateY(-8px) scale(0.98); } }
  `;

  private results(): Command[] { return matchCommands(this.q); }

  private run(c: Command): void {
    this.hide();
    void c.run();
  }

  private onKey(e: KeyboardEvent): void {
    const res = this.results();
    if (e.key === "Escape") this.hide();
    else if (e.key === "ArrowDown") { e.preventDefault(); this.sel = Math.min(this.sel + 1, res.length - 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); this.sel = Math.max(this.sel - 1, 0); }
    else if (e.key === "Enter" && res[this.sel]) this.run(res[this.sel]);
  }

  render() {
    if (!this.open) return html``;
    const res = this.results();
    return html`
      <div class="scrim" @click=${(e: Event) => { if (e.target === e.currentTarget) this.hide(); }}>
        <div class="box">
          <input
            placeholder="Type a command…"
            .value=${this.q}
            @input=${(e: Event) => { this.q = (e.target as HTMLInputElement).value; this.sel = 0; }}
            @keydown=${this.onKey}
          />
          ${res.length
            ? html`<ul>
                ${res.map(
                  (c, i) => html`
                    <li class=${i === this.sel ? "sel" : ""}
                        @mouseenter=${() => (this.sel = i)}
                        @click=${() => this.run(c)}>
                      <span>${c.label}</span>
                      ${c.hint ? html`<span class="hint">${c.hint}</span>` : ""}
                    </li>
                  `,
                )}
              </ul>`
            : html`<div class="none">No matching commands.</div>`}
        </div>
      </div>
    `;
  }
}
