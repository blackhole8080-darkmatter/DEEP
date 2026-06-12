import{a as l,j as v,k as h,b as e,i as u,r as d,t as g}from"./index-I4xx1e71.js";import"./ds-panel-CjDcRg63.js";var m=Object.defineProperty,b=Object.getOwnPropertyDescriptor,o=(a,t,n,s)=>{for(var i=s>1?void 0:s?b(t,n):t,p=a.length-1,c;p>=0;p--)(c=a[p])&&(i=(s?c(t,n,i):c(i))||i);return s&&i&&m(t,n,i),i};let r=class extends l{constructor(){super(...arguments),this.providers=null,this.security=null,this.kstats=null,this.docs=[]}connectedCallback(){super.connectedCallback(),this.refresh()}async refresh(){v().then(a=>this.providers=a).catch(()=>{}),fetch("/api/security/status").then(a=>a.json()).then(a=>this.security=a).catch(()=>{}),fetch("/api/knowledge/stats").then(a=>a.json()).then(a=>this.kstats=a).catch(()=>{}),h().then(a=>this.docs=a.documents).catch(()=>{})}render(){const a=this.providers,t=this.security,n=this.kstats;return e`
      <ds-panel heading="AI providers">
        ${a?a.providers.map(s=>e`
                <div class="row">
                  <span class="k"><span class="dot ${s.ok?"ok":"bad"}"></span>${s.provider}</span>
                  <span class=${s.ok?"muted":"danger-text"}>${s.detail}</span>
                </div>
              `):e`<span class="muted">loading…</span>`}
        <div slot="actions"><ds-button size="sm" @click=${()=>void this.refresh()}>refresh</ds-button></div>
      </ds-panel>

      <ds-panel heading="Network security">
        ${t?e`
              <div class="row"><span class="k">devices</span>
                <b>${t.summary.total} total · ${t.summary.trusted} trusted ·
                <span class=${t.summary.suspicious?"danger-text":""}>${t.summary.suspicious} suspicious</span></b></div>
              <div class="row"><span class="k">interface</span><b>${t.interface} · ${t.local_ip}</b></div>
              <div class="row"><span class="k">gateway</span><b>${t.gateway}</b></div>
              <div class="row"><span class="k">active connections</span><b>${t.active_connections}</b></div>
              <div class="row"><span class="k">listening ports</span>
                <span class="tags">${(t.listening_ports??[]).slice(0,10).map(s=>e`<span class="tag">${s}</span>`)}</span></div>
            `:e`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Knowledge graph">
        ${n?e`
              <div class="row"><span class="k">entities</span><b>${n.entities}</b></div>
              <div class="row"><span class="k">relationships</span><b>${n.relationships}</b></div>
              <div class="row"><span class="k">types</span>
                <span class="tags">${Object.entries(n.entity_types).map(([s,i])=>e`<span class="tag">${s} ${i}</span>`)}</span></div>
              <div class="row"><span class="k">most connected</span>
                <b>${(n.most_connected??[]).slice(0,3).map(s=>s.name).join(" · ")}</b></div>
            `:e`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Ingested documents">
        ${this.docs.length?this.docs.map(s=>e`<div class="row"><span class="k">${s.source}</span><b>${s.chunks} chunks</b></div>`):e`<span class="muted">No documents ingested yet — drop a file into the chat.</span>`}
      </ds-panel>
    `}};r.styles=u`
    :host {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: var(--ds-space-4);
      padding: var(--ds-space-5);
      max-width: 1100px;
      margin: 0 auto;
      align-content: start;
    }
    .row {
      display: flex; justify-content: space-between; align-items: center;
      gap: var(--ds-space-3); padding: var(--ds-space-2) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
    .ok { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .bad { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .warn { color: var(--ds-warning); }
    .danger-text { color: var(--ds-danger); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag {
      padding: 1px 8px; border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-xs); color: var(--ds-text-soft);
      font-family: var(--ds-font-mono);
    }
  `;o([d()],r.prototype,"providers",2);o([d()],r.prototype,"security",2);o([d()],r.prototype,"kstats",2);o([d()],r.prototype,"docs",2);r=o([g("ops-view")],r);export{r as OpsView};
//# sourceMappingURL=ops-view-DC2Xue7m.js.map
