import{i as v,g as c,d as e,e as g,r as p,t as f}from"./index-Cnh7q9sv.js";import"./ds-panel-h3qMLIrJ.js";import"./ds-button-p2sgz0xK.js";var u=Object.defineProperty,h=Object.getOwnPropertyDescriptor,n=(s,r,i,t)=>{for(var a=t>1?void 0:t?h(r,i):r,o=s.length-1,l;o>=0;o--)(l=s[o])&&(a=(t?l(r,i,a):l(a))||a);return t&&a&&u(r,i,a),a};let d=class extends v{constructor(){super(...arguments),this.world=null,this.refreshing=!1}connectedCallback(){super.connectedCallback(),this.load()}async load(){try{this.world=await(await fetch("/api/world")).json()}catch{}}async refresh(){this.refreshing=!0;try{await fetch("/api/world/refresh",{method:"POST"}),await this.load(),c("World model refreshed","success")}catch{c("Refresh failed","danger")}this.refreshing=!1}render(){const s=this.world;return s?e`
      <ds-panel heading="What Aryan is building">
        <p class="summary">${s.summary}</p>
        <div slot="actions"><ds-button size="sm" @click=${()=>void this.refresh()}>${this.refreshing?"…":"refresh"}</ds-button></div>
      </ds-panel>

      ${s.current_focus?e`<div class="focus"><div class="k">current focus</div><div class="v">${s.current_focus}</div></div>`:""}

      <ds-panel heading="Projects · ${s.projects.length}">
        <div class="cards">${s.projects.map(r=>e`<div class="card">${r}</div>`)}</div>
      </ds-panel>

      <ds-panel heading="Priorities">
        <div class="list">${s.priorities.map(r=>e`<div class="item">${r}</div>`)}</div>
      </ds-panel>

      <ds-panel heading="Interests">
        <div class="tags">${s.interests.map(r=>e`<span class="tag">${r}</span>`)}</div>
      </ds-panel>
    `:e`<ds-panel heading="Projects"><span class="muted">loading world model…</span></ds-panel>`}};d.styles=g`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .summary { font-size: var(--ds-text-lg); line-height: var(--ds-leading-normal); color: var(--ds-text-soft); }
    .focus { padding: var(--ds-space-4); background: linear-gradient(135deg, rgba(var(--ds-periwinkle-rgb),0.12), transparent); border: 1px solid var(--ds-border-accent); border-radius: var(--ds-radius-md); }
    .focus .k { font-size: var(--ds-text-xs); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); color: var(--ds-accent); }
    .focus .v { font-size: var(--ds-text-lg); margin-top: 4px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--ds-space-3); }
    .card { padding: var(--ds-space-4); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-left: 2px solid var(--ds-accent); border-radius: var(--ds-radius-md); font-weight: 600; }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-2); }
    .tag { padding: 3px 12px; border: 1px solid var(--ds-border); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .list { display: grid; gap: var(--ds-space-2); }
    .item { display: flex; gap: var(--ds-space-2); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    .item::before { content: "▸"; color: var(--ds-accent); }
    .muted { color: var(--ds-text-muted); }
  `;n([p()],d.prototype,"world",2);n([p()],d.prototype,"refreshing",2);d=n([f("projects-view")],d);export{d as ProjectsView};
//# sourceMappingURL=projects-view-r0pVGyPM.js.map
