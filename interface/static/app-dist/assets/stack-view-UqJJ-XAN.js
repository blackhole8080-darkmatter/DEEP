import{i as h,L as p,d as r,e as m,r as c,t as v}from"./index-D32vtdTm.js";import"./ds-panel-CCjNIXTY.js";import"./ds-button-CT02qjUn.js";var u=Object.defineProperty,g=Object.getOwnPropertyDescriptor,d=(a,s,e,t)=>{for(var o=t>1?void 0:t?g(s,e):s,n=a.length-1,i;n>=0;n--)(i=a[n])&&(o=(t?i(s,e,o):i(o))||o);return t&&o&&u(s,e,o),o};let l=class extends h{constructor(){super(...arguments),this.data=null,this.loading=!0,this.hours=24}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0;try{this.data=await p(this.hours)}catch(a){this.data={error:String(a)}}this.loading=!1}stat(a,s,e=!1){return r`<div class="stat"><div class="v ${e?"warn":""}">${s??"—"}</div><div class="k">${a}</div></div>`}render(){const a=this.data,s=a==null?void 0:a.llm,e=a==null?void 0:a.tools;return r`
      <ds-panel heading="DEEP stack telemetry · model + orchestration layers">
        <div class="head">
          <span class="muted">${this.loading?"loading…":`last ${this.hours}h`}</span>
          <div style="display:flex;gap:var(--ds-space-2);align-items:center">
            <select @change=${t=>{this.hours=+t.target.value,this.load()}}>
              <option value="1">1h</option><option value="24" selected>24h</option><option value="168">7d</option>
            </select>
            <ds-button @click=${()=>void this.load()}>refresh</ds-button>
          </div>
        </div>
        ${a!=null&&a.error?r`<div class="err">${a.error}</div>`:""}
      </ds-panel>

      <ds-panel heading="Model layer · LLM routing">
        ${s&&s.total_calls?r`
          <div class="stats">
            ${this.stat("calls",s.total_calls)}
            ${this.stat("ok",s.ok)}
            ${this.stat("fallthroughs",s.fallthroughs,s.fallthroughs>0)}
            ${this.stat("p50",s.p50_ms!=null?`${s.p50_ms}ms`:"—")}
            ${this.stat("~tokens",(s.est_tokens??0).toLocaleString())}
            ${this.stat("~cost",`$${(s.est_cost_usd??0).toFixed(4)}`)}
          </div>
          <table>
            <tr><th>provider:model</th><th class="num">calls</th><th class="num">ok</th><th class="num">p50</th><th class="num">~tok</th><th class="num">~cost</th></tr>
            ${s.providers.map(t=>r`<tr>
              <td>${t.provider}</td><td class="num">${t.calls}</td>
              <td class="num ${t.ok<t.calls?"err":""}">${t.ok}</td>
              <td class="num">${t.p50_ms??"—"}</td>
              <td class="num">${(t.tokens??0).toLocaleString()}</td>
              <td class="num">$${(t.cost??0).toFixed(4)}</td>
            </tr>`)}
          </table>
          <div class="muted" style="margin-top:var(--ds-space-2);font-size:var(--ds-text-xs)">Tokens & cost are estimates (~4 chars/token × published rates), not billed figures.</div>
        `:r`<span class="muted">No LLM calls recorded yet — send a chat message.</span>`}
      </ds-panel>

      <ds-panel heading="Orchestration layer · tool calls">
        ${e&&e.total_calls?r`
          <div class="stats">
            ${this.stat("calls",e.total_calls)}
            ${this.stat("errors",e.errors,e.errors>0)}
          </div>
          <table>
            <tr><th>tool</th><th class="num">calls</th><th class="num">errors</th><th class="num">p50</th><th class="num">p95</th></tr>
            ${e.by_tool.map(t=>r`<tr>
              <td class="name">${t.name}</td><td class="num">${t.calls}</td>
              <td class="num ${t.errors?"err":""}">${t.errors}</td>
              <td class="num">${t.p50_ms??"—"}</td><td class="num">${t.p95_ms??"—"}</td>
            </tr>`)}
          </table>
        `:r`<span class="muted">No tool calls recorded yet — ask DEEP something that uses a tool.</span>`}
      </ds-panel>
    `}};l.styles=m`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: var(--ds-space-3); }
    .muted { color: var(--ds-text-muted); }
    .stats { display: flex; gap: var(--ds-space-5); flex-wrap: wrap; margin-bottom: var(--ds-space-3); }
    .stat .v { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); color: var(--ds-accent); }
    .stat .v.warn { color: var(--ds-warning); }
    .stat .k { font-size: var(--ds-text-xs); color: var(--ds-text-soft); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); }
    table { width: 100%; border-collapse: collapse; font-size: var(--ds-text-sm); }
    th, td { text-align: left; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); }
    th { color: var(--ds-text-soft); font-size: var(--ds-text-xs); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); font-weight: 500; }
    td { font-family: var(--ds-font-mono); }
    td.name { font-family: var(--ds-font-sans); }
    .num { text-align: right; }
    .err { color: var(--ds-danger); }
    select { background: var(--ds-surface-2); color: var(--ds-text); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); padding: 2px 8px; font-family: var(--ds-font-mono); }
  `;d([c()],l.prototype,"data",2);d([c()],l.prototype,"loading",2);d([c()],l.prototype,"hours",2);l=d([v("stack-view")],l);export{l as StackView};
//# sourceMappingURL=stack-view-UqJJ-XAN.js.map
