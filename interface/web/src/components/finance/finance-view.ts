// <finance-view> — DEEP personal finance dashboard
// Spending summary, budgets, bills, anomalies, transaction history.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { SignalWatcher } from "@lit-labs/signals";
import {
  fetchFinanceSummary, fetchFinanceTransactions, fetchFinanceBudgets,
  fetchFinanceUpcomingBills, fetchFinanceAnomalies,
  addFinanceTransaction, addFinanceBill,
  type Transaction, type BudgetStatus, type Bill, type Anomaly,
} from "../../core/api";
import { toast } from "../primitives/ds-toast";
import "../primitives/ds-panel";
import "../primitives/ds-button";

@customElement("finance-view")
export class FinanceView extends SignalWatcher(LitElement) {
  @state() private summary: Awaited<ReturnType<typeof fetchFinanceSummary>> | null = null;
  @state() private budgets: BudgetStatus[] = [];
  @state() private upcoming: Bill[] = [];
  @state() private anomalies: Anomaly[] = [];
  @state() private txns: Transaction[] = [];
  @state() private loading = true;
  @state() private showAddTxn = false;
  @state() private showAddBill = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      this.summary = await fetchFinanceSummary(1);
      this.budgets = (await fetchFinanceBudgets()).budgets;
      this.upcoming = (await fetchFinanceUpcomingBills(14)).bills;
      this.anomalies = (await fetchFinanceAnomalies()).anomalies;
      this.txns = (await fetchFinanceTransactions({ limit: 20 })).transactions;
    } catch (e) {
      toast("Finance load failed", "danger");
    }
    this.loading = false;
  }

  private async addTxn(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await addFinanceTransaction({
        date: String(fd.get("date") || new Date().toISOString().slice(0, 10)),
        amount: parseFloat(String(fd.get("amount") || "0")),
        description: String(fd.get("desc") || ""),
        category: String(fd.get("cat") || ""),
        currency: "SEK",
      });
      toast("Transaction recorded", "success");
      this.showAddTxn = false;
      void this.load();
    } catch {
      toast("Failed to record", "danger");
    }
  }

  private async addBill(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await addFinanceBill({
        name: String(fd.get("name") || ""),
        amount: parseFloat(String(fd.get("amount") || "0")),
        frequency: String(fd.get("freq") || "monthly"),
        next_due: String(fd.get("due") || ""),
      });
      toast("Bill added", "success");
      this.showAddBill = false;
      void this.load();
    } catch {
      toast("Failed to add bill", "danger");
    }
  }

  static styles = css`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1100px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--ds-space-3); }
    .kpi { padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .kpi .label { font-size: var(--ds-text-xs); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); color: var(--ds-text-faint); }
    .kpi .value { font-size: var(--ds-text-xl); font-weight: 700; margin-top: var(--ds-space-1); }
    .kpi .value.pos { color: var(--ds-success); }
    .kpi .value.neg { color: var(--ds-danger); }
    .bar-wrap { display: flex; align-items: center; gap: var(--ds-space-2); margin-top: var(--ds-space-2); }
    .bar { flex: 1; height: 6px; background: var(--ds-surface-2); border-radius: var(--ds-radius-pill); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: var(--ds-radius-pill); }
    .bar-fill.ok { background: var(--ds-success); }
    .bar-fill.warn { background: var(--ds-warning); }
    .bar-fill.danger { background: var(--ds-danger); }
    .txn { display: flex; justify-content: space-between; align-items: center; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); }
    .txn:last-child { border-bottom: 0; }
    .txn .amt { font-family: var(--ds-font-mono); font-weight: 600; }
    .txn .amt.pos { color: var(--ds-success); }
    .txn .amt.neg { color: var(--ds-danger); }
    .bill { display: flex; justify-content: space-between; align-items: center; padding: var(--ds-space-2) var(--ds-space-3); }
    .form { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .form input { padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); }
    .row { display: flex; gap: var(--ds-space-2); }
  `;

  render() {
    if (this.loading) return html`<div class="muted">Loading finance data…</div>`;
    const s = this.summary;
    return html`
      <ds-panel heading="Finance Overview" slot="actions">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${() => (this.showAddTxn = !this.showAddTxn)}>${this.showAddTxn ? "cancel" : "+ txn"}</ds-button>
          <ds-button size="sm" @click=${() => (this.showAddBill = !this.showAddBill)}>${this.showAddBill ? "cancel" : "+ bill"}</ds-button>
          <ds-button size="sm" @click=${() => void this.load()}>refresh</ds-button>
        </div>
      </ds-panel>

      ${this.showAddTxn ? html`
        <form class="form" @submit=${this.addTxn}>
          <div class="row">
            <input type="date" name="date" .value=${new Date().toISOString().slice(0, 10)} />
            <input type="number" name="amount" placeholder="Amount (- for expense)" step="0.01" required />
          </div>
          <input type="text" name="desc" placeholder="Description" required />
          <input type="text" name="cat" placeholder="Category (auto if blank)" />
          <ds-button variant="primary" type="submit">Record</ds-button>
        </form>
      ` : ""}

      ${this.showAddBill ? html`
        <form class="form" @submit=${this.addBill}>
          <input type="text" name="name" placeholder="Bill name" required />
          <div class="row">
            <input type="number" name="amount" placeholder="Amount" step="0.01" required />
            <input type="text" name="freq" placeholder="monthly" value="monthly" />
          </div>
          <input type="date" name="due" placeholder="Next due date" />
          <ds-button variant="primary" type="submit">Add Bill</ds-button>
        </form>
      ` : ""}

      ${s ? html`
        <div class="grid">
          <div class="kpi"><div class="label">Income</div><div class="value pos">${s.total_income.toLocaleString()} SEK</div></div>
          <div class="kpi"><div class="label">Spent</div><div class="value neg">${Math.abs(s.total_spent).toLocaleString()} SEK</div></div>
          <div class="kpi"><div class="label">Net</div><div class="value ${s.net >= 0 ? "pos" : "neg"}">${s.net.toLocaleString()} SEK</div></div>
        </div>
      ` : ""}

      <ds-panel heading="Budgets">
        ${this.budgets.length === 0 ? html`<span class="muted">No budgets set yet.</span>` : html`
          ${this.budgets.map((b) => html`
            <div style="padding:var(--ds-space-2) 0;">
              <div style="display:flex;justify-content:space-between;font-size:var(--ds-text-sm);">
                <span style="text-transform:capitalize;">${b.category}</span>
                <span>${b.spent.toLocaleString()} / ${b.limit.toLocaleString()} ${b.currency}</span>
              </div>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill ${b.percent > 100 ? "danger" : b.percent > 80 ? "warn" : "ok"}" style="width:${Math.min(b.percent, 100)}%"></div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);min-width:36px;text-align:right;">${b.percent.toFixed(0)}%</span>
              </div>
            </div>
          `)}
        `}
      </ds-panel>

      <div class="grid">
        <ds-panel heading="Upcoming Bills · ${this.upcoming.length}">
          ${this.upcoming.length === 0 ? html`<span class="muted">No bills due soon.</span>` : html`
            ${this.upcoming.map((b) => html`
              <div class="bill"><span>${b.name}</span><span style="font-family:var(--ds-font-mono);">${b.amount.toLocaleString()} ${b.currency} — ${b.next_due}</span></div>
            `)}
          `}
        </ds-panel>
        <ds-panel heading="Anomalies · ${this.anomalies.length}">
          ${this.anomalies.length === 0 ? html`<span class="muted">No spending anomalies.</span>` : html`
            ${this.anomalies.map((a) => html`
              <div class="bill"><span>${a.description}</span><span style="color:var(--ds-danger);font-family:var(--ds-font-mono);">${a.z_score.toFixed(1)}σ</span></div>
            `)}
          `}
        </ds-panel>
      </div>

      <ds-panel heading="Recent Transactions">
        ${this.txns.length === 0 ? html`<span class="muted">No transactions yet.</span>` : html`
          ${this.txns.map((t) => html`
            <div class="txn">
              <div>
                <div style="font-weight:500;font-size:var(--ds-text-sm);">${t.description}</div>
                <div style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);text-transform:capitalize;">${t.category} · ${t.date}</div>
              </div>
              <div class="amt ${t.amount >= 0 ? "pos" : "neg"}">${t.amount >= 0 ? "+" : ""}${t.amount.toLocaleString()} ${t.currency}</div>
            </div>
          `)}
        `}
      </ds-panel>
    `;
  }
}
