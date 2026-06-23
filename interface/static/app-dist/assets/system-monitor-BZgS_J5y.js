import{e as u,n as v,i as f,d as i,t as g,H as $,I as w,r as p}from"./index-CNV0UZxn.js";import"./ds-panel-C-QBPNy4.js";var k=Object.defineProperty,_=Object.getOwnPropertyDescriptor,h=(s,t,e,a)=>{for(var r=a>1?void 0:a?_(t,e):t,o=s.length-1,n;o>=0;o--)(n=s[o])&&(r=(a?n(t,e,r):n(r))||r);return a&&r&&k(t,e,r),r};let c=class extends f{constructor(){super(...arguments),this.data=[],this.max=100,this.color="var(--ds-accent)",this.height=48}render(){const t=this.height,e=this.data.slice(-60);if(e.length<2)return i`<svg viewBox="0 0 ${200} ${t}"></svg>`;const a=this.max||Math.max(...e,1),r=200/(e.length-1),n=e.map((x,y)=>`${(y*r).toFixed(1)},${(t-Math.min(x,a)/a*t).toFixed(1)}`).join(" "),b=`0,${t} ${n} 200,${t}`,m=Math.random().toString(36).slice(2,7);return i`
      <svg viewBox="0 0 ${200} ${t}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="g${m}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color=${this.color} stop-opacity="0.32" />
            <stop offset="100%" stop-color=${this.color} stop-opacity="0" />
          </linearGradient>
        </defs>
        <polygon points=${b} fill="url(#g${m})" />
        <polyline points=${n} fill="none" stroke=${this.color} stroke-width="1.5"
          vector-effect="non-scaling-stroke" stroke-linejoin="round" />
      </svg>
    `}};c.styles=u`
    :host { display: block; }
    svg { width: 100%; height: 100%; display: block; }
  `;h([v({attribute:!1})],c.prototype,"data",2);h([v({type:Number})],c.prototype,"max",2);h([v()],c.prototype,"color",2);h([v({type:Number})],c.prototype,"height",2);c=h([g("spark-line")],c);var H=Object.defineProperty,M=Object.getOwnPropertyDescriptor,l=(s,t,e,a)=>{for(var r=a>1?void 0:a?M(t,e):t,o=s.length-1,n;o>=0;o--)(n=s[o])&&(r=(a?n(t,e,r):n(r))||r);return a&&r&&H(t,e,r),r};function P(s){const t=Math.floor(s/86400),e=Math.floor(s%86400/3600),a=Math.floor(s%3600/60);return t?`${t}d ${e}h ${a}m`:e?`${e}h ${a}m`:`${a}m`}let d=class extends f{constructor(){super(...arguments),this.info=null,this.cpuHist=[],this.ramHist=[],this.netHist=[],this.cur={cpu:0,ram:0,disk:0,net:0,ramUsed:0,ramTotal:0}}connectedCallback(){super.connectedCallback(),this.tickVitals(),this.tickInfo(),this.vt=setInterval(()=>void this.tickVitals(),2e3),this.it=setInterval(()=>void this.tickInfo(),5e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.vt),clearInterval(this.it)}async tickVitals(){try{const s=await $();this.cur={cpu:s.cpu,ram:s.ram,disk:s.disk,net:s.net_recv_mbs+s.net_sent_mbs,ramUsed:s.ram_used_gb,ramTotal:s.ram_total_gb},this.cpuHist=[...this.cpuHist,s.cpu].slice(-60),this.ramHist=[...this.ramHist,s.ram].slice(-60),this.netHist=[...this.netHist,s.net_recv_mbs+s.net_sent_mbs].slice(-60)}catch{}}async tickInfo(){try{this.info=await w()}catch{}}chart(s,t,e,a,r){return i`<div class="chart">
      <div class="top"><span class="k">${s}</span><span class="v">${t}</span></div>
      <spark-line .data=${e} .max=${a} color=${r} .height=${44}></spark-line>
    </div>`}displayLayout(){var e;const s=((e=this.info)==null?void 0:e.displays)??[];if(!s.length)return i`<span class="muted">no displays detected</span>`;const t=.05;return i`<div class="displays">
      ${s.map(a=>i`
        <div class="screen ${a.primary?"primary":""}"
          style="width:${Math.max(60,a.width*t)}px;height:${Math.max(36,a.height*t)}px">
          ${a.primary?i`<span class="badge">primary</span>`:""}
          ${a.width}×${a.height}
        </div>
      `)}
    </div>`}render(){var e,a;const s=this.info,t=this.cur;return i`
      <ds-panel heading="Live usage">
        <div class="charts">
          ${this.chart("CPU",`${t.cpu.toFixed(0)}%`,this.cpuHist,100,"var(--ds-accent)")}
          ${this.chart("Memory",`${t.ram.toFixed(0)}%`,this.ramHist,100,"var(--ds-success)")}
          ${this.chart("Network MB/s",t.net.toFixed(2),this.netHist,Math.max(2,...this.netHist),"var(--ds-info)")}
          <div class="chart">
            <div class="top"><span class="k">Disk</span><span class="v">${t.disk.toFixed(0)}%</span></div>
            <div style="margin-top:8px"><span class="muted">${t.ramUsed} / ${t.ramTotal} GB RAM used</span></div>
          </div>
        </div>
      </ds-panel>

      <ds-panel heading="Per-core load · ${(s==null?void 0:s.cores_logical)??"?"} threads">
        ${(e=s==null?void 0:s.per_core)!=null&&e.length?i`<div class="cores">
          ${s.per_core.map((r,o)=>i`
            <div class="core">
              <div class="bar"><i style="height:${Math.max(2,r)}%"></i></div>
              <div class="n">${o}</div>
            </div>
          `)}
        </div>`:i`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Connected displays · ${((a=s==null?void 0:s.displays)==null?void 0:a.length)??0}">
        ${this.displayLayout()}
      </ds-panel>

      <ds-panel heading="Machine">
        ${s?i`<div class="rows">
          <div class="row"><span class="k">hostname</span><b>${s.hostname}</b></div>
          <div class="row"><span class="k">OS</span><b>${s.os} · ${s.arch}</b></div>
          <div class="row"><span class="k">CPU</span><b>${s.cores_physical}c / ${s.cores_logical}t${s.cpu_freq_mhz?` · ${(s.cpu_freq_mhz/1e3).toFixed(1)} GHz`:""}</b></div>
          <div class="row"><span class="k">uptime</span><b>${P(s.uptime_s)}</b></div>
          ${s.battery?i`<div class="row"><span class="k">battery</span>
            <b class="batt"><span class="cell"><i style="width:${s.battery.percent}%;background:${s.battery.percent<20?"var(--ds-danger)":"var(--ds-success)"}"></i></span>
              ${s.battery.percent}% ${s.battery.plugged?"⚡":""}</b></div>`:""}
        </div>`:i`<span class="muted">loading…</span>`}
      </ds-panel>
    `}};d.styles=u`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1100px; margin: 0 auto; align-content: start; }
    .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--ds-space-3); }
    .chart { padding: var(--ds-space-3); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .chart .top { display: flex; justify-content: space-between; align-items: baseline; }
    .chart .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    .chart .v { font-size: var(--ds-text-xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .cores { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: var(--ds-space-2); }
    .core { text-align: center; }
    .core .bar { height: 46px; background: var(--ds-surface-3); border-radius: var(--ds-radius-xs); position: relative; overflow: hidden; display: flex; align-items: flex-end; }
    .core .bar > i { width: 100%; background: var(--ds-accent); box-shadow: var(--ds-glow); transition: height var(--ds-dur-base) var(--ds-ease-out); }
    .core .n { font-size: 0.6rem; color: var(--ds-text-faint); font-family: var(--ds-font-mono); }
    .displays { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; align-items: flex-end; }
    .screen { border: 2px solid var(--ds-border-accent); border-radius: var(--ds-radius-sm); background: linear-gradient(135deg, rgba(var(--ds-periwinkle-rgb),0.12), transparent); display: grid; place-items: center; color: var(--ds-text-soft); font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); position: relative; box-shadow: var(--ds-elev-2); }
    .screen.primary { border-color: var(--ds-accent); box-shadow: var(--ds-glow); }
    .screen .badge { position: absolute; top: 4px; left: 6px; font-size: 0.55rem; color: var(--ds-accent); }
    .rows { display: grid; gap: 0; }
    .row { display: flex; justify-content: space-between; padding: var(--ds-space-2) 0; border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .batt { display: inline-flex; align-items: center; gap: 6px; }
    .batt .cell { width: 30px; height: 13px; border: 1px solid var(--ds-text-soft); border-radius: 3px; position: relative; padding: 1px; }
    .batt .cell > i { display: block; height: 100%; border-radius: 1px; background: var(--ds-success); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;l([p()],d.prototype,"info",2);l([p()],d.prototype,"cpuHist",2);l([p()],d.prototype,"ramHist",2);l([p()],d.prototype,"netHist",2);l([p()],d.prototype,"cur",2);d=l([g("system-monitor")],d);export{d as SystemMonitor};
//# sourceMappingURL=system-monitor-BZgS_J5y.js.map
