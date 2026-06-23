import{i as y,J as m,K as b,d as e,G as h,e as w,r as d,t as k}from"./index-C-vDW79N.js";import"./ds-panel-l_RLqrwC.js";import"./ds-button-Ct7t32Fj.js";var z=Object.defineProperty,C=Object.getOwnPropertyDescriptor,n=(t,l,o,r)=>{for(var a=r>1?void 0:r?C(l,o):l,c=t.length-1,s;c>=0;c--)(s=t[c])&&(a=(r?s(l,o,a):s(a))||a);return r&&a&&z(l,o,a),a};const A=15e3;let i=class extends y{constructor(){super(...arguments),this.peers=[],this.origin=null,this.elevated=0,this.countries=[],this.loading=!0,this.err="",this.selected=null,this.dossier=null,this.dossierLoading=!1,this.auto=!0,this.timer=null}connectedCallback(){super.connectedCallback(),this.load(),this.startAuto()}disconnectedCallback(){super.disconnectedCallback(),this.stopAuto()}startAuto(){this.stopAuto(),this.auto&&(this.timer=window.setInterval(()=>{this.loading||this.load()},A))}stopAuto(){this.timer!==null&&(clearInterval(this.timer),this.timer=null)}toggleAuto(){this.auto=!this.auto,this.startAuto()}async load(){this.loading=!0,this.err="";try{const t=await m();t.error&&(this.err=t.error),this.peers=t.peers??[],this.origin=t.origin??null,this.elevated=t.elevated??0,this.countries=t.countries??[],this.selected&&!this.peers.some(l=>l.ip===this.selected)&&(this.selected=null,this.dossier=null)}catch(t){this.err=String(t)}this.loading=!1}async select(t){this.selected=t,this.dossier=null,this.dossierLoading=!0;try{this.dossier=await b(t)}catch(l){this.dossier={error:String(l)}}this.dossierLoading=!1}pinClass(t){return t.proxy?"proxy":t.hosting?"hosting":""}render(){var c;const o=s=>(s+180)/360*720,r=s=>(90-s)/180*360,a=[];for(let s=-150;s<=150;s+=30)a.push(h`<line class="grat" x1=${o(s)} y1="0" x2=${o(s)} y2=${360}></line>`);for(let s=-60;s<=60;s+=30)a.push(h`<line class="grat" x1="0" y1=${r(s)} x2=${720} y2=${r(s)}></line>`);return e`
      <ds-panel heading="Connection geography · live outbound peers">
        <div class="head">
          <span class="count">${this.loading?"scanning connections…":e`${this.peers.length} peer${this.peers.length===1?"":"s"} · ${this.countries.length} countr${this.countries.length===1?"y":"ies"}${this.elevated?e` · <b style="color:var(--ds-warning)">${this.elevated} elevated</b>`:""}`}</span>
          <div style="display:flex;gap:var(--ds-space-2);align-items:center">
            <button class="toggle ${this.auto?"on":""}" @click=${()=>this.toggleAuto()} title="Auto-refresh every 15s">${this.auto?"● live":"○ paused"}</button>
            <ds-button @click=${()=>void this.load()}>${this.loading?"…":"rescan"}</ds-button>
          </div>
        </div>
        ${this.err?e`<div class="muted">${this.err}</div>`:""}
        <div class="map" style="margin-top:var(--ds-space-3)">
          <svg viewBox="0 0 ${720} ${360}">
            <rect width=${720} height=${360} fill="var(--ds-surface-1)"></rect>
            ${a}
            <line class="grat" x1="0" y1=${360/2} x2=${720} y2=${360/2} stroke="var(--ds-border-strong)"></line>
            ${this.origin?this.peers.map(s=>{const p=o(this.origin.lon),g=r(this.origin.lat),v=o(s.lon),u=r(s.lat),f=(p+v)/2,$=(g+u)/2-Math.abs(v-p)*.25-12,x=this.selected===s.ip;return h`<path class="arc ${this.pinClass(s)} ${x?"sel":""}" d=${`M${p},${g} Q${f},${$} ${v},${u}`}></path>`}):""}
            ${this.peers.map(s=>{const p=this.pinClass(s),g=this.selected===s.ip;return h`<circle class="pin ${p} ${g?"sel":""}" cx=${o(s.lon)} cy=${r(s.lat)} r=${g?6:4}
                @click=${()=>void this.select(s.ip)}><title>${s.ip} — ${s.city}, ${s.country} (${s.isp})${s.processes.length?" ← "+s.processes.join(", "):""}</title></circle>`})}
            ${this.origin?h`
              <circle class="origin-ring" cx=${o(this.origin.lon)} cy=${r(this.origin.lat)} r="8"></circle>
              <circle class="origin" cx=${o(this.origin.lon)} cy=${r(this.origin.lat)} r="4"><title>egress · ${this.origin.city}, ${this.origin.country} (${this.origin.isp})</title></circle>
            `:""}
          </svg>
        </div>
        <div class="legend">
          ${this.origin?e`<span><i style="background:var(--ds-accent)"></i>egress · ${this.origin.city}, ${this.origin.country}</span>`:""}
          <span><i style="background:var(--ds-info)"></i>direct</span>
          <span><i style="background:var(--ds-warning)"></i>hosting / cloud</span>
          <span><i style="background:var(--ds-danger)"></i>proxy / VPN</span>
        </div>
      </ds-panel>

      <ds-panel heading="Peers · ${this.peers.length}">
        ${this.peers.length?e`
          <div class="rows">
            ${this.peers.map(s=>e`
              <div class="row ${this.selected===s.ip?"sel":""}" @click=${()=>void this.select(s.ip)}>
                <div>
                  <div class="loc">${s.city||"?"}, ${s.country||"?"} ${s.proxy?e`<span class="flag prox">PROXY</span>`:s.hosting?e`<span class="flag host">HOSTING</span>`:""}</div>
                  <div class="isp">${s.isp} · ${s.asn}</div>
                  <div class="ip">${s.ip}${s.processes.length?e` · <span class="proc">${s.processes.join(", ")}</span>`:""}</div>
                </div>
                <div class="ip">${s.connections}×</div>
              </div>
            `)}
          </div>
        `:e`<span class="muted">${this.loading?"locating…":"No public outbound connections found."}</span>`}
      </ds-panel>

      ${this.selected?e`
        <ds-panel heading="Dossier · ${this.selected}">
          ${this.dossierLoading?e`<span class="muted">investigating…</span>`:(c=this.dossier)!=null&&c.error?e`<span class="muted">${this.dossier.error}</span>`:this.dossier?e`
                    <div class="dossier">
                      ${this.dossier.summary?e`<div class="sum ${this.dossier.risk==="elevated"?"elevated":""}">${this.dossier.summary}</div>`:""}
                      ${(this.dossier.findings??[]).map(s=>e`<div class="drow"><span class="dk">${s.label}</span><span class="dv">${String(s.value)}</span></div>`)}
                    </div>`:e`<span class="muted">Select a peer for a full intelligence dossier.</span>`}
        </ds-panel>
      `:""}
    `}};i.styles=w`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .count { font-family: var(--ds-font-mono); color: var(--ds-text-soft); font-size: var(--ds-text-sm); }
    .map { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .grat { stroke: var(--ds-border); stroke-width: 0.5; fill: none; }
    .pin { fill: var(--ds-info); cursor: pointer; transition: r var(--ds-dur-fast); }
    .pin.hosting { fill: var(--ds-warning); }
    .pin.proxy { fill: var(--ds-danger); }
    .pin.sel { stroke: var(--ds-text); stroke-width: 1.5; }
    .origin { fill: var(--ds-accent); stroke: var(--ds-bg); stroke-width: 1; }
    .origin-ring { fill: none; stroke: var(--ds-accent); opacity: 0.4; }
    .arc { fill: none; stroke: var(--ds-info); stroke-width: 0.6; opacity: 0.28; }
    .arc.hosting { stroke: var(--ds-warning); }
    .arc.proxy { stroke: var(--ds-danger); }
    .arc.sel { opacity: 0.9; stroke-width: 1.4; }
    .label { fill: var(--ds-text); font-size: 10px; font-family: var(--ds-font-mono); }
    .proc { color: var(--ds-accent); font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .legend { display: flex; gap: var(--ds-space-4); font-size: var(--ds-text-xs); color: var(--ds-text-soft); margin-top: var(--ds-space-2); }
    .legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
    .rows { display: grid; gap: 0; max-height: 320px; overflow-y: auto; }
    .row { display: grid; grid-template-columns: 1fr auto auto; gap: var(--ds-space-3); align-items: center; padding: var(--ds-space-2) var(--ds-space-1); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); cursor: pointer; }
    .row:hover, .row.sel { background: var(--ds-surface-2); }
    .row .loc { color: var(--ds-text); }
    .row .isp { color: var(--ds-text-soft); font-size: var(--ds-text-xs); }
    .row .ip { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .flag { font-size: var(--ds-text-xs); padding: 1px 6px; border-radius: var(--ds-radius-pill); }
    .flag.host { color: var(--ds-warning); border: 1px solid var(--ds-warning); }
    .flag.prox { color: var(--ds-danger); border: 1px solid var(--ds-danger); }
    .muted { color: var(--ds-text-muted); }
    .toggle { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); padding: 4px 10px; border-radius: var(--ds-radius-pill); border: 1px solid var(--ds-border); background: var(--ds-surface-2); color: var(--ds-text-muted); cursor: pointer; }
    .toggle.on { color: var(--ds-success); border-color: var(--ds-success); }
    .dossier .drow { display: flex; justify-content: space-between; gap: var(--ds-space-4); padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .dossier .dk { color: var(--ds-text-soft); text-transform: uppercase; font-size: var(--ds-text-xs); letter-spacing: var(--ds-tracking-wide); }
    .dossier .dv { font-family: var(--ds-font-mono); text-align: right; overflow-wrap: anywhere; }
    .dossier .sum { color: var(--ds-text); margin-bottom: var(--ds-space-2); }
    .dossier .sum.elevated { color: var(--ds-warning); }
  `;n([d()],i.prototype,"peers",2);n([d()],i.prototype,"origin",2);n([d()],i.prototype,"elevated",2);n([d()],i.prototype,"countries",2);n([d()],i.prototype,"loading",2);n([d()],i.prototype,"err",2);n([d()],i.prototype,"selected",2);n([d()],i.prototype,"dossier",2);n([d()],i.prototype,"dossierLoading",2);n([d()],i.prototype,"auto",2);i=n([k("connection-map")],i);export{i as ConnectionMap};
//# sourceMappingURL=connection-map-Bfikq0ar.js.map
