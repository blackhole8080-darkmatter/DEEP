// <missions-view> — DEEP long-running mission control
// Create, monitor, and manage autonomous background missions.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { fetchMissions, createMission, cancelMission, type Mission } from "../../core/api";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

@customElement("missions-view")
export class MissionsView extends SignalWatcher(LitElement) {
  @state() private missions: Mission[] = [];
  @state() private filter = "all";
  @state() private loading = true;
  @state() private showCreate = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      const status = this.filter === "all" ? undefined : this.filter;
      this.missions = (await fetchMissions(status, 30)).missions;
    } catch {
      toast("Failed to load missions", "danger");
    }
    this.loading = false;
  }

  private async onCreate(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    const fd = new FormData(e.target as HTMLFormElement);
    const goal = String(fd.get("goal") || "");
    if (!goal) return;
    try {
      const r = await createMission(goal);
      if ("mission_id" in r && r.mission_id) {
        toast(`Mission ${r.mission_id} created`, "success");
        this.showCreate = false;
        void this.load();
      } else if ("error" in r) {
        toast(r.error, "danger");
      } else {
        toast("Create failed", "danger");
      }
    } catch {
      toast("Create failed", "danger");
    }
  }

  private async onCancel(id: string): Promise<void> {
    try {
      await cancelMission(id);
      toast("Mission cancelled", "info");
      void this.load();
    } catch {
      toast("Cancel failed", "danger");
    }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    .filters { display: flex; gap: var(--ds-space-2); }
    .filters button { padding: var(--ds-space-1) var(--ds-space-3); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); background: none; color: var(--ds-text-muted); font-size: var(--ds-text-sm); cursor: pointer; transition: all var(--ds-dur-fast); }
    .filters button.on { background: var(--ds-accent); color: var(--ds-on-accent); border-color: var(--ds-accent); }
    .mission { display: grid; gap: var(--ds-space-2); padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .mission .head { display: flex; justify-content: space-between; align-items: center; }
    .mission .goal { font-weight: 600; }
    .mission .meta { font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .bar-wrap { display: flex; align-items: center; gap: var(--ds-space-2); }
    .bar { flex: 1; height: 6px; background: var(--ds-surface-2); border-radius: var(--ds-radius-pill); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: var(--ds-radius-pill); background: var(--ds-accent); transition: width var(--ds-dur-base); }
    .status { display: inline-block; padding: 2px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; text-transform: uppercase; }
    .status.running { background: rgba(var(--ds-success-rgb), 0.15); color: var(--ds-success); }
    .status.pending { background: rgba(var(--ds-warning-rgb), 0.15); color: var(--ds-warning); }
    .status.completed { background: rgba(var(--ds-accent-rgb), 0.15); color: var(--ds-accent); }
    .status.failed, .status.cancelled { background: rgba(var(--ds-danger-rgb), 0.15); color: var(--ds-danger); }
    .form { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .form textarea { padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); min-height: 80px; resize: vertical; }
  `;

  render() {
    const filters = ["all", "running", "pending", "completed", "failed"];
    const filtered = this.filter === "all" ? this.missions : this.missions.filter((m) => m.status === this.filter);

    return html`
      <ds-panel heading="Missions">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${() => (this.showCreate = !this.showCreate)}>${this.showCreate ? "cancel" : "+ mission"}</ds-button>
          <ds-button size="sm" @click=${() => void this.load()}>refresh</ds-button>
        </div>
      </ds-panel>

      ${this.showCreate ? html`
        <form class="form" @submit=${this.onCreate}>
          <textarea name="goal" placeholder="Describe the mission — e.g. 'Research quantum AI breakthroughs in 2026 and write a 1-page summary'" required></textarea>
          <ds-button variant="primary" type="submit">Launch Mission</ds-button>
        </form>
      ` : ""}

      <div class="filters">
        ${filters.map((f) => html`
          <button class="${this.filter === f ? "on" : ""}" @click=${() => { this.filter = f; void this.load(); }}>${f}</button>
        `)}
      </div>

      ${this.loading ? html`<div class="muted">Loading…</div>` : html`
        ${filtered.length === 0 ? html`<div class="muted">No ${this.filter === "all" ? "" : this.filter} missions.</div>` : html`
          ${filtered.map((m) => html`
            <div class="mission">
              <div class="head">
                <div>
                  <div class="goal">${m.goal}</div>
                  <div class="meta">${m.id} · ${new Date(m.created_at).toLocaleString()}</div>
                </div>
                <div style="display:flex;gap:var(--ds-space-2);align-items:center;">
                  <span class="status ${m.status}">${m.status}</span>
                  ${m.status === "running" || m.status === "pending" ? html`
                    <ds-button size="sm" @click=${() => void this.onCancel(m.id)}>cancel</ds-button>
                  ` : ""}
                </div>
              </div>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill" style="width:${m.progress_pct}%"></div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);min-width:32px;text-align:right;">${m.progress_pct.toFixed(0)}%</span>
              </div>
              ${m.error ? html`<div style="font-size:var(--ds-text-xs);color:var(--ds-danger);">${m.error}</div>` : ""}
            </div>
          `)}
        `}
      `}
    `;
  }
}
