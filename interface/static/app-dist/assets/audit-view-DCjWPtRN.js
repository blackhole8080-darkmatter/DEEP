import{i as v,b as r,a as p,r as c,t as g}from"./index-BDF8Pc56.js";import"./ds-panel-B3Jr7Ayo.js";var f=Object.defineProperty,h=Object.getOwnPropertyDescriptor,l=(s,t,e,i)=>{for(var a=i>1?void 0:i?h(t,e):t,n=s.length-1,o;n>=0;n--)(o=s[n])&&(a=(i?o(t,e,a):o(a))||a);return i&&a&&f(t,e,a),a};let d=class extends v{constructor(){super(...arguments),this.stats=null,this.entries=[]}connectedCallback(){super.connectedCallback(),this.refresh(),this.timer=setInterval(()=>void this.refresh(),8e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async refresh(){fetch("/audit/stats").then(s=>s.json()).then(s=>this.stats=s).catch(()=>{}),fetch("/audit/log?limit=40").then(s=>s.json()).then(s=>this.entries=s.entries??[]).catch(()=>{})}render(){const s=this.stats;return r`
      ${s?r`
        <div class="integrity ${s.chain_intact?"ok":"bad"}">
          <span class="seal">${s.chain_intact?"🔒":"⚠"}</span>
          <span>Tamper-evident chain ${s.chain_intact?"INTACT":"BROKEN"} · ${s.total_entries} entries sealed</span>
        </div>
        <ds-panel heading="Ledger stats">
          <div class="stats">
            <div class="stat"><div class="k">total</div><div class="v">${s.total_entries}</div></div>
            <div class="stat"><div class="k">today</div><div class="v">${s.entries_today}</div></div>
            <div class="stat"><div class="k">threats today</div><div class="v">${s.threat_count_today}</div></div>
            <div class="stat"><div class="k">threats all-time</div><div class="v">${s.threat_count_total}</div></div>
          </div>
          <div style="margin-top:var(--ds-space-3)" class="tags">
            ${Object.entries(s.entries_by_type).map(([t,e])=>r`<span class="tag">${t} ${e}</span>`)}
          </div>
        </ds-panel>
      `:r`<span class="muted">loading ledger…</span>`}

      <ds-panel heading="Recent entries · live">
        <div class="log">
          ${this.entries.map(t=>r`
            <div class="row">
              <span class="t">#${t.id}</span>
              <span class="ty ${t.entry_type}">${t.entry_type}</span>
              <span>${t.action}</span>
            </div>
          `)}
        </div>
      </ds-panel>
    `}};d.styles=p`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .integrity {
      display: flex; align-items: center; gap: var(--ds-space-3);
      padding: var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      font-weight: 600;
    }
    .integrity.ok { background: rgba(0,255,174,0.08); border: 1px solid var(--ds-success); color: var(--ds-success); }
    .integrity.bad { background: rgba(255,45,120,0.08); border: 1px solid var(--ds-danger); color: var(--ds-danger); }
    .seal { font-size: var(--ds-text-xl); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .stat .v { font-size: var(--ds-text-xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag { padding: 1px 8px; border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); color: var(--ds-text-soft); font-family: var(--ds-font-mono); }
    .log { display: grid; gap: 2px; max-height: 360px; overflow-y: auto; font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .row { display: grid; grid-template-columns: 64px 130px 1fr; gap: var(--ds-space-2); padding: 3px 0; border-bottom: 1px solid var(--ds-border); color: var(--ds-text-soft); }
    .row .ty { font-weight: 600; }
    .ty.THREAT_DETECTED, .ty.INTEGRITY_FAIL { color: var(--ds-danger); }
    .ty.SYSTEM_START, .ty.SYSTEM_STOP { color: var(--ds-info); }
    .ty.DEVICE_JOINED { color: var(--ds-warning); }
    .t { color: var(--ds-text-faint); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;l([c()],d.prototype,"stats",2);l([c()],d.prototype,"entries",2);d=l([g("audit-view")],d);export{d as AuditView};
//# sourceMappingURL=audit-view-DCjWPtRN.js.map
