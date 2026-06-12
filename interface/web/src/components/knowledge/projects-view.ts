// <projects-view> — what Aryan is working on, from DEEP's world model
// (/api/world): projects, current focus, priorities, interests, key people.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

interface World {
  summary: string; projects: string[]; people: string[];
  priorities: string[]; interests: string[]; current_focus?: string;
}

@customElement("projects-view")
export class ProjectsView extends LitElement {
  @state() private world: World | null = null;
  @state() private refreshing = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }
  private async load(): Promise<void> {
    try { this.world = await (await fetch("/api/world")).json(); } catch { /* */ }
  }
  private async refresh(): Promise<void> {
    this.refreshing = true;
    try { await fetch("/api/world/refresh", { method: "POST" }); await this.load(); toast("World model refreshed", "success"); }
    catch { toast("Refresh failed", "danger"); }
    this.refreshing = false;
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .summary { font-size: var(--ds-text-lg); line-height: var(--ds-leading-normal); color: var(--ds-text-soft); }
    .focus { padding: var(--ds-space-4); background: linear-gradient(135deg, rgba(var(--ds-periwinkle-rgb),0.12), transparent); border: 1px solid var(--ds-border-accent); border-radius: var(--ds-radius-md); }
    .focus .k { font-size: var(--ds-text-xs); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); color: var(--ds-accent); }
    .focus .v { font-size: var(--ds-text-lg); margin-top: 4px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--ds-space-3); }
    .card { padding: var(--ds-space-4); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-left: 2px solid var(--ds-accent); border-radius: var(--ds-radius-md); font-weight: 600; }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-2); }
    .tag { padding: 3px 12px; border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .list { display: grid; gap: var(--ds-space-2); }
    .item { display: flex; gap: var(--ds-space-2); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .item::before { content: "▸"; color: var(--ds-accent); }
    .muted { color: var(--ds-text-muted); }
  `;

  render() {
    const w = this.world;
    if (!w) return html`<ds-panel heading="Projects"><span class="muted">loading world model…</span></ds-panel>`;
    return html`
      <ds-panel heading="What Aryan is building">
        <p class="summary">${w.summary}</p>
        <div slot="actions"><ds-button size="sm" @click=${() => void this.refresh()}>${this.refreshing ? "…" : "refresh"}</ds-button></div>
      </ds-panel>

      ${w.current_focus ? html`<div class="focus"><div class="k">current focus</div><div class="v">${w.current_focus}</div></div>` : ""}

      <ds-panel heading="Projects · ${w.projects.length}">
        <div class="cards">${w.projects.map((p) => html`<div class="card">${p}</div>`)}</div>
      </ds-panel>

      <ds-panel heading="Priorities">
        <div class="list">${w.priorities.map((p) => html`<div class="item">${p}</div>`)}</div>
      </ds-panel>

      <ds-panel heading="Interests">
        <div class="tags">${w.interests.map((i) => html`<span class="tag">${i}</span>`)}</div>
      </ds-panel>
    `;
  }
}
