import{i as z,G as m,M as E,N as H,d as l,e as _,r as n,t as q}from"./index-D32vtdTm.js";import{r as k,o as M,k as Q}from"./math-CqjoxtmL.js";import"./ds-panel-CCjNIXTY.js";import"./ds-button-CT02qjUn.js";var S=Object.defineProperty,P=Object.getOwnPropertyDescriptor,p=(e,r,t,o)=>{for(var i=o>1?void 0:o?P(r,t):r,c=e.length-1,u;c>=0;c--)(u=e[c])&&(i=(o?u(r,t,i):u(i))||i);return o&&i&&S(r,t,i),i};function C(e){const r=e.replace(/\^/g,"**").replace(/\b(sin|cos|tan|asin|acos|atan|sqrt|abs|log|log2|log10|exp|sign|floor|ceil|round|cbrt|sinh|cosh|tanh)\b/g,"Math.$1").replace(/\bpi\b/gi,"Math.PI").replace(/\be\b/g,"Math.E").replace(/\bln\b/g,"Math.log");if(/[^0-9x+\-*/().,%\sMathPIE_a-z]/i.test(r))return null;try{const t=new Function("x",`"use strict"; return (${r});`);return typeof t(1)!="number"||Number.isNaN(t(1))&&Number.isNaN(t(.5)),t}catch{return null}}let a=class extends z{constructor(){super(...arguments),this.expr="sin(x) * x",this.xmin=-10,this.xmax=10,this.error="",this.computeQ="derivative of x^3 + 2x",this.computeOut="",this.computeTeX="",this.computeTeXExpr="",this.computing=!1}plot(){const t=C(this.expr);if(!t)return this.error="invalid expression",m``;const o=this.xmin,i=this.xmax,c=480,u=[],$=[];for(let s=0;s<=c;s++){const d=o+s/c*(i-o);let O=NaN;try{O=t(d)}catch{}u.push(d),$.push(O)}const y=$.filter(s=>Number.isFinite(s));if(!y.length)return this.error="no finite values in range",m``;this.error="";let x=Math.min(...y),v=Math.max(...y);x===v&&(x-=1,v+=1);const T=(v-x)*.08;x-=T,v+=T;const h=s=>(s-o)/(i-o)*720,f=s=>380-(s-x)/(v-x)*380;let X="",w=!1;for(let s=0;s<=c;s++){const d=$[s];if(!Number.isFinite(d)||f(d)<-380||f(d)>2*380){w=!1;continue}X+=`${w?"L":"M"}${h(u[s]).toFixed(1)},${f(d).toFixed(1)} `,w=!0}const g=h(0),b=f(0),N=[];for(let s=Math.ceil(o);s<=i;s++)N.push(m`<line class="grid" x1=${h(s)} y1="0" x2=${h(s)} y2=${380}></line>`);return m`
      <svg viewBox="0 0 ${720} ${380}">
        ${N}
        ${b>=0&&b<=380?m`<line class="axis" x1="0" y1=${b} x2=${720} y2=${b}></line>`:""}
        ${g>=0&&g<=720?m`<line class="axis" x1=${g} y1="0" x2=${g} y2=${380}></line>`:""}
        <path class="curve" d=${X}></path>
      </svg>`}async runCompute(){this.computing=!0,this.computeOut="",this.computeTeX="",this.computeTeXExpr="";try{const e=await E(this.computeQ);if(e.ok&&e.result)this.computeOut=`${e.expression} = ${e.result}
(${e.kind}, verified by ${e.engine})`,e.latex&&(this.computeTeX=k(e.latex,!0)),e.latex_expr&&(this.computeTeXExpr=k(e.latex_expr,!0));else{const r=await H(this.computeQ);this.computeOut=r.verbal||JSON.stringify(r.result??r,null,1),r.latex&&(this.computeTeX=k(r.latex,!0))}}catch(e){this.computeOut="compute failed: "+String(e)}this.computing=!1}render(){const e=["sin(x) * x","x^2 - 4","1/x","exp(-x*x)","tan(x)","sqrt(abs(x))"],r=["solve x^2 - 5x + 6 = 0","integrate x^2","factor x^2 - 9","what is 2^20"];return l`
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
        ${this.error?l`<div class="err">${this.error}</div>`:""}
        <div class="plot" style="margin-top:var(--ds-space-3)">${this.plot()}</div>
        <div class="chips">${e.map(t=>l`<span class="chip" @click=${()=>{this.expr=t}}>${t}</span>`)}</div>
      </ds-panel>

      <ds-panel heading="Symbolic & science compute · live engine">
        <div class="compute">
          <textarea .value=${this.computeQ} @input=${t=>{this.computeQ=t.target.value}}></textarea>
          <div class="chips">${r.map(t=>l`<span class="chip" @click=${()=>{this.computeQ=t}}>${t}</span>`)}</div>
          <div style="margin-top:var(--ds-space-2)"><ds-button variant="primary" @click=${()=>void this.runCompute()}>${this.computing?"computing…":"compute"}</ds-button></div>
          ${this.computeTeX?l`<div class="tex-block">
                ${this.computeTeXExpr?l`<div class="tex-expr">${M(this.computeTeXExpr)}</div>`:""}
                ${M(this.computeTeX)}
              </div>`:""}
          ${this.computeOut?l`<div class="out">${this.computeOut}</div>`:""}
        </div>
      </ds-panel>
    `}};a.styles=[Q,_`
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
    .tex-block { margin-top: var(--ds-space-3); padding: var(--ds-space-3) var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border-accent); border-radius: var(--ds-radius-md); overflow-x: auto; }
    .tex-block .katex { color: var(--ds-text); font-size: 1.25em; }
    .tex-expr { color: var(--ds-text-muted); margin-bottom: var(--ds-space-2); padding-bottom: var(--ds-space-2); border-bottom: 1px dashed var(--ds-border); }
    .tex-expr .katex { font-size: 1em; }
    .tex-error { color: var(--ds-danger); font-family: var(--ds-font-mono); }
  `];p([n()],a.prototype,"expr",2);p([n()],a.prototype,"xmin",2);p([n()],a.prototype,"xmax",2);p([n()],a.prototype,"error",2);p([n()],a.prototype,"computeQ",2);p([n()],a.prototype,"computeOut",2);p([n()],a.prototype,"computeTeX",2);p([n()],a.prototype,"computeTeXExpr",2);p([n()],a.prototype,"computing",2);a=p([q("calc-view")],a);export{a as CalcView};
//# sourceMappingURL=calc-view-Cp2n9NRU.js.map
