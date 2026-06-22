import{m as u,V as h,W as v,g as n,X as g,Y as m,d as a,i as b,e as f,r as o,t as x}from"./index-BZpHEIVQ.js";import"./ds-panel-B0Coku7q.js";import"./ds-button-X_d22ss4.js";var y=Object.defineProperty,w=Object.getOwnPropertyDescriptor,i=(s,e,d,l)=>{for(var r=l>1?void 0:l?w(e,d):e,c=s.length-1,p;c>=0;c--)(p=s[c])&&(r=(l?p(e,d,r):p(r))||r);return l&&r&&y(e,d,r),r};let t=class extends u(b){constructor(){super(...arguments),this.inbox=null,this.awaiting=[],this.searchQuery="",this.searchResults=[],this.loading=!0,this.showCompose=!1}connectedCallback(){super.connectedCallback(),this.load()}async load(){this.loading=!0;try{const s=await h(15);s.ok?this.inbox={unread_count:s.unread_count,recent:s.recent,verbal:s.verbal}:this.inbox={unread_count:0,recent:[],verbal:s.verbal},this.awaiting=(await v()).threads}catch{n("Email load failed","danger"),this.inbox={unread_count:0,recent:[],verbal:"Email not configured."}}this.loading=!1}async doSearch(){if(this.searchQuery.trim())try{const s=await g(this.searchQuery,10);this.searchResults=s.ok?s.results:[]}catch{n("Search failed","danger")}}async onSend(s){s.preventDefault();const e=new FormData(s.target);try{const d=await m({to:String(e.get("to")||""),subject:String(e.get("subject")||""),body:String(e.get("body")||"")});d.ok?(n("Sent","success"),this.showCompose=!1):n(d.verbal||"Send failed","danger")}catch{n("Send failed","danger")}}render(){if(this.loading)return a`<div class="muted">Loading email…</div>`;const s=this.inbox;return a`
      <ds-panel heading="Email">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);">
          <ds-button size="sm" @click=${()=>this.showCompose=!this.showCompose}>${this.showCompose?"cancel":"compose"}</ds-button>
          <ds-button size="sm" @click=${()=>void this.load()}>refresh</ds-button>
        </div>
        ${s?a`<p class="muted" style="margin:0;">${s.verbal}</p>`:""}
      </ds-panel>

      ${this.showCompose?a`
        <form class="form" @submit=${this.onSend}>
          <input type="email" name="to" placeholder="To" required />
          <input type="text" name="subject" placeholder="Subject" required />
          <textarea name="body" placeholder="Message…" required></textarea>
          <ds-button variant="primary" type="submit">Send</ds-button>
        </form>
      `:""}

      <div class="search">
        <input type="text" placeholder="Search emails…" .value=${this.searchQuery} @input=${e=>{this.searchQuery=e.target.value}} @keydown=${e=>{e.key==="Enter"&&this.doSearch()}} />
        <ds-button @click=${()=>void this.doSearch()}>Search</ds-button>
      </div>

      ${this.searchResults.length>0?a`
        <ds-panel heading="Search Results · ${this.searchResults.length}">
          ${this.searchResults.map(e=>a`
            <div class="msg">
              <div><div class="from">${e.sender}</div><div class="subj">${e.subject}</div></div>
              <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);white-space:nowrap;">${e.date}</span>
            </div>
          `)}
        </ds-panel>
      `:""}

      <div class="grid">
        <ds-panel heading="Inbox · ${(s==null?void 0:s.unread_count)??0} unread">
          ${s&&s.recent.length?a`
            ${s.recent.map(e=>a`
              <div class="msg">
                ${e.unread?a`<div class="unread"></div>`:a`<div style="width:6px;"></div>`}
                <div style="flex:1;"><div class="from">${e.sender}</div><div class="subj">${e.subject}</div></div>
                <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);white-space:nowrap;">${e.date}</span>
              </div>
            `)}
          `:a`<span class="muted">No recent messages.</span>`}
        </ds-panel>
        <ds-panel heading="Awaiting Replies · ${this.awaiting.length}">
          ${this.awaiting.length?a`
            ${this.awaiting.map(e=>a`
              <div class="msg">
                <div style="flex:1;"><div class="from">${e.sender}</div><div class="subj">${e.subject}</div></div>
                ${e.notes?a`<span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);">${e.notes}</span>`:""}
              </div>
            `)}
          `:a`<span class="muted">Nothing flagged for follow-up.</span>`}
        </ds-panel>
      </div>
    `}};t.styles=f`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1000px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--ds-space-3); }
    .search { display: flex; gap: var(--ds-space-2); }
    .search input { flex: 1; padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); color: var(--ds-text); }
    .msg { display: flex; justify-content: space-between; align-items: flex-start; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); gap: var(--ds-space-3); }
    .msg:last-child { border-bottom: 0; }
    .msg .from { font-weight: 500; font-size: var(--ds-text-sm); }
    .msg .subj { font-size: var(--ds-text-xs); color: var(--ds-text-soft); }
    .msg .unread { width: 6px; height: 6px; border-radius: 50%; background: var(--ds-accent); flex-shrink: 0; margin-top: 6px; }
    .form { display: grid; gap: var(--ds-space-3); padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); }
    .form input, .form textarea { padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); font-family: inherit; }
    .form textarea { min-height: 120px; resize: vertical; }
  `;i([o()],t.prototype,"inbox",2);i([o()],t.prototype,"awaiting",2);i([o()],t.prototype,"searchQuery",2);i([o()],t.prototype,"searchResults",2);i([o()],t.prototype,"loading",2);i([o()],t.prototype,"showCompose",2);t=i([x("email-view")],t);export{t as EmailView};
//# sourceMappingURL=email-view-CU2o6-X2.js.map
