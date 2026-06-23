import{i as g,g as v,d,e as h,r as l,t as m}from"./index-C-vDW79N.js";import"./ds-panel-l_RLqrwC.js";import"./ds-button-Ct7t32Fj.js";var f=Object.defineProperty,u=Object.getOwnPropertyDescriptor,c=(s,e,a,n)=>{for(var t=n>1?void 0:n?u(e,a):e,o=s.length-1,i;o>=0;o--)(i=s[o])&&(t=(n?i(e,a,t):i(t))||t);return n&&t&&f(e,a,t),t};let r=class extends g{constructor(){super(...arguments),this.briefing=null,this.stats=null,this.papers=null,this.speaking=!1}connectedCallback(){super.connectedCallback(),this.load()}async load(){fetch("/api/briefing").then(s=>s.json()).then(s=>this.briefing=s).catch(()=>{}),fetch("/api/research/stats").then(s=>s.json()).then(s=>this.stats=s).catch(()=>{}),fetch("/knowledge/status").then(s=>s.json()).then(s=>this.papers=s).catch(()=>{})}async speak(){this.speaking=!0;try{await fetch("/api/briefing/speak",{method:"POST"}),v("Speaking briefing…","info")}catch{v("TTS unavailable","danger")}setTimeout(()=>this.speaking=!1,1500)}render(){var t,o;const s=this.briefing,e=this.stats,a=this.papers,n=a&&Object.values(a.papers_by_domain).reduce((i,p)=>i+p,0)||1;return d`
      <ds-panel heading="Daily briefing · news">
        ${s?d`
          <div class="when">${s.date} · ${s.time}</div>
          <p class="briefing">${s.briefing}</p>
          <div slot="actions"><ds-button size="sm" @click=${()=>void this.speak()}>${this.speaking?"🔊":"speak"}</ds-button></div>
        `:d`<span class="muted">loading briefing…</span>`}
      </ds-panel>

      <ds-panel heading="Research intake">
        ${e?d`<div class="stats">
          <div class="stat"><div class="k">topics tracked</div><div class="v">${e.topics}</div></div>
          <div class="stat"><div class="k">findings</div><div class="v">${e.total_findings}</div></div>
          <div class="stat alert"><div class="k">unread</div><div class="v">${e.unread_findings}</div></div>
          <div class="stat"><div class="k">last 24h</div><div class="v">${e.last_24h}</div></div>
        </div>`:d`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Research paper corpus${a?` · ${a.total_papers} indexed`:""}">
        ${a?d`
          <div class="domains">
            ${Object.entries(a.papers_by_domain).sort((i,p)=>p[1]-i[1]).map(([i,p])=>d`
              <div class="dom">
                <span>${i}</span>
                <span class="bar"><i style="width:${p/n*100}%"></i></span>
                <span class="n">${p}</span>
              </div>
            `)}
          </div>
          <p class="meta">${((o=(t=a.db_size_mb)==null?void 0:t.toFixed)==null?void 0:o.call(t,1))??a.db_size_mb} MB · updated ${new Date(a.last_updated).toLocaleString()}</p>
        `:d`<span class="muted">loading corpus…</span>`}
      </ds-panel>
    `}};r.styles=h`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .briefing { font-size: var(--ds-text-lg); line-height: 1.6; color: var(--ds-text); }
    .when { color: var(--ds-text-muted); font-size: var(--ds-text-sm); font-family: var(--ds-font-mono); margin-bottom: var(--ds-space-2); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); text-align: center; }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .stat.alert .v { color: var(--ds-warning); }
    .domains { display: grid; gap: var(--ds-space-2); }
    .dom { display: grid; grid-template-columns: 130px 1fr 50px; align-items: center; gap: var(--ds-space-3); font-size: var(--ds-text-sm); }
    .dom .bar { height: 8px; background: var(--ds-surface-3); border-radius: 4px; overflow: hidden; }
    .dom .bar > i { display: block; height: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .dom .n { font-family: var(--ds-font-mono); text-align: right; color: var(--ds-text-soft); }
    .meta { color: var(--ds-text-muted); font-size: var(--ds-text-xs); margin-top: var(--ds-space-2); }
    .muted { color: var(--ds-text-muted); }
  `;c([l()],r.prototype,"briefing",2);c([l()],r.prototype,"stats",2);c([l()],r.prototype,"papers",2);c([l()],r.prototype,"speaking",2);r=c([m("research-view")],r);export{r as ResearchView};
//# sourceMappingURL=research-view-Cx8asuSy.js.map
