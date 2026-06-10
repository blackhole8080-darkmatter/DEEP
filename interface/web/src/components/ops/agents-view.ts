// <agents-view> — launch sub-agent missions and watch the live task board.
// Polls /api/agents/tasks while visible.
import { LitElement, html, css } from "lit";
import { customElement, state, query } from "lit/decorators.js";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

interface AgentTask {
  id: string;
  role?: string;
  task?: string;
  status?: string;
  progress?: string | number;
  result?: string;
  [k: string]: unknown;
}

const ROLES = ["researcher", "writer", "planner", "analyst", "coder"];

@customElement("agents-view")
export class AgentsView extends LitElement {
  @state() private tasks: AgentTask[] = [];
  @state() private role = "planner";
  @query("textarea") private ta!: HTMLTextAreaElement;
  private timer?: ReturnType<typeof setInterval>;

  connectedCallback(): void {
    super.connectedCallback();
    void this.poll();
    this.timer = setInterval(() => void this.poll(), 4000);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.timer);
  }

  private async poll(): Promise<void> {
    try {
      const d = await (await fetch("/api/agents/tasks")).json();
      this.tasks = d.tasks ?? [];
    } catch { /* server transient */ }
  }

  private async launch(): Promise<void> {
    const task = this.ta.value.trim();
    if (!task) return;
    try {
      const r = await fetch("/api/agents/task", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ role: this.role, task }),
      });
      const d = await r.json();
      if (r.ok) { toast(`Agent launched (${this.role})`, "success"); this.ta.value = ""; void this.poll(); }
      else toast(`Launch failed: ${d.detail ?? r.status}`, "danger");
    } catch { toast("Launch failed", "danger"); }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 860px; margin: 0 auto; align-content: start; }
    .launch { display: grid; gap: var(--ds-space-3); }
    textarea {
      width: 100%; min-height: 64px; resize: vertical;
      background: var(--ds-surface-2); color: var(--ds-text);
      border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      padding: var(--ds-space-3); font-family: var(--ds-font-sans); font-size: var(--ds-text-sm);
    }
    textarea:focus { outline: none; border-color: var(--ds-border-accent); }
    .roles { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; align-items: center; }
    .chip {
      padding: 3px 12px; border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border); background: none;
      color: var(--ds-text-soft); font-size: var(--ds-text-xs); cursor: pointer;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .chip.on { background: rgba(var(--ds-periwinkle-rgb), 0.16); border-color: var(--ds-border-accent); color: var(--ds-text); }
    .task {
      display: grid; gap: 4px;
      padding: var(--ds-space-3) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .task:last-child { border-bottom: none; }
    .head { display: flex; justify-content: space-between; gap: var(--ds-space-3); }
    .status { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .status.running { color: var(--ds-info); }
    .status.done, .status.completed { color: var(--ds-success); }
    .status.failed, .status.error { color: var(--ds-danger); }
    .desc { color: var(--ds-text-soft); }
    .result { color: var(--ds-text-muted); font-size: var(--ds-text-xs); white-space: pre-wrap; max-height: 120px; overflow-y: auto; }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;

  render() {
    return html`
      <ds-panel heading="Launch agent mission">
        <div class="launch">
          <div class="roles">
            ${ROLES.map(
              (r) => html`
                <button class="chip ${this.role === r ? "on" : ""}" @click=${() => (this.role = r)}>${r}</button>
              `,
            )}
          </div>
          <textarea placeholder="Describe the mission… e.g. 'Plan a study schedule for my exams next month'"></textarea>
          <ds-button variant="primary" @click=${() => void this.launch()}>Launch</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Task board · ${this.tasks.length} task${this.tasks.length === 1 ? "" : "s"}">
        ${this.tasks.length
          ? this.tasks.map(
              (t) => html`
                <div class="task">
                  <div class="head">
                    <b>${t.role ?? "agent"}</b>
                    <span class="status ${String(t.status ?? "").toLowerCase()}">${t.status ?? "?"}${t.progress != null ? ` · ${t.progress}` : ""}</span>
                  </div>
                  <span class="desc">${t.task ?? ""}</span>
                  ${t.result ? html`<div class="result">${String(t.result).slice(0, 600)}</div>` : ""}
                </div>
              `,
            )
          : html`<span class="muted">No agent tasks yet. Launch one above — it runs in the background on the live system.</span>`}
      </ds-panel>
    `;
  }
}
