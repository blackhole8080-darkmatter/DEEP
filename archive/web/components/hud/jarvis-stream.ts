// <jarvis-stream> — Bottom-left: scrolling data / log feed with decode animation
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface StreamItem { id: number; ts: string; tag: string; text: string; color: string; }

const TAGS = ["SYS", "NET", "AI", "SEC", "MEM", "OPS"];
const TAG_COLORS: Record<string, string> = {
  SYS:"#00e5ff", NET:"#00ffd1", AI:"#bf40ff", SEC:"#ffb300", MEM:"#00e5ff", OPS:"#00e5ff"
};
const MESSAGES = [
  "Neural mesh synchronised — latency 4ms",
  "Agent PLANNER dispatched sub-task #47",
  "Vector embedding complete: 1.2k documents",
  "WebSocket heartbeat OK",
  "LLM context window: 82% utilised",
  "Proximity scan: no anomalies",
  "Predictive model updated — confidence 94%",
  "Memory consolidation pass complete",
  "Agent EXEC acquired tool: web_search",
  "TTS buffer flushed — 340ms render",
  "Security baseline recalculated",
  "Knowledge graph: 8,241 nodes active",
  "Network topology refreshed — 10 peers",
  "GPU inference queue: 0 pending",
];

let _id = 0;
function makeItem(): StreamItem {
  const tag = TAGS[Math.floor(Math.random() * TAGS.length)];
  const d = new Date();
  return {
    id: _id++,
    ts: d.toLocaleTimeString("en-US", { hour12: false }),
    tag,
    text: MESSAGES[Math.floor(Math.random() * MESSAGES.length)],
    color: TAG_COLORS[tag],
  };
}

@customElement("jarvis-stream")
export class JarvisStream extends LitElement {
  @state() private _items: StreamItem[] = [];
  private _timer = 0;

  static styles = css`
    :host { display:flex; flex-direction:column; height:100%; --j-cyan:#00e5ff; }
    .st-header {
      display:flex; align-items:center; justify-content:space-between;
      padding:6px 12px 5px; border-bottom:1px solid rgba(0,229,255,0.1); flex-shrink:0;
    }
    .st-title { font-family:"Rajdhani",monospace; font-size:0.6rem; font-weight:700; letter-spacing:0.28em; text-transform:uppercase; color:rgba(0,229,255,0.45); }
    .st-live { font-family:monospace; font-size:0.52rem; color:var(--j-cyan); text-shadow:0 0 6px var(--j-cyan); animation:st-blink 1.2s step-end infinite; }
    @keyframes st-blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

    .feed { flex:1; overflow:hidden; display:flex; flex-direction:column-reverse; padding:4px 0; }
    .item {
      display:flex; align-items:baseline; gap:7px;
      padding:2px 12px;
      animation:st-enter 0.25s ease;
      border-left:2px solid transparent;
      transition:border-color 0.2s;
    }
    .item:first-child { border-left-color:var(--j-cyan); }
    @keyframes st-enter { from{opacity:0;transform:translateX(-6px)} to{opacity:1;transform:none} }
    .ts { font-family:monospace; font-size:0.5rem; color:rgba(0,229,255,0.28); flex-shrink:0; }
    .tag {
      font-family:"Rajdhani",monospace; font-size:0.56rem; font-weight:700;
      letter-spacing:0.12em; flex-shrink:0; min-width:28px;
    }
    .text { font-family:monospace; font-size:0.55rem; color:rgba(200,235,245,0.65); line-height:1.4; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    // Seed initial items
    this._items = Array.from({ length: 6 }, makeItem).reverse();
    this._timer = window.setInterval(() => {
      this._items = [makeItem(), ...this._items].slice(0, 20);
    }, 2200);
  }
  disconnectedCallback(): void { super.disconnectedCallback(); clearInterval(this._timer); }

  render() {
    return html`
      <div class="st-header">
        <span class="st-title">◈ DATA FEED</span>
        <span class="st-live">▶ LIVE</span>
      </div>
      <div class="feed">
        ${this._items.map(i => html`
          <div class="item">
            <span class="ts">${i.ts}</span>
            <span class="tag" style="color:${i.color};text-shadow:0 0 6px ${i.color}">[${i.tag}]</span>
            <span class="text">${i.text}</span>
          </div>
        `)}
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { "jarvis-stream": JarvisStream; } }
