// <jarvis-systems> — Right panel: system status nodes + active processes
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface SysNode { id: string; label: string; sub: string; status: "online" | "active" | "warn" | "offline"; }
interface Process { name: string; cpu: number; mem: number; }

@customElement("jarvis-systems")
export class JarvisSystems extends LitElement {
  @property({ type: String }) mode = "idle";

  @state() private _nodes: SysNode[] = [
    { id: "llm",    label: "LLM ENGINE",   sub: "qwen3-235b",      status: "online"  },
    { id: "mem",    label: "VECTOR DB",    sub: "qdrant:6333",      status: "active"  },
    { id: "voice",  label: "VOICE I/O",    sub: "piper-tts",        status: "online"  },
    { id: "agents", label: "AGENT SWARM",  sub: "4 agents running", status: "active"  },
    { id: "net",    label: "NETWORK",      sub: "ws://localhost",   status: "online"  },
    { id: "sec",    label: "SECURITY",     sub: "scanning",         status: "warn"    },
  ];

  @state() private _processes: Process[] = [
    { name: "deep-cortex",  cpu: 12, mem: 340 },
    { name: "agent-planner",cpu: 8,  mem: 128 },
    { name: "qdrant",       cpu: 3,  mem: 512 },
    { name: "piper-tts",    cpu: 2,  mem: 96  },
  ];

  private _timer = 0;

  static styles = css`
    :host { display:flex; flex-direction:column; height:100%; --j-cyan:#00e5ff; }
    .s-header {
      display:flex; align-items:center; justify-content:space-between;
      padding:10px 14px 8px; border-bottom:1px solid rgba(0,229,255,0.1); flex-shrink:0;
      position:relative; overflow:hidden;
    }
    .s-header::after {
      content:"";
      position:absolute; bottom:0; left:-60%; width:60%; height:1px;
      background:linear-gradient(90deg,transparent,rgba(0,229,255,0.7),transparent);
      animation:s-scan-ticker 2.6s linear infinite;
    }
    @keyframes s-scan-ticker { from{left:-60%} to{left:160%} }
    .s-title { font-family:"Rajdhani",monospace; font-size:0.65rem; font-weight:700; letter-spacing:0.3em; text-transform:uppercase; color:rgba(0,229,255,0.5); }
    .s-count { font-family:monospace; font-size:0.58rem; letter-spacing:0.1em; color:var(--j-cyan); text-shadow:0 0 8px var(--j-cyan); }

    .nodes { flex:1; display:flex; flex-direction:column; gap:6px; padding:10px 14px; overflow:hidden; }
    .node {
      display:flex; align-items:center; gap:10px;
      padding:6px 10px;
      background:rgba(0,229,255,0.03);
      border:1px solid rgba(0,229,255,0.08);
      border-radius:3px;
      transition:border-color 0.2s, background 0.2s, box-shadow 0.2s;
    }
    .node:hover {
      border-color:rgba(0,229,255,0.3);
      background:rgba(0,229,255,0.06);
      box-shadow:0 0 16px rgba(0,229,255,0.08), inset 0 0 12px rgba(0,229,255,0.04);
    }
    .n-dot {
      width:6px; height:6px; border-radius:50%; flex-shrink:0;
      animation:s-pulse 2s ease-in-out infinite;
    }
    .n-dot.online  { background:#00e5ff; box-shadow:0 0 8px #00e5ff; }
    .n-dot.active  { background:#00ffd1; box-shadow:0 0 8px #00ffd1; animation-duration:0.8s; }
    .n-dot.warn    { background:#ffb300; box-shadow:0 0 8px #ffb300; }
    .n-dot.offline { background:#444; box-shadow:none; animation:none; }
    @keyframes s-pulse { 0%,100%{opacity:1} 50%{opacity:0.35} }

    .n-info { flex:1; min-width:0; }
    .n-label { font-family:"Rajdhani",monospace; font-size:0.68rem; font-weight:700; letter-spacing:0.15em; color:rgba(220,245,255,0.85); }
    .n-sub { font-family:monospace; font-size:0.52rem; letter-spacing:0.06em; color:rgba(0,229,255,0.35); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .n-status { font-family:monospace; font-size:0.52rem; letter-spacing:0.1em; flex-shrink:0; }
    .n-status.online  { color:#00e5ff; }
    .n-status.active  { color:#00ffd1; }
    .n-status.warn    { color:#ffb300; }
    .n-status.offline { color:#444; }

    .procs {
      border-top:1px solid rgba(0,229,255,0.08); flex-shrink:0;
      padding:8px 14px 10px;
    }
    .p-title { font-family:"Rajdhani",monospace; font-size:0.58rem; font-weight:700; letter-spacing:0.25em; color:rgba(0,229,255,0.35); margin-bottom:6px; }
    .proc-row { display:flex; align-items:center; gap:8px; margin-bottom:4px; }
    .p-name { font-family:monospace; font-size:0.56rem; color:rgba(220,245,255,0.6); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .p-bar { width:50px; height:2px; background:rgba(0,229,255,0.08); border-radius:1px; overflow:hidden; }
    .p-fill { height:100%; background:#00e5ff; box-shadow:0 0 4px #00e5ff; border-radius:1px; transition:width 0.6s ease; }
    .p-num { font-family:monospace; font-size:0.52rem; color:rgba(0,229,255,0.5); width:30px; text-align:right; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._timer = window.setInterval(() => {
      this._processes = this._processes.map(p => ({
        ...p, cpu: Math.max(1, Math.min(40, p.cpu + (Math.random() - 0.45) * 4)),
      }));
    }, 1600);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this._timer); }

  render() {
    const online = this._nodes.filter(n => n.status !== "offline").length;
    return html`
      <div class="s-header">
        <span class="s-title">◈ SYSTEMS</span>
        <span class="s-count">${online}/${this._nodes.length} ONLINE</span>
      </div>
      <div class="nodes">
        ${this._nodes.map(n => html`
          <div class="node">
            <span class="n-dot ${n.status}"></span>
            <div class="n-info">
              <div class="n-label">${n.label}</div>
              <div class="n-sub">${n.sub}</div>
            </div>
            <span class="n-status ${n.status}">${n.status.toUpperCase()}</span>
          </div>
        `)}
      </div>
      <div class="procs">
        <div class="p-title">PROCESSES</div>
        ${this._processes.map(p => html`
          <div class="proc-row">
            <span class="p-name">${p.name}</span>
            <div class="p-bar"><div class="p-fill" style="width:${p.cpu * 2.5}%"></div></div>
            <span class="p-num">${Math.round(p.cpu)}%</span>
          </div>
        `)}
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-systems": JarvisSystems; } }
