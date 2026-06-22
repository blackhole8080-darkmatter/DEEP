import{m as u,O as m,P as v,Q as g,R as h,S as f,g as r,T as y,U as x,d as s,i as b,e as w,r as d,t as $}from"./index-B9odUZEe.js";import"./ds-panel-D8ZUzx06.js";import"./ds-button-Ms_8tG_O.js";var S=Object.defineProperty,k=Object.getOwnPropertyDescriptor,i=(t,a,l,o)=>{for(var n=o>1?void 0:o?k(a,l):a,c=t.length-1,p;c>=0;c--)(p=t[c])&&(n=(o?p(a,l,n):p(n))||n);return o&&n&&S(a,l,n),n};let e=class extends u(b){constructor(){super(...arguments),this.summary=null,this.budgets=[],this.upcoming=[],this.anomalies=[],this.txns=[],this.loading=!0,this.showAddTxn=!1,this.showAddBill=!1}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0;try{this.summary=await m(1),this.budgets=(await v()).budgets,this.upcoming=(await g(14)).bills,this.anomalies=(await h()).anomalies,this.txns=(await f({limit:20})).transactions}catch{r("Finance load failed","danger")}this.loading=!1}async addTxn(t){t.preventDefault();const a=new FormData(t.target);try{await y({date:String(a.get("date")||new Date().toISOString().slice(0,10)),amount:parseFloat(String(a.get("amount")||"0")),description:String(a.get("desc")||""),category:String(a.get("cat")||""),currency:"SEK"}),r("Transaction recorded","success"),this.showAddTxn=!1,this.load()}catch{r("Failed to record","danger")}}async addBill(t){t.preventDefault();const a=new FormData(t.target);try{await x({name:String(a.get("name")||""),amount:parseFloat(String(a.get("amount")||"0")),frequency:String(a.get("freq")||"monthly"),next_due:String(a.get("due")||"")}),r("Bill added","success"),this.showAddBill=!1,this.load()}catch{r("Failed to add bill","danger")}}render(){if(this.loading)return s`<div class="muted">Loading finance data…</div>`;const t=this.summary;return s`
      <ds-panel heading="Finance Overview" slot="actions">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${()=>this.showAddTxn=!this.showAddTxn}>${this.showAddTxn?"cancel":"+ txn"}</ds-button>
          <ds-button size="sm" @click=${()=>this.showAddBill=!this.showAddBill}>${this.showAddBill?"cancel":"+ bill"}</ds-button>
          <ds-button size="sm" @click=${()=>void this.load()}>refresh</ds-button>
        </div>
      </ds-panel>

      ${this.showAddTxn?s`
        <form class="form" @submit=${this.addTxn}>
          <div class="row">
            <input type="date" name="date" .value=${new Date().toISOString().slice(0,10)} />
            <input type="number" name="amount" placeholder="Amount (- for expense)" step="0.01" required />
          </div>
          <input type="text" name="desc" placeholder="Description" required />
          <input type="text" name="cat" placeholder="Category (auto if blank)" />
          <ds-button variant="primary" type="submit">Record</ds-button>
        </form>
      `:""}

      ${this.showAddBill?s`
        <form class="form" @submit=${this.addBill}>
          <input type="text" name="name" placeholder="Bill name" required />
          <div class="row">
            <input type="number" name="amount" placeholder="Amount" step="0.01" required />
            <input type="text" name="freq" placeholder="monthly" value="monthly" />
          </div>
          <input type="date" name="due" placeholder="Next due date" />
          <ds-button variant="primary" type="submit">Add Bill</ds-button>
        </form>
      `:""}

      ${t?s`
        <div class="grid">
          <div class="kpi"><div class="label">Income</div><div class="value pos">${t.total_income.toLocaleString()} SEK</div></div>
          <div class="kpi"><div class="label">Spent</div><div class="value neg">${Math.abs(t.total_spent).toLocaleString()} SEK</div></div>
          <div class="kpi"><div class="label">Net</div><div class="value ${t.net>=0?"pos":"neg"}">${t.net.toLocaleString()} SEK</div></div>
        </div>
      `:""}

      <ds-panel heading="Budgets">
        ${this.budgets.length===0?s`<span class="muted">No budgets set yet.</span>`:s`
          ${this.budgets.map(a=>s`
            <div style="padding:var(--ds-space-2) 0;">
              <div style="display:flex;justify-content:space-between;font-size:var(--ds-text-sm);">
                <span style="text-transform:capitalize;">${a.category}</span>
                <span>${a.spent.toLocaleString()} / ${a.limit.toLocaleString()} ${a.currency}</span>
              </div>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill ${a.percent>100?"danger":a.percent>80?"warn":"ok"}" style="width:${Math.min(a.percent,100)}%"></div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);min-width:36px;text-align:right;">${a.percent.toFixed(0)}%</span>
              </div>
            </div>
          `)}
        `}
      </ds-panel>

      <div class="grid">
        <ds-panel heading="Upcoming Bills · ${this.upcoming.length}">
          ${this.upcoming.length===0?s`<span class="muted">No bills due soon.</span>`:s`
            ${this.upcoming.map(a=>s`
              <div class="bill"><span>${a.name}</span><span style="font-family:var(--ds-font-mono);">${a.amount.toLocaleString()} ${a.currency} — ${a.next_due}</span></div>
            `)}
          `}
        </ds-panel>
        <ds-panel heading="Anomalies · ${this.anomalies.length}">
          ${this.anomalies.length===0?s`<span class="muted">No spending anomalies.</span>`:s`
            ${this.anomalies.map(a=>s`
              <div class="bill"><span>${a.description}</span><span style="color:var(--ds-danger);font-family:var(--ds-font-mono);">${a.z_score.toFixed(1)}σ</span></div>
            `)}
          `}
        </ds-panel>
      </div>

      <ds-panel heading="Recent Transactions">
        ${this.txns.length===0?s`<span class="muted">No transactions yet.</span>`:s`
          ${this.txns.map(a=>s`
            <div class="txn">
              <div>
                <div style="font-weight:500;font-size:var(--ds-text-sm);">${a.description}</div>
                <div style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);text-transform:capitalize;">${a.category} · ${a.date}</div>
              </div>
              <div class="amt ${a.amount>=0?"pos":"neg"}">${a.amount>=0?"+":""}${a.amount.toLocaleString()} ${a.currency}</div>
            </div>
          `)}
        `}
      </ds-panel>
    `}};e.styles=w`
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
  `;i([d()],e.prototype,"summary",2);i([d()],e.prototype,"budgets",2);i([d()],e.prototype,"upcoming",2);i([d()],e.prototype,"anomalies",2);i([d()],e.prototype,"txns",2);i([d()],e.prototype,"loading",2);i([d()],e.prototype,"showAddTxn",2);i([d()],e.prototype,"showAddBill",2);e=i([$("finance-view")],e);export{e as FinanceView};
//# sourceMappingURL=finance-view-C61b4mzx.js.map
