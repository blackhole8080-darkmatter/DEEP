import{e as T,n as $,r as u,i as M,d,t as N,j as I,k as E,l as j,m as R,o as W,p as V,q as F,s as Y,u as H,v as B,w as U,x as X,y as q,g as L,z as G,A as J,B as C}from"./index-DZt9GVll.js";import"./ds-panel-Suvgx61N.js";import"./ds-button-CZz4S6VZ.js";var Z=Object.defineProperty,K=Object.getOwnPropertyDescriptor,z=(s,a,e,t)=>{for(var r=t>1?void 0:t?K(a,e):a,o=s.length-1,c;o>=0;o--)(c=s[o])&&(r=(t?c(a,e,r):c(r))||r);return t&&r&&Z(a,e,r),r};const O={lan:0,wifi:1,bluetooth:1,vpn:2,internet:3,dns:1,ai:3,cross:0};let k=class extends M{constructor(){super(...arguments),this.nodes=[],this.edges=[],this.visibleLayers=["lan","wifi","bluetooth","vpn","internet","dns","ai","cross"],this.hovered=null,this.selected=null,this.raf=0,this.camera={x:0,y:0,zoom:1},this.isDragging=!1,this.dragNode=null,this.lastMouse={x:0,y:0},this.time=0,this._colors={},this._themeColors={accent:"#00e5ff",threat:"#ef4444"},this._resize=()=>{var a;if(!this.canvas)return;const s=Math.min(window.devicePixelRatio,2);this.canvas.width=this.canvas.clientWidth*s,this.canvas.height=this.canvas.clientHeight*s,(a=this.ctx)==null||a.scale(s,s)},this._loop=()=>{var m,b,x;this.raf=requestAnimationFrame(this._loop),this.time+=1,this._stepPhysics();const s=this.canvas.clientWidth,a=this.canvas.clientHeight,e=this.ctx;e.clearRect(0,0,s,a),e.strokeStyle="rgba(0,229,255,0.03)",e.lineWidth=1;const t=40*this.camera.zoom,r=this.camera.x%t,o=this.camera.y%t;for(let i=r;i<s;i+=t)e.beginPath(),e.moveTo(i,0),e.lineTo(i,a),e.stroke();for(let i=o;i<a;i+=t)e.beginPath(),e.moveTo(0,i),e.lineTo(s,i),e.stroke();e.save(),e.translate(this.camera.x,this.camera.y),e.scale(this.camera.zoom,this.camera.zoom);const c=this.nodes.filter(i=>this.visibleLayers.includes(i.layer)),n=new Map(c.map(i=>[i.id,i])),l=this.edges.filter(i=>this.visibleLayers.includes(i.layer)&&n.has(i.source)&&n.has(i.target));for(const i of l){const v=n.get(i.source),f=n.get(i.target),p=(m=i.metadata)==null?void 0:m.threat_flag;e.beginPath(),e.moveTo(v.x,v.y),e.lineTo(f.x,f.y),e.strokeStyle=p?"rgba(239,68,68,0.4)":(this._colors[i.layer]||this._themeColors.accent)+"28",e.lineWidth=p?2.5:Math.max(.5,i.strength*1.5),i.layer==="vpn"?e.setLineDash([4,4]):i.layer==="wifi"?e.setLineDash([2,3]):e.setLineDash([]),e.stroke(),e.setLineDash([])}if(l.length>0){const i=this.time*.008%1,v=Math.floor(this.time*.002)%l.length,f=l[v],p=n.get(f.source),_=n.get(f.target),S=p.x+(_.x-p.x)*i,D=p.y+(_.y-p.y)*i;e.beginPath(),e.arc(S,D,2.5/this.camera.zoom,0,Math.PI*2),e.fillStyle="rgba(0,229,255,0.7)",e.fill()}const h=[...c].sort((i,v)=>(O[i.layer]||0)-(O[v.layer]||0));for(const i of h){const v=this.hovered===i.id,f=this.selected===i.id,p=i.node_type==="gateway"?18:i.layer==="ai"?12:8,_=v?1.4:f?1.2:1,S=this._colors[i.layer]||this._themeColors.accent,D=((b=i.metadata)==null?void 0:b.threat_type)||((x=i.metadata)==null?void 0:x.rogue);e.beginPath(),e.arc(i.x,i.y,p*_*3,0,Math.PI*2),e.fillStyle=D?"rgba(239,68,68,0.12)":S+"15",e.fill(),e.beginPath(),e.arc(i.x,i.y,p*_,0,Math.PI*2),e.fillStyle=D?this._themeColors.threat:S,e.fill(),(f||v)&&(e.beginPath(),e.arc(i.x,i.y,p*_+3,0,Math.PI*2),e.strokeStyle=f?"rgba(0,229,255,0.6)":"rgba(255,255,255,0.4)",e.lineWidth=1.5,e.stroke());const A=i.label.length>14?i.label.slice(0,12)+"…":i.label;e.font=`${v?600:500} ${(v?11:9)/this.camera.zoom}px var(--ds-font-mono, monospace)`,e.fillStyle=v?"#eaf6ff":"rgba(234,246,255,0.55)",e.textAlign="center",e.fillText(A,i.x,i.y+p*_+12/this.camera.zoom)}e.restore()},this._onDown=s=>{const a=this._worldPos(s),e=this._hitTest(a.x,a.y);e?(this.isDragging=!0,this.dragNode=e,this.selected=e,this.dispatchEvent(new CustomEvent("node-select",{detail:e,bubbles:!0,composed:!0}))):(this.isDragging=!0,this.dragNode=null,this.lastMouse={x:s.clientX,y:s.clientY})},this._onMove=s=>{const a=this._worldPos(s);if(this.isDragging&&this.dragNode){const e=this.nodes.find(t=>t.id===this.dragNode);e&&(e.x=a.x,e.y=a.y,e.vx=0,e.vy=0)}else this.isDragging?(this.camera.x+=s.clientX-this.lastMouse.x,this.camera.y+=s.clientY-this.lastMouse.y,this.lastMouse={x:s.clientX,y:s.clientY}):(this.hovered=this._hitTest(a.x,a.y),this.canvas.style.cursor=this.hovered?"pointer":"grab")},this._onUp=()=>{this.isDragging=!1,this.dragNode=null},this._onWheel=s=>{s.preventDefault();const a=Math.max(.2,Math.min(4,this.camera.zoom-s.deltaY*.001)),e=this.canvas.getBoundingClientRect(),t=s.clientX-e.left,r=s.clientY-e.top;this.camera.x=t-(t-this.camera.x)*(a/this.camera.zoom),this.camera.y=r-(r-this.camera.y)*(a/this.camera.zoom),this.camera.zoom=a}}connectedCallback(){super.connectedCallback(),window.addEventListener("resize",this._resize)}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf),window.removeEventListener("resize",this._resize)}firstUpdated(){this.canvas=this.renderRoot.querySelector("canvas"),this.ctx=this.canvas.getContext("2d");const s=getComputedStyle(document.body);this._colors={lan:s.getPropertyValue("--ds-success").trim()||"#10b981",wifi:s.getPropertyValue("--ds-warning").trim()||"#f59e0b",bluetooth:s.getPropertyValue("--ds-iris").trim()||"#8b5cf6",vpn:s.getPropertyValue("--ds-info").trim()||"#00e5ff",internet:s.getPropertyValue("--ds-danger").trim()||"#ef4444",dns:s.getPropertyValue("--ds-coral").trim()||"#d946ef",ai:s.getPropertyValue("--ds-sky").trim()||"#3b82f6",cross:s.getPropertyValue("--ds-text-muted").trim()||"#94a3b8"},this._themeColors.accent=s.getPropertyValue("--ds-accent").trim()||"#00e5ff",this._themeColors.threat=s.getPropertyValue("--ds-danger").trim()||"#ef4444",this._resize(),this._initPositions(),this._loop(),this.canvas.addEventListener("mousedown",this._onDown),this.canvas.addEventListener("mousemove",this._onMove),this.canvas.addEventListener("mouseup",this._onUp),this.canvas.addEventListener("wheel",this._onWheel,{passive:!1})}_initPositions(){var t,r;const s=((t=this.canvas)==null?void 0:t.clientWidth)||800,a=((r=this.canvas)==null?void 0:r.clientHeight)||400,e=this.nodes.find(o=>o.node_type==="gateway");for(const o of this.nodes){if(o.fx!=null)continue;if(o.id===(e==null?void 0:e.id)){o.x=s/2,o.y=a/2,o.fx=s/2,o.fy=a/2;continue}const n=Object.keys(LAYER_COLORS).indexOf(o.layer)/7*Math.PI*2+Math.random()*.5,l=120+Math.random()*180;o.x=s/2+Math.cos(n)*l,o.y=a/2+Math.sin(n)*l,o.vx=0,o.vy=0}}_stepPhysics(){var o,c;const s=this.nodes.filter(n=>this.visibleLayers.includes(n.layer)),a=new Map(s.map(n=>[n.id,n])),e=this.edges.filter(n=>this.visibleLayers.includes(n.layer)&&a.has(n.source)&&a.has(n.target));for(let n=0;n<s.length;n++)for(let l=n+1;l<s.length;l++){const h=s[n],m=s[l];if(h.fx!=null||m.fx!=null)continue;const b=m.x-h.x,x=m.y-h.y,i=Math.sqrt(b*b+x*x)||1,v=2500/(i*i),f=b/i*v,p=x/i*v;h.vx=(h.vx||0)-f,h.vy=(h.vy||0)-p,m.vx=(m.vx||0)+f,m.vy=(m.vy||0)+p}for(const n of e){const l=a.get(n.source),h=a.get(n.target),m=h.x-l.x,b=h.y-l.y,x=Math.sqrt(m*m+b*b)||1,i=90+(1-n.strength)*60,v=(x-i)*.008*n.strength,f=m/x*v,p=b/x*v;l.fx==null&&(l.vx=(l.vx||0)+f,l.vy=(l.vy||0)+p),h.fx==null&&(h.vx=(h.vx||0)-f,h.vy=(h.vy||0)-p)}const t=((o=this.canvas)==null?void 0:o.clientWidth)/2||400,r=((c=this.canvas)==null?void 0:c.clientHeight)/2||200;for(const n of s)n.fx==null&&(n.vx=(n.vx||0)+(t-n.x)*3e-4,n.vy=(n.vy||0)+(r-n.y)*3e-4,n.vx*=.88,n.vy*=.88,n.x+=n.vx,n.y+=n.vy)}_worldPos(s){const a=this.canvas.getBoundingClientRect();return{x:(s.clientX-a.left-this.camera.x)/this.camera.zoom,y:(s.clientY-a.top-this.camera.y)/this.camera.zoom}}_hitTest(s,a){for(const e of this.nodes){if(!this.visibleLayers.includes(e.layer))continue;const t=e.node_type==="gateway"?18:e.layer==="ai"?12:8;if(Math.hypot(e.x-s,e.y-a)<t+4)return e.id}return null}render(){return d`
      <canvas></canvas>
      <div class="legend">
        ${Object.entries(this._colors).map(([s,a])=>d`
          <div class="legend-item">
            <span class="dot" style="background:${a}"></span>
            <span>${s}</span>
          </div>
        `)}
      </div>
    `}};k.styles=T`
    :host { display: block; width: 100%; height: 100%; position: relative; }
    canvas { width: 100%; height: 100%; display: block; border-radius: var(--ds-radius-md); cursor: grab; }
    canvas:active { cursor: grabbing; }
    .legend { position: absolute; bottom: 8px; left: 8px; display: flex; gap: 10px; flex-wrap: wrap; padding: 6px 10px; background: rgba(10,18,30,0.85); border-radius: 10px; border: 1px solid var(--ds-border); font-size: var(--ds-text-xs); }
    .legend-item { display: flex; align-items: center; gap: 4px; color: var(--ds-text-muted); }
    .dot { width: 7px; height: 7px; border-radius: 50%; }
  `;z([$({type:Array})],k.prototype,"nodes",2);z([$({type:Array})],k.prototype,"edges",2);z([$({type:Array})],k.prototype,"visibleLayers",2);z([u()],k.prototype,"hovered",2);z([u()],k.prototype,"selected",2);k=z([N("topology-canvas")],k);var Q=Object.defineProperty,ss=Object.getOwnPropertyDescriptor,P=(s,a,e,t)=>{for(var r=t>1?void 0:t?ss(a,e):a,o=s.length-1,c;o>=0;o--)(c=s[o])&&(r=(t?c(a,e,r):c(r))||r);return t&&r&&Q(a,e,r),r};let w=class extends M{constructor(){super(...arguments),this.node=null,this.open=!1,this.observations=[],this.inferences=[],this.analysis=null,this.loading=!1}updated(s){s.has("node")&&this.node&&this._loadData()}async _loadData(){if(this.node){this.loading=!0;try{const[s,a]=await Promise.all([I(this.node.id,void 0,24).catch(()=>({observations:[]})),E(this.node.id,void 0,10).catch(()=>({inferences:[]}))]);this.observations=s.observations,this.inferences=a.inferences}catch{}this.loading=!1}}async _analyse(){if(this.node){this.loading=!0;try{const s=await j("device",this.node.id);this.analysis=s.analysis||s}catch{}this.loading=!1}}render(){if(!this.node)return d`<div class="panel"><span class="muted">Select a node to view details.</span></div>`;const s=this.node,a=`layer-${s.layer}`;return d`
      <div class="panel">
        <div class="header">
          <span class="layer-badge ${a}">${s.layer}</span>
          <h3 style="margin:0;font-size:var(--ds-text-lg);">${s.label}</h3>
        </div>

        <div class="section">
          <div class="section-title">Metadata</div>
          <div class="meta-grid">
            <div class="meta-item"><div class="k">ID</div><div class="v">${s.id}</div></div>
            <div class="meta-item"><div class="k">Type</div><div class="v">${s.node_type}</div></div>
            ${Object.entries(s.metadata).map(([e,t])=>d`
              <div class="meta-item"><div class="k">${e}</div><div class="v">${typeof t=="object"?JSON.stringify(t):String(t)}</div></div>
            `)}
          </div>
        </div>

        <div class="section">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="section-title">AI Analysis</div>
            <button @click=${()=>void this._analyse()} ?disabled=${this.loading}>${this.loading?"Analysing…":"Analyse"}</button>
          </div>
          ${this.analysis?d`
            <div class="analysis-result">${this.analysis.explanation||JSON.stringify(this.analysis,null,2)}</div>
          `:d`<span class="muted">Click Analyse to generate AI insight.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Inferences · ${this.inferences.length}</div>
          ${this.inferences.length?this.inferences.map(e=>d`
            <div class="inference">
              <div class="conf">${e.inference_type} · ${(e.confidence*100).toFixed(0)}% · ${new Date(e.timestamp).toLocaleString()}</div>
              <div class="text">${e.explanation}</div>
            </div>
          `):d`<span class="muted">No inferences yet.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Observations · ${this.observations.length}</div>
          ${this.observations.length?d`
            <div class="meta-grid">
              ${this.observations.slice(0,6).map(e=>{var t,r;return d`
                <div class="meta-item">
                  <div class="k">${e.metric}</div>
                  <div class="v">${((r=(t=e.value)==null?void 0:t.toFixed)==null?void 0:r.call(t,2))??e.value}</div>
                </div>
              `})}
            </div>
          `:d`<span class="muted">No observations in the last 24h.</span>`}
        </div>
      </div>
    `}};w.styles=T`
    :host { display: block; }
    .panel { background: var(--ds-surface-1); border-left: 1px solid var(--ds-border); padding: var(--ds-space-4); height: 100%; overflow-y: auto; }
    .header { display: flex; align-items: center; gap: var(--ds-space-2); margin-bottom: var(--ds-space-3); }
    .layer-badge { padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; text-transform: uppercase; }
    .layer-lan { background: color-mix(in srgb, var(--ds-success) 12%, transparent); color: var(--ds-success); }
    .layer-wifi { background: color-mix(in srgb, var(--ds-warning) 12%, transparent); color: var(--ds-warning); }
    .layer-bluetooth { background: color-mix(in srgb, var(--ds-iris, var(--ds-iris, #8b5cf6)) 12%, transparent); color: var(--ds-iris, #8b5cf6); }
    .layer-vpn { background: color-mix(in srgb, var(--ds-info) 12%, transparent); color: var(--ds-info); }
    .layer-internet { background: color-mix(in srgb, var(--ds-danger) 12%, transparent); color: var(--ds-danger); }
    .layer-dns { background: color-mix(in srgb, var(--ds-coral, var(--ds-coral, #d946ef)) 12%, transparent); color: var(--ds-coral, #d946ef); }
    .layer-ai { background: color-mix(in srgb, var(--ds-sky, var(--ds-sky, #3b82f6)) 12%, transparent); color: var(--ds-sky, #3b82f6); }
    .section { margin-bottom: var(--ds-space-4); }
    .section-title { font-size: var(--ds-text-xs); color: var(--ds-text-faint); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); margin-bottom: var(--ds-space-2); }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-2); }
    .meta-item { background: var(--ds-surface-2); padding: var(--ds-space-2); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); }
    .meta-item .k { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; }
    .meta-item .v { color: var(--ds-text); font-family: var(--ds-font-mono); word-break: break-all; }
    .inference { background: var(--ds-surface-2); padding: var(--ds-space-3); border-radius: var(--ds-radius-sm); margin-bottom: var(--ds-space-2); border-left: 3px solid var(--ds-accent); }
    .inference .conf { font-size: var(--ds-text-xs); color: var(--ds-text-muted); }
    .inference .text { font-size: var(--ds-text-sm); color: var(--ds-text); margin-top: var(--ds-space-1); }
    .analysis-result { background: var(--ds-surface-2); padding: var(--ds-space-3); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); color: var(--ds-text); white-space: pre-wrap; }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    button { background: var(--ds-accent); color: var(--ds-on-accent); border: none; padding: var(--ds-space-2) var(--ds-space-3); border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
  `;P([$({type:Object})],w.prototype,"node",2);P([$({type:Boolean})],w.prototype,"open",2);P([$({type:Array})],w.prototype,"observations",2);P([$({type:Array})],w.prototype,"inferences",2);P([$({type:Object})],w.prototype,"analysis",2);P([$({type:Boolean})],w.prototype,"loading",2);w=P([N("network-detail-panel")],w);var es=Object.defineProperty,ts=Object.getOwnPropertyDescriptor,y=(s,a,e,t)=>{for(var r=t>1?void 0:t?ts(a,e):a,o=s.length-1,c;o>=0;o--)(c=s[o])&&(r=(t?c(a,e,r):c(r))||r);return t&&r&&es(a,e,r),r};let g=class extends R(M){constructor(){super(...arguments),this.status=null,this.devices=[],this.events=[],this.threats=[],this.aps=[],this.evilTwin=!1,this.loading=!0,this.filter="all",this.scanIp="",this.scanResult=null,this.scanLoading=!1,this.graph={nodes:[],edges:[]},this.graphStats=null,this.selectedNode=null}connectedCallback(){super.connectedCallback(),this.load(),this.timer=setInterval(()=>void this.load(),8e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async load(){try{const[s,a,e,t,r,o,c]=await Promise.all([W().catch(()=>null),V().catch(()=>({devices:[]})),F(20).catch(()=>({events:[]})),Y(24).catch(()=>({threats:[]})),H().catch(()=>({aps:[],evil_twin_detected:!1})),B().catch(()=>({nodes:[],edges:[]})),U().catch(()=>null)]);this.status=s,this.devices=a.devices,this.events=e.events,this.threats=t.threats,this.aps=r.aps,this.evilTwin=r.evil_twin_detected,this.graph=o,this.graphStats=c}catch{}this.loading=!1}async act(s,a){try{await(a==="trust"?X:q)(s),L(`Device ${a}ed`,a==="trust"?"success":"danger"),this.load()}catch{L(`${a} failed`,"danger")}}async ackEvent(s){try{await G(s),this.load()}catch{L("Ack failed","danger")}}async doScan(){if(this.scanIp.trim()){this.scanLoading=!0;try{this.scanResult=await J(this.scanIp.trim())}catch{L("Scan failed","danger")}this.scanLoading=!1}}filteredDevices(){return this.filter==="all"?this.devices:this.devices.filter(s=>s.trust_status===this.filter)}render(){if(this.loading)return d`<div class="muted">Loading network command center…</div>`;const s=this.status,a=this.filteredDevices(),e=this.events.filter(t=>!t.acknowledged);return d`
      <!-- Security Score Header -->
      <div class="score-row">
        <div class="score-card">
          <div class="num ${s?s.score>=80?"ok":s.score>=50?"warn":"danger":""}">${(s==null?void 0:s.score)??"--"}</div>
          <div class="label">Security Score</div>
        </div>
        <div class="score-card"><div class="num ok">${(s==null?void 0:s.devices_trusted)??0}</div><div class="label">Trusted</div></div>
        <div class="score-card"><div class="num warn">${(s==null?void 0:s.devices_unknown)??0}</div><div class="label">Unknown</div></div>
        <div class="score-card"><div class="num danger">${(s==null?void 0:s.devices_suspicious)??0}</div><div class="label">Suspicious</div></div>
        <div class="score-card"><div class="num ${((s==null?void 0:s.threats_24h)??0)>0?"danger":"ok"}">${(s==null?void 0:s.threats_24h)??0}</div><div class="label">Threats 24h</div></div>
      </div>

      <!-- Topology + Detail Panel -->
      <ds-panel heading="Network Topology · ${this.graph.nodes.length} nodes · ${this.graph.edges.length} edges">
        <div slot="actions" style="display:flex;gap:var(--ds-space-2);align-items:center;">
          <span style="font-size:var(--ds-text-xs);color:var(--ds-text-muted);">${this.graphStats?Object.entries(this.graphStats.nodes_by_layer).map(([t,r])=>`${t}:${r}`).join(" · "):""}</span>
          <ds-button size="sm" @click=${()=>void this.load()}>refresh</ds-button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 320px;gap:var(--ds-space-3);height:400px;">
          <div class="topo-wrap" style="height:100%;">
            <topology-canvas
              .nodes=${this.graph.nodes}
              .edges=${this.graph.edges}
              @node-select=${t=>{this.selectedNode=this.graph.nodes.find(r=>r.id===t.detail)||null}}
            ></topology-canvas>
          </div>
          <network-detail-panel
            .node=${this.selectedNode}
            style="height:100%;overflow:hidden;"
          ></network-detail-panel>
        </div>
      </ds-panel>

      <!-- Active Alerts -->
      ${e.length>0?d`
        <ds-panel heading="Active Alerts · ${e.length}">
          ${e.map(t=>d`
            <div class="ev">
              <span class="sev-${t.severity}">●</span>
              <span style="flex:1;">${t.message}</span>
              <span class="muted" style="font-size:var(--ds-text-xs);">${new Date(t.timestamp).toLocaleTimeString()}</span>
              <ds-button size="sm" @click=${()=>void this.ackEvent(t.id)}>ack</ds-button>
            </div>
          `)}
        </ds-panel>
      `:""}

      <!-- Device Inventory -->
      <ds-panel heading="Device Inventory · ${a.length}">
        <div slot="actions" class="tabs">
          ${["all","trusted","unknown","suspicious"].map(t=>d`
            <button class="tab ${this.filter===t?"on":""}" @click=${()=>this.filter=t}>${t}</button>
          `)}
        </div>
        <div class="dev-table">
          <div class="dev-row head"><span>Device</span><span>IP</span><span>MAC / Vendor</span><span>Last seen</span><span>Status</span><span></span></div>
          ${a.length?a.map(t=>d`
            <div class="dev-row">
              <span style="display:flex;align-items:center;gap:var(--ds-space-2);">
                <span class="dot trust-${t.trust_status}"></span>
                ${t.hostname||"Unknown"}${t.is_gateway?" · GW":""}
              </span>
              <span class="muted">${t.ip}</span>
              <span class="muted">${t.mac}${t.vendor?` · ${t.vendor}`:""}</span>
              <span class="muted">${new Date(t.last_seen).toLocaleTimeString()}</span>
              <span class="badge badge-${t.trust_status}">${t.trust_status}</span>
              <span style="display:flex;gap:var(--ds-space-1);">
                ${t.trust_status!=="trusted"?d`<ds-button size="sm" @click=${()=>void this.act(t.mac,"trust")}>trust</ds-button>`:""}
                ${t.trust_status!=="blocked"?d`<ds-button size="sm" variant="danger" @click=${()=>void this.act(t.mac,"block")}>block</ds-button>`:""}
              </span>
            </div>
          `):d`<div class="dev-row"><span class="muted">No devices match this filter.</span></div>`}
        </div>
      </ds-panel>

      <!-- Threats -->
      <ds-panel heading="Recent Threats · ${this.threats.length}">
        ${this.threats.length?this.threats.map(t=>d`
          <div class="ev">
            <span class="sev-critical">●</span>
            <span style="flex:1;">${t.type}</span>
            <span class="muted">${t.confidence.toFixed(0)}% confidence</span>
            <span class="muted">${new Date(t.detected_at).toLocaleString()}</span>
          </div>
        `):d`<span class="muted">No threats detected in the last 24 hours.</span>`}
      </ds-panel>

      <!-- Scanner -->
      <ds-panel heading="Port Scanner">
        <div class="scan-row">
          <input type="text" placeholder="192.168.1.1" .value=${this.scanIp} @input=${t=>this.scanIp=t.target.value} @keydown=${t=>t.key==="Enter"&&void this.doScan()} />
          <ds-button @click=${()=>void this.doScan()} ?disabled=${this.scanLoading}>${this.scanLoading?"scanning…":"scan"}</ds-button>
        </div>
        ${this.scanResult?d`
          <pre style="margin-top:var(--ds-space-3);padding:var(--ds-space-3);background:var(--ds-surface-2);border-radius:var(--ds-radius-sm);font-size:var(--ds-text-xs);overflow:auto;">${JSON.stringify(this.scanResult,null,2)}</pre>
        `:""}
      </ds-panel>

      <!-- WiFi / Evil Twin -->
      <ds-panel heading="WiFi Spectrum · ${this.aps.length} APs">
        ${this.evilTwin?d`<div class="evil-twin">⚠ Evil Twin / Rogue AP detected!</div>`:""}
        ${this.aps.map(t=>d`
          <div class="ap">
            <span>${t.ssid||"Hidden"} <span class="muted">ch${t.channel}</span></span>
            <span class="muted">${t.bssid}</span>
            <span>${t.signal} dBm</span>
            ${t.rogue?d`<span class="rogue">ROGUE</span>`:""}
          </div>
        `)}
        ${this.aps.length?"":d`<span class="muted">No WiFi data available.</span>`}
      </ds-panel>

      <!-- Proximity -->
      <ds-panel heading="Proximity & RF · live">
        ${C.get().length?d`<div style="display:grid;gap:3px;font-family:var(--ds-font-mono);font-size:var(--ds-text-xs);max-height:200px;overflow:auto;">
          ${C.get().map(t=>d`<div style="display:flex;gap:var(--ds-space-2);color:var(--ds-text-soft);"><span style="color:var(--ds-text-faint);">${t.time}</span><span>${t.label}</span></div>`)}
        </div>`:d`<span class="muted">Listening for nearby access points & proximity changes…</span>`}
      </ds-panel>
    `}};g.styles=T`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 1200px; margin: 0 auto; align-content: start; }
    .muted { color: var(--ds-text-muted); }
    /* Score header */
    .score-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: var(--ds-space-3); }
    .score-card { padding: var(--ds-space-4); background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); text-align: center; }
    .score-card .num { font-size: var(--ds-text-2xl); font-weight: 700; font-family: var(--ds-font-mono); }
    .score-card .num.ok { color: var(--ds-success); }
    .score-card .num.warn { color: var(--ds-warning); }
    .score-card .num.danger { color: var(--ds-danger); }
    .score-card .label { font-size: var(--ds-text-xs); color: var(--ds-text-muted); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); margin-top: var(--ds-space-1); }
    /* Topology */
    .topo-wrap { height: 320px; background: var(--ds-surface-1); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md); overflow: hidden; }
    /* Tabs */
    .tabs { display: flex; gap: var(--ds-space-1); margin-bottom: var(--ds-space-3); }
    .tab { padding: var(--ds-space-1) var(--ds-space-3); border-radius: var(--ds-radius-pill); border: 1px solid var(--ds-border); background: none; color: var(--ds-text-muted); font-size: var(--ds-text-sm); cursor: pointer; }
    .tab.on { color: var(--ds-on-accent); background: var(--ds-accent); border-color: var(--ds-accent); }
    /* Device table */
    .dev-table { display: grid; gap: 1px; }
    .dev-row { display: grid; grid-template-columns: 1.2fr 1fr 1.2fr 0.9fr 0.8fr auto; gap: var(--ds-space-2); align-items: center; padding: var(--ds-space-2) var(--ds-space-3); background: var(--ds-surface-1); font-size: var(--ds-text-sm); }
    .dev-row.head { font-size: var(--ds-text-xs); color: var(--ds-text-faint); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); background: none; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .trust-trusted { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .trust-unknown { background: var(--ds-warning); }
    .trust-suspicious, .trust-blocked { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .badge { padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; }
    .badge-trusted { background: rgba(16,185,129,0.12); color: var(--ds-success); }
    .badge-unknown { background: rgba(245,158,11,0.12); color: var(--ds-warning); }
    .badge-suspicious { background: rgba(239,68,68,0.12); color: var(--ds-danger); }
    .badge-blocked { background: rgba(220,38,38,0.12); color: #dc2626; }
    /* Events */
    .ev { display: flex; align-items: center; gap: var(--ds-space-2); padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .ev:last-child { border-bottom: 0; }
    .sev-critical { color: #ef4444; }
    .sev-warning { color: #f59e0b; }
    .sev-info { color: var(--ds-text-muted); }
    /* Scanner */
    .scan-row { display: flex; gap: var(--ds-space-2); }
    .scan-row input { flex: 1; padding: var(--ds-space-2); background: var(--ds-surface-2); border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm); color: var(--ds-text); }
    /* WiFi */
    .ap { display: flex; justify-content: space-between; align-items: center; padding: var(--ds-space-2) var(--ds-space-3); border-bottom: 1px solid var(--ds-border); font-size: var(--ds-text-sm); }
    .ap .rogue { color: #ef4444; font-weight: 600; }
    .evil-twin { padding: var(--ds-space-2) var(--ds-space-4); background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: var(--ds-radius-md); color: #ef4444; font-size: var(--ds-text-sm); text-align: center; }
  `;y([u()],g.prototype,"status",2);y([u()],g.prototype,"devices",2);y([u()],g.prototype,"events",2);y([u()],g.prototype,"threats",2);y([u()],g.prototype,"aps",2);y([u()],g.prototype,"evilTwin",2);y([u()],g.prototype,"loading",2);y([u()],g.prototype,"filter",2);y([u()],g.prototype,"scanIp",2);y([u()],g.prototype,"scanResult",2);y([u()],g.prototype,"scanLoading",2);y([u()],g.prototype,"graph",2);y([u()],g.prototype,"graphStats",2);y([u()],g.prototype,"selectedNode",2);g=y([N("network-view")],g);export{g as NetworkView};
//# sourceMappingURL=network-view-D6eW8hGd.js.map
