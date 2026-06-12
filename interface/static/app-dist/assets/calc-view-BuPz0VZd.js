import{a as M,w as x,s as q,u as z,b as m,i as Q,r as d,t as _}from"./index-TJd2YPHQ.js";import"./ds-panel-Dqkt3HLT.js";var P=Object.defineProperty,S=Object.getOwnPropertyDescriptor,n=(e,r,t,i)=>{for(var a=i>1?void 0:i?S(r,t):r,p=e.length-1,l;p>=0;p--)(l=e[p])&&(a=(i?l(r,t,a):l(a))||a);return i&&a&&P(r,t,a),a};function C(e){const r=e.replace(/\^/g,"**").replace(/\b(sin|cos|tan|asin|acos|atan|sqrt|abs|log|log2|log10|exp|sign|floor|ceil|round|cbrt|sinh|cosh|tanh)\b/g,"Math.$1").replace(/\bpi\b/gi,"Math.PI").replace(/\be\b/g,"Math.E").replace(/\bln\b/g,"Math.log");if(/[^0-9x+\-*/().,%\sMathPIE_a-z]/i.test(r))return null;try{const t=new Function("x",`"use strict"; return (${r});`);return typeof t(1)!="number"||Number.isNaN(t(1))&&Number.isNaN(t(.5)),t}catch{return null}}let o=class extends M{constructor(){super(...arguments),this.expr="sin(x) * x",this.xmin=-10,this.xmax=10,this.error="",this.computeQ="derivative of x^3 + 2x",this.computeOut="",this.computing=!1}plot(){const t=C(this.expr);if(!t)return this.error="invalid expression",x``;const i=this.xmin,a=this.xmax,p=480,l=[],$=[];for(let s=0;s<=p;s++){const c=i+s/p*(a-i);let H=NaN;try{H=t(c)}catch{}l.push(c),$.push(H)}const y=$.filter(s=>Number.isFinite(s));if(!y.length)return this.error="no finite values in range",x``;this.error="";let u=Math.min(...y),v=Math.max(...y);u===v&&(u-=1,v+=1);const O=(v-u)*.08;u-=O,v+=O;const h=s=>(s-i)/(a-i)*720,f=s=>380-(s-u)/(v-u)*380;let k="",w=!1;for(let s=0;s<=p;s++){const c=$[s];if(!Number.isFinite(c)||f(c)<-380||f(c)>2*380){w=!1;continue}k+=`${w?"L":"M"}${h(l[s]).toFixed(1)},${f(c).toFixed(1)} `,w=!0}const g=h(0),b=f(0),N=[];for(let s=Math.ceil(i);s<=a;s++)N.push(x`<line class="grid" x1=${h(s)} y1="0" x2=${h(s)} y2=${380}></line>`);return x`
      <svg viewBox="0 0 ${720} ${380}">
        ${N}
        ${b>=0&&b<=380?x`<line class="axis" x1="0" y1=${b} x2=${720} y2=${b}></line>`:""}
        ${g>=0&&g<=720?x`<line class="axis" x1=${g} y1="0" x2=${g} y2=${380}></line>`:""}
        <path class="curve" d=${k}></path>
      </svg>`}async runCompute(){this.computing=!0,this.computeOut="";try{const e=await q(this.computeQ);if(e.ok&&e.result)this.computeOut=`${e.expression} = ${e.result}
(${e.kind}, verified by ${e.engine})`;else{const r=await z(this.computeQ);this.computeOut=r.verbal||JSON.stringify(r.result??r,null,1)}}catch(e){this.computeOut="compute failed: "+String(e)}this.computing=!1}render(){const e=["sin(x) * x","x^2 - 4","1/x","exp(-x*x)","tan(x)","sqrt(abs(x))"],r=["solve x^2 - 5x + 6 = 0","integrate x^2","factor x^2 - 9","what is 2^20"];return m`
      <ds-panel heading="Graphing calculator">
        <div class="controls">
          <span class="eq">y =</span>
          <input class="fn" .value=${this.expr} @input=${t=>{this.expr=t.target.value}} />
          <span class="eq">x ∈ [</span>
          <input class="rng" type="number" .value=${String(this.xmin)} @input=${t=>{this.xmin=+t.target.value}} />
          <span class="eq">,</span>
          <input class="rng" type="number" .value=${String(this.xmax)} @input=${t=>{this.xmax=+t.target.value}} />
          <span class="eq">]</span>
          <ds-button @click=${()=>this.requestUpdate()}>plot</ds-button>
        </div>
        ${this.error?m`<div class="err">${this.error}</div>`:""}
        <div class="plot" style="margin-top:var(--ds-space-3)">${this.plot()}</div>
        <div class="chips">${e.map(t=>m`<span class="chip" @click=${()=>{this.expr=t}}>${t}</span>`)}</div>
      </ds-panel>

      <ds-panel heading="Symbolic & science compute · live engine">
        <div class="compute">
          <textarea .value=${this.computeQ} @input=${t=>{this.computeQ=t.target.value}}></textarea>
          <div class="chips">${r.map(t=>m`<span class="chip" @click=${()=>{this.computeQ=t}}>${t}</span>`)}</div>
          <div style="margin-top:var(--ds-space-2)"><ds-button variant="primary" @click=${()=>void this.runCompute()}>${this.computing?"computing…":"compute"}</ds-button></div>
          ${this.computeOut?m`<div class="out">${this.computeOut}</div>`:""}
        </div>
      </ds-panel>
    `}};o.styles=Q`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .controls { display: flex; gap: var(--ds-space-2); align-items: center; flex-wrap: wrap; }
    input { padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); }
    input.fn { flex: 1; min-width: 200px; }
    input.rng { width: 64px; }
    .eq { color: var(--ds-text-muted); font-family: var(--ds-font-mono); }
    .plot { background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-lg); overflow: hidden; }
    svg { width: 100%; height: auto; display: block; }
    .axis { stroke: var(--ds-border-strong); stroke-width: 1; }
    .grid { stroke: var(--ds-border); stroke-width: 0.5; }
    .curve { fill: none; stroke: var(--ds-accent); stroke-width: 2; filter: drop-shadow(0 0 4px var(--ds-accent)); }
    .err { color: var(--ds-danger); font-size: var(--ds-text-sm); }
    .compute textarea { width: 100%; min-height: 44px; resize: vertical; background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); padding: var(--ds-space-3); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); }
    .out { margin-top: var(--ds-space-3); padding: var(--ds-space-3); background: var(--ds-surface-2); border-left: 2px solid var(--ds-accent); border-radius: var(--ds-radius-sm); font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); white-space: pre-wrap; }
    .chips { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; margin-top: var(--ds-space-2); }
    .chip { padding: 2px 10px; border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); color: var(--ds-text-soft); cursor: pointer; font-family: var(--ds-font-mono); }
    .chip:hover { border-color: var(--ds-border-accent); color: var(--ds-accent); }
  `;n([d()],o.prototype,"expr",2);n([d()],o.prototype,"xmin",2);n([d()],o.prototype,"xmax",2);n([d()],o.prototype,"error",2);n([d()],o.prototype,"computeQ",2);n([d()],o.prototype,"computeOut",2);n([d()],o.prototype,"computing",2);o=n([_("calc-view")],o);export{o as CalcView};
//# sourceMappingURL=calc-view-BuPz0VZd.js.map
