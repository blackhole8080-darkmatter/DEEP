import{a as u,c,b as o,i as v,r as p,e as h,t as g}from"./index-CUIHgJB1.js";import"./ds-panel-Dgug3kt1.js";var b=Object.defineProperty,f=Object.getOwnPropertyDescriptor,d=(s,a,r,n)=>{for(var t=n>1?void 0:n?f(a,r):a,i=s.length-1,l;i>=0;i--)(l=s[i])&&(t=(n?l(a,r,t):l(t))||t);return n&&t&&b(a,r,t),t};const x=["researcher","writer","planner","analyst","coder"];let e=class extends u{constructor(){super(...arguments),this.tasks=[],this.role="planner"}connectedCallback(){super.connectedCallback(),this.poll(),this.timer=setInterval(()=>void this.poll(),4e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async poll(){try{const s=await(await fetch("/api/agents/tasks")).json();this.tasks=s.tasks??[]}catch{}}async launch(){const s=this.ta.value.trim();if(s)try{const a=await fetch("/api/agents/task",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({role:this.role,task:s})}),r=await a.json();a.ok?(c(`Agent launched (${this.role})`,"success"),this.ta.value="",this.poll()):c(`Launch failed: ${r.detail??a.status}`,"danger")}catch{c("Launch failed","danger")}}render(){return o`
      <ds-panel heading="Launch agent mission">
        <div class="launch">
          <div class="roles">
            ${x.map(s=>o`
                <button class="chip ${this.role===s?"on":""}" @click=${()=>this.role=s}>${s}</button>
              `)}
          </div>
          <textarea placeholder="Describe the mission… e.g. 'Plan a study schedule for my exams next month'"></textarea>
          <ds-button variant="primary" @click=${()=>void this.launch()}>Launch</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Task board · ${this.tasks.length} task${this.tasks.length===1?"":"s"}">
        ${this.tasks.length?this.tasks.map(s=>o`
                <div class="task">
                  <div class="head">
                    <b>${s.role??"agent"}</b>
                    <span class="status ${String(s.status??"").toLowerCase()}">${s.status??"?"}${s.progress!=null?` · ${s.progress}`:""}</span>
                  </div>
                  <span class="desc">${s.task??""}</span>
                  ${s.result?o`<div class="result">${String(s.result).slice(0,600)}</div>`:""}
                </div>
              `):o`<span class="muted">No agent tasks yet. Launch one above — it runs in the background on the live system.</span>`}
      </ds-panel>
    `}};e.styles=v`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 860px; margin: 0 auto; align-content: start; }
    .launch { display: grid; gap: var(--ds-space-3); }
    textarea {
      width: 100%; min-height: 64px; resize: vertical;
      background: var(--ds-surface-2); color: var(--ds-text);
      border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      padding: var(--ds-space-3); font-family: var(--ds-font-sans); font-size: var(--ds-text-sm);
    }
    textarea:focus { outline: none; border-color: var(--ds-border-accent); }
    .roles { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; align-items: center; }
    .chip {
      padding: 3px 12px; border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border); background: none;
      color: var(--ds-text-soft); font-size: var(--ds-text-xs); cursor: pointer;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .chip.on { background: rgba(var(--ds-periwinkle-rgb), 0.16); border-color: var(--ds-border-accent); color: var(--ds-text); }
    .task {
      display: grid; gap: 4px;
      padding: var(--ds-space-3) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .task:last-child { border-bottom: none; }
    .head { display: flex; justify-content: space-between; gap: var(--ds-space-3); }
    .status { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .status.running { color: var(--ds-info); }
    .status.done, .status.completed { color: var(--ds-success); }
    .status.failed, .status.error { color: var(--ds-danger); }
    .desc { color: var(--ds-text-soft); }
    .result { color: var(--ds-text-muted); font-size: var(--ds-text-xs); white-space: pre-wrap; max-height: 120px; overflow-y: auto; }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;d([p()],e.prototype,"tasks",2);d([p()],e.prototype,"role",2);d([h("textarea")],e.prototype,"ta",2);e=d([g("agents-view")],e);export{e as AgentsView};
//# sourceMappingURL=agents-view-Cc_PNVal.js.map
