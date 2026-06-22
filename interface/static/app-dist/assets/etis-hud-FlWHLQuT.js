import{i as O,d as e,F as r,e as P,r as n,t as N}from"./index-B9odUZEe.js";import"./ds-panel-D8ZUzx06.js";import"./ds-button-Ms_8tG_O.js";var A=Object.defineProperty,F=Object.getOwnPropertyDescriptor,l=(t,s,i,a)=>{for(var c=a>1?void 0:a?F(s,i):s,p=t.length-1,h;p>=0;p--)(h=t[p])&&(c=(a?h(s,i,c):h(c))||c);return a&&c&&A(s,i,c),c};let o=class extends O{constructor(){super(...arguments),this.activePanel="overview",this.domains={},this.loading=!1,this.error="",this.intelItems=[],this.intelLoading=!1,this.cveId="",this.cveResult=null,this.cveSearchKeyword="",this.cveSearchResults=[],this.rfFreq="2437000000",this.rfBw="20000000",this.rfResult=null,this.wifiNetworks=[],this.bleDevices=[],this.physExpr="",this.physVars="",this.physResult=null,this.physSim="pendulum",this.physSimResult=null,this.robotModel="ur5",this.robotAngles="0,0,0,0,0,0",this.robotFkResult=null,this.robotTarget="0.3,0.2,0.5",this.robotIkResult=null,this.sandboxCode=`import sys, platform
print(f"Python {sys.version}")
print(f"Platform: {platform.system()}")
print("ETIS sandbox operational.")
print(2**64)`,this.sandboxLang="python",this.sandboxResult=null,this.sandboxRunning=!1,this.sandboxStatus=null,this.hexSamples="",this.protoResult=null}connectedCallback(){super.connectedCallback(),this.loadStatus()}async loadStatus(){this.loading=!0;try{const s=await(await fetch("/api/etis/status")).json();s.ok&&(this.domains=s.data.domains)}catch{this.error="ETIS status unreachable"}this.loading=!1}async api(t,s){const a=await(await fetch(`/api/etis${t}`,s)).json();if(!a.ok)throw new Error(a.error||"API error");return a.data}async apiPost(t,s){return this.api(t,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(s)})}async loadIntel(){this.intelLoading=!0;try{const t=await this.api("/intel/feed?days_back=14");this.intelItems=t.items}catch(t){this.error=t.message}this.intelLoading=!1}async lookupCve(){if(this.cveId.trim())try{this.cveResult=await this.api(`/cve/${this.cveId.trim().toUpperCase()}`)}catch(t){this.error=t.message}}async searchCve(){if(this.cveSearchKeyword.trim())try{const t=await this.apiPost("/cve/search",{keyword:this.cveSearchKeyword,min_cvss:7,days_back:30});this.cveSearchResults=t.results}catch(t){this.error=t.message}}async identifyRfProtocol(){try{const t=await this.api(`/rf/protocol?center_freq=${this.rfFreq}&bandwidth=${this.rfBw}`);this.rfResult=t}catch(t){this.error=t.message}}async wifiScan(){try{const t=await this.apiPost("/rf/wifi/scan",{});this.wifiNetworks=t.networks}catch(t){this.error=t.message}}async bleScan(){try{const t=await this.apiPost("/rf/ble/scan",{duration:8});this.bleDevices=t.devices}catch(t){this.error=t.message}}async computePhysics(){if(!this.physExpr.trim())return;let t={};try{this.physVars.trim()&&this.physVars.split(",").forEach(s=>{const[i,a]=s.trim().split("=");i&&a&&(t[i.trim()]=parseFloat(a.trim()))}),this.physResult=await this.apiPost("/physics/compute",{expression:this.physExpr,variables:t})}catch(s){this.error=s.message}}async simulatePhysics(){try{this.physSimResult=await this.apiPost("/physics/simulate",{system:this.physSim,t_span:[0,15]})}catch(t){this.error=t.message}}async computeFk(){try{const t=this.robotAngles.split(",").map(Number);this.robotFkResult=await this.apiPost("/robotics/fk",{joint_angles:t,model:this.robotModel})}catch(t){this.error=t.message}}async computeIk(){try{const t=this.robotTarget.split(",").map(Number);this.robotIkResult=await this.apiPost("/robotics/ik",{target_pos:t,model:this.robotModel})}catch(t){this.error=t.message}}async runSandbox(){this.sandboxRunning=!0,this.sandboxResult=null;try{this.sandboxResult=await this.apiPost("/sandbox/execute",{code:this.sandboxCode,language:this.sandboxLang,timeout:30})}catch(t){this.error=t.message}this.sandboxRunning=!1}async checkSandboxStatus(){try{this.sandboxStatus=await this.api("/sandbox/status")}catch(t){this.error=t.message}}async analyzeProto(){const t=this.hexSamples.trim().split(`
`).map(s=>s.trim()).filter(Boolean);if(t.length)try{this.protoResult=await this.apiPost("/protocols/binary-re",{hex_samples:t})}catch(s){this.error=s.message}}_sev(t){return e`<span class="sev sev-${t.toUpperCase()}">${t}</span>`}_cvss(t){if(!t)return r;const s=t>=9?"red":t>=7?"amber":t>=4?"blue":"green";return e`<span class="metric-value ${s}">CVSS ${t.toFixed(1)}</span>`}_termJson(t){return t?e`<div class="term"><span class="hi">${JSON.stringify(t,null,2)}</span></div>`:r}_renderOverview(){return e`
      <div class="card">
        <div class="card-header">ETIS OVERVIEW</div>
        <div class="domain-grid">
          ${Object.entries({cybersec:{icon:"🛡",label:"CYBERSEC",panel:"cyber"},rf:{icon:"📡",label:"RF / WIRELESS",panel:"rf"},protocols:{icon:"⚙",label:"PROTOCOLS",panel:"rf"},hardware:{icon:"🔬",label:"HARDWARE",panel:"rf"},physics:{icon:"⚛",label:"PHYSICS",panel:"physics"},robotics:{icon:"🤖",label:"ROBOTICS",panel:"robotics"},sandbox:{icon:"📦",label:"SANDBOX",panel:"sandbox"}}).map(([s,i])=>{const a=this.domains[s];return e`
              <div class="domain-card ${a!=null&&a.available?"":"unavail"}"
                   @click=${()=>{a!=null&&a.available&&(this.activePanel=i.panel)}}>
                <div class="dc-name">
                  <span class="dc-icon">${i.icon}</span>${i.label}
                </div>
                <div class="dc-status ${a!=null&&a.available?"":"err"}">
                  ${this.loading?e`<span class="spin"></span>loading`:a!=null&&a.available?"● OPERATIONAL":"○ UNAVAILABLE"}
                </div>
                ${a!=null&&a.capabilities?e`
                  <div class="dc-caps">
                    ${a.capabilities.map(c=>e`<span class="dc-cap">${c}</span>`)}
                  </div>
                `:r}
              </div>
            `})}
        </div>
      </div>

      <!-- Quick intel summary -->
      <div class="card">
        <div class="card-header">LIVE THREAT INTEL</div>
        ${this.intelItems.length?e`
            <div style="font-size:11px; color:var(--ds-text-soft); margin-bottom:8px;">
              ${this.intelItems.filter(s=>s.is_kev).length} KEV &nbsp;·&nbsp;
              ${this.intelItems.filter(s=>s.severity==="CRITICAL").length} CRITICAL &nbsp;·&nbsp;
              ${this.intelItems.length} total items
            </div>
            ${this.intelItems.slice(0,4).map(s=>{var i;return e`
              <div class="intel-item ${s.is_kev?"kev":(i=s.severity)==null?void 0:i.toLowerCase()}">
                <div class="intel-item-title">${s.title}</div>
                <div class="intel-item-meta">
                  <span class="source">[${s.source}]</span>
                  <span>${s.published}</span>
                  ${this._sev(s.severity)}
                  ${s.is_kev?e`<span class="kev">🔴 KEV</span>`:r}
                </div>
              </div>
            `})}
          `:e`
            <button class="etis-btn" @click=${()=>{this.loadIntel(),this.activePanel="intel"}}>
              LOAD INTEL FEED
            </button>
          `}
      </div>
    `}_renderCyber(){var t;return e`
      <!-- CVE Lookup -->
      <div class="card">
        <div class="card-header">🛡 CVE LOOKUP</div>
        <div class="field-row">
          <div class="field">
            <label>CVE ID</label>
            <input .value=${this.cveId}
                   @input=${s=>this.cveId=s.target.value}
                   placeholder="CVE-2024-3400"
                   @keydown=${s=>{s.key==="Enter"&&this.lookupCve()}}
            />
          </div>
          <button class="etis-btn" @click=${()=>void this.lookupCve()}>LOOKUP</button>
        </div>
        ${this.cveResult?e`
          <div class="term">
<span class="hi">[CVE] ${this.cveResult.cve_id}</span>
<span class="dim">Severity: </span><span class="${((t=this.cveResult.severity)==null?void 0:t.toLowerCase())==="critical"?"err":"warn"}">${this.cveResult.severity}</span>  ${this._cvss(this.cveResult.cvss_score)}
<span class="dim">Published:</span> ${this.cveResult.published}
<span class="dim">KEV:      </span> ${this.cveResult.is_kev?e`<span class="kev">YES — actively exploited in the wild!</span>`:e`<span class="ok">No</span>`}
<span class="dim">CWEs:     </span> ${(this.cveResult.cwes||[]).join(", ")||"None"}
<span class="dim">Affected: </span> ${(this.cveResult.affected_products||[]).slice(0,4).join(", ")}
<span class="dim">Desc:     </span> ${this.cveResult.description}
          </div>
        `:r}
      </div>

      <!-- CVE Search -->
      <div class="card">
        <div class="card-header">🔍 CVE SEARCH</div>
        <div class="field-row">
          <div class="field">
            <label>KEYWORD</label>
            <input .value=${this.cveSearchKeyword}
                   @input=${s=>this.cveSearchKeyword=s.target.value}
                   placeholder="palo alto, cisco, apache..."
                   @keydown=${s=>{s.key==="Enter"&&this.searchCve()}}
            />
          </div>
          <button class="etis-btn" @click=${()=>void this.searchCve()}>SEARCH NVD</button>
        </div>
        ${this.cveSearchResults.length?e`
          <div class="term">
            ${this.cveSearchResults.map(s=>{var i;return e`
<span class="hi">${s.cve_id}</span>  ${this._cvss(s.cvss_score)}  ${s.is_kev?e`<span class="kev">KEV</span>`:r}
<span class="dim">${(i=s.description)==null?void 0:i.slice(0,120)}…</span>

            `})}
          </div>
        `:r}
      </div>

      <!-- OSINT Recon -->
      <div class="card">
        <div class="card-header">🕵 OSINT PASSIVE RECON</div>
        <div class="field-row">
          <div class="field">
            <label>TARGET (domain or IP)</label>
            <input id="osint-target" placeholder="example.com  or  1.2.3.4" />
          </div>
          <button class="etis-btn" @click=${async()=>{const i=this.shadowRoot.querySelector("#osint-target").value.trim();if(i)try{const a=await this.apiPost("/osint/recon",{target:i}),c=this.shadowRoot.querySelector("#osint-out");c&&(c.textContent=JSON.stringify(a,null,2))}catch(a){this.error=a.message}}}>RECON</button>
        </div>
        <div id="osint-out" class="term" style="display:block;"></div>
      </div>

      <!-- Exploit lookup -->
      <div class="card">
        <div class="card-header">💥 EXPLOIT SEARCH</div>
        <div class="field-row">
          <div class="field">
            <label>CVE ID</label>
            <input id="exploit-cve" placeholder="CVE-2024-3400" />
          </div>
          <button class="etis-btn danger" @click=${async()=>{const i=this.shadowRoot.querySelector("#exploit-cve").value.trim().toUpperCase();if(i)try{const a=await this.apiPost("/exploit/search",{cve_id:i}),c=this.shadowRoot.querySelector("#exploit-out");c&&(c.textContent=JSON.stringify(a.exploits,null,2))}catch(a){this.error=a.message}}}>SEARCH EXPLOITS</button>
        </div>
        <div id="exploit-out" class="term" style="display:block;"></div>
      </div>
    `}_renderRF(){var t;return e`
      <!-- Protocol ID -->
      <div class="card">
        <div class="card-header">📡 RF PROTOCOL IDENTIFIER</div>
        <div class="field-row">
          <div class="field">
            <label>CENTER FREQ (Hz)</label>
            <input .value=${this.rfFreq}
                   @input=${s=>this.rfFreq=s.target.value}
                   placeholder="2437000000" />
          </div>
          <div class="field">
            <label>BANDWIDTH (Hz)</label>
            <input .value=${this.rfBw}
                   @input=${s=>this.rfBw=s.target.value}
                   placeholder="20000000" />
          </div>
          <button class="etis-btn" @click=${()=>void this.identifyRfProtocol()}>IDENTIFY</button>
        </div>
        ${this.rfResult?e`
          <div class="term">
            ${(t=this.rfResult.matches)==null?void 0:t.map((s,i)=>e`
<span class="${i===0?"ok":"dim"}">[${Math.round(s.confidence*100)}%] ${s.protocol}</span>
<span class="dim">    Modulation: ${s.modulation}  |  BW: ${(s.bandwidth_khz||0).toFixed(0)} kHz</span>
<span class="dim">    Use: ${s.typical_use}</span>
${s.security_notes?e`<span class="warn">    ⚠ ${s.security_notes}</span>`:r}

            `)}
          </div>
        `:r}
      </div>

      <!-- WiFi scan -->
      <div class="card">
        <div class="card-header">📶 WIFI DEEP SCAN</div>
        <div class="field-row">
          <button class="etis-btn blue" @click=${()=>void this.wifiScan()}>SCAN NEARBY NETWORKS</button>
        </div>
        ${this.wifiNetworks.length?e`
          <div class="term">
            ${this.wifiNetworks.map(s=>e`
<span class="hi">${s.ssid||"(hidden)"}</span>  <span class="dim">${s.bssid}</span>  ch<span class="ok">${s.channel}</span>  <span class="${s.signal_strength>-60?"ok":"warn"}">${s.signal_strength} dBm</span>  <span class="dim">${s.security}</span>
            `)}
          </div>
        `:r}
      </div>

      <!-- BLE scan -->
      <div class="card">
        <div class="card-header">🔵 BLUETOOTH / BLE ENUMERATION</div>
        <div class="field-row">
          <button class="etis-btn blue" @click=${()=>void this.bleScan()}>SCAN BLE DEVICES (8s)</button>
        </div>
        ${this.bleDevices.length?e`
          <div class="term">
            ${this.bleDevices.map(s=>e`
<span class="hi">${s.address}</span>  <span class="dim">${s.name||"(no name)"}</span>  ${s.rssi} dBm  ~${(s.distance_m||0).toFixed(1)}m${s.is_airtag?e`  <span class="warn">🍎 AirTag</span>`:r}
            `)}
          </div>
        `:r}
      </div>

      <!-- Binary Protocol RE -->
      <div class="card">
        <div class="card-header">🔬 BINARY PROTOCOL REVERSE ENGINEERING</div>
        <div class="field-row">
          <div class="field" style="flex:1">
            <label>HEX SAMPLES (one per line)</label>
            <textarea .value=${this.hexSamples}
                      @input=${s=>this.hexSamples=s.target.value}
                      placeholder="AABB0001000B48656C6C6F0000CDEF&#10;AABB0002000648692100FFEE"></textarea>
          </div>
        </div>
        <div class="field-row">
          <button class="etis-btn" @click=${()=>void this.analyzeProto()}>ANALYZE PROTOCOL</button>
        </div>
        ${this.protoResult?e`
          <div class="term">
<span class="hi">Protocol: ${this.protoResult.description}</span>
Entropy: ${(this.protoResult.entropy||0).toFixed(2)} bits/byte  |  Confidence: ${Math.round((this.protoResult.confidence||0)*100)}%
Encrypted: ${this.protoResult.is_encrypted}  |  Magic: ${this.protoResult.has_magic}  |  Checksum: ${this.protoResult.has_checksum}
Header: ${this.protoResult.header_size}B

Fields:
${(this.protoResult.fields||[]).map(s=>`  @${s.offset}+${s.size}B [${s.type}]: ${s.description}`).join(`
`)}

${(this.protoResult.security_issues||[]).length?e`<span class="err">Security Issues:\n${(this.protoResult.security_issues||[]).map(s=>`  ⚠ ${s}`).join(`
`)}</span>`:r}
          </div>
        `:r}
      </div>
    `}_renderPhysics(){return e`
      <!-- Symbolic / numeric compute -->
      <div class="card">
        <div class="card-header">⚛ PHYSICS COMPUTATION</div>
        <div class="field-row">
          <div class="field" style="flex:2">
            <label>EXPRESSION</label>
            <input .value=${this.physExpr}
                   @input=${t=>this.physExpr=t.target.value}
                   placeholder="plasma_frequency, lorentz_force, E = m*c**2, ..."
                   @keydown=${t=>{t.key==="Enter"&&this.computePhysics()}}
            />
          </div>
          <div class="field">
            <label>VARIABLES (k=v, ...)</label>
            <input .value=${this.physVars}
                   @input=${t=>this.physVars=t.target.value}
                   placeholder="n=1e18, B=0.5" />
          </div>
          <button class="etis-btn" @click=${()=>void this.computePhysics()}>COMPUTE</button>
        </div>
        ${this.physResult?this._termJson(this.physResult):r}
      </div>

      <!-- ODE Simulation -->
      <div class="card">
        <div class="card-header">🌀 SYSTEM SIMULATION</div>
        <div class="field-row">
          <div class="field">
            <label>SYSTEM</label>
            <select .value=${this.physSim} @change=${t=>this.physSim=t.target.value}>
              <option value="pendulum">Pendulum</option>
              <option value="lorenz">Lorenz Attractor</option>
              <option value="harmonic_oscillator">Harmonic Oscillator</option>
              <option value="plasma_wave">Plasma Wave</option>
            </select>
          </div>
          <button class="etis-btn" @click=${()=>void this.simulatePhysics()}>SIMULATE [0, 15s]</button>
        </div>
        ${this.physSimResult?e`
          <div class="term">
<span class="hi">[SIM] ${this.physSim}</span>
Time steps: ${(this.physSimResult.t||[]).length}
Final state: ${JSON.stringify((this.physSimResult.y||[]).map(t=>{var s;return(s=t[t.length-1])==null?void 0:s.toFixed(4)}))}
${this.physSimResult.plot_url?e`<span class="ok">Plot: <a href="${this.physSimResult.plot_url}" target="_blank">${this.physSimResult.plot_url}</a></span>`:r}
          </div>
        `:r}
      </div>

      <!-- Constants lookup -->
      <div class="card">
        <div class="card-header">🔭 PHYSICAL CONSTANTS</div>
        <div class="field-row">
          <div class="field">
            <label>CONSTANT NAME</label>
            <input id="const-name" placeholder="speed_of_light, planck_constant, ..."
                   @keydown=${async t=>{if(t.key!=="Enter")return;const s=t.target;try{const i=await this.api(`/physics/constant/${s.value.trim()}`),a=this.shadowRoot.querySelector("#const-out");a&&(a.textContent=`${i.name}: ${i.value} ${i.unit}
${i.description||""}`)}catch(i){this.error=i.message}}}
            />
          </div>
          <button class="etis-btn" @click=${async()=>{const s=this.shadowRoot.querySelector("#const-name").value.trim();if(s)try{const i=await this.api(`/physics/constant/${s}`),a=this.shadowRoot.querySelector("#const-out");a&&(a.textContent=`${i.name}: ${i.value} ${i.unit}
${i.description||""}`)}catch(i){this.error=i.message}}}>LOOKUP</button>
        </div>
        <div id="const-out" class="term" style="display:block;min-height:0;"></div>
      </div>
    `}_renderRobotics(){var t,s,i,a,c,p,h,b,m,x,g,y,f,$,R,E,w,k,S,I;return e`
      <div class="two-col">
        <!-- FK -->
        <div class="card">
          <div class="card-header">🤖 FORWARD KINEMATICS</div>
          <div class="field-row">
            <div class="field">
              <label>MODEL</label>
              <select .value=${this.robotModel} @change=${d=>this.robotModel=d.target.value}>
                <option value="ur5">UR5 (6-DOF)</option>
                <option value="puma560">PUMA 560</option>
              </select>
            </div>
          </div>
          <div class="field-row">
            <div class="field">
              <label>JOINT ANGLES (rad, comma sep)</label>
              <input .value=${this.robotAngles}
                     @input=${d=>this.robotAngles=d.target.value}
                     placeholder="0,0,0,0,0,0" />
            </div>
            <button class="etis-btn" @click=${()=>void this.computeFk()}>COMPUTE FK</button>
          </div>
          ${this.robotFkResult?e`
            <div class="term">
<span class="hi">[FK] ${this.robotModel.toUpperCase()}</span>
Position:
  x = <span class="ok">${(s=(t=this.robotFkResult.position)==null?void 0:t.x)==null?void 0:s.toFixed(4)}m</span>
  y = <span class="ok">${(a=(i=this.robotFkResult.position)==null?void 0:i.y)==null?void 0:a.toFixed(4)}m</span>
  z = <span class="ok">${(p=(c=this.robotFkResult.position)==null?void 0:c.z)==null?void 0:p.toFixed(4)}m</span>
Manipulability: ${(h=this.robotFkResult.manipulability)==null?void 0:h.toFixed(4)}
Singularity: ${this.robotFkResult.singularity?e`<span class="err">⚠ YES</span>`:e`<span class="ok">No</span>`}
            </div>
          `:r}
        </div>

        <!-- IK -->
        <div class="card">
          <div class="card-header">🎯 INVERSE KINEMATICS</div>
          <div class="field-row">
            <div class="field">
              <label>TARGET POSITION (x,y,z in m)</label>
              <input .value=${this.robotTarget}
                     @input=${d=>this.robotTarget=d.target.value}
                     placeholder="0.3,0.2,0.5" />
            </div>
            <button class="etis-btn" @click=${()=>void this.computeIk()}>COMPUTE IK</button>
          </div>
          ${this.robotIkResult?e`
            <div class="term">
<span class="hi">[IK] ${this.robotModel.toUpperCase()}</span>
Target:   (${(m=(b=this.robotIkResult.target)==null?void 0:b.x)==null?void 0:m.toFixed(3)}, ${(g=(x=this.robotIkResult.target)==null?void 0:x.y)==null?void 0:g.toFixed(3)}, ${(f=(y=this.robotIkResult.target)==null?void 0:y.z)==null?void 0:f.toFixed(3)})m
Achieved: (${(R=($=this.robotIkResult.achieved)==null?void 0:$.x)==null?void 0:R.toFixed(4)}, ${(w=(E=this.robotIkResult.achieved)==null?void 0:E.y)==null?void 0:w.toFixed(4)}, ${(S=(k=this.robotIkResult.achieved)==null?void 0:k.z)==null?void 0:S.toFixed(4)})m
Error:    <span class="${this.robotIkResult.error_mm<1?"ok":"warn"}">${(I=this.robotIkResult.error_mm)==null?void 0:I.toFixed(3)} mm</span>

Joint angles (deg):
${(this.robotIkResult.joint_angles_deg||[]).map((d,u)=>`  J${u+1}: ${d.toFixed(2)}°`).join(`
`)}
            </div>
          `:r}
        </div>
      </div>

      <!-- Trajectory -->
      <div class="card">
        <div class="card-header">📈 CUBIC TRAJECTORY PLANNER</div>
        <div class="field-row">
          <div class="field">
            <label>START ANGLES (rad)</label>
            <input id="traj-start" placeholder="0,0,0,0,0,0" />
          </div>
          <div class="field">
            <label>END ANGLES (rad)</label>
            <input id="traj-end" placeholder="1.57,0.5,-1.0,0,0,0" />
          </div>
          <div class="field" style="max-width:100px">
            <label>DURATION (s)</label>
            <input id="traj-dur" placeholder="3.0" />
          </div>
          <button class="etis-btn" @click=${async()=>{const d=this.shadowRoot.querySelector("#traj-start").value.split(",").map(Number),u=this.shadowRoot.querySelector("#traj-end").value.split(",").map(Number),T=parseFloat(this.shadowRoot.querySelector("#traj-dur").value||"3");try{const v=await this.apiPost("/robotics/trajectory",{q_start:d,q_end:u,duration:T}),C=this.shadowRoot.querySelector("#traj-out");C&&(C.textContent=`Duration: ${v.duration_s}s  |  ${v.n_points} waypoints
Max vel (rad/s): ${(v.max_velocities||[]).map(_=>_.toFixed(3)).join(", ")}`)}catch(v){this.error=v.message}}}>GENERATE</button>
        </div>
        <div id="traj-out" class="term" style="display:block;min-height:0;"></div>
      </div>
    `}_renderSandbox(){var t;return e`
      <div class="card">
        <div class="card-header">📦 ISOLATED CODE SANDBOX</div>

        ${this.sandboxStatus?e`
          <div class="metric-row">
            <span class="metric-label">ISOLATION</span>
            <span class="metric-value ${this.sandboxStatus.docker_available?"green":"amber"}">
              ${(t=this.sandboxStatus.isolation)==null?void 0:t.toUpperCase()}
            </span>
          </div>
          <div class="metric-row">
            <span class="metric-label">SECURITY</span>
            <span class="metric-value blue" style="font-size:10px">${this.sandboxStatus.security}</span>
          </div>
          <div class="metric-row" style="margin-bottom:12px">
            <span class="metric-label">LANGUAGES</span>
            <span class="metric-value">${(this.sandboxStatus.languages||[]).join(" · ")}</span>
          </div>
        `:e`
          <div style="margin-bottom:12px">
            <button class="etis-btn blue" @click=${()=>void this.checkSandboxStatus()}>CHECK STATUS</button>
          </div>
        `}

        <div class="field-row">
          <div class="field">
            <label>LANGUAGE</label>
            <select .value=${this.sandboxLang} @change=${s=>this.sandboxLang=s.target.value}>
              <option value="python">Python 3</option>
              <option value="bash">Bash</option>
              <option value="node">Node.js</option>
            </select>
          </div>
        </div>

        <div style="margin-bottom:10px">
          <label>CODE</label>
          <textarea .value=${this.sandboxCode}
                    @input=${s=>this.sandboxCode=s.target.value}
                    style="width:100%;min-height:160px;margin-top:4px;box-sizing:border-box;"></textarea>
        </div>

        <div class="field-row">
          <button class="etis-btn"
                  ?disabled=${this.sandboxRunning}
                  @click=${()=>void this.runSandbox()}>
            ${this.sandboxRunning?e`<span class="spin"></span>EXECUTING...`:"▶ EXECUTE"}
          </button>
          <button class="etis-btn" style="margin-left:auto"
                  @click=${()=>this.sandboxCode=""}>CLEAR</button>
        </div>

        ${this.sandboxResult?e`
          <div class="term">
<span class="dim">[SANDBOX] exit=${this.sandboxResult.exit_code}  time=${this.sandboxResult.execution_time_ms.toFixed(0)}ms  runtime=${this.sandboxResult.runtime}</span>
<span class="dim">─────────── stdout ───────────</span>
<span class="${this.sandboxResult.exit_code===0?"ok":"err"}">${this.sandboxResult.stdout||"(no output)"}</span>
${this.sandboxResult.stderr?e`<span class="dim">─────────── stderr ───────────</span>
<span class="err">${this.sandboxResult.stderr}</span>`:r}
${this.sandboxResult.timed_out?e`<span class="err">⚠ TIMED OUT</span>`:r}
          </div>
        `:r}
      </div>
    `}_renderIntel(){return e`
      <div class="card">
        <div class="card-header">📰 LIVE THREAT INTELLIGENCE FEED</div>
        <div class="field-row">
          <button class="etis-btn" ?disabled=${this.intelLoading} @click=${()=>void this.loadIntel()}>
            ${this.intelLoading?e`<span class="spin"></span>FETCHING...`:"REFRESH FEED"}
          </button>
          <span style="font-size:10px;color:var(--ds-text-soft);margin-left:auto">${this.intelItems.length} items loaded</span>
        </div>
        ${this.intelItems.map(t=>{var s;return e`
          <div class="intel-item ${t.is_kev?"kev":(s=t.severity)==null?void 0:s.toLowerCase()}"
               @click=${()=>window.open(t.url,"_blank")}>
            <div class="intel-item-title">${t.title}</div>
            <div class="intel-item-meta">
              <span class="source">[${t.source}]</span>
              <span>${t.published}</span>
              ${this._sev(t.severity)}
              ${t.cvss_score?e`<span>CVSS ${t.cvss_score.toFixed(1)}</span>`:r}
              ${t.is_kev?e`<span class="kev">🔴 KEV</span>`:r}
            </div>
            ${t.summary?e`<div style="font-size:10px;color:var(--ds-text-soft);margin-top:5px">${t.summary.slice(0,150)}…</div>`:r}
            ${(t.tags||[]).length?e`
              <div class="tag-row">${t.tags.slice(0,6).map(i=>e`<span class="tag">${i}</span>`)}</div>
            `:r}
          </div>
        `})}
        ${!this.intelItems.length&&!this.intelLoading?e`
          <div class="term"><span class="dim">No intel loaded — click REFRESH FEED.</span></div>
        `:r}
      </div>
    `}render(){const t=[{id:"overview",label:"OVERVIEW",icon:"◉"},{id:"cyber",label:"CYBER",icon:"🛡"},{id:"rf",label:"RF / PROTO",icon:"📡"},{id:"physics",label:"PHYSICS",icon:"⚛"},{id:"robotics",label:"ROBOTICS",icon:"🤖"},{id:"sandbox",label:"SANDBOX",icon:"📦"},{id:"intel",label:"INTEL",icon:"📰"}];return e`
      <!-- Header -->
      <div class="etis-header">
        <div class="etis-logo">ETIS</div>
        <div class="etis-subtitle">EXPERT TECHNICAL INTELLIGENCE SYSTEM</div>
        <div class="etis-status">
          ${Object.entries(this.domains).map(([,s])=>e`
            <div class="domain-dot ${s.available?"ok":"err"}"
                 title="${s.available?"operational":s.error||"unavailable"}"></div>
          `)}
          <button class="etis-btn" style="padding:3px 10px;font-size:9px"
                  @click=${()=>void this.loadStatus()}>↻</button>
        </div>
      </div>

      <!-- Tab bar -->
      <div class="etis-nav">
        ${t.map(s=>e`
          <button class="tab ${this.activePanel===s.id?"active":""}"
                  @click=${()=>this.activePanel=s.id}>
            <span class="tab-icon">${s.icon}</span>${s.label}
          </button>
        `)}
      </div>

      <!-- Error banner -->
      ${this.error?e`
        <div class="err-banner" style="margin:8px 20px 0">
          ⚠ ${this.error}
          <button @click=${()=>this.error=""}>✕</button>
        </div>
      `:r}

      <!-- Panel body -->
      <div class="etis-body">
        ${this.activePanel==="overview"?this._renderOverview():r}
        ${this.activePanel==="cyber"?this._renderCyber():r}
        ${this.activePanel==="rf"?this._renderRF():r}
        ${this.activePanel==="physics"?this._renderPhysics():r}
        ${this.activePanel==="robotics"?this._renderRobotics():r}
        ${this.activePanel==="sandbox"?this._renderSandbox():r}
        ${this.activePanel==="intel"?this._renderIntel():r}
      </div>
    `}};o.styles=P`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
      font-family: var(--ds-font-mono, 'JetBrains Mono', 'Fira Code', monospace);
      background: var(--ds-bg, var(--ds-bg));
      color: var(--ds-text, var(--ds-text));
    }

    /* ── Top bar ── */
    .etis-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 20px;
      border-bottom: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-success) calc(0.03 * 100%), transparent);
      flex-shrink: 0;
    }
    .etis-logo {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 4px;
      color: var(--ds-success);
      text-shadow: 0 0 12px color-mix(in srgb, var(--ds-success) calc(0.6 * 100%), transparent);
    }
    .etis-subtitle {
      font-size: 10px;
      color: var(--ds-text-muted);
      letter-spacing: 1px;
    }
    .etis-status {
      margin-left: auto;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .domain-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--ds-text-muted);
      transition: all 0.3s;
    }
    .domain-dot.ok { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .domain-dot.err { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }

    /* ── Nav tabs ── */
    .etis-nav {
      display: flex;
      gap: 2px;
      padding: 8px 20px 0;
      border-bottom: 1px solid color-mix(in srgb, var(--ds-success) calc(0.1 * 100%), transparent);
      flex-shrink: 0;
      overflow-x: auto;
    }
    .tab {
      padding: 6px 14px;
      font-size: 10px;
      font-family: inherit;
      letter-spacing: 1.5px;
      cursor: pointer;
      border: none;
      background: transparent;
      color: var(--ds-text-soft);
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .tab:hover { color: var(--ds-info); }
    .tab.active {
      color: var(--ds-success);
      border-bottom-color: var(--ds-success);
      text-shadow: 0 0 8px color-mix(in srgb, var(--ds-success) calc(0.5 * 100%), transparent);
    }
    .tab .tab-icon { margin-right: 5px; }

    /* ── Content area ── */
    .etis-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    /* ── Error banner ── */
    .err-banner {
      background: color-mix(in srgb, var(--ds-danger) calc(0.1 * 100%), transparent);
      border: 1px solid color-mix(in srgb, var(--ds-danger) calc(0.4 * 100%), transparent);
      border-radius: 4px;
      padding: 8px 12px;
      font-size: 11px;
      color: var(--ds-danger);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .err-banner button {
      background: none; border: none; cursor: pointer; color: var(--ds-danger); font-size: 14px;
    }

    /* ── Cards / panels ── */
    .card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
      border-radius: 6px;
      padding: 14px 16px;
      transition: border-color 0.2s;
    }
    .card:hover { border-color: color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent); }
    .card-header {
      font-size: 10px;
      color: var(--ds-success);
      letter-spacing: 2px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .card-header::after {
      content: '';
      flex: 1;
      height: 1px;
      background: color-mix(in srgb, var(--ds-success) calc(0.1 * 100%), transparent);
    }

    /* ── Domain grid ── */
    .domain-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 10px;
    }
    .domain-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .domain-card:hover {
      border-color: color-mix(in srgb, var(--ds-info) calc(0.4 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-info) calc(0.04 * 100%), transparent);
    }
    .domain-card.active-domain {
      border-color: color-mix(in srgb, var(--ds-success) calc(0.5 * 100%), transparent);
      background: color-mix(in srgb, var(--ds-success) calc(0.05 * 100%), transparent);
    }
    .domain-card.unavail {
      opacity: 0.45;
    }
    .dc-name {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: var(--ds-info);
      margin-bottom: 6px;
    }
    .dc-name .dc-icon { margin-right: 6px; }
    .dc-status {
      font-size: 10px;
      color: var(--ds-success);
    }
    .dc-status.err { color: var(--ds-danger); }
    .dc-caps {
      margin-top: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .dc-cap {
      font-size: 9px;
      padding: 1px 6px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 3px;
      color: var(--ds-text-soft);
      letter-spacing: 0.5px;
    }

    /* ── Terminal output ── */
    .term {
      background: var(--ds-surface-1);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 11px;
      line-height: 1.7;
      max-height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .term .ok { color: var(--ds-success); }
    .term .err { color: var(--ds-danger); }
    .term .warn { color: var(--ds-warning); }
    .term .dim { color: var(--ds-text-muted); }
    .term .hi { color: var(--ds-info); }
    .term .kev { color: var(--ds-danger); font-weight: 700; background: color-mix(in srgb, var(--ds-danger) calc(0.1 * 100%), transparent); padding: 1px 4px; border-radius: 2px; }

    /* ── Form inputs ── */
    .field-row {
      display: flex;
      gap: 8px;
      align-items: flex-end;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      min-width: 140px;
    }
    label {
      font-size: 9px;
      letter-spacing: 1.5px;
      color: var(--ds-text-soft);
    }
    input, select, textarea {
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.15 * 100%), transparent);
      border-radius: 4px;
      color: var(--ds-text);
      font-family: inherit;
      font-size: 11px;
      padding: 6px 10px;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus {
      border-color: color-mix(in srgb, var(--ds-success) calc(0.45 * 100%), transparent);
      box-shadow: 0 0 0 2px color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
    }
    textarea {
      resize: vertical;
      min-height: 120px;
      line-height: 1.6;
    }
    select option { background: var(--ds-bg); }

    /* ── ETIS action buttons ── */
    .etis-btn {
      background: color-mix(in srgb, var(--ds-success) calc(0.08 * 100%), transparent);
      border: 1px solid color-mix(in srgb, var(--ds-success) calc(0.3 * 100%), transparent);
      border-radius: 4px;
      color: var(--ds-success);
      font-family: inherit;
      font-size: 10px;
      letter-spacing: 1.5px;
      padding: 7px 16px;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .etis-btn:hover {
      background: color-mix(in srgb, var(--ds-success) calc(0.18 * 100%), transparent);
      box-shadow: 0 0 12px color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent);
    }
    .etis-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .etis-btn.danger {
      background: color-mix(in srgb, var(--ds-danger) calc(0.08 * 100%), transparent);
      border-color: color-mix(in srgb, var(--ds-danger) calc(0.3 * 100%), transparent);
      color: var(--ds-danger);
    }
    .etis-btn.blue {
      background: color-mix(in srgb, var(--ds-info) calc(0.08 * 100%), transparent);
      border-color: color-mix(in srgb, var(--ds-info) calc(0.3 * 100%), transparent);
      color: var(--ds-info);
    }

    /* ── Severity badges ── */
    .sev {
      display: inline-block;
      padding: 1px 7px;
      border-radius: 3px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1px;
    }
    .sev-CRITICAL { background: rgba(255,0,80,0.2); color: #ff0050; border: 1px solid rgba(255,0,80,0.4); }
    .sev-HIGH     { background: rgba(255,80,0,0.2); color: #ff5000; border: 1px solid rgba(255,80,0,0.4); }
    .sev-MEDIUM   { background: rgba(255,180,0,0.15); color: #ffb400; border: 1px solid rgba(255,180,0,0.3); }
    .sev-LOW      { background: rgba(0,200,80,0.1); color: #00c850; border: 1px solid rgba(0,200,80,0.2); }
    .sev-INFO     { background: rgba(0,180,255,0.1); color: #00b4ff; border: 1px solid rgba(0,180,255,0.2); }

    /* ── Intel feed ── */
    .intel-item {
      padding: 10px 12px;
      border: 1px solid rgba(255,255,255,0.05);
      border-left: 3px solid color-mix(in srgb, var(--ds-info) calc(0.4 * 100%), transparent);
      border-radius: 4px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .intel-item:hover { background: rgba(255,255,255,0.03); }
    .intel-item.kev { border-left-color: var(--ds-danger); background: color-mix(in srgb, var(--ds-danger) calc(0.04 * 100%), transparent); }
    .intel-item.critical { border-left-color: #ff0050; }
    .intel-item.high { border-left-color: #ff5000; }
    .intel-item-title { font-size: 11px; color: var(--ds-text); margin-bottom: 4px; line-height: 1.4; }
    .intel-item-meta { font-size: 9px; color: var(--ds-text-soft); display: flex; gap: 10px; flex-wrap: wrap; }
    .intel-item-meta .source { color: var(--ds-info); }

    /* ── Metric row ── */
    .metric-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 5px 0;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      font-size: 11px;
    }
    .metric-row:last-child { border-bottom: none; }
    .metric-label { color: var(--ds-text-soft); }
    .metric-value { color: var(--ds-text); font-family: inherit; }
    .metric-value.green { color: var(--ds-success); }
    .metric-value.red { color: var(--ds-danger); }
    .metric-value.blue { color: var(--ds-info); }
    .metric-value.amber { color: var(--ds-warning); }

    /* ── Tags ── */
    .tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
    .tag {
      font-size: 9px;
      padding: 1px 7px;
      border: 1px solid color-mix(in srgb, var(--ds-info) calc(0.2 * 100%), transparent);
      border-radius: 3px;
      color: var(--ds-info);
      letter-spacing: 0.5px;
    }

    /* ── 2-col layout ── */
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    @media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

    /* ── Spinner ── */
    .spin {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 1.5px solid color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent);
      border-top-color: var(--ds-success);
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      vertical-align: middle;
      margin-right: 6px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--ds-success) calc(0.2 * 100%), transparent); border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: color-mix(in srgb, var(--ds-success) calc(0.4 * 100%), transparent); }
  `;l([n()],o.prototype,"activePanel",2);l([n()],o.prototype,"domains",2);l([n()],o.prototype,"loading",2);l([n()],o.prototype,"error",2);l([n()],o.prototype,"intelItems",2);l([n()],o.prototype,"intelLoading",2);l([n()],o.prototype,"cveId",2);l([n()],o.prototype,"cveResult",2);l([n()],o.prototype,"cveSearchKeyword",2);l([n()],o.prototype,"cveSearchResults",2);l([n()],o.prototype,"rfFreq",2);l([n()],o.prototype,"rfBw",2);l([n()],o.prototype,"rfResult",2);l([n()],o.prototype,"wifiNetworks",2);l([n()],o.prototype,"bleDevices",2);l([n()],o.prototype,"physExpr",2);l([n()],o.prototype,"physVars",2);l([n()],o.prototype,"physResult",2);l([n()],o.prototype,"physSim",2);l([n()],o.prototype,"physSimResult",2);l([n()],o.prototype,"robotModel",2);l([n()],o.prototype,"robotAngles",2);l([n()],o.prototype,"robotFkResult",2);l([n()],o.prototype,"robotTarget",2);l([n()],o.prototype,"robotIkResult",2);l([n()],o.prototype,"sandboxCode",2);l([n()],o.prototype,"sandboxLang",2);l([n()],o.prototype,"sandboxResult",2);l([n()],o.prototype,"sandboxRunning",2);l([n()],o.prototype,"sandboxStatus",2);l([n()],o.prototype,"hexSamples",2);l([n()],o.prototype,"protoResult",2);o=l([N("etis-hud")],o);export{o as ETISHud};
//# sourceMappingURL=etis-hud-FlWHLQuT.js.map
