import{a as y,A as u,w as f,b as v,i as w,r as l,t as $}from"./index-CFs9j95j.js";var k=Object.defineProperty,M=Object.getOwnPropertyDescriptor,c=(e,s,i,t)=>{for(var a=t>1?void 0:t?M(s,i):s,r=e.length-1,o;r>=0;r--)(o=e[r])&&(a=(t?o(s,i,a):o(a))||a);return t&&a&&k(s,i,a),a};const b={technology:"var(--ds-periwinkle)",topic:"var(--ds-lilac)",concept:"var(--ds-sky)",person:"var(--ds-amber)",project:"var(--ds-coral)",organization:"var(--ds-iris)",place:"var(--ds-mint)",preference:"var(--ds-mint)"},x=["#7c93ff","#56c596","#e0a35a","#e5736a","#5ec8e5","#b58cff","#9a8cff","#f5b942","#00e5ff","#ff6ad5"];let n=class extends y{constructor(){super(...arguments),this.nodes=[],this.edges=[],this.query="",this.focusedId=null,this.hover=null,this.stats={},this.inferences=[],this.colorMode="community",this.showSemantic=!0,this.busy="",this.loading=!0,this.raf=0,this.alpha=1,this.drag=null,this.W=960,this.H=620}connectedCallback(){super.connectedCallback(),this.load(),this.loadInferences()}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf)}async load(){this.loading=!0;try{const e=await(await fetch("/api/knowledge/vault?limit=220")).json(),s=e.entities??[],i=e.relationships??[];this.stats=e.stats??{};const t={};for(const r of i)t[r.source]=(t[r.source]??0)+1,t[r.target]=(t[r.target]??0)+1;const a=new Map;this.nodes=s.map((r,o)=>{const d=o/Math.max(1,s.length)*Math.PI*2,p=120+((r.pagerank??0)>0?0:o%5*30),h={...r,x:this.W/2+Math.cos(d)*(p+80),y:this.H/2+Math.sin(d)*(p+40),vx:0,vy:0,deg:t[r.id]??0};return a.set(r.id,h),h}),this.edges=i.map(r=>{const o=a.get(r.source),d=a.get(r.target);return o&&d?{s:o,t:d,relation:r.relation,kind:r.kind??"relation",confidence:r.confidence??.6}:null}).filter(r=>!!r),this.alpha=1,this.run()}catch{}this.loading=!1}async loadInferences(){try{const e=await(await fetch("/api/knowledge/inferences?limit=7&connections=true")).json();this.inferences=e.inferences??[]}catch{}}async runGnn(){this.busy="Running GraphSAGE…";try{const s=(await(await fetch("/api/knowledge/gnn?epochs=50",{method:"POST"})).json()).predicted_links??[],i=new Map(this.nodes.map(a=>[a.id,a])),t=[];for(const a of s){const r=i.get(a.source),o=i.get(a.target);r&&o&&t.push({s:r,t:o,relation:"predicted",kind:"gnn",confidence:a.score})}this.edges=[...this.edges.filter(a=>a.kind!=="gnn"),...t],this.alpha=Math.max(this.alpha,.4),this.run(),this.busy=`GNN linked ${t.length} predicted pairs`}catch{this.busy="GNN unavailable"}setTimeout(()=>{this.busy=""},3200)}run(){cancelAnimationFrame(this.raf);const e=()=>{const s=this.nodes,i=Math.max(this.alpha,.02);for(let t=0;t<s.length;t++)for(let a=t+1;a<s.length;a++){const r=s[t],o=s[a];let d=r.x-o.x,p=r.y-o.y,h=d*d+p*p||.01;const g=1700/h*i,m=Math.sqrt(h);d/=m,p/=m,r.vx+=d*g,r.vy+=p*g,o.vx-=d*g,o.vy-=p*g}for(const t of this.edges){const a=t.kind==="semantic"?130:t.kind==="gnn"?150:88;let r=t.t.x-t.s.x,o=t.t.y-t.s.y;const d=Math.sqrt(r*r+o*o)||.01,p=t.kind==="relation"?.012:.005,h=(d-a)*p*i;r/=d,o/=d,t.s.vx+=r*h,t.s.vy+=o*h,t.t.vx-=r*h,t.t.vy-=o*h}for(const t of s){if(t===this.drag){t.vx=0,t.vy=0;continue}t.vx+=(this.W/2-t.x)*.0016*i,t.vy+=(this.H/2-t.y)*.0016*i,t.vx*=.86,t.vy*=.86,t.x=Math.max(24,Math.min(this.W-24,t.x+t.vx)),t.y=Math.max(24,Math.min(this.H-24,t.y+t.vy))}this.alpha*=.992,this.requestUpdate(),this.raf=requestAnimationFrame(e)};this.raf=requestAnimationFrame(e)}toSvg(e){const s=this.renderRoot.querySelector("svg");if(!s)return{x:0,y:0};const i=s.createSVGPoint();i.x=e.clientX,i.y=e.clientY;const t=s.getScreenCTM();if(!t)return{x:0,y:0};const a=i.matrixTransform(t.inverse());return{x:a.x,y:a.y}}onDown(e,s){var i,t;s.stopPropagation(),this.drag=e,e.fixed=!0,(t=(i=s.target).setPointerCapture)==null||t.call(i,s.pointerId)}onMove(e){if(!this.drag)return;const s=this.toSvg(e);this.drag.x=s.x,this.drag.y=s.y,this.alpha=Math.max(this.alpha,.25),this.requestUpdate()}onUp(){this.drag&&(this.drag.fixed=!1),this.drag=null}nodeColor(e){return this.colorMode==="community"&&e.community!==void 0?x[e.community%x.length]:b[e.type]??"var(--ds-text-muted)"}nodeRadius(e){const s=(e.pagerank??0)*1400;return Math.max(5,Math.min(22,5+e.deg*1.5+s))}dim(e){const s=this.query.toLowerCase();if(this.focusedId)return e===this.focusedId?!1:!this.edges.some(i=>i.s.id===this.focusedId&&i.t.id===e||i.t.id===this.focusedId&&i.s.id===e);if(s){const i=this.nodes.find(t=>t.id===e);return!!i&&!i.name.toLowerCase().includes(s)}return!1}edgeStroke(e){return e==="gnn"?"var(--ds-accent)":e==="semantic"?"var(--ds-lilac)":e==="suggestion"||e==="suggested"?"var(--ds-sky)":"var(--ds-border-strong)"}render(){var i;const e=this.stats.graph??{},s=this.hover;return v`
      <div class="main">
        <div class="bar">
          <h2>Memory Graph</h2>
          <span class="s">${this.stats.entities??this.nodes.length} nodes · ${this.edges.length} links</span>
          <span class="spacer"></span>
          <button class=${this.colorMode==="community"?"on":""}
            @click=${()=>{this.colorMode=this.colorMode==="community"?"type":"community"}}>
            ${this.colorMode==="community"?"◍ Clusters":"◐ Types"}
          </button>
          <button class=${this.showSemantic?"on":""} @click=${()=>{this.showSemantic=!this.showSemantic}}>~ Semantic</button>
          <button class="gnn" @click=${()=>this.runGnn()}>⚡ Run GNN</button>
          <input placeholder="Search…" @input=${t=>{this.query=t.target.value,this.focusedId=null}} />
        </div>

        <div class="canvas">
          <svg viewBox="0 0 ${this.W} ${this.H}"
            @pointermove=${t=>this.onMove(t)}
            @pointerup=${()=>this.onUp()} @pointerleave=${()=>this.onUp()}
            @click=${t=>{t.target.tagName==="svg"&&(this.focusedId=null)}}>
            <defs>
              <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="3.2" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            ${this.edges.filter(t=>this.showSemantic||t.kind!=="semantic").map(t=>{const a=this.dim(t.s.id)||this.dim(t.t.id),r=t.kind==="relation"?.34:t.kind==="gnn"?.7:.18,o=t.kind==="semantic"?"4 5":t.kind==="gnn"?"1 6":"0";return f`<line x1=${t.s.x} y1=${t.s.y} x2=${t.t.x} y2=${t.t.y}
                  stroke=${this.edgeStroke(t.kind)} stroke-width=${t.kind==="gnn"?1.6:1}
                  stroke-dasharray=${o}
                  opacity=${a?.04:r}></line>`})}

            ${this.nodes.map(t=>{const a=this.nodeRadius(t),r=this.dim(t.id),o=(t.pagerank??0)*1400>6||t.deg>=4;return f`
                <circle cx=${t.x} cy=${t.y} r=${a}
                  fill=${this.nodeColor(t)}
                  filter=${o&&!r?"url(#glow)":u}
                  opacity=${r?.1:.94}
                  stroke=${this.focusedId===t.id?"var(--ds-white)":"transparent"} stroke-width="1.5"
                  @pointerdown=${d=>this.onDown(t,d)}
                  @pointerenter=${()=>{this.hover=t}}
                  @pointerleave=${()=>{this.hover===t&&(this.hover=null)}}
                  @click=${d=>{d.stopPropagation(),this.focusedId=this.focusedId===t.id?null:t.id}}></circle>
                ${(t.deg>=2||this.focusedId===t.id||o)&&!r?f`<text x=${t.x+a+3} y=${t.y+3} font-size=${o?11:9}>${t.name}</text>`:""}
              `})}
          </svg>

          ${s?v`
            <div class="tip" style=${`left:${s.x/this.W*100}%; top:${s.y/this.H*100}%`}>
              <h4>${s.name}</h4>
              <div class="meta">${s.type}${s.community!==void 0?` · cluster ${s.community}`:""} · ${s.deg} links</div>
              ${s.description?v`<p>${s.description}</p>`:(i=s.context)!=null&&i[0]?v`<p>${s.context[0]}</p>`:u}
            </div>`:u}

          ${this.busy?v`<div class="toast">${this.busy}</div>`:u}
          ${this.loading?v`<div class="toast">Loading memory…</div>`:u}
        </div>

        <div class="legend">
          ${this.colorMode==="type"?Object.entries(b).map(([t,a])=>v`<span><i style="background:${a}"></i>${t}</span>`):v`<span class="empty">Coloured by detected community · node size = PageRank importance</span>`}
          <span class="spacer"></span>
          <span><i class="edge" style="border-color:var(--ds-border-strong)"></i>fact</span>
          <span><i class="edge" style="border-color:var(--ds-lilac);border-top-style:dashed"></i>semantic</span>
          <span><i class="edge" style="border-color:var(--ds-accent);border-top-style:dotted"></i>GNN</span>
        </div>
      </div>

      <div class="rail">
        <div class="card">
          <h3>Network</h3>
          <div class="metrics">
            <div class="m"><b>${this.stats.entities??"—"}</b><span>entities</span></div>
            <div class="m"><b>${this.stats.relationships??"—"}</b><span>relations</span></div>
            <div class="m"><b>${e.communities??"—"}</b><span>clusters</span></div>
            <div class="m"><b>${e.density!==void 0?e.density.toFixed(3):"—"}</b><span>density</span></div>
          </div>
        </div>
        <div class="card">
          <h3>Inferences</h3>
          <div class="infer">
            ${this.inferences.length?this.inferences.map(t=>v`
                  <div class="row ${t.type}">
                    <span class="tag">${t.type}</span><br />${t.text}
                  </div>`):v`<span class="empty">No inferences yet — teach DEEP more and they'll appear.</span>`}
          </div>
        </div>
      </div>
    `}};n.styles=w`
    :host { display: grid; grid-template-columns: 1fr 260px; gap: var(--ds-space-4);
      padding: var(--ds-space-4); max-width: 1320px; margin: 0 auto; color: var(--ds-text); }
    @media (max-width: 880px) { :host { grid-template-columns: 1fr; } .rail { order: -1; } }

    .main { display: grid; gap: var(--ds-space-3); min-width: 0; }
    .bar { display: flex; align-items: center; gap: var(--ds-space-3); flex-wrap: wrap; }
    .bar h2 { font-size: var(--ds-text-xl); margin: 0; letter-spacing: var(--ds-tracking-wide);
      background: linear-gradient(90deg, var(--ds-white), var(--ds-periwinkle));
      -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .bar .s { color: var(--ds-text-muted); font-size: var(--ds-text-xs); font-family: var(--ds-font-mono); }
    .spacer { flex: 1; }
    input {
      padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2);
      color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-sm); width: 200px; transition: border-color var(--ds-dur-fast), box-shadow var(--ds-dur-fast);
    }
    input:focus { outline: none; border-color: var(--ds-border-accent); box-shadow: var(--ds-glow); }

    button { font: inherit; font-size: var(--ds-text-xs); cursor: pointer; color: var(--ds-text-soft);
      background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill);
      padding: var(--ds-space-2) var(--ds-space-3); transition: all var(--ds-dur-fast); white-space: nowrap; }
    button:hover { color: var(--ds-text); border-color: var(--ds-border-accent); box-shadow: var(--ds-glow); }
    button.on { color: var(--ds-on-accent); background: var(--ds-accent); border-color: transparent; }
    button.gnn { color: var(--ds-accent); border-color: var(--ds-border-accent); }
    button.gnn:hover { background: rgba(var(--ds-periwinkle-rgb), 0.12); }

    .canvas { position: relative; background:
        radial-gradient(120% 90% at 50% 0%, rgba(var(--ds-periwinkle-rgb),0.10), transparent 60%),
        radial-gradient(80% 80% at 80% 100%, rgba(154,140,255,0.08), transparent 55%),
        var(--ds-charcoal-900);
      border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden;
      box-shadow: var(--ds-elev-3), inset 0 0 60px rgba(0,0,0,0.4); }
    svg { width: 100%; height: auto; display: block; touch-action: none; }
    text { font-family: var(--ds-font-sans); fill: var(--ds-text-soft); pointer-events: none; }
    circle { cursor: grab; }
    circle:active { cursor: grabbing; }

    .tip { position: absolute; pointer-events: none; max-width: 240px; z-index: 5;
      background: var(--ds-glass); backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-strong); border-radius: var(--ds-radius-md);
      padding: var(--ds-space-2) var(--ds-space-3); box-shadow: var(--ds-elev-3);
      transform: translate(-50%, calc(-100% - 14px)); transition: opacity var(--ds-dur-fast); }
    .tip h4 { margin: 0 0 2px; font-size: var(--ds-text-sm); }
    .tip .meta { font-size: var(--ds-text-xs); color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .tip p { margin: 4px 0 0; font-size: var(--ds-text-xs); color: var(--ds-text-soft); line-height: 1.4; }

    .legend { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; font-size: var(--ds-text-xs); color: var(--ds-text-muted); align-items: center; }
    .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
    .legend .edge { width: 18px; height: 0; border-top: 2px solid; margin-right: 4px; display: inline-block; vertical-align: middle; }

    .rail { display: grid; gap: var(--ds-space-3); align-content: start; }
    .card { background: var(--ds-surface-1); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md); padding: var(--ds-space-3); }
    .card h3 { margin: 0 0 var(--ds-space-2); font-size: var(--ds-text-sm); color: var(--ds-text-soft);
      display: flex; align-items: center; gap: 6px; }
    .card h3::before { content: ""; width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent); box-shadow: var(--ds-glow); }
    .infer { display: grid; gap: var(--ds-space-2); }
    .infer .row { font-size: var(--ds-text-xs); line-height: 1.4; padding: var(--ds-space-2);
      background: var(--ds-surface-2); border-radius: var(--ds-radius-sm); border-left: 2px solid var(--ds-border-strong); }
    .infer .row.habit { border-left-color: var(--ds-periwinkle); }
    .infer .row.connection { border-left-color: var(--ds-sky); }
    .infer .row.hub { border-left-color: var(--ds-amber); }
    .infer .row.stale { border-left-color: var(--ds-text-muted); }
    .infer .tag { font-family: var(--ds-font-mono); font-size: 10px; text-transform: uppercase;
      letter-spacing: 0.05em; color: var(--ds-text-muted); }
    .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-2); }
    .metrics .m { background: var(--ds-surface-2); border-radius: var(--ds-radius-sm); padding: var(--ds-space-2); }
    .metrics .m b { display: block; font-size: var(--ds-text-lg); font-family: var(--ds-font-mono); color: var(--ds-text); }
    .metrics .m span { font-size: 10px; color: var(--ds-text-muted); }
    .toast { position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
      background: var(--ds-glass); border: 1px solid var(--ds-border-accent); color: var(--ds-text);
      padding: var(--ds-space-2) var(--ds-space-4); border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-xs); box-shadow: var(--ds-glow); backdrop-filter: blur(var(--ds-blur-md)); }
    .empty { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
  `;c([l()],n.prototype,"nodes",2);c([l()],n.prototype,"edges",2);c([l()],n.prototype,"query",2);c([l()],n.prototype,"focusedId",2);c([l()],n.prototype,"hover",2);c([l()],n.prototype,"stats",2);c([l()],n.prototype,"inferences",2);c([l()],n.prototype,"colorMode",2);c([l()],n.prototype,"showSemantic",2);c([l()],n.prototype,"busy",2);c([l()],n.prototype,"loading",2);n=c([$("memory-graph")],n);export{n as MemoryGraph};
//# sourceMappingURL=memory-graph-DxMfm4IN.js.map
