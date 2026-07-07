// <deep-boot> — DEEP startup sequence overlay
// Shows for ~4.0s on first visit. Advanced hardcore cyber terminal boot.
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const ASCII_LOGO = `
  ____  _____ _____ ____  
 |  _ \\| ____| ____|  _ \\ 
 | | | |  _| |  _| | |_) |
 | |_| | |___| |___|  __/ 
 |____/|_____|_____|_|    
`;

const HACK_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>/\\|{}[]~";

const BOOT_LOGS = [
  { text: "INIT: Booting DEEP Neural Kernel v9.4.2...", status: "ok" },
  { text: "Mounting virtual filesystems...", status: "ok" },
  { text: "Loading cryptographic modules...", status: "ok" },
  { text: "Bypassing standard protocol handlers...", status: "warn", override: "[WARNING: Unauthorized]", glitch: true },
  { text: "Injecting payload into memory space...", status: "ok" },
  { text: "Establishing secure P2P uplink...", status: "ok" },
  { text: "Scanning local network topology...", status: "active", override: "[ACTIVE]" },
  { text: "Initializing exploit payloads...", status: "ok", override: "[READY]" },
  { text: "Warming up predictive threat analysis...", status: "ok" },
  { text: "Loading world model...", status: "ok" },
  { text: "SYSTEM ONLINE. Welcome, Operator.", status: "ok" }
];

@customElement("deep-boot")
export class DeepBoot extends LitElement {
  @state() private visible = true;
  @state() private visibleLogs: { prefix: string, text: string, scrambledText: string, statusText: string, statusClass: string, createdAt: number }[] = [];
  @state() private hexDumps: string[] = [];
  @state() private progress = 0;
  @state() private isGlitching = false;
  
  private raf = 0;
  private start = performance.now();
  private hexTimer = 0;

  static styles = css`
    :host {
      position: fixed; inset: 0; z-index: 100;
      background: #010205;
      color: var(--ds-neon-green, #00ff41);
      font-family: var(--ds-font-mono, monospace);
      transition: opacity 0.5s ease, visibility 0.5s;
      overflow: hidden;
      display: flex;
    }
    :host(.fade) { opacity: 0; visibility: hidden; pointer-events: none; }
    
    .crt {
      position: absolute; inset: 0; pointer-events: none; z-index: 10;
      background: linear-gradient(rgba(0, 255, 65, 0.05) 1px, transparent 1px);
      background-size: 100% 3px;
    }
    .vignette {
      position: absolute; inset: 0; pointer-events: none; z-index: 11;
      background: radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.8) 100%);
    }
    .scanline {
      position: absolute; top: 0; left: 0; right: 0; height: 100px;
      background: linear-gradient(to bottom, transparent, rgba(0, 255, 255, 0.15), transparent);
      animation: scan 4s linear infinite; pointer-events: none; z-index: 12;
    }
    @keyframes scan {
      0% { transform: translateY(-100px); }
      100% { transform: translateY(100vh); }
    }

    /* Chromatic Aberration & Glitch */
    .glitch-active {
      animation: crt-glitch 0.15s infinite;
    }
    @keyframes crt-glitch {
      0% { transform: translate(0); filter: drop-shadow(0 0 0 transparent); }
      20% { transform: translate(-2px, 1px); filter: drop-shadow(2px 0 0 red) drop-shadow(-2px 0 0 blue); }
      40% { transform: translate(1px, -1px); filter: drop-shadow(-2px 0 0 red) drop-shadow(2px 0 0 blue); }
      60% { transform: translate(2px, 2px); filter: drop-shadow(2px 0 0 red) drop-shadow(-2px 0 0 blue); }
      80% { transform: translate(-1px, -2px); filter: drop-shadow(-2px 0 0 red) drop-shadow(2px 0 0 blue); }
      100% { transform: translate(0); filter: drop-shadow(0 0 0 transparent); }
    }

    .layout {
      position: relative; z-index: 2;
      display: flex; width: 100%; height: 100%;
      padding: 3rem; box-sizing: border-box;
      gap: 3rem;
    }

    .side-panel {
      flex: 0 0 250px;
      display: flex; flex-direction: column;
      font-size: 0.75rem;
      opacity: 0.8;
      text-shadow: 0 0 5px var(--ds-neon-green, #00ff41);
    }
    .side-panel .header {
      border-bottom: 1px solid var(--ds-neon-green, #00ff41);
      margin-bottom: 8px; padding-bottom: 4px;
      font-weight: bold; letter-spacing: 0.1em;
      color: var(--ds-neon-cyan, #00ffff);
    }

    .hw-stat { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .hw-stat .val { color: var(--ds-neon-cyan, #00ffff); }
    .hw-stat.warn .val { color: var(--ds-neon-amber, #ffb000); }

    .hex-dump {
      display: flex; flex-direction: column; gap: 2px;
      font-size: 0.7rem;
      overflow: hidden;
      white-space: pre;
    }

    .main-panel {
      flex: 1; display: flex; flex-direction: column; justify-content: flex-end;
      text-shadow: 0 0 8px rgba(0, 255, 65, 0.6);
    }

    .ascii {
      white-space: pre; font-size: 1.1rem; line-height: 1.1; margin-bottom: 2.5rem;
      color: var(--ds-neon-cyan, #00ffff); opacity: 0.9;
      text-shadow: 0 0 15px rgba(0, 255, 255, 0.8);
      animation: flicker 4s infinite alternate;
    }

    @keyframes flicker {
      0%, 100% { opacity: 0.9; }
      10% { opacity: 0.6; }
      20% { opacity: 1; }
      80% { opacity: 0.9; }
      82% { opacity: 0.3; }
      85% { opacity: 0.9; }
    }

    .log-line { font-size: 0.85rem; line-height: 1.5; margin-bottom: 6px; display: flex; }
    .log-line .prefix { color: var(--ds-neon-cyan, #00ffff); margin-right: 12px; opacity: 0.7; }
    .log-line .text { flex: 1; }
    .log-line .status { margin-left: 12px; font-weight: bold; }
    
    .ok { color: var(--ds-neon-green, #00ff41); }
    .warn { color: var(--ds-neon-amber, #ffb000); text-shadow: 0 0 10px rgba(255, 176, 0, 0.8); }
    .err { color: var(--ds-neon-red, #ff003c); text-shadow: 0 0 10px rgba(255, 0, 60, 0.8); }
    .active { color: var(--ds-neon-cyan, #00ffff); }

    .cursor {
      display: inline-block; width: 10px; height: 1.1em;
      background: var(--ds-neon-green, #00ff41);
      vertical-align: middle; margin-left: 8px;
      animation: blink 1s step-end infinite;
      box-shadow: 0 0 10px var(--ds-neon-green, #00ff41);
    }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

    .progress-wrap {
      margin-top: 2rem;
      font-size: 0.9rem;
      color: var(--ds-neon-cyan, #00ffff);
      display: flex; align-items: center; gap: 12px;
    }
    .progress-bar-text { letter-spacing: 2px; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.hexTimer = window.setInterval(() => this._addHexDump(), 50);
    this._loop();
  }

  private _addHexDump() {
    const addr = "0x" + Math.floor(Math.random() * 0xFFFFFF).toString(16).toUpperCase().padStart(6, "0");
    let hex = "";
    for(let i=0; i<4; i++) hex += Math.floor(Math.random() * 0xFFFF).toString(16).toUpperCase().padStart(4, "0") + " ";
    this.hexDumps = [...this.hexDumps.slice(-40), `${addr}  ${hex}`];
  }

  private _loop = () => {
    const elapsed = performance.now() - this.start;
    this.progress = Math.min(100, (elapsed / 4500) * 100);
    
    const expectedLogs = Math.floor(elapsed / 300);
    
    if (expectedLogs > this.visibleLogs.length && this.visibleLogs.length < BOOT_LOGS.length) {
      const nextLog = BOOT_LOGS[this.visibleLogs.length];
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`;
      
      const pid = Math.floor(Math.random() * 8000 + 1000);
      const mem = "0x" + Math.floor(Math.random() * 0xFFFFFF).toString(16).toUpperCase().padStart(6, "0");
      
      this.visibleLogs = [...this.visibleLogs, {
        prefix: `[${timeStr}] [PID:${pid}] [${mem}]`,
        text: nextLog.text,
        scrambledText: "",
        statusText: nextLog.override || "[OK]",
        statusClass: nextLog.status,
        createdAt: elapsed
      }];

      if ((nextLog as any).glitch) {
        this.isGlitching = true;
        setTimeout(() => this.isGlitching = false, 300);
      }
    }

    this.visibleLogs = this.visibleLogs.map(log => {
      const age = elapsed - log.createdAt;
      const decodeDuration = 250;
      if (age > decodeDuration) return log.scrambledText === log.text ? log : { ...log, scrambledText: log.text };
      
      const progress = age / decodeDuration;
      const resolvedCount = Math.floor(progress * log.text.length);
      
      let scrambled = "";
      for (let i = 0; i < log.text.length; i++) {
        if (log.text[i] === " ") scrambled += " ";
        else if (i < resolvedCount) scrambled += log.text[i];
        else scrambled += HACK_CHARS[Math.floor(Math.random() * HACK_CHARS.length)];
      }
      return { ...log, scrambledText: scrambled };
    });

    if (elapsed > 4500) {
      this.classList.add("fade");
      setTimeout(() => { this.visible = false; }, 500);
      return;
    }
    
    this.raf = requestAnimationFrame(this._loop);
  };

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    clearInterval(this.hexTimer);
  }

  render() {
    if (!this.visible) return html``;
    
    const barWidth = 40;
    const filled = Math.floor((this.progress / 100) * barWidth);
    const barStr = "█".repeat(filled) + "░".repeat(barWidth - filled);

    return html`
      <div class="crt"></div>
      <div class="vignette"></div>
      <div class="scanline"></div>
      
      <div class="layout ${this.isGlitching ? 'glitch-active' : ''}">
        
        <div class="side-panel">
          <div class="header">SYS_TELEMETRY</div>
          <div class="hw-stat"><span>CPU0 [CORE]</span><span class="val">${Math.floor(Math.random()*40 + 20)}%</span></div>
          <div class="hw-stat"><span>CPU1 [CORE]</span><span class="val">${Math.floor(Math.random()*60 + 10)}%</span></div>
          <div class="hw-stat"><span>CPU2 [CORE]</span><span class="val">${Math.floor(Math.random()*90 + 5)}%</span></div>
          <div class="hw-stat"><span>CPU3 [CORE]</span><span class="val">${Math.floor(Math.random()*30 + 10)}%</span></div>
          <br>
          <div class="hw-stat"><span>MEM_ALLOC</span><span class="val">0x0A4F</span></div>
          <div class="hw-stat warn"><span>SEC_BYPASS</span><span class="val">ACTIVE</span></div>
          <div class="hw-stat"><span>NET_UPLINK</span><span class="val">ESTABLISHED</span></div>
          <div class="hw-stat"><span>V_FS_MOUNT</span><span class="val">RO</span></div>
        </div>

        <div class="main-panel">
          <div class="ascii">${ASCII_LOGO}</div>
          <div class="logs">
            ${this.visibleLogs.map(log => html`
              <div class="log-line">
                <span class="prefix">${log.prefix}</span>
                <span class="text">${log.scrambledText}</span>
                <span class="status ${log.statusClass}">${log.statusText}</span>
              </div>
            `)}
            <div class="log-line">
               <span class="cursor"></span>
            </div>
          </div>
          
          <div class="progress-wrap">
            <span>BOOT SEQUENCE:</span>
            <span class="progress-bar-text">[${barStr}]</span>
            <span>${Math.floor(this.progress)}%</span>
          </div>
        </div>

        <div class="side-panel">
          <div class="header">MEM_DUMP // KERNEL</div>
          <div class="hex-dump">
            ${this.hexDumps.map(h => html`<div>${h}</div>`)}
          </div>
        </div>

      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { "deep-boot": DeepBoot; }
}
