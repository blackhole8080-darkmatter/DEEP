import{i as u,b as o,a as m,r as p,t as f}from"./index-2Z09ZJ8J.js";var b=Object.defineProperty,x=Object.getOwnPropertyDescriptor,c=(a,t,e,s)=>{for(var i=s>1?void 0:s?x(t,e):t,n=a.length-1,r;n>=0;n--)(r=a[n])&&(i=(s?r(t,e,i):r(i))||i);return s&&i&&b(t,e,i),i};let l=class extends u{constructor(){super(...arguments),this.vitals=[{label:"CPU CORE 0",value:"12.4%",spark:Array.from({length:40},()=>Math.random()*30+10),status:"good"},{label:"SYS RAM",value:"32.1 GB",spark:Array.from({length:40},()=>Math.random()*10+40),status:"good"},{label:"NET I/O",value:"402 Mbps",spark:Array.from({length:40},()=>Math.random()*50+20),status:"good"},{label:"THREAT",value:"SECURE",spark:Array.from({length:40},()=>Math.random()*5),status:"good"}],this.events=[{time:"14:32",type:"success",message:"Network scan completed — 24 devices found"},{time:"14:28",type:"info",message:"Agent 'Alpha-7' started analysis task"},{time:"14:15",type:"warn",message:"Unrecognized device joined LAN: 192.168.1.44"},{time:"13:52",type:"info",message:"Knowledge graph synced — 520 entities"},{time:"13:30",type:"success",message:"Voice assistant model loaded"},{time:"12:45",type:"alert",message:"Critical update available: security patch"}],this._ringCircumference=2*Math.PI*34}connectedCallback(){super.connectedCallback(),this._interval=setInterval(()=>this._tick(),1e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this._interval)}_tick(){this.vitals=this.vitals.map(a=>{const t=a.spark[a.spark.length-1]+(Math.random()-.5)*15,e=[...a.spark.slice(1),Math.max(0,Math.min(100,t))];let s=a.value;return a.label.includes("CPU")?s=e[e.length-1].toFixed(1)+"%":a.label.includes("RAM")?s=(e[e.length-1]/2).toFixed(1)+" GB":a.label.includes("NET")&&(s=Math.abs(e[e.length-1]*10).toFixed(0)+" Mbps"),{...a,spark:e,value:s}})}_ringDash(a){const t=this._ringCircumference;return`${t*(1-a)} ${t}`}_getColor(a){return a==="critical"?"#ef4444":a==="warn"?"#eab308":"#00e5ff"}_renderGraph(a,t){const e=Math.max(0,Math.min(...a)-5),i=Math.max(...a)+5-e||1,n=200,r=50,v=n/(a.length-1),d=a.map((g,h)=>`${(h*v).toFixed(1)},${(r-(g-e)/i*r).toFixed(1)}`).join(" ");return o`
      <svg class="telemetry-svg" viewBox="0 -5 ${n} ${r+10}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="grad-${t.replace("#","")}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${t}" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="${t}" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <path class="telemetry-area" d="M 0,${r} L ${d.split(" ")[0]} L ${d} L ${n},${r} Z" fill="url(#grad-${t.replace("#","")})"></path>
        <polyline class="telemetry-line" points="${d}" style="stroke: ${t}; filter: drop-shadow(0 0 4px ${t})"></polyline>
        <line x1="0" y1="${r/2}" x2="${n}" y2="${r/2}" class="telemetry-grid" stroke-dasharray="2,4" />
        <line x1="0" y1="${r}" x2="${n}" y2="${r}" class="telemetry-grid" stroke-dasharray="2,4" />
      </svg>
    `}render(){const a=new Date().getHours(),t=a<12?"Good morning, Aryan":a<18?"Good afternoon, Aryan":"Good evening, Aryan";return o`
      <div class="greeting">${t}</div>
      <div class="subgreeting">DEEP is online and monitoring your systems.</div>

      <div class="hud">
        ${this.vitals.map((e,s)=>o`
          <holo-panel title="${e.label}" accent="cyan" .pulseOnUpdate=${s}>
            <div class="hud-value ${e.status}">${e.value}</div>
            ${this._renderGraph(e.spark,this._getColor(e.status))}
          </holo-panel>
        `)}
      </div>

      <div class="mid">
        <holo-panel title="System Activity" accent="green">
          <div class="rings">
            ${[{label:"Agents",pct:Math.max(.1,this.vitals[0].spark[39]/100),color:"var(--ds-accent)"},{label:"Security",pct:Math.max(.1,1-this.vitals[3].spark[39]/10),color:"var(--ds-success)"},{label:"Queue",pct:Math.max(.05,this.vitals[2].spark[39]/100),color:"var(--ds-warning)"}].map(e=>o`
              <div class="ring-wrap">
                <svg class="ring-svg" viewBox="0 0 80 80">
                  <circle class="ring-track" cx="40" cy="40" r="34" />
                  <circle class="ring-fill" cx="40" cy="40" r="34"
                    stroke-dasharray="${this._ringDash(e.pct)}"
                    style="stroke:${e.color}" />
                </svg>
                <div class="ring-label">${e.label}<br/><strong>${Math.round(e.pct*100)}%</strong></div>
              </div>
            `)}
          </div>
          <div class="actions">
            <button class="action-btn" @click=${()=>location.hash="network"}>◉ Scan Network</button>
            <button class="action-btn" @click=${()=>location.hash="home"}>◆ Open Chat</button>
            <button class="action-btn" @click=${()=>location.hash="agents"}>✦ Launch Agent</button>
            <button class="action-btn" @click=${()=>location.hash="system"}>⚙ System Check</button>
          </div>
        </holo-panel>

        <holo-panel title="Live Events" accent="violet">
          <div class="feed">
            ${this.events.map((e,s)=>o`
              <div class="event ${e.type}" style="animation-delay:${s*.05}s">
                <span class="event-time">${e.time}</span>
                <span class="event-msg">${e.message}</span>
              </div>
            `)}
          </div>
        </holo-panel>
      </div>
    `}};l.styles=m`
    :host {
      display: grid;
      gap: var(--ds-space-4);
      padding: var(--ds-space-5);
      overflow-y: auto;
      height: 100%;
    }

    /* ── Top HUD row ── */
    .hud {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--ds-space-3);
    }
    .hud-card {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      padding: var(--ds-space-4);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s var(--ds-ease-out), box-shadow 0.2s var(--ds-ease-out);
    }
    .hud-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--ds-elev-2), 0 0 20px rgba(var(--ds-periwinkle-rgb), 0.08);
    }
    .hud-card::after {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--ds-accent), transparent);
      opacity: 0.25;
    }
    .hud-label {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-faint);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
      margin-bottom: var(--ds-space-2);
    }
    .hud-value {
      font-size: var(--ds-text-2xl);
      font-weight: 700;
      color: var(--ds-text);
      font-family: var(--ds-font-mono);
      animation: text-glow 3s ease-in-out infinite;
    }
    .hud-value.warn { color: var(--ds-warning); }
    .hud-value.critical { color: var(--ds-danger); }

    /* Telemetry Graphs */
    .telemetry-svg {
      width: 100%; height: 50px;
      margin-top: var(--ds-space-2);
      overflow: visible;
    }
    .telemetry-line {
      fill: none;
      stroke-width: 1.5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .telemetry-area {
      opacity: 0.15;
    }
    .telemetry-grid {
      stroke: rgba(0, 229, 255, 0.15);
      stroke-width: 1;
    }

    /* ── Middle row ── */
    .mid {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: var(--ds-space-4);
    }
    @media (max-width: 900px) { .mid { grid-template-columns: 1fr; } }

    .panel {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      padding: var(--ds-space-4);
      position: relative;
    }
    .panel::after {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, var(--ds-accent), transparent);
      opacity: 0.25;
    }
    .panel-title {
      font-size: var(--ds-text-sm);
      color: var(--ds-text-soft);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
      margin-bottom: var(--ds-space-3);
      display: flex; align-items: center; gap: var(--ds-space-2);
    }
    .panel-title .dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent);
      box-shadow: 0 0 6px var(--ds-accent);
    }

    /* ── Activity rings ── */
    .rings {
      display: flex; gap: var(--ds-space-4);
      justify-content: center;
      padding: var(--ds-space-3) 0;
    }
    .ring-wrap {
      display: flex; flex-direction: column; align-items: center; gap: var(--ds-space-2);
    }
    .ring-svg {
      width: 80px; height: 80px;
      transform: rotate(-90deg);
    }
    .ring-track { fill: none; stroke: var(--ds-surface-3); stroke-width: 6; }
    .ring-fill {
      fill: none; stroke: var(--ds-accent); stroke-width: 6;
      stroke-linecap: round;
      transition: stroke-dashoffset 1s var(--ds-ease-out);
      filter: drop-shadow(0 0 4px var(--ds-accent));
    }
    .ring-label {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
      text-align: center;
    }

    /* ── Event feed ── */
    .feed {
      display: flex; flex-direction: column; gap: var(--ds-space-2);
      max-height: 280px;
      overflow-y: auto;
    }
    .event {
      display: flex; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-3);
      border-radius: var(--ds-radius-sm);
      background: var(--ds-surface-1);
      border-left: 2px solid transparent;
      font-size: var(--ds-text-sm);
      animation: fade-up 0.3s var(--ds-ease-out) both;
    }
    .event.info  { border-left-color: var(--ds-info); }
    .event.warn  { border-left-color: var(--ds-warning); }
    .event.alert { border-left-color: var(--ds-danger); }
    .event.success { border-left-color: var(--ds-success); }
    .event-time {
      color: var(--ds-text-faint);
      font-family: var(--ds-font-mono);
      font-size: var(--ds-text-xs);
      white-space: nowrap;
    }
    .event-msg { color: var(--ds-text-soft); }

    /* ── Quick actions ── */
    .actions {
      display: flex; gap: var(--ds-space-3);
      flex-wrap: wrap;
    }
    .action-btn {
      display: inline-flex; align-items: center; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-4);
      border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border-accent);
      background: rgba(var(--ds-periwinkle-rgb), 0.08);
      color: var(--ds-accent);
      font-size: var(--ds-text-sm);
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s var(--ds-ease-out);
    }
    .action-btn:hover {
      background: rgba(var(--ds-periwinkle-rgb), 0.15);
      box-shadow: 0 0 16px rgba(var(--ds-periwinkle-rgb), 0.2);
      transform: translateY(-1px);
    }

    .greeting {
      font-size: var(--ds-text-2xl);
      font-weight: 600;
      color: var(--ds-text);
      margin-bottom: var(--ds-space-1);
      animation: text-glow 3s ease-in-out infinite;
    }
    .subgreeting {
      font-size: var(--ds-text-sm);
      color: var(--ds-text-muted);
      margin-bottom: var(--ds-space-4);
    }
  `;c([p()],l.prototype,"vitals",2);c([p()],l.prototype,"events",2);l=c([f("dashboard-view")],l);export{l as DashboardView};
//# sourceMappingURL=dashboard-view-CD32Sh4G.js.map
