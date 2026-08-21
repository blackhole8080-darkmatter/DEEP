// <approvals-view> — the human-in-the-loop queue: actions DEEP has parked
// rather than taken on its own, each with Approve and Reject.
//
// The gate this renders is only as good as the decision it presents, so the
// card leads with what will actually happen — the exact URL, the exact
// visibility — and shows the consequence text underneath rather than a bare
// "confirm?". A user approving a urlscan submission should be able to see, in
// the panel, that it publishes permanently and tells the site owner.
//
// Two things this deliberately does not do:
//   * It never pre-selects or highlights Approve. The panel exists to make a
//     no as easy as a yes, and a styled-up primary button is a thumb on the
//     scale for an action the user may not want.
//   * It never removes a card optimistically. Approving runs a real tool that
//     can fail; the card stays, showing the outcome, until the user dismisses
//     it. Vanishing on click would report success DEEP has not had yet.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import { pendingApprovals, refreshApprovals } from "../../core/store";
import { approveAction, rejectAction, type PendingAction } from "../../core/api";
import "../primitives/ds-panel";

interface Outcome {
  kind: "approved" | "rejected" | "failed";
  text: string;
}

@customElement("approvals-view")
export class ApprovalsView extends SignalWatcher(LitElement) {
  /** Cards whose decision has been made, keyed by action id, kept until dismissed. */
  @state() private outcomes: Record<string, Outcome> = {};
  /** Ids with a request in flight, so a double-click cannot double-submit. */
  @state() private busy = new Set<string>();
  private ticker?: ReturnType<typeof setInterval>;

  connectedCallback(): void {
    super.connectedCallback();
    void refreshApprovals();
    // Only to re-render the countdowns; the list itself arrives over the
    // socket and the store's own slower poll.
    this.ticker = setInterval(() => this.requestUpdate(), 1000);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.ticker);
  }

  private setBusy(id: string, on: boolean): void {
    const next = new Set(this.busy);
    if (on) next.add(id);
    else next.delete(id);
    this.busy = next;
  }

  private async approve(a: PendingAction): Promise<void> {
    this.setBusy(a.id, true);
    try {
      const out = await approveAction(a.id);
      this.outcomes = {
        ...this.outcomes,
        [a.id]: out.ok
          ? { kind: "approved", text: out.result || "Done." }
          : { kind: "failed", text: out.result || "The tool reported a failure." },
      };
    } catch (e) {
      // Most often a 404: the action expired while the panel was open. Say so
      // rather than leaving a card that looks actionable but is not.
      this.outcomes = {
        ...this.outcomes,
        [a.id]: { kind: "failed", text: (e as Error).message },
      };
    } finally {
      this.setBusy(a.id, false);
      void refreshApprovals();
    }
  }

  private async reject(a: PendingAction): Promise<void> {
    this.setBusy(a.id, true);
    try {
      await rejectAction(a.id);
      this.outcomes = { ...this.outcomes, [a.id]: { kind: "rejected", text: "Declined. Nothing ran." } };
    } catch (e) {
      this.outcomes = { ...this.outcomes, [a.id]: { kind: "failed", text: (e as Error).message } };
    } finally {
      this.setBusy(a.id, false);
      void refreshApprovals();
    }
  }

  private dismiss(id: string): void {
    const next = { ...this.outcomes };
    delete next[id];
    this.outcomes = next;
  }

  private static countdown(seconds: number): string {
    if (seconds <= 0) return "expired";
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
  }

  static styles = css`
    :host {
      display: grid; gap: var(--ds-space-4);
      padding: var(--ds-space-5); max-width: 860px; margin: 0 auto;
      align-content: start;
    }
    .lede { font-size: var(--ds-text-sm); color: var(--ds-text-muted); line-height: 1.5; }
    .empty {
      display: grid; gap: var(--ds-space-2); justify-items: center;
      padding: var(--ds-space-6) var(--ds-space-4);
      color: var(--ds-text-muted); text-align: center;
    }
    .empty .glyph { font-size: var(--ds-text-xl); opacity: 0.6; }

    .card { display: grid; gap: var(--ds-space-3); }
    .label { font-size: var(--ds-text-md); font-weight: 600; color: var(--ds-text); line-height: 1.4; word-break: break-word; }
    .detail {
      font-size: var(--ds-text-sm); line-height: 1.55; color: var(--ds-text-soft);
      padding: var(--ds-space-3);
      border-left: 2px solid var(--ds-warning);
      background: rgba(255, 176, 32, 0.06);
      border-radius: 0 var(--ds-radius-sm) var(--ds-radius-sm) 0;
    }
    .args {
      display: grid; gap: 2px;
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-soft);
    }
    .arg { display: grid; grid-template-columns: 96px 1fr; gap: var(--ds-space-2); }
    .arg .k { color: var(--ds-text-muted); }
    .arg .v { word-break: break-all; }

    .meta {
      display: flex; flex-wrap: wrap; align-items: center; gap: var(--ds-space-3);
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
    }
    .soon { color: var(--ds-warning); }

    .actions { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    button {
      font: inherit; font-size: var(--ds-text-sm); font-weight: 600;
      padding: var(--ds-space-2) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-2);
      color: var(--ds-text);
      cursor: pointer;
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    button:hover:not(:disabled) { border-color: var(--ds-border-strong); background: var(--ds-surface-3, var(--ds-surface-2)); }
    button:disabled { opacity: 0.5; cursor: default; }
    button:focus-visible { outline: 2px solid var(--ds-accent); outline-offset: 2px; }
    /* Approve and Reject are weighted the same on purpose — see the header. */
    .approve:hover:not(:disabled) { border-color: var(--ds-success); color: var(--ds-success); }
    .reject:hover:not(:disabled)  { border-color: var(--ds-danger);  color: var(--ds-danger); }

    .outcome {
      display: grid; gap: var(--ds-space-2);
      padding: var(--ds-space-3);
      border-radius: var(--ds-radius-md);
      font-size: var(--ds-text-sm);
      border: 1px solid var(--ds-border);
    }
    .outcome pre {
      margin: 0; white-space: pre-wrap; word-break: break-word;
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-soft);
    }
    .outcome.approved { border-color: var(--ds-success); background: rgba(0,255,174,0.06); }
    .outcome.rejected { border-color: var(--ds-border-strong); }
    .outcome.failed   { border-color: var(--ds-danger);  background: rgba(255,45,120,0.06); }
    .outcome .head { font-weight: 600; }
    .outcome.approved .head { color: var(--ds-success); }
    .outcome.failed .head    { color: var(--ds-danger); }
    .outcome .dismiss { justify-self: start; }
  `;

  private renderCard(a: PendingAction) {
    const outcome = this.outcomes[a.id];
    const busy = this.busy.has(a.id);
    const expired = a.expires_in_s <= 0;

    return html`
      <ds-panel heading=${a.tool}>
        <div class="card">
          <div class="label">${a.label}</div>
          ${a.detail ? html`<div class="detail">${a.detail}</div>` : ""}

          <div class="args">
            ${Object.entries(a.args).map(
              ([k, v]) => html`<div class="arg"><span class="k">${k}</span><span class="v">${String(v)}</span></div>`,
            )}
          </div>

          ${outcome
            ? html`
                <div class="outcome ${outcome.kind}">
                  <span class="head">
                    ${outcome.kind === "approved" ? "Approved and run" : ""}
                    ${outcome.kind === "rejected" ? "Rejected" : ""}
                    ${outcome.kind === "failed" ? "Did not run" : ""}
                  </span>
                  <pre>${outcome.text}</pre>
                  <button class="dismiss" @click=${() => this.dismiss(a.id)}>Dismiss</button>
                </div>
              `
            : html`
                <div class="meta">
                  <span class=${a.expires_in_s < 120 ? "soon" : ""}>
                    ${expired ? "expired — ask DEEP again" : `expires in ${ApprovalsView.countdown(a.expires_in_s)}`}
                  </span>
                </div>
                <div class="actions">
                  <button class="approve" ?disabled=${busy || expired} @click=${() => this.approve(a)}>
                    ${busy ? "Working…" : "Approve"}
                  </button>
                  <button class="reject" ?disabled=${busy} @click=${() => this.reject(a)}>Reject</button>
                </div>
              `}
        </div>
      </ds-panel>
    `;
  }

  render() {
    const pending = pendingApprovals.get();
    // A resolved card outlives its queue entry, so keep showing any card whose
    // outcome the user has not dismissed yet.
    const resolved = Object.keys(this.outcomes).filter(
      (id) => !pending.some((a) => a.id === id),
    );

    return html`
      <div class="lede">
        Actions DEEP wants to take that reach outside this machine, or that it
        cannot undo.
        ${pending.length > 0
          ? html`Nothing below has run yet.`
          : ""}
      </div>

      ${pending.length === 0 && resolved.length === 0
        ? html`
            <div class="empty">
              <span class="glyph">✓</span>
              <span>Nothing waiting on you.</span>
            </div>
          `
        : ""}

      ${pending.map((a) => this.renderCard(a))}
      ${resolved.map((id) => {
        const o = this.outcomes[id];
        return html`
          <ds-panel>
            <div class="outcome ${o.kind}">
              <span class="head">
                ${o.kind === "approved" ? "Approved and run" : ""}
                ${o.kind === "rejected" ? "Rejected" : ""}
                ${o.kind === "failed" ? "Did not run" : ""}
              </span>
              <pre>${o.text}</pre>
              <button class="dismiss" @click=${() => this.dismiss(id)}>Dismiss</button>
            </div>
          </ds-panel>
        `;
      })}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "approvals-view": ApprovalsView; }
}
