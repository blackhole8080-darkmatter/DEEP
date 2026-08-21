import{c as v,i as u,d as c,f as m,g,b as o,p as h,a as b,r as p,t as f}from"./index-CBQjtX3d.js";import"./ds-panel-CZBUV-lc.js";var x=Object.defineProperty,y=Object.getOwnPropertyDescriptor,l=(e,s,t,r)=>{for(var a=r>1?void 0:r?y(s,t):s,i=e.length-1,n;i>=0;i--)(n=e[i])&&(a=(r?n(s,t,a):n(a))||a);return r&&a&&x(s,t,a),a};let d=class extends v(u){constructor(){super(...arguments),this.outcomes={},this.busy=new Set}connectedCallback(){super.connectedCallback(),c(),this.ticker=setInterval(()=>this.requestUpdate(),1e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.ticker)}setBusy(e,s){const t=new Set(this.busy);s?t.add(e):t.delete(e),this.busy=t}async approve(e){this.setBusy(e.id,!0);try{const s=await m(e.id);this.outcomes={...this.outcomes,[e.id]:s.ok?{kind:"approved",text:s.result||"Done."}:{kind:"failed",text:s.result||"The tool reported a failure."}}}catch(s){this.outcomes={...this.outcomes,[e.id]:{kind:"failed",text:s.message}}}finally{this.setBusy(e.id,!1),c()}}async reject(e){this.setBusy(e.id,!0);try{await g(e.id),this.outcomes={...this.outcomes,[e.id]:{kind:"rejected",text:"Declined. Nothing ran."}}}catch(s){this.outcomes={...this.outcomes,[e.id]:{kind:"failed",text:s.message}}}finally{this.setBusy(e.id,!1),c()}}dismiss(e){const s={...this.outcomes};delete s[e],this.outcomes=s}static countdown(e){if(e<=0)return"expired";const s=Math.floor(e/60),t=e%60;return s>0?`${s}m ${String(t).padStart(2,"0")}s`:`${t}s`}renderCard(e){const s=this.outcomes[e.id],t=this.busy.has(e.id),r=e.expires_in_s<=0;return o`
      <ds-panel heading=${e.tool}>
        <div class="card">
          <div class="label">${e.label}</div>
          ${e.detail?o`<div class="detail">${e.detail}</div>`:""}

          <div class="args">
            ${Object.entries(e.args).map(([a,i])=>o`<div class="arg"><span class="k">${a}</span><span class="v">${String(i)}</span></div>`)}
          </div>

          ${s?o`
                <div class="outcome ${s.kind}">
                  <span class="head">
                    ${s.kind==="approved"?"Approved and run":""}
                    ${s.kind==="rejected"?"Rejected":""}
                    ${s.kind==="failed"?"Did not run":""}
                  </span>
                  <pre>${s.text}</pre>
                  <button class="dismiss" @click=${()=>this.dismiss(e.id)}>Dismiss</button>
                </div>
              `:o`
                <div class="meta">
                  <span class=${e.expires_in_s<120?"soon":""}>
                    ${r?"expired — ask DEEP again":`expires in ${d.countdown(e.expires_in_s)}`}
                  </span>
                </div>
                <div class="actions">
                  <button class="approve" ?disabled=${t||r} @click=${()=>this.approve(e)}>
                    ${t?"Working…":"Approve"}
                  </button>
                  <button class="reject" ?disabled=${t} @click=${()=>this.reject(e)}>Reject</button>
                </div>
              `}
        </div>
      </ds-panel>
    `}render(){const e=h.get(),s=Object.keys(this.outcomes).filter(t=>!e.some(r=>r.id===t));return o`
      <div class="lede">
        Actions DEEP wants to take that reach outside this machine, or that it
        cannot undo.
        ${e.length>0?o`Nothing below has run yet.`:""}
      </div>

      ${e.length===0&&s.length===0?o`
            <div class="empty">
              <span class="glyph">✓</span>
              <span>Nothing waiting on you.</span>
            </div>
          `:""}

      ${e.map(t=>this.renderCard(t))}
      ${s.map(t=>{const r=this.outcomes[t];return o`
          <ds-panel>
            <div class="outcome ${r.kind}">
              <span class="head">
                ${r.kind==="approved"?"Approved and run":""}
                ${r.kind==="rejected"?"Rejected":""}
                ${r.kind==="failed"?"Did not run":""}
              </span>
              <pre>${r.text}</pre>
              <button class="dismiss" @click=${()=>this.dismiss(t)}>Dismiss</button>
            </div>
          </ds-panel>
        `})}
    `}};d.styles=b`
    :host {
      display: grid; gap: var(--ds-space-4);
      padding: var(--ds-space-5); max-width: 860px; margin: 0 auto;
      align-content: start;
    }
    .lede { font-size: var(--ds-text-sm); color: var(--ds-text-muted); line-height: 1.5; }
    .empty {
      display: grid; gap: var(--ds-space-2); justify-items: center;
      padding: var(--ds-space-6) var(--ds-space-4);
      color: var(--ds-text-muted); text-align: center;
    }
    .empty .glyph { font-size: var(--ds-text-xl); opacity: 0.6; }

    .card { display: grid; gap: var(--ds-space-3); }
    .label { font-size: var(--ds-text-md); font-weight: 600; color: var(--ds-text); line-height: 1.4; word-break: break-word; }
    .detail {
      font-size: var(--ds-text-sm); line-height: 1.55; color: var(--ds-text-soft);
      padding: var(--ds-space-3);
      border-left: 2px solid var(--ds-warning);
      background: rgba(255, 176, 32, 0.06);
      border-radius: 0 var(--ds-radius-sm) var(--ds-radius-sm) 0;
    }
    .args {
      display: grid; gap: 2px;
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-soft);
    }
    .arg { display: grid; grid-template-columns: 96px 1fr; gap: var(--ds-space-2); }
    .arg .k { color: var(--ds-text-muted); }
    .arg .v { word-break: break-all; }

    .meta {
      display: flex; flex-wrap: wrap; align-items: center; gap: var(--ds-space-3);
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
    }
    .soon { color: var(--ds-warning); }

    .actions { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    button {
      font: inherit; font-size: var(--ds-text-sm); font-weight: 600;
      padding: var(--ds-space-2) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-2);
      color: var(--ds-text);
      cursor: pointer;
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    button:hover:not(:disabled) { border-color: var(--ds-border-strong); background: var(--ds-surface-3, var(--ds-surface-2)); }
    button:disabled { opacity: 0.5; cursor: default; }
    button:focus-visible { outline: 2px solid var(--ds-accent); outline-offset: 2px; }
    /* Approve and Reject are weighted the same on purpose — see the header. */
    .approve:hover:not(:disabled) { border-color: var(--ds-success); color: var(--ds-success); }
    .reject:hover:not(:disabled)  { border-color: var(--ds-danger);  color: var(--ds-danger); }

    .outcome {
      display: grid; gap: var(--ds-space-2);
      padding: var(--ds-space-3);
      border-radius: var(--ds-radius-md);
      font-size: var(--ds-text-sm);
      border: 1px solid var(--ds-border);
    }
    .outcome pre {
      margin: 0; white-space: pre-wrap; word-break: break-word;
      font-family: var(--ds-font-mono); font-size: var(--ds-text-xs);
      color: var(--ds-text-soft);
    }
    .outcome.approved { border-color: var(--ds-success); background: rgba(0,255,174,0.06); }
    .outcome.rejected { border-color: var(--ds-border-strong); }
    .outcome.failed   { border-color: var(--ds-danger);  background: rgba(255,45,120,0.06); }
    .outcome .head { font-weight: 600; }
    .outcome.approved .head { color: var(--ds-success); }
    .outcome.failed .head    { color: var(--ds-danger); }
    .outcome .dismiss { justify-self: start; }
  `;l([p()],d.prototype,"outcomes",2);l([p()],d.prototype,"busy",2);d=l([f("approvals-view")],d);export{d as ApprovalsView};
//# sourceMappingURL=approvals-view-D0R9AptX.js.map
