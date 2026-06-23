import{i as y,J as x,d as o,G as g,e as m,r as d,t as b}from"./index-CNV0UZxn.js";import"./ds-panel-C-QBPNy4.js";import"./ds-button-CvDvh5Ru.js";var w=Object.defineProperty,k=Object.getOwnPropertyDescriptor,l=(t,c,r,i)=>{for(var e=i>1?void 0:i?k(c,r):c,s=t.length-1,n;s>=0;s--)(n=t[s])&&(e=(i?n(c,r,e):n(e))||e);return i&&e&&w(c,r,e),e};let a=class extends y{constructor(){super(...arguments),this.peers=[],this.origin=null,this.elevated=0,this.countries=[],this.loading=!0,this.err="",this.selected=null}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0,this.err="";try{const t=await x();t.error&&(this.err=t.error),this.peers=t.peers??[],this.origin=t.origin??null,this.elevated=t.elevated??0,this.countries=t.countries??[]}catch(t){this.err=String(t)}this.loading=!1}pinClass(t){return t.proxy?"proxy":t.hosting?"hosting":""}render(){const r=s=>(s+180)/360*720,i=s=>(90-s)/180*360,e=[];for(let s=-150;s<=150;s+=30)e.push(g`<line class="grat" x1=${r(s)} y1="0" x2=${r(s)} y2=${360}></line>`);for(let s=-60;s<=60;s+=30)e.push(g`<line class="grat" x1="0" y1=${i(s)} x2=${720} y2=${i(s)}></line>`);return o`
      <ds-panel heading="Connection geography · live outbound peers">
        <div class="head">
          <span class="count">${this.loading?"scanning connections…":o`${this.peers.length} peer${this.peers.length===1?"":"s"} · ${this.countries.length} countr${this.countries.length===1?"y":"ies"}${this.elevated?o` · <b style="color:var(--ds-warning)">${this.elevated} elevated</b>`:""}`}</span>
          <ds-button @click=${()=>void this.load()}>${this.loading?"…":"rescan"}</ds-button>
        </div>
        ${this.err?o`<div class="muted">${this.err}</div>`:""}
        <div class="map" style="margin-top:var(--ds-space-3)">
          <svg viewBox="0 0 ${720} ${360}">
            <rect width=${720} height=${360} fill="var(--ds-surface-1)"></rect>
            ${e}
            <line class="grat" x1="0" y1=${360/2} x2=${720} y2=${360/2} stroke="var(--ds-border-strong)"></line>
            ${this.origin?this.peers.map(s=>{const n=r(this.origin.lon),p=i(this.origin.lat),h=r(s.lon),v=i(s.lat),$=(n+h)/2,u=(p+v)/2-Math.abs(h-n)*.25-12,f=this.selected===s.ip;return g`<path class="arc ${this.pinClass(s)} ${f?"sel":""}" d=${`M${n},${p} Q${$},${u} ${h},${v}`}></path>`}):""}
            ${this.peers.map(s=>{const n=this.pinClass(s),p=this.selected===s.ip;return g`<circle class="pin ${n} ${p?"sel":""}" cx=${r(s.lon)} cy=${i(s.lat)} r=${p?6:4}
                @click=${()=>{this.selected=s.ip}}><title>${s.ip} — ${s.city}, ${s.country} (${s.isp})${s.processes.length?" ← "+s.processes.join(", "):""}</title></circle>`})}
            ${this.origin?g`
              <circle class="origin-ring" cx=${r(this.origin.lon)} cy=${i(this.origin.lat)} r="8"></circle>
              <circle class="origin" cx=${r(this.origin.lon)} cy=${i(this.origin.lat)} r="4"><title>egress · ${this.origin.city}, ${this.origin.country} (${this.origin.isp})</title></circle>
            `:""}
          </svg>
        </div>
        <div class="legend">
          ${this.origin?o`<span><i style="background:var(--ds-accent)"></i>egress · ${this.origin.city}, ${this.origin.country}</span>`:""}
          <span><i style="background:var(--ds-info)"></i>direct</span>
          <span><i style="background:var(--ds-warning)"></i>hosting / cloud</span>
          <span><i style="background:var(--ds-danger)"></i>proxy / VPN</span>
        </div>
      </ds-panel>

      <ds-panel heading="Peers · ${this.peers.length}">
        ${this.peers.length?o`
          <div class="rows">
            ${this.peers.map(s=>o`
              <div class="row ${this.selected===s.ip?"sel":""}" @click=${()=>{this.selected=s.ip}}>
                <div>
                  <div class="loc">${s.city||"?"}, ${s.country||"?"} ${s.proxy?o`<span class="flag prox">PROXY</span>`:s.hosting?o`<span class="flag host">HOSTING</span>`:""}</div>
                  <div class="isp">${s.isp} · ${s.asn}</div>
                  <div class="ip">${s.ip}${s.processes.length?o` · <span class="proc">${s.processes.join(", ")}</span>`:""}</div>
                </div>
                <div class="ip">${s.connections}×</div>
              </div>
            `)}
          </div>
        `:o`<span class="muted">${this.loading?"locating…":"No public outbound connections found."}</span>`}
      </ds-panel>
    `}};a.styles=m`
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
  `;l([d()],a.prototype,"peers",2);l([d()],a.prototype,"origin",2);l([d()],a.prototype,"elevated",2);l([d()],a.prototype,"countries",2);l([d()],a.prototype,"loading",2);l([d()],a.prototype,"err",2);l([d()],a.prototype,"selected",2);a=l([b("connection-map")],a);export{a as ConnectionMap};
//# sourceMappingURL=connection-map-PAS4AZTr.js.map
