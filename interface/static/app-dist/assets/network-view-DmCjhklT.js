import{i as ae,n as A,a as oe,b as h,t as re,r as _,f as ue,c as me,d as ye,e as xe,g as we,h as ke,j as _e,k as $e,l as Me,m as Se,o as Te,p as Pe,q as Ce,s as se,u as ze,v as Ae}from"./index-CbyoqPmk.js";import"./ds-panel-DKEcxy7u.js";var De=Object.defineProperty,Re=Object.getOwnPropertyDescriptor,ie=(e,s,t,i)=>{for(var n=i>1?void 0:i?Re(s,t):s,o=e.length-1,d;o>=0;o--)(d=e[o])&&(n=(i?d(s,t,n):d(n))||n);return i&&n&&De(s,t,n),n};let q=class extends oe{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return h`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};q.styles=ae`
    :host { display: inline-block; }
    button {
      display: inline-flex;
      align-items: center;
      gap: var(--ds-space-2);
      font-family: var(--ds-font-sans);
      font-weight: 500;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-2);
      color: var(--ds-text);
      cursor: pointer;
      transition:
        background var(--ds-dur-fast) var(--ds-ease-out),
        border-color var(--ds-dur-fast) var(--ds-ease-out),
        transform var(--ds-dur-fast) var(--ds-ease-spring);
    }
    button:hover:not(:disabled) { background: var(--ds-surface-3); transform: translateY(-1px); }
    button:active:not(:disabled) { transform: translateY(0); }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    button:focus-visible { outline: none; box-shadow: var(--ds-focus-ring); }

    .md { padding: var(--ds-space-2) var(--ds-space-4); font-size: var(--ds-text-sm); }
    .sm { padding: var(--ds-space-1) var(--ds-space-3); font-size: var(--ds-text-xs); }

    .primary {
      background: var(--ds-accent);
      border-color: var(--ds-accent);
      color: var(--ds-on-accent);
      font-weight: 600;
    }
    .primary:hover:not(:disabled) { background: var(--ds-accent); filter: brightness(1.1); box-shadow: var(--ds-glow); }
    .danger { border-color: rgba(229, 115, 106, 0.4); color: var(--ds-danger); background: rgba(229, 115, 106, 0.08); }
    .danger:hover:not(:disabled) { background: rgba(229, 115, 106, 0.16); }

    /* ETIS overrides */
    :host-context([data-skin="etis"]) .primary {
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      border-color: var(--ds-accent);
      color: var(--ds-accent);
    }
    :host-context([data-skin="etis"]) .primary:hover:not(:disabled) {
      background: rgba(var(--ds-periwinkle-rgb), 0.15);
      box-shadow: var(--ds-glow);
    }
    :host-context([data-skin="etis"]) .danger {
      border-color: var(--ds-danger);
      color: var(--ds-danger);
      background: rgba(255, 68, 102, 0.08);
    }
    :host-context([data-skin="etis"]) .danger:hover:not(:disabled) {
      background: rgba(255, 68, 102, 0.16);
      box-shadow: 0 0 12px rgba(255, 68, 102, 0.2);
    }
  `;ie([A()],q.prototype,"variant",2);ie([A()],q.prototype,"size",2);ie([A({type:Boolean})],q.prototype,"disabled",2);q=ie([re("ds-button")],q);var Ie=Object.defineProperty,Le=Object.getOwnPropertyDescriptor,G=(e,s,t,i)=>{for(var n=i>1?void 0:i?Le(s,t):s,o=e.length-1,d;o>=0;o--)(d=e[o])&&(n=(i?d(s,t,n):d(n))||n);return i&&n&&Ie(s,t,n),n};const ce={lan:0,wifi:1,bluetooth:1,vpn:2,internet:3,dns:1,ai:3,cross:0},he="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",pe=["#00e5ff","#ff00e5","#39ff14","#ffb300","#bf5af2","#00fff7","#ff3d71","#7aff3a","#ffd54f","#a78bfa"];let j=class extends oe{constructor(){super(...arguments),this.nodes=[],this.edges=[],this.visibleLayers=["lan","wifi","bluetooth","vpn","internet","dns","ai","cross"],this.hovered=null,this.selected=null,this.raf=0,this.camera={x:0,y:0,zoom:1},this.isDragging=!1,this.time=0,this.sonarRadius=0,this.packets=[],this.cameraVel={x:0,y:0},this.consoleLogs=[],this.dragNode=null,this.lastMouse={x:0,y:0},this._colors={},this._themeColors={accent:"#00e5ff",threat:"#ef4444"},this._ambientParticles=[],this._ambientInited=!1,this._arrivalRings=[],this._sonarGlow=new Map,this._nodeState=new Map,this._resize=()=>{var s;if(!this.canvas)return;const e=Math.min(window.devicePixelRatio,2);this.canvas.width=this.canvas.clientWidth*e,this.canvas.height=this.canvas.clientHeight*e,(s=this.ctx)==null||s.scale(e,e)},this._loop=()=>{var U;this.raf=requestAnimationFrame(this._loop),this.time+=1,this._stepPhysics();const e=this.canvas.clientWidth,s=this.canvas.clientHeight,t=this.ctx,i=Date.now();this.isDragging||(this.camera.x+=this.cameraVel.x,this.camera.y+=this.cameraVel.y,this.cameraVel.x*=.9,this.cameraVel.y*=.9),t.fillStyle="#030508",t.fillRect(0,0,e,s);const n=e/2,o=s/2,d=t.createRadialGradient(n,o,e*.15,n,o,e*.85);d.addColorStop(0,"rgba(6,8,14,0)"),d.addColorStop(.6,"rgba(3,5,8,0.15)"),d.addColorStop(1,"rgba(0,0,0,0.45)"),t.fillStyle=d,t.fillRect(0,0,e,s);const O=e*.3+Math.sin(this.time*.0015)*180,r=s*.35+Math.cos(this.time*.001)*120,f=t.createRadialGradient(O,r,0,O,r,e*.35);f.addColorStop(0,"rgba(0, 200, 220, 0.025)"),f.addColorStop(1,"rgba(0, 200, 220, 0)"),t.fillStyle=f,t.fillRect(0,0,e,s);const a=e*.7+Math.cos(this.time*.001)*200,g=s*.55+Math.sin(this.time*.002)*150,v=t.createRadialGradient(a,g,0,a,g,e*.35);v.addColorStop(0,"rgba(160, 80, 220, 0.02)"),v.addColorStop(1,"rgba(160, 80, 220, 0)"),t.fillStyle=v,t.fillRect(0,0,e,s);const $=e*.5+Math.sin(this.time*8e-4+2)*250,w=s*.7+Math.cos(this.time*.0012)*180,D=t.createRadialGradient($,w,0,$,w,e*.3);D.addColorStop(0,"rgba(255, 180, 60, 0.018)"),D.addColorStop(1,"rgba(255, 180, 60, 0)"),t.fillStyle=D,t.fillRect(0,0,e,s);const u=50,L=this.time*.08%u,R=this.time*.05%u,x=e/2,P=s/2,K=Math.hypot(x,P);for(let c=-u;c<e+u;c+=u)for(let T=-u;T<s+u;T+=u){const F=c+L,M=T+R,J=Math.hypot(F-x,M-P),p=Math.max(0,1-J/(K*.8)),b=.08*p*p;b<.003||(t.beginPath(),t.arc(F,M,1,0,Math.PI*2),t.fillStyle=`rgba(100, 140, 180, ${b})`,t.fill())}this._ambientInited||this._initAmbientParticles(e,s);for(const c of this._ambientParticles)c.x+=c.vx+Math.sin(this.time*c.wobbleFreq+c.phase)*c.wobbleAmp*.1,c.y+=c.vy+Math.cos(this.time*c.wobbleFreq*.7+c.phase)*c.wobbleAmp*.1,c.x<-10&&(c.x=e+10),c.x>e+10&&(c.x=-10),c.y<-10&&(c.y=s+10),c.y>s+10&&(c.y=-10),t.beginPath(),t.arc(c.x,c.y,c.size,0,Math.PI*2),t.fillStyle=c.color,t.globalAlpha=c.alpha,t.shadowColor=c.color,t.shadowBlur=6,t.fill(),t.shadowBlur=0;t.globalAlpha=1,t.save();try{t.translate(this.camera.x,this.camera.y),t.scale(this.camera.zoom,this.camera.zoom);const c=this.nodes.filter(p=>this.visibleLayers.includes(p.layer)),T=new Map(c.map(p=>[p.id,p])),F=this.edges.filter(p=>this.visibleLayers.includes(p.layer)&&T.has(p.source)&&T.has(p.target)),M=this.selected!=null;this.sonarRadius+=2.5,this.sonarRadius>e&&(this.sonarRadius=0);for(const p of F){const b=T.get(p.source),m=T.get(p.target),Y=M&&(p.source===this.selected||p.target===this.selected);M&&!Y?t.globalAlpha=.05:t.globalAlpha=1;const l=((U=p.metadata)==null?void 0:U.threat_flag)||p.layer==="internet",y=this._colors[b.layer]||this._themeColors.accent,C=this._colors[m.layer]||this._themeColors.accent,E=m.x-b.x,N=m.y-b.y,B=Math.sqrt(E*E+N*N)||1,Z=-N/B,z=E/B,W=Math.sin(b.x+m.y)*45,Q=(b.x+m.x)/2+Z*W,ee=(b.y+m.y)/2+z*W,I=t.createLinearGradient(b.x,b.y,m.x,m.y);I.addColorStop(0,y+"AA"),I.addColorStop(1,C+"AA"),t.beginPath(),t.moveTo(b.x,b.y),t.quadraticCurveTo(Q,ee,m.x,m.y);const H=p.strength>.7?1.5:1;if(l){const te=Math.sin(i/400)*.5+.5;t.shadowColor="#ef4444",t.shadowBlur=2+te*6,t.strokeStyle=`rgba(239, 68, 68, ${.6+te*.3})`,t.lineWidth=H}else t.shadowColor=y,t.shadowBlur=4,t.strokeStyle=I,t.lineWidth=H;t.setLineDash([3,8]),t.lineDashOffset=-this.time*(.8+p.strength*1.2),t.stroke(),t.setLineDash([]),t.shadowBlur=0}for(const p of this.packets){const b=T.get(p.edge.source),m=T.get(p.edge.target);if(!b||!m)continue;const Y=m.x-b.x,l=m.y-b.y,y=Math.sqrt(Y*Y+l*l)||1,C=-l/y,E=Y/y,N=Math.sin(b.x+m.y)*45,B=(b.x+m.x)/2+C*N,Z=(b.y+m.y)/2+E*N,z=p.progress,W=1-z,Q=W*W*b.x+2*W*z*B+z*z*m.x,ee=W*W*b.y+2*W*z*Z+z*z*m.y,I=Math.max(0,z-.05),H=1-I,te=H*H*b.x+2*H*I*B+I*I*m.x,ge=H*H*b.y+2*H*I*Z+I*I*m.y,be=Math.atan2(ee-ge,Q-te);t.save(),t.translate(Q,ee),t.rotate(be),t.beginPath(),t.arc(0,0,3/this.camera.zoom,0,Math.PI*2),t.fillStyle="#ffffff",t.shadowColor=p.color,t.shadowBlur=18/this.camera.zoom,t.fill();const le=50*p.speed/this.camera.zoom,ne=t.createLinearGradient(0,0,-le,0);if(ne.addColorStop(0,p.color+"CC"),ne.addColorStop(1,p.color+"00"),t.beginPath(),t.moveTo(0,0),t.lineTo(-le,0),t.strokeStyle=ne,t.lineWidth=2/this.camera.zoom,t.stroke(),t.shadowBlur=0,z>.9){const de=(z-.9)/.1,fe=de*20/this.camera.zoom,ve=1-de;t.beginPath(),t.arc(0,0,fe,0,Math.PI*2),t.strokeStyle=p.color,t.globalAlpha=ve*.8,t.lineWidth=1.5/this.camera.zoom,t.shadowColor=p.color,t.shadowBlur=6/this.camera.zoom,t.stroke(),t.globalAlpha=1,t.shadowBlur=0}t.restore()}t.globalAlpha=1;const J=this.hovered&&T.get(this.hovered)||null;this._drawNodes(t,c,J,F)}catch(c){console.error("Topology rendering error:",c)}finally{t.restore()}},this._onDown=e=>{const s=this._worldPos(e),t=this._hitTest(s.x,s.y);t?(this.isDragging=!0,this.dragNode=t,this.selected=t,this.dispatchEvent(new CustomEvent("node-select",{detail:t,bubbles:!0,composed:!0}))):(this.isDragging=!0,this.dragNode=null,this.lastMouse={x:e.clientX,y:e.clientY})},this._onMove=e=>{const s=this._worldPos(e);if(this.isDragging&&this.dragNode){const t=this.nodes.find(i=>i.id===this.dragNode);t&&(t.x=s.x,t.y=s.y,t.vx=0,t.vy=0)}else if(this.isDragging){const t=e.clientX-this.lastMouse.x,i=e.clientY-this.lastMouse.y;this.camera.x+=t,this.camera.y+=i,this.cameraVel.x=t,this.cameraVel.y=i,this.lastMouse={x:e.clientX,y:e.clientY}}else this.hovered=this._hitTest(s.x,s.y)},this._onUp=()=>{this.isDragging=!1,this.dragNode=null},this._onWheel=e=>{e.preventDefault();const s=Math.max(.15,Math.min(5,this.camera.zoom-e.deltaY*.001)),t=this.canvas.getBoundingClientRect(),i=e.clientX-t.left,n=e.clientY-t.top;this.camera.x=i-(i-this.camera.x)*(s/this.camera.zoom),this.camera.y=n-(n-this.camera.y)*(s/this.camera.zoom),this.camera.zoom=s}}connectedCallback(){super.connectedCallback(),window.addEventListener("resize",this._resize)}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf),window.removeEventListener("resize",this._resize)}firstUpdated(){this.canvas=this.renderRoot.querySelector("canvas"),this.ctx=this.canvas.getContext("2d");const e=getComputedStyle(document.body);this._colors={lan:e.getPropertyValue("--ds-success").trim()||"#10b981",wifi:e.getPropertyValue("--ds-warning").trim()||"#f59e0b",bluetooth:e.getPropertyValue("--ds-iris").trim()||"#8b5cf6",vpn:e.getPropertyValue("--ds-info").trim()||"#00e5ff",internet:e.getPropertyValue("--ds-danger").trim()||"#ef4444",dns:e.getPropertyValue("--ds-coral").trim()||"#d946ef",ai:e.getPropertyValue("--ds-sky").trim()||"#3b82f6",cross:e.getPropertyValue("--ds-text-muted").trim()||"#94a3b8"},this._themeColors.accent=e.getPropertyValue("--ds-accent").trim()||"#00e5ff",this._themeColors.threat=e.getPropertyValue("--ds-danger").trim()||"#ef4444",this.domHud=this.renderRoot.querySelector(".dom-hud"),this._resize(),this._loop(),this.canvas.addEventListener("mousedown",this._onDown),this.canvas.addEventListener("mousemove",this._onMove),this.canvas.addEventListener("mouseup",this._onUp),this.canvas.addEventListener("wheel",this._onWheel,{passive:!1})}updated(e){var s,t;if(e.has("nodes")&&this.nodes.length>0){const i=((s=this.canvas)==null?void 0:s.clientWidth)||800,n=((t=this.canvas)==null?void 0:t.clientHeight)||400;for(const o of this.nodes){const d=this._nodeState.get(o.id);if(d)o.x=d.x,o.y=d.y,o.vx=d.vx,o.vy=d.vy,o.fx=d.fx,o.fy=d.fy,o.scrambleTime=d.scrambleTime;else if(o.scrambleTime=60+Math.random()*60,o.node_type==="gateway")o.x=i/2,o.y=n/2,o.fx=i/2,o.fy=n/2;else{const r=Object.keys(this._colors).indexOf(o.layer)/7*Math.PI*2+Math.random()*.5,f=150+Math.random()*300;o.x=i/2+Math.cos(r)*f,o.y=n/2+Math.sin(r)*f,o.vx=0,o.vy=0}this._nodeState.set(o.id,o)}}}_initAmbientParticles(e,s){this._ambientParticles=[];for(let t=0;t<50;t++)this._ambientParticles.push({x:Math.random()*e,y:Math.random()*s,vx:(Math.random()-.5)*.4+(Math.random()>.5?.1:-.1),vy:(Math.random()-.5)*.4+(Math.random()>.5?.1:-.1),size:.5+Math.random()*1.5,color:pe[Math.floor(Math.random()*pe.length)],alpha:.2+Math.random()*.4,phase:Math.random()*Math.PI*2,wobbleAmp:.3+Math.random()*.6,wobbleFreq:.01+Math.random()*.02});this._ambientInited=!0}_stepPhysics(){var d,O;const e=this.nodes.filter(r=>this.visibleLayers.includes(r.layer)),s=new Map(e.map(r=>[r.id,r])),t=this.edges.filter(r=>this.visibleLayers.includes(r.layer)&&s.has(r.source)&&s.has(r.target)),i=((d=this.canvas)==null?void 0:d.clientWidth)/2||400,n=((O=this.canvas)==null?void 0:O.clientHeight)/2||300;for(const r of this.nodes)if(r.node_type==="gateway")r.x+=(i-r.x)*.1,r.y+=(n+100-r.y)*.1;else{const a=["lan","wifi","bluetooth","cross"].includes(r.layer)?i-160:i+160,g=n-60;r.vx=(r.vx||0)+(a-r.x)*6e-4,r.vy=(r.vy||0)+(g-r.y)*6e-4;const v=r.x-i;if(Math.abs(v)<80&&Math.abs(v)>.1){const $=(80-Math.abs(v))*.005;r.vx+=(v>0?1:-1)*$}}const o=new Map;for(const r of t)o.set(r.source,(o.get(r.source)||0)+1),o.set(r.target,(o.get(r.target)||0)+1);for(let r=0;r<e.length;r++)for(let f=r+1;f<e.length;f++){const a=e[r],g=e[f];let v=g.x-a.x,$=g.y-a.y;v===0&&$===0&&(v=(Math.random()-.5)*10,$=(Math.random()-.5)*10);const w=Math.max(100,v*v+$*$),D=Math.sqrt(w),u=2e4/w,L=v/D*u,R=$/D*u,x=1+(o.get(a.id)||0)*.5,P=1+(o.get(g.id)||0)*.5;a.fx==null&&(a.vx=(a.vx||0)-L/x,a.vy=(a.vy||0)-R/x),g.fx==null&&(g.vx=(g.vx||0)+L/P,g.vy=(g.vy||0)+R/P)}for(const r of t){const f=s.get(r.source),a=s.get(r.target);let g=a.x-f.x,v=a.y-f.y;g===0&&v===0&&(g=.1,v=.1);const $=Math.sqrt(g*g+v*v)||1,w=r.strength??.5,D=120+(1-w)*60,u=($-D)*.008*w,L=g/$*u,R=v/$*u,x=1+(o.get(f.id)||0)*.5,P=1+(o.get(a.id)||0)*.5;!Number.isNaN(L)&&!Number.isNaN(R)&&(f.fx==null&&(f.vx=(f.vx||0)+L/x,f.vy=(f.vy||0)+R/x),a.fx==null&&(a.vx=(a.vx||0)-L/P,a.vy=(a.vy||0)-R/P))}for(const r of e)r.scrambleTime&&r.scrambleTime>0&&r.scrambleTime--,r.fx==null&&(r.vx=(r.vx||0)+(i-r.x)*5e-5,r.vy=(r.vy||0)+(n-r.y)*5e-5,r.vx*=.85,r.vy*=.85,r.vx=Math.max(-25,Math.min(25,r.vx)),r.vy=Math.max(-25,Math.min(25,r.vy)),r.x+=r.vx,r.y+=r.vy);if(Math.random()>.3&&t.length>0){const r=t[Math.floor(Math.random()*t.length)],f=this._colors[r.layer]||this._themeColors.accent;this.packets.push({edge:r,progress:0,speed:.015+Math.random()*.025,color:f});const a=`[XFER] ${r.source.substring(0,8)} >> ${r.target.substring(0,8)} | ${(Math.random()*40).toFixed(1)}ms`;this.consoleLogs=[a,...this.consoleLogs].slice(0,10)}this.packets.forEach(r=>r.progress+=r.speed),this.packets=this.packets.filter(r=>r.progress<1)}_drawNodes(e,s,t,i){var O,r,f;const n=this.selected!=null,o=[...s].sort((a,g)=>(ce[a.layer]||0)-(ce[g.layer]||0)),d=Date.now();for(const a of o){const g=a===t,v=a.id===this.selected,$=n?i.some(l=>l.source===this.selected&&l.target===a.id||l.target===this.selected&&l.source===a.id):!1;n&&!v&&!$?e.globalAlpha=.15:e.globalAlpha=1;const w=this._colors[a.layer]||this._themeColors.accent,D=g||v?"#ffffff":w,u=((O=a.metadata)==null?void 0:O.risk)==="high"||((r=a.metadata)==null?void 0:r.trust)==="blocked",L=.75+a.id.charCodeAt(a.id.length-1)%5*.15,R=(g?1.4:1)*L;let x=(a.node_type==="gateway"?14:a.node_type==="compute"?10:7)*R;u&&(x+=2*R);const P=s.find(l=>l.node_type==="gateway");let K=0;if(P&&a!==P){const l=Math.hypot(a.x-P.x,a.y-P.y);Math.abs(l-this.sonarRadius)<40&&(K=1-Math.abs(l-this.sonarRadius)/40)}const U=this._sonarGlow.get(a.id)||0,c=U+(K-U)*.2;if(this._sonarGlow.set(a.id,c),a.node_type==="gateway"){const l=Math.sin(d/1600)*.5+.5,y=Math.sin(d/2200+1)*.5+.5,C=x*2.5+l*12,E=x*3.5+y*16;e.beginPath(),e.arc(a.x,a.y,C,0,Math.PI*2),e.strokeStyle=`rgba(0, 229, 255, ${.12+l*.08})`,e.lineWidth=1,e.shadowColor="#00e5ff",e.shadowBlur=6,e.stroke(),e.shadowBlur=0,e.beginPath(),e.arc(a.x,a.y,E,0,Math.PI*2),e.strokeStyle=`rgba(0, 229, 255, ${.06+y*.06})`,e.lineWidth=.8,e.shadowColor="#00e5ff",e.shadowBlur=4,e.stroke(),e.shadowBlur=0;const B=Math.max(0,1-this.sonarRadius/1200)*.5*(.5+.5*Math.cos(this.sonarRadius*.003));B>.005&&(e.beginPath(),e.arc(a.x,a.y,this.sonarRadius,0,Math.PI*2),e.strokeStyle=`rgba(0, 229, 255, ${B})`,e.lineWidth=1,e.stroke(),e.beginPath(),e.arc(a.x,a.y,this.sonarRadius+4,0,Math.PI*2),e.strokeStyle=`rgba(0, 229, 255, ${B*.6})`,e.lineWidth=.6,e.stroke())}else if(u){const l=Math.sin(d/300)*.5+.5,y=x*3+l*8,C=e.createRadialGradient(a.x,a.y,x,a.x,a.y,y);C.addColorStop(0,`rgba(239, 68, 68, ${.25+l*.15})`),C.addColorStop(1,"rgba(239, 68, 68, 0)"),e.beginPath(),e.arc(a.x,a.y,y,0,Math.PI*2),e.fillStyle=C,e.fill()}(a.node_type==="gateway"||a.node_type==="compute")&&(e.save(),e.translate(a.x,a.y),e.rotate(this.time*(a.node_type==="gateway"?.008:-.012)),e.beginPath(),e.arc(0,0,x+8,0,Math.PI*1.4),e.strokeStyle=w+"30",e.lineWidth=.8,e.stroke(),e.restore(),e.save(),e.translate(a.x,a.y),e.rotate(this.time*(a.node_type==="gateway"?-.015:.018)),e.beginPath(),e.arc(0,0,x+5,Math.PI*.5,Math.PI*1.9),e.strokeStyle=w+"20",e.lineWidth=.8,e.stroke(),e.restore());const T=c*14,F=g?25:12;if(e.beginPath(),e.arc(a.x,a.y,x,0,Math.PI*2),e.fillStyle=u?"rgba(40,5,5,0.9)":"rgba(8,10,18,0.9)",e.fill(),e.shadowColor=u?"#ef4444":w,e.shadowBlur=F+T,e.strokeStyle=u?"#ef4444":w,e.lineWidth=2,e.stroke(),e.shadowBlur=0,e.beginPath(),e.arc(a.x,a.y,x*.4,0,Math.PI*2),e.fillStyle=u?"#ef4444":w,e.shadowColor=u?"#ef4444":w,e.shadowBlur=8+T,e.fill(),e.shadowBlur=0,v||g){e.beginPath(),e.arc(a.x,a.y,x*1.8+Math.sin(d/200)*1.5,0,Math.PI*2),e.strokeStyle=D,e.lineWidth=1/this.camera.zoom,e.setLineDash([4,4]),e.stroke(),e.setLineDash([]);const l=x*2.5,y=l*.3;e.beginPath(),e.moveTo(a.x-l,a.y-l+y),e.lineTo(a.x-l,a.y-l),e.lineTo(a.x-l+y,a.y-l),e.moveTo(a.x+l-y,a.y-l),e.lineTo(a.x+l,a.y-l),e.lineTo(a.x+l,a.y-l+y),e.moveTo(a.x+l,a.y+l-y),e.lineTo(a.x+l,a.y+l),e.lineTo(a.x+l-y,a.y+l),e.moveTo(a.x-l+y,a.y+l),e.lineTo(a.x-l,a.y+l),e.lineTo(a.x-l,a.y+l-y),e.strokeStyle=D,e.lineWidth=1.5/this.camera.zoom,e.stroke()}let M=a.label.toUpperCase();a.scrambleTime&&a.scrambleTime>0?M=M.split("").map(l=>Math.random()>.5?he[Math.floor(Math.random()*he.length)]:l).join(""):M.length>18&&(M=M.slice(0,16)+"…");const J=10/this.camera.zoom;e.font=`500 ${J}px monospace`,e.textAlign="center";const p=a.y+x+22/this.camera.zoom;e.shadowColor=u?"#ef4444":w,e.shadowBlur=4,e.fillStyle=g||v?"#ffffff":w;const b=1.5/this.camera.zoom,m=e.measureText(M).width+b*(M.length-1);let Y=a.x-m/2;for(let l=0;l<M.length;l++)e.fillText(M[l],Y,p),Y+=e.measureText(M[l]).width+b;if(e.shadowBlur=0,g&&this.domHud){const l=a.x*this.camera.zoom+this.camera.x,y=a.y*this.camera.zoom+this.camera.y;this.domHud.style.display="block",this.domHud.style.left=`${l}px`,this.domHud.style.top=`${y}px`;const C=`> TARGET_LOCK: ${a.id}
> IP_RESOLVE : ${((f=a.metadata)==null?void 0:f.ip)||"UNKNOWN"}
> SEC_STATUS : ${u?"COMPROMISED":"ENCRYPTED"}`;a._hoverStartTime||(a._hoverStartTime=this.time);const E=(this.time-a._hoverStartTime)/2,N=Math.min(C.length,Math.floor(E));this.domHud.innerText=C.substring(0,N)+(Math.random()>.5&&N<C.length?"_":""),this.domHud.className=`dom-hud ${u?"threat":""}`}else!g&&!a._hoverStartTime&&(a._hoverStartTime=0)}!t&&this.domHud&&(this.domHud.style.display="none")}_drawTargetReticule(e,s,t,i,n){e.strokeStyle=n,e.lineWidth=1.5;const o=i+8,d=6;e.beginPath(),e.moveTo(s-o,t-o+d),e.lineTo(s-o,t-o),e.lineTo(s-o+d,t-o),e.moveTo(s+o-d,t-o),e.lineTo(s+o,t-o),e.lineTo(s+o,t-o+d),e.moveTo(s+o,t+o-d),e.lineTo(s+o,t+o),e.lineTo(s+o-d,t+o),e.moveTo(s-o+d,t+o),e.lineTo(s-o,t+o),e.lineTo(s-o,t+o-d),e.stroke(),e.save(),e.translate(s,t),e.rotate(this.time*.02),e.beginPath(),e.arc(0,0,i+3,0,Math.PI*2),e.setLineDash([4,6]),e.stroke(),e.restore()}_worldPos(e){const s=this.canvas.getBoundingClientRect();return{x:(e.clientX-s.left-this.camera.x)/this.camera.zoom,y:(e.clientY-s.top-this.camera.y)/this.camera.zoom}}_hitTest(e,s){for(const t of this.nodes){if(!this.visibleLayers.includes(t.layer))continue;const i=t.node_type==="gateway"?24:t.layer==="ai"?18:10;if(Math.hypot(t.x-e,t.y-s)<i+8)return t.id}return null}render(){return h`
      <div class="vignette"></div>
      <div class="hud-overlay">
        <div>SYS.OP // TOPOLOGY TRACE ACTIVE</div>
        <div>NODES: ${this.nodes.length}</div>
        <div style="color:var(--ds-danger, #ef4444)">THREATS DETECTED</div>
      </div>
      <div class="packet-console">
        ${this.consoleLogs.map(e=>h`<div>${e}</div>`)}
      </div>
      <div class="dom-hud"></div>
      <canvas></canvas>
      <div class="legend">
        ${Object.entries(this._colors).map(([e,s])=>h`
          <div class="legend-item">
            <span class="dot" style="background:${s}; box-shadow: 0 0 6px ${s}"></span>
            <span>${e}</span>
          </div>
        `)}
      </div>
    `}};j.styles=ae`
    :host { display: block; width: 100%; height: 100%; position: relative; background: #030508; overflow: hidden; }
    canvas { width: 100%; height: 100%; display: block; cursor: crosshair; }
    canvas:active { cursor: grabbing; }

    .hud-overlay {
      position: absolute; top: 20px; left: 20px; pointer-events: none;
      font-family: var(--ds-font-mono, monospace); color: var(--ds-accent, #00e5ff);
      font-size: 10px; letter-spacing: 0.14em; opacity: 0.7;
      text-shadow: 0 0 6px rgba(0,229,255,0.4);
      line-height: 1.8; text-transform: uppercase;
    }

    .legend {
      position: absolute; bottom: 16px; left: 16px; display: flex; gap: 12px; flex-wrap: wrap;
      padding: 10px 16px;
      background: rgba(6,8,14,0.65);
      border: 1px solid rgba(255,255,255,0.06);
      border-left: 2px solid var(--ds-accent, #00e5ff);
      font-size: 10px; font-family: var(--ds-font-mono, monospace);
      text-transform: uppercase; letter-spacing: 0.14em;
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border-radius: 4px;
      box-shadow: 0 4px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .legend-item { display: flex; align-items: center; gap: 6px; color: rgba(255,255,255,0.6); }
    .dot { width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }

    .vignette {
      position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%);
      z-index: 9;
    }
    .packet-console {
      position: absolute; bottom: 80px; left: 20px;
      font-family: var(--ds-font-mono, monospace); font-size: 10px;
      color: rgba(0,229,255,0.65); pointer-events: none;
      text-shadow: 0 0 4px rgba(0,229,255,0.3);
      display: flex; flex-direction: column; gap: 3px; z-index: 100; width: 300px;
    }
    .dom-hud {
      position: absolute; pointer-events: none; display: none;
      background: rgba(4,6,12,0.85);
      border: 1px solid rgba(0,229,255,0.2);
      padding: 10px 14px;
      font-family: var(--ds-font-mono, monospace); font-size: 11px;
      color: rgba(0,229,255,0.9); z-index: 100;
      backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
      box-shadow: 0 0 20px rgba(0,229,255,0.08);
      border-left: 2px solid var(--ds-accent, #00e5ff);
      border-radius: 3px;
      transform: translate(25px, -50%); white-space: pre; line-height: 1.6;
    }
    .dom-hud.threat {
      border-color: rgba(239,68,68,0.3);
      border-left-color: var(--ds-danger, #ef4444);
      box-shadow: 0 0 20px rgba(239,68,68,0.12);
      color: #ff003c;
    }
  `;G([A({type:Array})],j.prototype,"nodes",2);G([A({type:Array})],j.prototype,"edges",2);G([A({type:Array})],j.prototype,"visibleLayers",2);G([_()],j.prototype,"hovered",2);G([_()],j.prototype,"selected",2);G([_()],j.prototype,"consoleLogs",2);j=G([re("topology-canvas")],j);var Ne=Object.defineProperty,Oe=Object.getOwnPropertyDescriptor,X=(e,s,t,i)=>{for(var n=i>1?void 0:i?Oe(s,t):s,o=e.length-1,d;o>=0;o--)(d=e[o])&&(n=(i?d(s,t,n):d(n))||n);return i&&n&&Ne(s,t,n),n};let V=class extends oe{constructor(){super(...arguments),this.node=null,this.open=!1,this.observations=[],this.inferences=[],this.analysis=null,this.loading=!1}updated(e){e.has("node")&&this.node&&this._loadData()}async _loadData(){if(this.node){this.loading=!0;try{const[e,s]=await Promise.all([ue(this.node.id,void 0,24).catch(()=>({observations:[]})),me(this.node.id,void 0,10).catch(()=>({inferences:[]}))]);this.observations=e.observations,this.inferences=s.inferences}catch{}this.loading=!1}}async _analyse(){if(this.node){this.loading=!0;try{const e=await ye("device",this.node.id);this.analysis=e.analysis||e}catch{}this.loading=!1}}render(){if(!this.node)return h`<div class="panel"><span class="muted">Select a node to view details.</span></div>`;const e=this.node,s=`layer-${e.layer}`;return h`
      <div class="panel">
        <div class="header">
          <span class="layer-badge ${s}">${e.layer}</span>
          <h3 style="margin:0;font-size:var(--ds-text-lg);">${e.label}</h3>
        </div>

        <div class="section">
          <div class="section-title">Metadata</div>
          <div class="meta-grid">
            <div class="meta-item"><div class="k">ID</div><div class="v">${e.id}</div></div>
            <div class="meta-item"><div class="k">Type</div><div class="v">${e.node_type}</div></div>
            ${Object.entries(e.metadata).map(([t,i])=>h`
              <div class="meta-item"><div class="k">${t}</div><div class="v">${typeof i=="object"?JSON.stringify(i):String(i)}</div></div>
            `)}
          </div>
        </div>

        <div class="section">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="section-title">AI Analysis</div>
            <button @click=${()=>void this._analyse()} ?disabled=${this.loading}>${this.loading?"Analysing…":"Analyse"}</button>
          </div>
          ${this.analysis?h`
            <div class="analysis-result">${this.analysis.explanation||JSON.stringify(this.analysis,null,2)}</div>
          `:h`<span class="muted">Click Analyse to generate AI insight.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Inferences · ${this.inferences.length}</div>
          ${this.inferences.length?this.inferences.map(t=>h`
            <div class="inference">
              <div class="conf">${t.inference_type} · ${(t.confidence*100).toFixed(0)}% · ${new Date(t.timestamp).toLocaleString()}</div>
              <div class="text">${t.explanation}</div>
            </div>
          `):h`<span class="muted">No inferences yet.</span>`}
        </div>

        <div class="section">
          <div class="section-title">Observations · ${this.observations.length}</div>
          ${this.observations.length?h`
            <div class="meta-grid">
              ${this.observations.slice(0,6).map(t=>{var i,n;return h`
                <div class="meta-item">
                  <div class="k">${t.metric}</div>
                  <div class="v">${((n=(i=t.value)==null?void 0:i.toFixed)==null?void 0:n.call(i,2))??t.value}</div>
                </div>
              `})}
            </div>
          `:h`<span class="muted">No observations in the last 24h.</span>`}
        </div>
      </div>
    `}};V.styles=ae`
    :host { display: block; font-family: var(--ds-font-mono, monospace); }
    .panel { 
      background: rgba(2, 4, 8, 0.6); 
      padding: 20px; 
      height: 100%; 
      overflow-y: auto; 
      color: rgba(0, 229, 255, 0.8);
    }
    .header { 
      display: flex; align-items: center; gap: 12px; margin-bottom: 24px; 
      padding-bottom: 12px; border-bottom: 1px solid rgba(0, 229, 255, 0.2);
    }
    .layer-badge { 
      padding: 4px 10px; border-radius: 2px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
      border: 1px solid currentColor;
    }
    .layer-lan { color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .layer-wifi { color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
    .layer-bluetooth { color: #8b5cf6; background: rgba(139, 92, 246, 0.1); }
    .layer-vpn { color: var(--ds-accent); background: rgba(0, 229, 255, 0.1); }
    .layer-internet { color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .layer-dns { color: #d946ef; background: rgba(217, 70, 239, 0.1); }
    .layer-ai { color: #3b82f6; background: rgba(59, 130, 246, 0.1); }
    
    .section { margin-bottom: 24px; }
    .section-title { font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 0.2em; margin-bottom: 12px; }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .meta-item { 
      background: rgba(0, 0, 0, 0.5); 
      border: 1px solid rgba(0, 229, 255, 0.15);
      padding: 10px; border-radius: 2px; font-size: 0.8rem; 
    }
    .meta-item .k { font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }
    .meta-item .v { color: var(--ds-accent); word-break: break-all; }
    
    .inference { 
      background: rgba(0, 0, 0, 0.5); padding: 12px; border-radius: 2px; margin-bottom: 8px; 
      border: 1px solid rgba(0, 229, 255, 0.15); border-left: 3px solid var(--ds-accent); 
    }
    .inference .conf { font-size: 0.65rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; }
    .inference .text { font-size: 0.8rem; color: var(--ds-accent); margin-top: 6px; }
    
    .analysis-result { background: #000; border: 1px solid var(--ds-accent); padding: 16px; border-radius: 2px; font-size: 0.8rem; color: var(--ds-accent); white-space: pre-wrap; box-shadow: inset 0 0 15px rgba(0, 229, 255, 0.1); }
    .muted { color: rgba(255,255,255,0.3); font-size: 0.8rem; font-style: italic; }
    
    button { 
      background: transparent; color: var(--ds-accent); border: 1px solid var(--ds-accent); 
      padding: 6px 12px; border-radius: 2px; font-size: 0.7rem; font-family: var(--ds-font-mono, monospace);
      text-transform: uppercase; letter-spacing: 0.15em; cursor: pointer; transition: all 0.2s;
    }
    button:hover:not(:disabled) { background: var(--ds-accent); color: #000; box-shadow: 0 0 15px var(--ds-accent); }
    button:disabled { opacity: 0.5; cursor: not-allowed; border-color: rgba(0, 229, 255, 0.3); color: rgba(0, 229, 255, 0.5); }
    
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(0, 229, 255, 0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 229, 255, 0.6); }
  `;X([A({type:Object})],V.prototype,"node",2);X([A({type:Boolean})],V.prototype,"open",2);X([A({type:Array})],V.prototype,"observations",2);X([A({type:Array})],V.prototype,"inferences",2);X([A({type:Object})],V.prototype,"analysis",2);X([A({type:Boolean})],V.prototype,"loading",2);V=X([re("network-detail-panel")],V);var Ee=Object.defineProperty,Be=Object.getOwnPropertyDescriptor,S=(e,s,t,i)=>{for(var n=i>1?void 0:i?Be(s,t):s,o=e.length-1,d;o>=0;o--)(d=e[o])&&(n=(i?d(s,t,n):d(n))||n);return i&&n&&Ee(s,t,n),n};let k=class extends xe(oe){constructor(){super(...arguments),this.status=null,this.devices=[],this.events=[],this.threats=[],this.aps=[],this.evilTwin=!1,this.loading=!0,this.filter="all",this.scanIp="",this.scanResult=null,this.scanLoading=!1,this.graph={nodes:[],edges:[]},this.graphStats=null,this.selectedNode=null,this.activeTab="devices"}connectedCallback(){super.connectedCallback(),this.load(),this.timer=setInterval(()=>void this.load(),8e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async load(){try{const[e,s,t,i,n,o,d]=await Promise.all([we().catch(()=>null),ke().catch(()=>({devices:[]})),_e(20).catch(()=>({events:[]})),$e(24).catch(()=>({threats:[]})),Me().catch(()=>({aps:[],evil_twin_detected:!1})),Se().catch(()=>({nodes:[],edges:[]})),Te().catch(()=>null)]);this.status=e,this.devices=s.devices,this.events=t.events,this.threats=i.threats,this.aps=n.aps,this.evilTwin=n.evil_twin_detected,this.graph=o,this.graphStats=d}catch{}this.loading=!1}async act(e,s){try{await(s==="trust"?Pe:Ce)(e),se(`Device ${s}ed`,s==="trust"?"success":"danger"),this.load()}catch{se(`${s} failed`,"danger")}}async ackEvent(e){try{await ze(e),this.load()}catch{se("Ack failed","danger")}}async doScan(){if(this.scanIp.trim()){this.scanLoading=!0;try{this.scanResult=await Ae(this.scanIp.trim())}catch{se("Scan failed","danger")}this.scanLoading=!1}}filteredDevices(){return this.filter==="all"?this.devices:this.devices.filter(e=>e.trust_status===this.filter)}render(){if(this.loading)return h`<div class="empty-state" style="padding:60px;">Initializing SYS.OP Trace...</div>`;const e=this.status,s=this.filteredDevices(),t=this.events.filter(i=>!i.acknowledged);return h`
      <!-- ═══ HERO: Full-bleed Topology ═══ -->
      <div class="hero">
        <div class="topo-wrap">
          <div class="topo-header">
            <span class="topo-title">// Global Topology Trace</span>
            <span style="display:flex;gap:16px;align-items:center;">
              <span class="topo-stats">${this.graphStats?Object.entries(this.graphStats.nodes_by_layer).map(([i,n])=>`${i}:${n}`).join(" · "):""}</span>
              <button class="rescan-btn" @click=${()=>void this.load()}>Rescan</button>
            </span>
          </div>
          <topology-canvas
            .nodes=${this.graph.nodes}
            .edges=${this.graph.edges}
            @node-select=${i=>{this.selectedNode=this.graph.nodes.find(n=>n.id===i.detail)||null}}
          ></topology-canvas>
        </div>
        <div class="detail-sidebar">
          <network-detail-panel .node=${this.selectedNode}></network-detail-panel>
        </div>
      </div>

      <!-- ═══ Score Ribbon ═══ -->
      <div class="score-ribbon">
        <div class="score-cell">
          <div class="score-val ${e?e.score>=80?"ok":e.score>=50?"warn":"danger":""}">${(e==null?void 0:e.score)??"--"}</div>
          <div class="score-label">Trust Score</div>
        </div>
        <div class="score-cell">
          <div class="score-val ok">${(e==null?void 0:e.devices_trusted)??0}</div>
          <div class="score-label">Trusted</div>
        </div>
        <div class="score-cell">
          <div class="score-val warn">${(e==null?void 0:e.devices_unknown)??0}</div>
          <div class="score-label">Unknown</div>
        </div>
        <div class="score-cell">
          <div class="score-val danger">${(e==null?void 0:e.devices_suspicious)??0}</div>
          <div class="score-label">Suspicious</div>
        </div>
        <div class="score-cell">
          <div class="score-val ${((e==null?void 0:e.threats_24h)??0)>0?"danger":"ok"}">${(e==null?void 0:e.threats_24h)??0}</div>
          <div class="score-label">Threats 24h</div>
        </div>
      </div>

      <!-- ═══ Lower: Tabbed Intelligence ═══ -->
      <div class="lower">
        <div class="tab-bar">
          <button class="tab-btn ${this.activeTab==="devices"?"active":""}" @click=${()=>this.activeTab="devices"}>
            Devices <span class="count">${this.devices.length}</span>
          </button>
          <button class="tab-btn ${this.activeTab==="threats"?"active":""}" @click=${()=>this.activeTab="threats"}>
            Threats ${this.threats.length>0?h`<span class="count danger">${this.threats.length}</span>`:""}
          </button>
          <button class="tab-btn ${this.activeTab==="scanner"?"active":""}" @click=${()=>this.activeTab="scanner"}>
            Scanner
          </button>
          <button class="tab-btn ${this.activeTab==="wifi"?"active":""}" @click=${()=>this.activeTab="wifi"}>
            RF Spectrum <span class="count">${this.aps.length}</span>
          </button>
        </div>

        <div class="tab-content">
          ${this.activeTab==="devices"?this._renderDevices(s):""}
          ${this.activeTab==="threats"?this._renderThreats(t):""}
          ${this.activeTab==="scanner"?this._renderScanner():""}
          ${this.activeTab==="wifi"?this._renderWifi():""}
        </div>
      </div>
    `}_renderDevices(e){return h`
      <div class="filter-row">
        ${["all","trusted","unknown","suspicious"].map(s=>h`
          <button class="filter-btn ${this.filter===s?"on":""}" @click=${()=>this.filter=s}>${s}</button>
        `)}
      </div>
      <div class="dev-grid">
        <div class="dev-header">
          <span>Identity</span><span>IPv4</span><span>MAC / Vendor</span><span>Last Seen</span><span>Status</span><span>Actions</span>
        </div>
        ${e.length?e.map(s=>h`
          <div class="dev-row">
            <div class="dev-name">
              <span class="status-dot ${s.trust_status}"></span>
              ${s.hostname||"Unknown_Client"}${s.is_gateway?" [GW]":""}
            </div>
            <span class="dim">${s.ip}</span>
            <span class="dim">${s.mac}${s.vendor?` · ${s.vendor}`:""}</span>
            <span class="dim">${new Date(s.last_seen).toLocaleTimeString()}</span>
            <span class="badge badge-${s.trust_status}">${s.trust_status}</span>
            <span style="display:flex;gap:6px;">
              ${s.trust_status!=="trusted"?h`<button class="action-btn trust" @click=${()=>void this.act(s.mac,"trust")}>Trust</button>`:""}
              ${s.trust_status!=="blocked"?h`<button class="action-btn block" @click=${()=>void this.act(s.mac,"block")}>Block</button>`:""}
            </span>
          </div>
        `):h`<div class="empty-state">No devices match current filter.</div>`}
      </div>
    `}_renderThreats(e){return h`
      ${e.length>0?h`
        <div class="alert-banner">\u26A0 ${e.length} Unacknowledged Security Alert${e.length>1?"s":""}</div>
        ${e.map(s=>h`
          <div class="threat-row" style="border-left-color:#ef4444;">
            <span class="threat-dot"></span>
            <span style="flex:1;color:rgba(255,255,255,0.85);">${s.message}</span>
            <span class="dim">${new Date(s.timestamp).toLocaleTimeString()}</span>
            <button class="action-btn trust" @click=${()=>void this.ackEvent(s.id)}>ACK</button>
          </div>
        `)}
        <div style="height:16px;"></div>
      `:""}

      ${this.threats.length?this.threats.map(s=>h`
        <div class="threat-row">
          <span class="threat-dot"></span>
          <span style="flex:1;color:#00e5ff;">${s.type}</span>
          <span class="dim">${s.confidence.toFixed(0)}% conf</span>
          <span class="dim">${new Date(s.detected_at).toLocaleTimeString()}</span>
        </div>
      `):h`<div class="empty-state">No active threat vectors tracked. System secure.</div>`}
    `}_renderScanner(){return h`
      <div class="scan-input-row">
        <input class="scan-input" type="text" placeholder="Target IP or range..." .value=${this.scanIp}
          @input=${e=>this.scanIp=e.target.value}
          @keydown=${e=>e.key==="Enter"&&void this.doScan()} />
        <button class="scan-btn" @click=${()=>void this.doScan()} ?disabled=${this.scanLoading}>
          ${this.scanLoading?"Scanning...":"Execute"}
        </button>
      </div>
      ${this.scanResult?h`<div class="scan-output">${JSON.stringify(this.scanResult,null,2)}</div>`:""}
    `}_renderWifi(){return h`
      ${this.evilTwin?h`<div class="alert-banner">CRITICAL: Evil Twin / Rogue AP Detected</div>`:""}
      ${this.aps.length?this.aps.map(e=>h`
        <div class="ap-row">
          <span style="display:flex;gap:10px;align-items:center;">
            <span style="color:#00e5ff;font-weight:600;">${e.ssid||"[HIDDEN_SSID]"}</span>
            <span class="dim">CH:${e.channel}</span>
          </span>
          <span class="dim">${e.bssid}</span>
          <span style="color:rgba(255,255,255,0.7);">${e.signal} dBm</span>
          ${e.rogue?h`<span class="rogue-tag">Rogue</span>`:""}
        </div>
      `):h`<div class="empty-state">Awaiting RF telemetry...</div>`}
    `}};k.styles=ae`
    :host {
      display: flex; flex-direction: column;
      height: 100%; width: 100%;
      font-family: var(--ds-font-mono, monospace);
      background: #030508;
      color: rgba(220, 240, 255, 0.9);
      overflow: hidden;
    }

    /* ─── Hero: Full-bleed topology ─── */
    .hero {
      position: relative;
      flex: 1 1 55%;
      min-height: 340px;
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 0;
      border-bottom: 1px solid rgba(0, 229, 255, 0.1);
    }
    .topo-wrap {
      position: relative;
      overflow: hidden;
      background: #030508;
    }
    .topo-header {
      position: absolute; top: 0; left: 0; right: 0; z-index: 20;
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 24px;
      background: linear-gradient(to bottom, rgba(3,5,8,0.9) 0%, rgba(3,5,8,0) 100%);
      pointer-events: none;
    }
    .topo-title {
      font-size: 0.7rem; color: rgba(0,229,255,0.7);
      letter-spacing: 0.3em; text-transform: uppercase; font-weight: 600;
      text-shadow: 0 0 8px rgba(0,229,255,0.2);
    }
    .topo-stats {
      font-size: 0.6rem; color: rgba(0,229,255,0.5);
      letter-spacing: 0.15em; text-transform: uppercase;
    }
    .detail-sidebar {
      background: rgba(4, 8, 16, 0.7);
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border-left: 1px solid rgba(0, 229, 255, 0.1);
      overflow-y: auto;
    }

    /* ─── Score ribbon ─── */
    .score-ribbon {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 1px;
      background: rgba(0, 229, 255, 0.06);
      flex: 0 0 auto;
    }
    .score-cell {
      padding: 16px 20px;
      background: rgba(4, 8, 16, 0.85);
      display: flex; flex-direction: column; gap: 6px;
      position: relative; overflow: hidden;
      transition: background 0.3s;
    }
    .score-cell:hover {
      background: rgba(0, 229, 255, 0.04);
    }
    .score-cell::after {
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(0,229,255,0.15), transparent);
    }
    .score-val {
      font-size: 1.6rem; font-weight: 700; letter-spacing: -0.5px;
      text-shadow: 0 0 20px currentColor;
    }
    .score-val.ok { color: #00e5ff; }
    .score-val.warn { color: #f59e0b; }
    .score-val.danger { color: #ef4444; }
    .score-label {
      font-size: 0.6rem; color: rgba(255,255,255,0.4);
      text-transform: uppercase; letter-spacing: 0.2em;
    }

    /* ─── Lower panels ─── */
    .lower {
      flex: 1 1 45%;
      min-height: 0;
      display: flex; flex-direction: column;
      overflow: hidden;
    }

    /* ─── Tab bar ─── */
    .tab-bar {
      display: flex; gap: 0;
      background: rgba(4, 8, 16, 0.85);
      border-bottom: 1px solid rgba(0, 229, 255, 0.08);
      flex: 0 0 auto;
    }
    .tab-btn {
      padding: 10px 20px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.65rem; font-weight: 500;
      text-transform: uppercase; letter-spacing: 0.2em;
      color: rgba(0, 229, 255, 0.45);
      background: transparent;
      border: none; border-bottom: 2px solid transparent;
      cursor: pointer;
      transition: all 0.25s;
      position: relative;
    }
    .tab-btn:hover {
      color: rgba(0, 229, 255, 0.7);
      background: rgba(0, 229, 255, 0.03);
    }
    .tab-btn.active {
      color: #00e5ff;
      border-bottom-color: #00e5ff;
      text-shadow: 0 0 10px rgba(0,229,255,0.4);
    }
    .tab-btn .count {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 16px; height: 16px; padding: 0 4px;
      border-radius: 8px;
      background: rgba(0, 229, 255, 0.15);
      color: #00e5ff;
      font-size: 0.55rem; font-weight: 700;
      margin-left: 6px;
    }
    .tab-btn .count.danger {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    /* ─── Tab content ─── */
    .tab-content {
      flex: 1 1 auto;
      overflow-y: auto;
      padding: 16px 24px;
      background: rgba(3, 5, 8, 0.7);
    }

    /* ─── Device table ─── */
    .filter-row {
      display: flex; gap: 6px; margin-bottom: 12px;
    }
    .filter-btn {
      padding: 4px 12px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.12em;
      background: transparent;
      border: 1px solid rgba(0, 229, 255, 0.12);
      border-radius: 3px;
      color: rgba(0, 229, 255, 0.5);
      cursor: pointer;
      transition: all 0.2s;
    }
    .filter-btn:hover { border-color: rgba(0,229,255,0.3); color: rgba(0,229,255,0.8); }
    .filter-btn.on {
      color: #030508; background: #00e5ff; border-color: #00e5ff;
      font-weight: 700;
      box-shadow: 0 0 12px rgba(0,229,255,0.3);
    }

    .dev-grid { display: flex; flex-direction: column; gap: 2px; }
    .dev-header {
      display: grid;
      grid-template-columns: 1.5fr 1fr 1.5fr 0.8fr 0.7fr auto;
      gap: 12px; align-items: center;
      padding: 8px 14px;
      font-size: 0.6rem; color: rgba(0,229,255,0.6);
      text-transform: uppercase; letter-spacing: 0.2em;
      border-bottom: 1px solid rgba(0,229,255,0.12);
    }
    .dev-row {
      display: grid;
      grid-template-columns: 1.5fr 1fr 1.5fr 0.8fr 0.7fr auto;
      gap: 12px; align-items: center;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-left: 2px solid transparent;
      border-radius: 2px;
      font-size: 0.75rem;
      transition: all 0.2s;
    }
    .dev-row:hover {
      background: rgba(0, 229, 255, 0.04);
      border-left-color: #00e5ff;
    }
    .dev-name {
      display: flex; align-items: center; gap: 8px;
      font-weight: 600; color: rgba(255,255,255,0.85);
    }
    .status-dot {
      width: 6px; height: 6px; border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
      flex: none;
    }
    .status-dot.trusted { color: #00e5ff; background: #00e5ff; }
    .status-dot.unknown { color: #f59e0b; background: #f59e0b; }
    .status-dot.suspicious, .status-dot.blocked { color: #ef4444; background: #ef4444; }
    .dim { color: rgba(0, 229, 255, 0.4); font-size: 0.7rem; }

    .badge {
      padding: 3px 8px; border-radius: 2px;
      font-size: 0.55rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.12em;
      border: 1px solid currentColor; text-align: center;
    }
    .badge-trusted { color: #00e5ff; background: rgba(0,229,255,0.06); }
    .badge-unknown { color: #f59e0b; background: rgba(245,158,11,0.06); }
    .badge-suspicious { color: #ef4444; background: rgba(239,68,68,0.06); }
    .badge-blocked { color: #ef4444; background: rgba(239,68,68,0.1); box-shadow: 0 0 8px rgba(239,68,68,0.15); }

    .action-btn {
      padding: 3px 8px; font-size: 0.55rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.1em;
      font-family: var(--ds-font-mono, monospace);
      background: transparent; cursor: pointer;
      border: 1px solid; border-radius: 2px;
      transition: all 0.2s;
    }
    .action-btn.trust { color: #00e5ff; border-color: rgba(0,229,255,0.3); }
    .action-btn.trust:hover { background: rgba(0,229,255,0.1); border-color: #00e5ff; }
    .action-btn.block { color: #ef4444; border-color: rgba(239,68,68,0.3); }
    .action-btn.block:hover { background: rgba(239,68,68,0.1); border-color: #ef4444; }

    /* ─── Threat / event rows ─── */
    .threat-row {
      display: flex; align-items: center; gap: 14px;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-left: 2px solid rgba(239, 68, 68, 0.3);
      border-radius: 0 2px 2px 0;
      font-size: 0.75rem;
      margin-bottom: 2px;
      transition: all 0.2s;
    }
    .threat-row:hover {
      background: rgba(239, 68, 68, 0.04);
      border-left-color: #ef4444;
    }
    .threat-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #ef4444;
      box-shadow: 0 0 8px rgba(239,68,68,0.6);
      animation: threat-pulse 2s infinite;
      flex: none;
    }
    @keyframes threat-pulse {
      0%, 100% { box-shadow: 0 0 4px rgba(239,68,68,0.4); }
      50% { box-shadow: 0 0 12px rgba(239,68,68,0.8); }
    }

    .alert-banner {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 16px; margin-bottom: 12px;
      background: rgba(239, 68, 68, 0.06);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-left: 3px solid #ef4444;
      border-radius: 3px;
      color: #ef4444;
      font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.15em;
      animation: alert-glow 2s infinite;
    }
    @keyframes alert-glow {
      0%, 100% { box-shadow: inset 0 0 0 rgba(239,68,68,0); }
      50% { box-shadow: inset 0 0 20px rgba(239,68,68,0.08); }
    }

    /* ─── Scanner ─── */
    .scan-input-row { display: flex; gap: 10px; }
    .scan-input {
      flex: 1; padding: 10px 14px;
      background: rgba(0,0,0,0.5);
      border: 1px solid rgba(0,229,255,0.15);
      border-radius: 3px;
      color: #00e5ff;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.75rem;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .scan-input:focus {
      outline: none;
      border-color: rgba(0,229,255,0.5);
      box-shadow: 0 0 16px rgba(0,229,255,0.1);
    }
    .scan-btn {
      padding: 0 20px;
      background: #00e5ff; border: none; border-radius: 3px;
      color: #030508; font-weight: 700;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 0 12px rgba(0,229,255,0.2);
    }
    .scan-btn:hover { box-shadow: 0 0 24px rgba(0,229,255,0.4); }
    .scan-btn:disabled { opacity: 0.5; cursor: wait; }
    .scan-output {
      margin-top: 12px; padding: 14px;
      background: rgba(0,0,0,0.6);
      border: 1px solid rgba(0,229,255,0.12);
      border-left: 2px solid #00e5ff;
      border-radius: 3px;
      color: #00e5ff; font-size: 0.7rem;
      overflow: auto; max-height: 240px;
      white-space: pre-wrap;
      text-shadow: 0 0 4px rgba(0,229,255,0.15);
    }

    /* ─── WiFi / AP list ─── */
    .ap-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 14px;
      background: rgba(6, 10, 18, 0.5);
      border-radius: 2px;
      font-size: 0.75rem;
      margin-bottom: 2px;
      transition: background 0.2s;
    }
    .ap-row:hover { background: rgba(0,229,255,0.04); }
    .rogue-tag {
      color: #ef4444; font-weight: 700; font-size: 0.6rem;
      text-transform: uppercase; letter-spacing: 0.12em;
      text-shadow: 0 0 8px rgba(239,68,68,0.5);
      animation: threat-pulse 1s infinite;
    }

    .empty-state {
      padding: 24px; text-align: center;
      color: rgba(0,229,255,0.35);
      font-size: 0.7rem; letter-spacing: 0.15em;
      text-transform: uppercase;
    }

    .rescan-btn {
      pointer-events: auto;
      background: transparent;
      border: 1px solid rgba(0,229,255,0.25);
      color: rgba(0,229,255,0.6);
      padding: 4px 14px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.55rem; letter-spacing: 0.15em; text-transform: uppercase;
      cursor: pointer; border-radius: 3px;
      transition: all 0.2s;
    }
    .rescan-btn:hover {
      border-color: #00e5ff; color: #00e5ff;
      box-shadow: 0 0 12px rgba(0,229,255,0.15);
    }

    @media (max-width: 900px) {
      .hero { grid-template-columns: 1fr; }
      .detail-sidebar { display: none; }
      .score-ribbon { grid-template-columns: repeat(3, 1fr); }
    }
  `;S([_()],k.prototype,"status",2);S([_()],k.prototype,"devices",2);S([_()],k.prototype,"events",2);S([_()],k.prototype,"threats",2);S([_()],k.prototype,"aps",2);S([_()],k.prototype,"evilTwin",2);S([_()],k.prototype,"loading",2);S([_()],k.prototype,"filter",2);S([_()],k.prototype,"scanIp",2);S([_()],k.prototype,"scanResult",2);S([_()],k.prototype,"scanLoading",2);S([_()],k.prototype,"graph",2);S([_()],k.prototype,"graphStats",2);S([_()],k.prototype,"selectedNode",2);S([_()],k.prototype,"activeTab",2);k=S([re("network-view")],k);export{k as NetworkView};
//# sourceMappingURL=network-view-DmCjhklT.js.map
