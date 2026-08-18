import{i as u,b as r,a as m,r as l,t as f}from"./index-Dadyro_p.js";import"./ds-panel-ClgPOpfB.js";var g=Object.defineProperty,h=Object.getOwnPropertyDescriptor,o=(s,e,t,n)=>{for(var i=n>1?void 0:n?h(e,t):e,a=s.length-1,c;a>=0;a--)(c=s[a])&&(i=(n?c(e,t,i):c(i))||i);return n&&i&&g(e,t,i),i};const p=["critical","high","medium","low","info"],v={critical:"Critical",high:"High",medium:"Medium",low:"Low",info:"Info"};let d=class extends u{constructor(){super(...arguments),this.items=[],this.stats=null,this.minSeverity="",this._expanded=new Set,this._seen=new Set,this._reqGen=0}connectedCallback(){super.connectedCallback(),this.refresh(),this.timer=setInterval(()=>void this.refresh(),6e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async refresh(){const s=++this._reqGen,e=this.minSeverity?`?min_severity=${this.minSeverity}&limit=60`:"?limit=60";fetch(`/api/security/timeline${e}`).then(t=>t.json()).then(t=>{s===this._reqGen&&(this.items=t.timeline??[])}).catch(()=>{}),fetch("/api/security/timeline/stats").then(t=>t.json()).then(t=>{this.stats=t}).catch(()=>{})}toggle(s){const e=new Set(this._expanded);e.has(s)?e.delete(s):e.add(s),this._expanded=e}isNew(s){const e=!this._seen.has(s);return this._seen.add(s),e}render(){const s=this.stats;return r`
      ${s?r`
        <ds-panel heading="Live security timeline">
          <div class="stats">
            <div class="stat total"><div class="k">total</div><div class="v">${s.total}</div></div>
            ${p.filter(e=>s.by_severity[e]).map(e=>r`
              <div class="stat ${e}"><div class="k">${v[e]}</div><div class="v">${s.by_severity[e]}</div></div>
            `)}
          </div>
        </ds-panel>
      `:r`<span class="muted">loading timeline…</span>`}

      <div class="filters">
        <button class="filter-btn ${this.minSeverity===""?"on":""}" @click=${()=>{this.minSeverity="",this.refresh()}}>All</button>
        ${p.map(e=>r`
          <button class="filter-btn ${this.minSeverity===e?"on":""}"
                  @click=${()=>{this.minSeverity=e,this.refresh()}}>${v[e]}+</button>
        `)}
      </div>

      <div class="list">
        ${this.items.length===0?r`<div class="empty">No security events yet — this feed lights up as anomaly/threat detection and network monitoring produce live signal.</div>`:null}
        ${this.items.map(e=>{const t=this._expanded.has(e.id),n=e.techniques.length>0||e.related_cves.length>0||e.device_mac,i=this.isNew(e.id);return r`
            <div class="row ${i?"is-new":""}" style="--sev-color: var(--ds-${e.severity==="critical"||e.severity==="high"?"danger":e.severity==="medium"?"warning":"info"})">
              <div class="stripe"></div>
              <div class="main" @click=${()=>n&&this.toggle(e.id)}>
                <div class="head">
                  <span class="kind">${e.kind}</span>
                  <span class="source">${e.source}</span>
                  <span class="time">${this._fmtTime(e.timestamp)}</span>
                </div>
                <div class="summary">${e.summary}</div>
              </div>
              <span class="chip">${v[e.severity]}</span>
              ${t?r`
                <div class="detail">
                  ${e.techniques.length?r`
                    <div class="tag-group">
                      ${e.techniques.map(a=>r`<span class="tag technique" title=${a.detection}>${a.id} · ${a.name}</span>`)}
                    </div>
                  `:null}
                  ${e.related_cves.length?r`
                    <div class="tag-group">
                      ${e.related_cves.map(a=>r`<span class="tag cve ${a.is_kev?"kev":""}">${a.cve_id}${a.is_kev?" · KEV":""}</span>`)}
                    </div>
                  `:null}
                  ${e.device_mac?r`<div class="muted">Device: ${e.device_mac} ${e.device_ip?`(${e.device_ip})`:""}</div>`:null}
                </div>
              `:null}
            </div>
          `})}
      </div>
    `}_fmtTime(s){if(!s)return"";try{const e=new Date(s);return isNaN(e.getTime())?s.slice(11,19)||s:e.toLocaleTimeString([],{hour12:!1})}catch{return s}}};d.styles=m`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }

    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .stat .v { font-size: var(--ds-text-xl); font-weight: 700; font-family: var(--ds-font-mono); font-variant-numeric: tabular-nums; }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .stat.critical .v, .stat.high .v { color: var(--ds-danger); }
    .stat.medium .v { color: var(--ds-warning); }
    .stat.low .v, .stat.info .v { color: var(--ds-info); }
    .stat.total .v { color: var(--ds-accent); }

    .filters { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    .filter-btn {
      padding: 3px 10px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs);
      font-family: var(--ds-font-mono); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); color: var(--ds-text-soft);
      cursor: pointer; transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .filter-btn:hover { border-color: var(--ds-border-strong); color: var(--ds-text); }
    .filter-btn.on { background: var(--ds-surface-3); border-color: var(--ds-border-accent); color: var(--ds-text); box-shadow: var(--ds-glow); }

    .list { display: grid; gap: 6px; }
    .row {
      display: grid; grid-template-columns: 4px 1fr auto; gap: var(--ds-space-3);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      overflow: hidden;
    }
    /* Only genuinely new rows animate in — the list re-renders every poll
       (6s), so animating every row unconditionally would flicker instead of
       reading as "alive". isNew() tracks what's already been seen. */
    .row.is-new { animation: fade-up var(--ds-dur-slow) var(--ds-ease-out); }
    @media (prefers-reduced-motion: reduce) { .row.is-new { animation: none; } }
    .row .stripe { background: var(--sev-color, var(--ds-text-faint)); }
    .row .main { padding: var(--ds-space-3) var(--ds-space-2); min-width: 0; cursor: pointer; }
    .row .head { display: flex; align-items: baseline; gap: var(--ds-space-2); flex-wrap: wrap; }
    .row .kind { font-weight: 600; font-size: var(--ds-text-sm); }
    .row .source { font-size: var(--ds-text-xs); color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .row .time { font-size: var(--ds-text-xs); color: var(--ds-text-faint); font-family: var(--ds-font-mono); margin-left: auto; }
    .row .summary { margin-top: 2px; font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .chip {
      padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: 0.66rem;
      font-family: var(--ds-font-mono); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      color: var(--sev-color, var(--ds-text-soft)); border: 1px solid var(--sev-color, var(--ds-border));
      background: color-mix(in srgb, var(--sev-color, transparent) 12%, transparent);
      align-self: center; margin-right: var(--ds-space-3);
    }
    .detail { grid-column: 1 / -1; padding: 0 var(--ds-space-3) var(--ds-space-3); display: grid; gap: var(--ds-space-2); }
    .tag-group { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag {
      padding: 1px 8px; border-radius: var(--ds-radius-sm); font-size: 0.68rem; font-family: var(--ds-font-mono);
      border: 1px solid var(--ds-border); color: var(--ds-text-soft);
    }
    .tag.technique { border-color: var(--ds-accent); color: var(--ds-accent); }
    .tag.cve { border-color: var(--ds-danger); color: var(--ds-danger); }
    .tag.kev { background: color-mix(in srgb, var(--ds-danger) 18%, transparent); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    .empty { padding: var(--ds-space-5); text-align: center; color: var(--ds-text-muted); }
  `;o([l()],d.prototype,"items",2);o([l()],d.prototype,"stats",2);o([l()],d.prototype,"minSeverity",2);o([l()],d.prototype,"_expanded",2);d=o([f("security-timeline-view")],d);export{d as SecurityTimelineView};
//# sourceMappingURL=security-timeline-view-gEXAFKzN.js.map
