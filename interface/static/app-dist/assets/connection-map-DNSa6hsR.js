import{i as g,J as h,d as r,G as p,e as u,r as d,t as f}from"./index-CJGGrPhg.js";import"./ds-panel-FtUUrq9W.js";import"./ds-button-Dv6SWwF9.js";var x=Object.defineProperty,$=Object.getOwnPropertyDescriptor,n=(e,l,o,a)=>{for(var t=a>1?void 0:a?$(l,o):l,s=e.length-1,c;s>=0;s--)(c=e[s])&&(t=(a?c(l,o,t):c(t))||t);return a&&t&&x(l,o,t),t};let i=class extends g{constructor(){super(...arguments),this.peers=[],this.elevated=0,this.countries=[],this.loading=!0,this.err="",this.selected=null}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0,this.err="";try{const e=await h();e.error&&(this.err=e.error),this.peers=e.peers??[],this.elevated=e.elevated??0,this.countries=e.countries??[]}catch(e){this.err=String(e)}this.loading=!1}pinClass(e){return e.proxy?"proxy":e.hosting?"hosting":""}render(){const o=s=>(s+180)/360*720,a=s=>(90-s)/180*360,t=[];for(let s=-150;s<=150;s+=30)t.push(p`<line class="grat" x1=${o(s)} y1="0" x2=${o(s)} y2=${360}></line>`);for(let s=-60;s<=60;s+=30)t.push(p`<line class="grat" x1="0" y1=${a(s)} x2=${720} y2=${a(s)}></line>`);return r`
      <ds-panel heading="Connection geography · live outbound peers">
        <div class="head">
          <span class="count">${this.loading?"scanning connections…":r`${this.peers.length} peer${this.peers.length===1?"":"s"} · ${this.countries.length} countr${this.countries.length===1?"y":"ies"}${this.elevated?r` · <b style="color:var(--ds-warning)">${this.elevated} elevated</b>`:""}`}</span>
          <ds-button @click=${()=>void this.load()}>${this.loading?"…":"rescan"}</ds-button>
        </div>
        ${this.err?r`<div class="muted">${this.err}</div>`:""}
        <div class="map" style="margin-top:var(--ds-space-3)">
          <svg viewBox="0 0 ${720} ${360}">
            <rect width=${720} height=${360} fill="var(--ds-surface-1)"></rect>
            ${t}
            <line class="grat" x1="0" y1=${360/2} x2=${720} y2=${360/2} stroke="var(--ds-border-strong)"></line>
            ${this.peers.map(s=>{const c=this.pinClass(s),v=this.selected===s.ip;return p`<circle class="pin ${c} ${v?"sel":""}" cx=${o(s.lon)} cy=${a(s.lat)} r=${v?6:4}
                @click=${()=>{this.selected=s.ip}}><title>${s.ip} — ${s.city}, ${s.country} (${s.isp})</title></circle>`})}
          </svg>
        </div>
        <div class="legend">
          <span><i style="background:var(--ds-info)"></i>direct</span>
          <span><i style="background:var(--ds-warning)"></i>hosting / cloud</span>
          <span><i style="background:var(--ds-danger)"></i>proxy / VPN</span>
        </div>
      </ds-panel>

      <ds-panel heading="Peers · ${this.peers.length}">
        ${this.peers.length?r`
          <div class="rows">
            ${this.peers.map(s=>r`
              <div class="row ${this.selected===s.ip?"sel":""}" @click=${()=>{this.selected=s.ip}}>
                <div>
                  <div class="loc">${s.city||"?"}, ${s.country||"?"} ${s.proxy?r`<span class="flag prox">PROXY</span>`:s.hosting?r`<span class="flag host">HOSTING</span>`:""}</div>
                  <div class="isp">${s.isp} · ${s.asn}</div>
                  <div class="ip">${s.ip}</div>
                </div>
                <div class="ip">${s.connections}×</div>
              </div>
            `)}
          </div>
        `:r`<span class="muted">${this.loading?"locating…":"No public outbound connections found."}</span>`}
      </ds-panel>
    `}};i.styles=u`
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
    .label { fill: var(--ds-text); font-size: 10px; font-family: var(--ds-font-mono); }
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
  `;n([d()],i.prototype,"peers",2);n([d()],i.prototype,"elevated",2);n([d()],i.prototype,"countries",2);n([d()],i.prototype,"loading",2);n([d()],i.prototype,"err",2);n([d()],i.prototype,"selected",2);i=n([f("connection-map")],i);export{i as ConnectionMap};
//# sourceMappingURL=connection-map-DNSa6hsR.js.map
