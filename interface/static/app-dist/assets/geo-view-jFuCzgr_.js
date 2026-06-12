import{a as g,q as f,b as i,w as c,i as u,r as v,t as b}from"./index-I4xx1e71.js";import"./ds-panel-CjDcRg63.js";var x=Object.defineProperty,$=Object.getOwnPropertyDescriptor,p=(s,e,r,o)=>{for(var t=o>1?void 0:o?$(e,r):e,n=s.length-1,a;n>=0;n--)(a=s[n])&&(t=(o?a(e,r,t):a(t))||t);return o&&t&&x(e,r,t),t};let d=class extends g{constructor(){super(...arguments),this.geo=null,this.err=""}connectedCallback(){super.connectedCallback(),f().then(s=>this.geo=s).catch(s=>this.err=String(s))}render(){if(this.err)return i`<ds-panel heading="Location"><span class="muted">${this.err}</span></ds-panel>`;const s=this.geo,e=720,r=360,o=s?(s.lon+180)/360*e:0,t=s?(90-s.lat)/180*r:0,n=[];for(let a=-150;a<=150;a+=30){const l=(a+180)/360*e;n.push(c`<line class="grat" x1=${l} y1="0" x2=${l} y2=${r}></line>`)}for(let a=-60;a<=60;a+=30){const l=(90-a)/180*r;n.push(c`<line class="grat" x1="0" y1=${l} x2=${e} y2=${l}></line>`)}return i`
      <ds-panel heading="Precise location · network-reported">
        <div class="map">
          <svg viewBox="0 0 ${e} ${r}">
            <rect width=${e} height=${r} fill="var(--ds-surface-1)"></rect>
            ${n}
            <line class="grat" x1="0" y1=${r/2} x2=${e} y2=${r/2} stroke="var(--ds-border-strong)"></line>
            ${s?c`
              <circle class="pulse" cx=${o} cy=${t} r="5"></circle>
              <circle class="pin" cx=${o} cy=${t} r="5"></circle>
              <text x=${o+9} y=${t+4} fill="var(--ds-text)" font-size="12" font-family="var(--ds-font-mono)">${s.city}, ${s.country}</text>
            `:""}
          </svg>
        </div>
        ${s?i`<div class="big" style="margin-top:var(--ds-space-3);color:var(--ds-accent)">${s.city}, ${s.regionName}</div>`:""}
      </ds-panel>

      ${s?i`
        <ds-panel heading="Coordinates & network">
          <div class="rows">
            <div class="row"><span class="k">country</span><b>${s.country}</b></div>
            <div class="row"><span class="k">region</span><b>${s.regionName}</b></div>
            <div class="row"><span class="k">latitude</span><b>${s.lat}°</b></div>
            <div class="row"><span class="k">longitude</span><b>${s.lon}°</b></div>
            <div class="row"><span class="k">public IP</span><b>${s.query}</b></div>
            ${s.isp?i`<div class="row"><span class="k">ISP</span><b>${s.isp}</b></div>`:""}
          </div>
          <p class="note">Derived from the public IP DEEP currently exits through — reflects your VPN/network egress, not GPS.</p>
        </ds-panel>
      `:i`<ds-panel heading="Coordinates"><span class="muted">locating…</span></ds-panel>`}
    `}};d.styles=u`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 980px; margin: 0 auto; align-content: start; }
    .map { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .grat { stroke: var(--ds-border); stroke-width: 0.5; fill: none; }
    .pin { fill: var(--ds-danger); }
    .pulse { fill: var(--ds-danger); opacity: 0.4; animation: ping 2s ease-out infinite; transform-origin: center; transform-box: fill-box; }
    @keyframes ping { 0% { transform: scale(1); opacity: 0.5; } 100% { transform: scale(4); opacity: 0; } }
    .rows { display: grid; gap: 0; }
    .row { display: flex; justify-content: space-between; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); text-transform: uppercase; font-size: var(--ds-text-xs); letter-spacing: var(--ds-tracking-wide); }
    .row b { font-family: var(--ds-font-mono); }
    .big { font-size: var(--ds-text-2xl); font-weight: 700; }
    .note { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
    .muted { color: var(--ds-text-muted); }
  `;p([v()],d.prototype,"geo",2);p([v()],d.prototype,"err",2);d=p([b("geo-view")],d);export{d as GeoView};
//# sourceMappingURL=geo-view-jFuCzgr_.js.map
