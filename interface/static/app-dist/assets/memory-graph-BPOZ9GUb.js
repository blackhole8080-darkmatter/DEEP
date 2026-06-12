import{a as y,w as v,b as g,i as m,r as h,t as b}from"./index-I4xx1e71.js";var $=Object.defineProperty,w=Object.getOwnPropertyDescriptor,l=(s,r,a,t)=>{for(var i=t>1?void 0:t?w(r,a):r,e=s.length-1,o;e>=0;e--)(o=s[e])&&(i=(t?o(r,a,i):o(i))||i);return t&&i&&$(r,a,i),i};const x={technology:"var(--ds-accent)",topic:"var(--ds-neon-violet, var(--ds-info))",concept:"var(--ds-success)",person:"var(--ds-warning)",project:"var(--ds-danger)"};let c=class extends y{constructor(){super(...arguments),this.nodes=[],this.edges=[],this.query="",this.focus=null,this.stats={},this.raf=0,this.W=900,this.H=560}connectedCallback(){super.connectedCallback(),this.load()}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf)}async load(){try{const s=await(await fetch("/api/knowledge/vault?limit=200")).json(),r=s.entities??[],a=s.relationships??[];this.stats=s.stats??{};const t={};for(const e of a)t[e.source]=(t[e.source]??0)+1,t[e.target]=(t[e.target]??0)+1;const i=new Map;this.nodes=r.map((e,o)=>{const n=o/r.length*Math.PI*2,d={...e,x:this.W/2+Math.cos(n)*200,y:this.H/2+Math.sin(n)*160,vx:0,vy:0,deg:t[e.id]??0};return i.set(e.id,d),d}),this.edges=a.map(e=>({s:i.get(e.source),t:i.get(e.target),relation:e.relation})).filter(e=>e.s&&e.t),this.simulate(220)}catch{}}simulate(s){const r=()=>{const a=this.nodes;for(let t=0;t<a.length;t++)for(let i=t+1;i<a.length;i++){const e=a[t],o=a[i];let n=e.x-o.x,d=e.y-o.y,u=n*n+d*d||.01;const p=1400/u,f=Math.sqrt(u);n/=f,d/=f,e.vx+=n*p,e.vy+=d*p,o.vx-=n*p,o.vy-=d*p}for(const t of this.edges){let i=t.t.x-t.s.x,e=t.t.y-t.s.y;const o=Math.sqrt(i*i+e*e)||.01,n=(o-90)*.01;i/=o,e/=o,t.s.vx+=i*n,t.s.vy+=e*n,t.t.vx-=i*n,t.t.vy-=e*n}for(const t of this.nodes)t.vx+=(this.W/2-t.x)*.002,t.vy+=(this.H/2-t.y)*.002,t.vx*=.85,t.vy*=.85,t.x=Math.max(20,Math.min(this.W-20,t.x+t.vx)),t.y=Math.max(20,Math.min(this.H-20,t.y+t.vy));this.requestUpdate(),--s>0&&(this.raf=requestAnimationFrame(r))};this.raf=requestAnimationFrame(r)}dim(s){const r=this.query.toLowerCase(),a=this.nodes.find(t=>t.id===s);return this.focus?s===this.focus?!1:!this.edges.some(t=>t.s.id===this.focus&&t.t.id===s||t.t.id===this.focus&&t.s.id===s):r&&a?!a.name.toLowerCase().includes(r):!1}render(){return g`
      <div class="bar">
        <h2>Memory graph</h2>
        <span class="s">${this.stats.total_entities??this.nodes.length} entities · ${this.edges.length} links</span>
        <input placeholder="Search entities…" @input=${s=>{this.query=s.target.value,this.focus=null}} />
      </div>
      <div class="canvas">
        <svg viewBox="0 0 ${this.W} ${this.H}" @click=${s=>{s.target.tagName==="svg"&&(this.focus=null)}}>
          ${this.edges.map(s=>v`<line x1=${s.s.x} y1=${s.s.y} x2=${s.t.x} y2=${s.t.y}
            stroke="var(--ds-border-strong)" stroke-width="1"
            opacity=${this.dim(s.s.id)||this.dim(s.t.id)?.05:.35}></line>`)}
          ${this.nodes.map(s=>{const r=Math.min(5+s.deg*1.6,16),a=this.dim(s.id);return v`
              <circle cx=${s.x} cy=${s.y} r=${r}
                fill=${x[s.type]??"var(--ds-text-muted)"}
                opacity=${a?.12:.92}
                @click=${()=>this.focus=this.focus===s.id?null:s.id}></circle>
              ${(s.deg>=2||this.focus===s.id)&&!a?v`<text x=${s.x+r+2} y=${s.y+3} font-size="9">${s.name}</text>`:""}
            `})}
        </svg>
      </div>
      <div class="legend">
        ${Object.entries(x).map(([s,r])=>g`<span><i style="background:${r}"></i>${s}</span>`)}
      </div>
    `}};c.styles=m`
    :host { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); max-width: 1000px; margin: 0 auto; }
    .bar { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .bar h2 { font-size: var(--ds-text-lg); margin: 0; }
    .bar .s { color: var(--ds-text-muted); font-size: var(--ds-text-sm); font-family: var(--ds-font-mono); }
    input {
      padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2);
      color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-sm); width: 220px;
    }
    input:focus { outline: none; border-color: var(--ds-border-accent); }
    .canvas { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    text { font-family: var(--ds-font-sans); fill: var(--ds-text-soft); pointer-events: none; }
    circle { cursor: pointer; transition: r var(--ds-dur-fast); }
    .legend { display: flex; gap: var(--ds-space-3); flex-wrap: wrap; font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
  `;l([h()],c.prototype,"nodes",2);l([h()],c.prototype,"edges",2);l([h()],c.prototype,"query",2);l([h()],c.prototype,"focus",2);l([h()],c.prototype,"stats",2);c=l([b("memory-graph")],c);export{c as MemoryGraph};
//# sourceMappingURL=memory-graph-BPOZ9GUb.js.map
