// <ops-terminal> — the operations-center command line.
//
// A real terminal surface over /api/intel/terminal: history (↑/↓), tab
// completion from the server-declared command catalog, inline usage hints, and
// monospaced structured output. Every command is read-only; the backend refuses
// anything it doesn't recognise rather than passing it anywhere.
import { LitElement, html, css, nothing } from "lit";
import { customElement, state, query } from "lit/decorators.js";

interface CommandSpec {
  name: string;
  summary: string;
  usage: string;
  group: string;
  examples: string[];
}

interface ExecResult {
  ok: boolean;
  command: string;
  text: string;
  rows: Record<string, unknown>[];
  data: Record<string, unknown>;
  error: string;
  elapsed_ms: number;
}

interface Line {
  kind: "input" | "output" | "error" | "system";
  text: string;
  elapsed?: number;
}

const BANNER = `DEEP OPERATIONS TERMINAL
Read-only intelligence console. 'help' lists commands, Tab completes, ↑/↓ recalls.`;

@customElement("ops-terminal")
export class OpsTerminal extends LitElement {
  @state() private lines: Line[] = [{ kind: "system", text: BANNER }];
  @state() private draft = "";
  @state() private busy = false;
  @state() private commands: CommandSpec[] = [];
  @state() private suggestions: CommandSpec[] = [];

  private history: string[] = [];
  private historyIndex = -1;

  @query(".scroll") private scroller?: HTMLElement;
  @query("input") private input?: HTMLInputElement;

  static styles = css`
    :host {
      display: block;
      height: 100%;
      font-family: var(--ds-font-mono, ui-monospace, "SFMono-Regular", Menlo, monospace);
      font-size: 0.8rem;
      color: rgba(200, 230, 245, 0.9);
    }
    .wrap { display: flex; flex-direction: column; height: 100%; min-height: 0; }

    .scroll {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overflow-x: auto;
      padding: 12px 14px;
      line-height: 1.45;
      scrollbar-width: thin;
    }
    .scroll::-webkit-scrollbar { width: 8px; height: 8px; }
    .scroll::-webkit-scrollbar-thumb {
      background: rgba(120, 200, 230, 0.22); border-radius: 4px;
    }

    pre {
      margin: 0 0 10px;
      white-space: pre;
      font: inherit;
    }
    pre.input { color: rgba(150, 240, 200, 0.95); }
    pre.input::before { content: "❯ "; opacity: 0.6; }
    pre.output { color: rgba(200, 230, 245, 0.88); }
    pre.error { color: rgba(255, 150, 150, 0.95); }
    pre.system { color: rgba(140, 200, 230, 0.6); }

    .elapsed {
      display: block;
      margin-top: 2px;
      font-size: 0.68rem;
      opacity: 0.4;
    }

    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 6px 14px 0;
    }
    .chip {
      border: 1px solid rgba(120, 200, 230, 0.25);
      background: rgba(120, 200, 230, 0.07);
      border-radius: 3px;
      padding: 2px 7px;
      font-size: 0.7rem;
      cursor: pointer;
      color: inherit;
      font-family: inherit;
    }
    .chip:hover { background: rgba(120, 200, 230, 0.2); }
    .chip .hint { opacity: 0.5; margin-left: 6px; }

    .prompt {
      display: flex;
      align-items: center;
      gap: 8px;
      border-top: 1px solid rgba(120, 200, 230, 0.16);
      padding: 9px 14px;
    }
    .sigil { color: rgba(150, 240, 200, 0.8); }
    input {
      flex: 1;
      background: transparent;
      border: 0;
      outline: none;
      color: inherit;
      font: inherit;
      caret-color: rgba(150, 240, 200, 0.9);
    }
    input::placeholder { color: rgba(200, 230, 245, 0.32); }
    .spinner { opacity: 0.6; animation: blink 1s steps(2) infinite; }
    @keyframes blink { 50% { opacity: 0.15; } }
    @media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadCommands();
  }

  private async loadCommands(): Promise<void> {
    try {
      const r = await fetch("/api/intel/terminal/commands");
      if (!r.ok) throw new Error(`${r.status}`);
      const body = (await r.json()) as { commands: CommandSpec[] };
      this.commands = body.commands ?? [];
    } catch {
      this.pushLine({
        kind: "error",
        text: "Could not load the command catalog. Tab completion is unavailable; commands still run.",
      });
    }
  }

  private pushLine(line: Line): void {
    this.lines = [...this.lines, line];
    // Wait for the new line to render before pinning to the bottom.
    void this.updateComplete.then(() => {
      if (this.scroller) this.scroller.scrollTop = this.scroller.scrollHeight;
    });
  }

  private async run(raw: string): Promise<void> {
    const line = raw.trim();
    if (!line) return;

    this.pushLine({ kind: "input", text: line });
    this.history = [line, ...this.history.filter((h) => h !== line)].slice(0, 100);
    this.historyIndex = -1;
    this.draft = "";
    this.suggestions = [];

    if (line === "clear") {
      this.lines = [];
      return;
    }

    this.busy = true;
    try {
      const r = await fetch("/api/intel/terminal/exec", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line }),
      });
      if (!r.ok) {
        this.pushLine({ kind: "error", text: `Request failed: HTTP ${r.status}` });
        return;
      }
      const result = (await r.json()) as ExecResult;
      if (result.data?.action === "clear") {
        this.lines = [];
        return;
      }
      if (!result.ok) {
        this.pushLine({ kind: "error", text: result.error || "command failed" });
        if (result.text) this.pushLine({ kind: "output", text: result.text });
        return;
      }
      this.pushLine({ kind: "output", text: result.text || "(no output)", elapsed: result.elapsed_ms });
    } catch (err) {
      this.pushLine({ kind: "error", text: `Network error: ${(err as Error).message}` });
    } finally {
      this.busy = false;
      void this.updateComplete.then(() => this.input?.focus());
    }
  }

  private onInput(e: Event): void {
    this.draft = (e.target as HTMLInputElement).value;
    const head = this.draft.trimStart();
    // Only suggest while typing the verb itself, not its arguments.
    this.suggestions =
      head && !head.includes(" ")
        ? this.commands.filter((c) => c.name.startsWith(head.toLowerCase())).slice(0, 8)
        : [];
  }

  private onKey(e: KeyboardEvent): void {
    if (e.key === "Enter") {
      e.preventDefault();
      if (!this.busy) void this.run(this.draft);
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      const [first] = this.suggestions;
      if (first) {
        this.draft = `${first.name} `;
        this.suggestions = [];
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (this.historyIndex + 1 < this.history.length) {
        this.historyIndex += 1;
        this.draft = this.history[this.historyIndex];
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (this.historyIndex > 0) {
        this.historyIndex -= 1;
        this.draft = this.history[this.historyIndex];
      } else {
        this.historyIndex = -1;
        this.draft = "";
      }
    }
  }

  render() {
    return html`
      <div class="wrap" @click=${() => this.input?.focus()}>
        <div class="scroll">
          ${this.lines.map(
            (l) => html`
              <pre class=${l.kind}>${l.text}${l.elapsed !== undefined
                ? html`<span class="elapsed">${l.elapsed} ms</span>`
                : nothing}</pre>
            `,
          )}
        </div>

        ${this.suggestions.length
          ? html`
              <div class="suggestions">
                ${this.suggestions.map(
                  (s) => html`
                    <button
                      class="chip"
                      @click=${() => {
                        this.draft = `${s.name} `;
                        this.suggestions = [];
                        this.input?.focus();
                      }}
                    >
                      ${s.name}<span class="hint">${s.summary}</span>
                    </button>
                  `,
                )}
              </div>
            `
          : nothing}

        <div class="prompt">
          <span class="sigil">❯</span>
          <input
            .value=${this.draft}
            ?disabled=${this.busy}
            placeholder=${this.busy ? "working…" : "investigate 1.1.1.1   ·   kev   ·   help"}
            autocomplete="off"
            spellcheck="false"
            @input=${this.onInput}
            @keydown=${this.onKey}
          />
          ${this.busy ? html`<span class="spinner">▊</span>` : nothing}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "ops-terminal": OpsTerminal;
  }
}
