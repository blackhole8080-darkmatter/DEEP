import{l as h,a as m,c,b as t,p as l,i as g,r as p,t as u}from"./index-I4xx1e71.js";import"./ds-panel-CjDcRg63.js";var f=Object.defineProperty,x=Object.getOwnPropertyDescriptor,v=(a,s,e,r)=>{for(var i=r>1?void 0:r?x(s,e):s,n=a.length-1,o;n>=0;n--)(o=a[n])&&(i=(r?o(s,e,i):o(i))||i);return r&&i&&f(s,e,i),i};let d=class extends h(m){constructor(){super(...arguments),this.devices=[],this.vitals=null}connectedCallback(){super.connectedCallback(),this.refresh(),this.timer=setInterval(()=>void this.refresh(),6e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async refresh(){fetch("/api/security/devices").then(a=>a.json()).then(a=>this.devices=a.devices??[]).catch(()=>{}),fetch("/api/vitals").then(a=>a.json()).then(a=>this.vitals=a).catch(()=>{})}async act(a,s){try{(await fetch(`/api/security/${s}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({mac:a})})).ok?(c(`Device ${s}ed`,s==="trust"?"success":"danger"),this.refresh()):c(`${s} failed`,"danger")}catch{c(`${s} failed`,"danger")}}statBar(a,s,e="%"){return t`<div class="stat"><div class="k">${a}</div><div class="v">${s.toFixed(s<10?1:0)}${e}</div>
      ${e==="%"?t`<div class="bar"><i style="width:${Math.min(s,100)}%"></i></div>`:""}</div>`}render(){const a=this.vitals;return t`
      <ds-panel heading="System vitals">
        ${a?t`<div class="vitals">
          ${this.statBar("CPU",a.cpu)}
          ${this.statBar("RAM",a.ram)}
          ${this.statBar("Disk",a.disk)}
          <div class="stat"><div class="k">RAM used</div><div class="v">${a.ram_used_gb}<span style="font-size:0.6em">/${a.ram_total_gb}GB</span></div></div>
          <div class="stat"><div class="k">Net ↓↑</div><div class="v" style="font-size:var(--ds-text-lg)">${a.net_recv_mbs.toFixed(2)}/${a.net_sent_mbs.toFixed(2)}</div></div>
          <div class="stat"><div class="k">Cores</div><div class="v">${a.cores}</div></div>
        </div>`:t`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Network devices · ${this.devices.length}">
        ${this.devices.length?this.devices.map(s=>t`
          <div class="dev">
            <div class="name">
              <span class="dot ${s.trust_status}"></span>
              <span>${s.hostname||s.ip}${s.is_gateway?" · gateway":""}</span>
              <span class="meta">${s.ip} · ${s.mac}${s.vendor?` · ${s.vendor}`:""}</span>
            </div>
            <div class="acts">
              <ds-button size="sm" @click=${()=>void this.act(s.mac,"trust")}>trust</ds-button>
              <ds-button size="sm" variant="danger" @click=${()=>void this.act(s.mac,"block")}>block</ds-button>
            </div>
          </div>
        `):t`<span class="muted">scanning…</span>`}
      </ds-panel>

      <ds-panel heading="Proximity & RF events · live">
        ${l.get().length?t`<div class="feed">
          ${l.get().map(s=>t`<div class="ev"><span class="t">${s.time}</span><span>${s.label}</span></div>`)}
        </div>`:t`<span class="muted">Listening for nearby access points & proximity changes…</span>`}
      </ds-panel>
    `}};d.styles=g`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1100px; margin: 0 auto; align-content: start; }
    .vitals { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: var(--ds-space-3); }
    .stat { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .bar { height: 4px; border-radius: 2px; background: var(--ds-surface-3); margin-top: 6px; overflow: hidden; }
    .bar > i { display: block; height: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .dev { display: grid; grid-template-columns: 1fr auto; gap: var(--ds-space-3); align-items: center; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .dev:last-child { border-bottom: none; }
    .dev .name { display: flex; align-items: center; gap: var(--ds-space-2); }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .trusted { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .unknown { background: var(--ds-warning); }
    .blocked, .suspicious { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .acts { display: flex; gap: var(--ds-space-1); }
    .feed { display: grid; gap: 3px; max-height: 220px; overflow-y: auto; font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .ev { color: var(--ds-text-soft); display: flex; gap: var(--ds-space-2); }
    .ev .t { color: var(--ds-text-faint); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;v([p()],d.prototype,"devices",2);v([p()],d.prototype,"vitals",2);d=v([u("network-view")],d);export{d as NetworkView};
//# sourceMappingURL=network-view-fCNm8ToZ.js.map
