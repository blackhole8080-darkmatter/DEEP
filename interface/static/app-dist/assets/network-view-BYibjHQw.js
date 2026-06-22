import{e as M,n as $,r as u,i as N,d,t as O,j as C,k as j,l as R,m as W,o as F,p as Y,q as H,s as B,u as U,v as X,w as q,x as G,y as J,g as L,z as V,A as Z,B as A}from"./index-BZpHEIVQ.js";import"./ds-panel-B0Coku7q.js";import"./ds-button-X_d22ss4.js";var K=Object.defineProperty,Q=Object.getOwnPropertyDescriptor,S=(e,a,s,t)=>{for(var r=t>1?void 0:t?Q(a,s):a,o=e.length-1,c;o>=0;o--)(c=e[o])&&(r=(t?c(a,s,r):c(r))||r);return t&&r&&K(a,s,r),r};const T={lan:"#10b981",wifi:"#f59e0b",bluetooth:"#8b5cf6",vpn:"#00e5ff",internet:"#ef4444",dns:"#d946ef",ai:"#3b82f6",cross:"#94a3b8"},I={lan:0,wifi:1,bluetooth:1,vpn:2,internet:3,dns:1,ai:3,cross:0};let k=class extends N{constructor(){super(...arguments),this.nodes=[],this.edges=[],this.visibleLayers=["lan","wifi","bluetooth","vpn","internet","dns","ai","cross"],this.hovered=null,this.selected=null,this.raf=0,this.camera={x:0,y:0,zoom:1},this.isDragging=!1,this.dragNode=null,this.lastMouse={x:0,y:0},this.time=0,this._resize=()=>{var a;if(!this.canvas)return;const e=Math.min(window.devicePixelRatio,2);this.canvas.width=this.canvas.clientWidth*e,this.canvas.height=this.canvas.clientHeight*e,(a=this.ctx)==null||a.scale(e,e)},this._loop=()=>{var m,b,x;this.raf=requestAnimationFrame(this._loop),this.time+=1,this._stepPhysics();const e=this.canvas.clientWidth,a=this.canvas.clientHeight,s=this.ctx;s.clearRect(0,0,e,a),s.strokeStyle="rgba(0,229,255,0.03)",s.lineWidth=1;const t=40*this.camera.zoom,r=this.camera.x%t,o=this.camera.y%t;for(let i=r;i<e;i+=t)s.beginPath(),s.moveTo(i,0),s.lineTo(i,a),s.stroke();for(let i=o;i<a;i+=t)s.beginPath(),s.moveTo(0,i),s.lineTo(e,i),s.stroke();s.save(),s.translate(this.camera.x,this.camera.y),s.scale(this.camera.zoom,this.camera.zoom);const c=this.nodes.filter(i=>this.visibleLayers.includes(i.layer)),n=new Map(c.map(i=>[i.id,i])),l=this.edges.filter(i=>this.visibleLayers.includes(i.layer)&&n.has(i.source)&&n.has(i.target));for(const i of l){const v=n.get(i.source),f=n.get(i.target),p=(m=i.metadata)==null?void 0:m.threat_flag;s.beginPath(),s.moveTo(v.x,v.y),s.lineTo(f.x,f.y),s.strokeStyle=p?"rgba(239,68,68,0.4)":(T[i.layer]||"#00e5ff")+"28",s.lineWidth=p?2.5:Math.max(.5,i.strength*1.5),i.layer==="vpn"?s.setLineDash([4,4]):i.layer==="wifi"?s.setLineDash([2,3]):s.setLineDash([]),s.stroke(),s.setLineDash([])}if(l.length>0){const i=this.time*.008%1,v=Math.floor(this.time*.002)%l.length,f=l[v],p=n.get(f.source),_=n.get(f.target),P=p.x+(_.x-p.x)*i,D=p.y+(_.y-p.y)*i;s.beginPath(),s.arc(P,D,2.5/this.camera.zoom,0,Math.PI*2),s.fillStyle="rgba(0,229,255,0.7)",s.fill()}const h=[...c].sort((i,v)=>(I[i.layer]||0)-(I[v.layer]||0));for(const i of h){const v=this.hovered===i.id,f=this.selected===i.id,p=i.node_type==="gateway"?18:i.layer==="ai"?12:8,_=v?1.4:f?1.2:1,P=T[i.layer]||"#00e5ff",D=((b=i.metadata)==null?void 0:b.threat_type)||((x=i.metadata)==null?void 0:x.rogue);s.beginPath(),s.arc(i.x,i.y,p*_*3,0,Math.PI*2),s.fillStyle=D?"rgba(239,68,68,0.12)":P+"15",s.fill(),s.beginPath(),s.arc(i.x,i.y,p*_,0,Math.PI*2),s.fillStyle=D?"#ef4444":P,s.fill(),(f||v)&&(s.beginPath(),s.arc(i.x,i.y,p*_+3,0,Math.PI*2),s.strokeStyle=f?"rgba(0,229,255,0.6)":"rgba(255,255,255,0.4)",s.lineWidth=1.5,s.stroke());const E=i.label.length>14?i.label.slice(0,12)+"…":i.label;s.font=`${v?600:500} ${(v?11:9)/this.camera.zoom}px var(--ds-font-mono, monospace)`,s.fillStyle=v?"#eaf6ff":"rgba(234,246,255,0.55)",s.textAlign="center",s.fillText(E,i.x,i.y+p*_+12/this.camera.zoom)}s.restore()},this._onDown=e=>{const a=this._worldPos(e),s=this._hitTest(a.x,a.y);s?(this.isDragging=!0,this.dragNode=s,this.selected=s,this.dispatchEvent(new CustomEvent("node-select",{detail:s,bubbles:!0,composed:!0}))):(this.isDragging=!0,this.dragNode=null,this.lastMouse={x:e.clientX,y:e.clientY})},this._onMove=e=>{const a=this._worldPos(e);if(this.isDragging&&this.dragNode){const s=this.nodes.find(t=>t.id===this.dragNode);s&&(s.x=a.x,s.y=a.y,s.vx=0,s.vy=0)}else this.isDragging?(this.camera.x+=e.clientX-this.lastMouse.x,this.camera.y+=e.clientY-this.lastMouse.y,this.lastMouse={x:e.clientX,y:e.clientY}):(this.hovered=this._hitTest(a.x,a.y),this.canvas.style.cursor=this.hovered?"pointer":"grab")},this._onUp=()=>{this.isDragging=!1,this.dragNode=null},this._onWheel=e=>{e.preventDefault();const a=Math.max(.2,Math.min(4,this.camera.zoom-e.deltaY*.001)),s=this.canvas.getBoundingClientRect(),t=e.clientX-s.left,r=e.clientY-s.top;this.camera.x=t-(t-this.camera.x)*(a/this.camera.zoom),this.camera.y=r-(r-this.camera.y)*(a/this.camera.zoom),this.camera.zoom=a}}connectedCallback(){super.connectedCallback(),window.addEventListener("resize",this._resize)}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf),window.removeEventListener("resize",this._resize)}firstUpdated(){this.canvas=this.renderRoot.querySelector("canvas"),this.ctx=this.canvas.getContext("2d"),this._resize(),this._initPositions(),this._loop(),this.canvas.addEventListener("mousedown",this._onDown),this.canvas.addEventListener("mousemove",this._onMove),this.canvas.addEventListener("mouseup",this._onUp),this.canvas.addEventListener("wheel",this._onWheel,{passive:!1})}_initPositions(){var t,r;const e=((t=this.canvas)==null?void 0:t.clientWidth)||800,a=((r=this.canvas)==null?void 0:r.clientHeight)||400,s=this.nodes.find(o=>o.node_type==="gateway");for(const o of this.nodes){if(o.fx!=null)continue;if(o.id===(s==null?void 0:s.id)){o.x=e/2,o.y=a/2,o.fx=e/2,o.fy=a/2;continue}const n=Object.keys(T).indexOf(o.layer)/7*Math.PI*2+Math.random()*.5,l=120+Math.random()*180;o.x=e/2+Math.cos(n)*l,o.y=a/2+Math.sin(n)*l,o.vx=0,o.vy=0}}_stepPhysics(){var o,c;const e=this.nodes.filter(n=>this.visibleLayers.includes(n.layer)),a=new Map(e.map(n=>[n.id,n])),s=this.edges.filter(n=>this.visibleLayers.includes(n.layer)&&a.has(n.source)&&a.has(n.target));for(let n=0;n<e.length;n++)for(let l=n+1;l<e.length;l++){const h=e[n],m=e[l];if(h.fx!=null||m.fx!=null)continue;const b=m.x-h.x,x=m.y-h.y,i=Math.sqrt(b*b+x*x)||1,v=2500/(i*i),f=b/i*v,p=x/i*v;h.vx=(h.vx||0)-f,h.vy=(h.vy||0)-p,m.vx=(m.vx||0)+f,m.vy=(m.vy||0)+p}for(const n of s){const l=a.get(n.source),h=a.get(n.target),m=h.x-l.x,b=h.y-l.y,x=Math.sqrt(m*m+b*b)||1,i=90+(1-n.strength)*60,v=(x-i)*.008*n.strength,f=m/x*v,p=b/x*v;l.fx==null&&(l.vx=(l.vx||0)+f,l.vy=(l.vy||0)+p),h.fx==null&&(h.vx=(h.vx||0)-f,h.vy=(h.vy||0)-p)}const t=((o=this.canvas)==null?void 0:o.clientWidth)/2||400,r=((c=this.canvas)==null?void 0:c.clientHeight)/2||200;for(const n of e)n.fx==null&&(n.vx=(n.vx||0)+(t-n.x)*3e-4,n.vy=(n.vy||0)+(r-n.y)*3e-4,n.vx*=.88,n.vy*=.88,n.x+=n.vx,n.y+=n.vy)}_worldPos(e){const a=this.canvas.getBoundingClientRect();return{x:(e.clientX-a.left-this.camera.x)/this.camera.zoom,y:(e.clientY-a.top-this.camera.y)/this.camera.zoom}}_hitTest(e,a){for(const s of this.nodes){if(!this.visibleLayers.includes(s.layer))continue;const t=s.node_type==="gateway"?18:s.layer==="ai"?12:8;if(Math.hypot(s.x-e,s.y-a)<t+4)return s.id}return null}render(){return d`
      <canvas></canvas>
      <div class="legend">
        ${Object.entries(T).map(([e,a])=>d`
          <div class="legend-item">
            <span class="dot" style="background:${a}"></span>
            <span>${e}</span>
          </div>
        `)}
      </div>
    `}};k.styles=M`
    :host { display: block; width: 100%; height: 100%; position: relative; }
    canvas { width: 100%; height: 100%; display: block; border-radius: var(--ds-radius-md); cursor: grab; }
    canvas:active { cursor: grabbing; }
    .legend { position: absolute; bottom: 8px; left: 8px; display: flex; gap: 10px; flex-wrap: wrap; padding: 6px 10px; background: rgba(10,18,30,0.85); border-radius: 10px; border: 1px solid var(--ds-border); font-size: var(--ds-text-xs); }
    .legend-item { display: flex; align-items: center; gap: 4px; color: var(--ds-text-muted); }
    .dot { width: 7px; height: 7px; border-radius: 50%; }
  `;S([$({type:Array})],k.prototype,"nodes",2);S([$({type:Array})],k.prototype,"edges",2);S([$({type:Array})],k.prototype,"visibleLayers",2);S([u()],k.prototype,"hovered",2);S([u()],k.prototype,"selected",2);k=S([O("topology-canvas")],k);var ss=Object.defineProperty,es=Object.getOwnPropertyDescriptor,z=(e,a,s,t)=>{for(var r=t>1?void 0:t?es(a,s):a,o=e.length-1,c;o>=0;o--)(c=e[o])&&(r=(t?c(a,s,r):c(r))||r);return t&&r&&ss(a,s,r),r};let w=class extends N{constructor(){super(...arguments),this.node=null,this.open=!1,this.observations=[],this.inferences=[],this.analysis=null,this.loading=!1}updated(e){e.has("node")&&this.node&&this._loadData()}async _loadData(){if(this.node){this.loading=!0;try{const[e,a]=await Promise.all([C(this.node.id,void 0,24).catch(()=>({observations:[]})),j(this.node.id,void 0,10).catch(()=>({inferences:[]}))]);this.observations=e.observations,this.inferences=a.inferences}catch{}this.loading=!1}}async _analyse(){if(this.node){this.loading=!0;try{const e=await R("device",this.node.id);this.analysis=e.analysis||e}catch{}this.loading=!1}}render(){if(!this.node)return d`<div class="panel"><span class="muted">Select a node to view details.</span></div>`;const e=this.node,a=`layer-${e.layer}`;return d`
      <div class="panel">
        <div class="header">
          <span class="layer-badge ${a}">${e.layer}</span>
          <h3 style="margin:0;font-size:var(--ds-text-lg);">${e.label}</h3>
        </div>

        <div class="section">
          <div class="section-title">Metadata</div>
          <div class="meta-grid">
            <div class="meta-item"><div class="k">ID</div><div class="v">${e.id}</div></div>
            <div class="meta-item"><div class="k">Type</div><div class="v">${e.node_type}</div></div>
            ${Object.entries(e.metadata).map(([s,t])=>d`
              <div class="meta-item"><div class="k">${s}</div><div class="v">${typeof t=="object"?JSON.stringify(t):String(t)}</div></div>
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
          ${this.inferences.length?this.inferences.map(s=>d`
            <div class="inference">
              <div class="conf">${s.inference_type} · ${(s.confidence*100).toFixed(0)}% · ${new Date(s.timestamp).toLocaleString()}</div>
              <div class="text">${s.explanation}</div>
            </div>
          `):d`<span class="muted">No inferences yet.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Observations · ${this.observations.length}</div>
          ${this.observations.length?d`
            <div class="meta-grid">
              ${this.observations.slice(0,6).map(s=>{var t,r;return d`
                <div class="meta-item">
                  <div class="k">${s.metric}</div>
                  <div class="v">${((r=(t=s.value)==null?void 0:t.toFixed)==null?void 0:r.call(t,2))??s.value}</div>
                </div>
              `})}
            </div>
          `:d`<span class="muted">No observations in the last 24h.</span>`}
        </div>
      </div>
    `}};w.styles=M`
    :host { display: block; }
    .panel { background: var(--ds-surface-1); border-left: 1px solid var(--ds-border); padding: var(--ds-space-4); height: 100%; overflow-y: auto; }
    .header { display: flex; align-items: center; gap: var(--ds-space-2); margin-bottom: var(--ds-space-3); }
    .layer-badge { padding: 1px 8px; border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: 600; text-transform: uppercase; }
    .layer-lan { background: rgba(16,185,129,0.12); color: #10b981; }
    .layer-wifi { background: rgba(245,158,11,0.12); color: #f59e0b; }
    .layer-bluetooth { background: rgba(139,92,246,0.12); color: #8b5cf6; }
    .layer-vpn { background: rgba(0,229,255,0.12); color: #00e5ff; }
    .layer-internet { background: rgba(239,68,68,0.12); color: #ef4444; }
    .layer-dns { background: rgba(217,70,239,0.12); color: #d946ef; }
    .layer-ai { background: rgba(59,130,246,0.12); color: #3b82f6; }
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
  `;z([$({type:Object})],w.prototype,"node",2);z([$({type:Boolean})],w.prototype,"open",2);z([$({type:Array})],w.prototype,"observations",2);z([$({type:Array})],w.prototype,"inferences",2);z([$({type:Object})],w.prototype,"analysis",2);z([$({type:Boolean})],w.prototype,"loading",2);w=z([O("network-detail-panel")],w);var ts=Object.defineProperty,as=Object.getOwnPropertyDescriptor,y=(e,a,s,t)=>{for(var r=t>1?void 0:t?as(a,s):a,o=e.length-1,c;o>=0;o--)(c=e[o])&&(r=(t?c(a,s,r):c(r))||r);return t&&r&&ts(a,s,r),r};let g=class extends W(N){constructor(){super(...arguments),this.status=null,this.devices=[],this.events=[],this.threats=[],this.aps=[],this.evilTwin=!1,this.loading=!0,this.filter="all",this.scanIp="",this.scanResult=null,this.scanLoading=!1,this.graph={nodes:[],edges:[]},this.graphStats=null,this.selectedNode=null}connectedCallback(){super.connectedCallback(),this.load(),this.timer=setInterval(()=>void this.load(),8e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async load(){try{const[e,a,s,t,r,o,c]=await Promise.all([F().catch(()=>null),Y().catch(()=>({devices:[]})),H(20).catch(()=>({events:[]})),B(24).catch(()=>({threats:[]})),U().catch(()=>({aps:[],evil_twin_detected:!1})),X().catch(()=>({nodes:[],edges:[]})),q().catch(()=>null)]);this.status=e,this.devices=a.devices,this.events=s.events,this.threats=t.threats,this.aps=r.aps,this.evilTwin=r.evil_twin_detected,this.graph=o,this.graphStats=c}catch{}this.loading=!1}async act(e,a){try{await(a==="trust"?G:J)(e),L(`Device ${a}ed`,a==="trust"?"success":"danger"),this.load()}catch{L(`${a} failed`,"danger")}}async ackEvent(e){try{await V(e),this.load()}catch{L("Ack failed","danger")}}async doScan(){if(this.scanIp.trim()){this.scanLoading=!0;try{this.scanResult=await Z(this.scanIp.trim())}catch{L("Scan failed","danger")}this.scanLoading=!1}}filteredDevices(){return this.filter==="all"?this.devices:this.devices.filter(e=>e.trust_status===this.filter)}render(){if(this.loading)return d`<div class="muted">Loading network command center…</div>`;const e=this.status,a=this.filteredDevices(),s=this.events.filter(t=>!t.acknowledged);return d`
      <!-- Security Score Header -->
      <div class="score-row">
        <div class="score-card">
          <div class="num ${e?e.score>=80?"ok":e.score>=50?"warn":"danger":""}">${(e==null?void 0:e.score)??"--"}</div>
          <div class="label">Security Score</div>
        </div>
        <div class="score-card"><div class="num ok">${(e==null?void 0:e.devices_trusted)??0}</div><div class="label">Trusted</div></div>
        <div class="score-card"><div class="num warn">${(e==null?void 0:e.devices_unknown)??0}</div><div class="label">Unknown</div></div>
        <div class="score-card"><div class="num danger">${(e==null?void 0:e.devices_suspicious)??0}</div><div class="label">Suspicious</div></div>
        <div class="score-card"><div class="num ${((e==null?void 0:e.threats_24h)??0)>0?"danger":"ok"}">${(e==null?void 0:e.threats_24h)??0}</div><div class="label">Threats 24h</div></div>
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
      ${s.length>0?d`
        <ds-panel heading="Active Alerts · ${s.length}">
          ${s.map(t=>d`
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
        ${A.get().length?d`<div style="display:grid;gap:3px;font-family:var(--ds-font-mono);font-size:var(--ds-text-xs);max-height:200px;overflow:auto;">
          ${A.get().map(t=>d`<div style="display:flex;gap:var(--ds-space-2);color:var(--ds-text-soft);"><span style="color:var(--ds-text-faint);">${t.time}</span><span>${t.label}</span></div>`)}
        </div>`:d`<span class="muted">Listening for nearby access points & proximity changes…</span>`}
      </ds-panel>
    `}};g.styles=M`
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
  `;y([u()],g.prototype,"status",2);y([u()],g.prototype,"devices",2);y([u()],g.prototype,"events",2);y([u()],g.prototype,"threats",2);y([u()],g.prototype,"aps",2);y([u()],g.prototype,"evilTwin",2);y([u()],g.prototype,"loading",2);y([u()],g.prototype,"filter",2);y([u()],g.prototype,"scanIp",2);y([u()],g.prototype,"scanResult",2);y([u()],g.prototype,"scanLoading",2);y([u()],g.prototype,"graph",2);y([u()],g.prototype,"graphStats",2);y([u()],g.prototype,"selectedNode",2);g=y([O("network-view")],g);export{g as NetworkView};
//# sourceMappingURL=network-view-BYibjHQw.js.map
