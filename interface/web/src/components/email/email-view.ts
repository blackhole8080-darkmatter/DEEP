// <email-view> — DEEP email intelligence dashboard
// Inbox summary, search, follow-up tracking, quick compose.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import {
  fetchEmailInbox, fetchEmailSearch, fetchEmailAwaiting, sendEmail,
  type EmailMsg, type TrackedThread,
} from "../../core/api";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

@customElement("email-view")
export class EmailView extends SignalWatcher(LitElement) {
  @state() private inbox: { unread_count: number; recent: EmailMsg[]; verbal: string } | null = null;
  @state() private awaiting: TrackedThread[] = [];
  @state() private searchQuery = "";
  @state() private searchResults: EmailMsg[] = [];
  @state() private loading = true;
  @state() private showCompose = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      const inboxRes = await fetchEmailInbox(15);
      if (inboxRes.ok) {
        this.inbox = { unread_count: inboxRes.unread_count, recent: inboxRes.recent, verbal: inboxRes.verbal };
      } else {
        this.inbox = { unread_count: 0, recent: [], verbal: inboxRes.verbal };
      }
      this.awaiting = (await fetchEmailAwaiting()).threads;
    } catch (e) {
      toast("Email load failed", "danger");
      this.inbox = { unread_count: 0, recent: [], verbal: "Email not configured." };
    }
    this.loading = false;
  }

  private async doSearch(): Promise<void> {
    if (!this.searchQuery.trim()) return;
    try {
      const r = await fetchEmailSearch(this.searchQuery, 10);
      this.searchResults = r.ok ? r.results : [];
    } catch {
      toast("Search failed", "danger");
    }
  }

  private async onSend(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const r = await sendEmail({
        to: String(fd.get("to") || ""),
        subject: String(fd.get("subject") || ""),
        body: String(fd.get("body") || ""),
      });
      if (r.ok) {
        toast("Sent", "success");
        this.showCompose = false;
      } else {
        toast(r.verbal || "Send failed", "danger");
      }
    } catch {
      toast("Send failed", "danger");
    }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--ds-space-3); }
    .search { display: flex; gap: var(--ds-space-2); }
    .search input { flex: 1; padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); color: var(--ds-text); }
    .msg { display: flex; justify-content: space-between; align-items: flex-start; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); gap: var(--ds-space-3); }
    .msg:last-child { border-bottom: 0; }
    .msg .from { font-weight: 500; font-size: var(--ds-text-sm); }
    .msg .subj { font-size: var(--ds-text-xs); color: var(--ds-text-soft); }
    .msg .unread { width: 6px; height: 6px; border-radius: 50%; background: var(--ds-accent); flex-shrink: 0; margin-top: 6px; }
    .form { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .form input, .form textarea { padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); font-family: inherit; }
    .form textarea { min-height: 120px; resize: vertical; }
  `;

  render() {
    if (this.loading) return html`<div class="muted">Loading email…</div>`;
    const inbox = this.inbox;
    return html`
      <ds-panel heading="Email">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${() => (this.showCompose = !this.showCompose)}>${this.showCompose ? "cancel" : "compose"}</ds-button>
          <ds-button size="sm" @click=${() => void this.load()}>refresh</ds-button>
        </div>
        ${inbox ? html`<p class="muted" style="margin:0;">${inbox.verbal}</p>` : ""}
      </ds-panel>

      ${this.showCompose ? html`
        <form class="form" @submit=${this.onSend}>
          <input type="email" name="to" placeholder="To" required />
          <input type="text" name="subject" placeholder="Subject" required />
          <textarea name="body" placeholder="Message…" required></textarea>
          <ds-button variant="primary" type="submit">Send</ds-button>
        </form>
      ` : ""}

      <div class="search">
        <input type="text" placeholder="Search emails…" .value=${this.searchQuery} @input=${(e: InputEvent) => { this.searchQuery = (e.target as HTMLInputElement).value; }} @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") void this.doSearch(); }} />
        <ds-button @click=${() => void this.doSearch()}>Search</ds-button>
      </div>

      ${this.searchResults.length > 0 ? html`
        <ds-panel heading="Search Results · ${this.searchResults.length}">
          ${this.searchResults.map((m) => html`
            <div class="msg">
              <div><div class="from">${m.sender}</div><div class="subj">${m.subject}</div></div>
              <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);white-space:nowrap;">${m.date}</span>
            </div>
          `)}
        </ds-panel>
      ` : ""}

      <div class="grid">
        <ds-panel heading="Inbox · ${inbox?.unread_count ?? 0} unread">
          ${inbox && inbox.recent.length ? html`
            ${inbox.recent.map((m) => html`
              <div class="msg">
                ${m.unread ? html`<div class="unread"></div>` : html`<div style="width:6px;"></div>`}
                <div style="flex:1;"><div class="from">${m.sender}</div><div class="subj">${m.subject}</div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);white-space:nowrap;">${m.date}</span>
              </div>
            `)}
          ` : html`<span class="muted">No recent messages.</span>`}
        </ds-panel>
        <ds-panel heading="Awaiting Replies · ${this.awaiting.length}">
          ${this.awaiting.length ? html`
            ${this.awaiting.map((t) => html`
              <div class="msg">
                <div style="flex:1;"><div class="from">${t.sender}</div><div class="subj">${t.subject}</div></div>
                ${t.notes ? html`<span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);">${t.notes}</span>` : ""}
              </div>
            `)}
          ` : html`<span class="muted">Nothing flagged for follow-up.</span>`}
        </ds-panel>
      </div>
    `;
  }
}
