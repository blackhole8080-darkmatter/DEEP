import{m as p,C as u,g as d,D as g,E as h,d as e,i as b,e as f,r as l,t as m}from"./index-CNV0UZxn.js";import"./ds-panel-C-QBPNy4.js";import"./ds-button-CvDvh5Ru.js";var x=Object.defineProperty,w=Object.getOwnPropertyDescriptor,n=(a,i,s,r)=>{for(var t=r>1?void 0:r?w(i,s):i,c=a.length-1,v;c>=0;c--)(v=a[c])&&(t=(r?v(i,s,t):v(t))||t);return r&&t&&x(i,s,t),t};let o=class extends p(b){constructor(){super(...arguments),this.missions=[],this.filter="all",this.loading=!0,this.showCreate=!1}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0;try{const a=this.filter==="all"?void 0:this.filter;this.missions=(await u(a,30)).missions}catch{d("Failed to load missions","danger")}this.loading=!1}async onCreate(a){a.preventDefault();const i=new FormData(a.target),s=String(i.get("goal")||"");if(s)try{const r=await g(s);"mission_id"in r&&r.mission_id?(d(`Mission ${r.mission_id} created`,"success"),this.showCreate=!1,this.load()):"error"in r?d(r.error,"danger"):d("Create failed","danger")}catch{d("Create failed","danger")}}async onCancel(a){try{await h(a),d("Mission cancelled","info"),this.load()}catch{d("Cancel failed","danger")}}render(){const a=["all","running","pending","completed","failed"],i=this.filter==="all"?this.missions:this.missions.filter(s=>s.status===this.filter);return e`
      <ds-panel heading="Missions">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${()=>this.showCreate=!this.showCreate}>${this.showCreate?"cancel":"+ mission"}</ds-button>
          <ds-button size="sm" @click=${()=>void this.load()}>refresh</ds-button>
        </div>
      </ds-panel>

      ${this.showCreate?e`
        <form class="form" @submit=${this.onCreate}>
          <textarea name="goal" placeholder="Describe the mission — e.g. 'Research quantum AI breakthroughs in 2026 and write a 1-page summary'" required></textarea>
          <ds-button variant="primary" type="submit">Launch Mission</ds-button>
        </form>
      `:""}

      <div class="filters">
        ${a.map(s=>e`
          <button class="${this.filter===s?"on":""}" @click=${()=>{this.filter=s,this.load()}}>${s}</button>
        `)}
      </div>

      ${this.loading?e`<div class="muted">Loading…</div>`:e`
        ${i.length===0?e`<div class="muted">No ${this.filter==="all"?"":this.filter} missions.</div>`:e`
          ${i.map(s=>e`
            <div class="mission">
              <div class="head">
                <div>
                  <div class="goal">${s.goal}</div>
                  <div class="meta">${s.id} · ${new Date(s.created_at).toLocaleString()}</div>
                </div>
                <div style="display:flex;gap:var(--ds-space-2);align-items:center;">
                  <span class="status ${s.status}">${s.status}</span>
                  ${s.status==="running"||s.status==="pending"?e`
                    <ds-button size="sm" @click=${()=>void this.onCancel(s.id)}>cancel</ds-button>
                  `:""}
                </div>
              </div>
              <div class="bar-wrap">
                <div class="bar"><div class="bar-fill" style="width:${s.progress_pct}%"></div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);min-width:32px;text-align:right;">${s.progress_pct.toFixed(0)}%</span>
              </div>
              ${s.error?e`<div style="font-size:var(--ds-text-xs);color:var(--ds-danger);">${s.error}</div>`:""}
            </div>
          `)}
        `}
      `}
    `}};o.styles=f`
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
  `;n([l()],o.prototype,"missions",2);n([l()],o.prototype,"filter",2);n([l()],o.prototype,"loading",2);n([l()],o.prototype,"showCreate",2);o=n([m("missions-view")],o);export{o as MissionsView};
//# sourceMappingURL=missions-view-ClxhFLkV.js.map
