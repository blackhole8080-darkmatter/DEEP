// <voice-status-orb> — Floating visual indicator for DEEP Voice Assistant
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

interface VoiceStatePayload {
  state: "IDLE" | "WAKE" | "LISTENING" | "THINKING" | "ACTING" | "SPEAKING" | "COOLDOWN" | "CONFIRMING" | "ALERT";
  transcript?: string;
  session_id?: string;
}

@customElement("voice-status-orb")
export class VoiceStatusOrb extends LitElement {
  @state() private voiceState: VoiceStatePayload["state"] = "IDLE";
  @state() private transcript = "";
  @state() private muted = false;
  @state() private connected = false;
  @state() private ws: WebSocket | null = null;

  static styles = css`
    :host { display: block; position: fixed; bottom: 20px; right: 20px; z-index: 9999; }
    .wrap { position: relative; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }

    /* ── Transcript bubble ── */
    .transcript-bubble {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-accent);
      border-radius: var(--ds-radius-md);
      padding: var(--ds-space-2) var(--ds-space-3);
      font-size: var(--ds-text-sm);
      color: var(--ds-text-soft);
      max-width: 260px;
      word-break: break-word;
      opacity: 0; transform: translateY(8px);
      transition: opacity 0.3s ease, transform 0.3s ease;
      pointer-events: none;
      box-shadow: var(--ds-elev-2);
    }
    .wrap:hover .transcript-bubble,
    .transcript-bubble.show { opacity: 1; transform: translateY(0); }
    .transcript-bubble .state-label {
      font-size: var(--ds-text-xs); color: var(--ds-accent);
      text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      font-weight: 600; margin-bottom: 2px;
    }

    /* ── Holographic orb ── */
    .orb {
      width: 56px; height: 56px; border-radius: 50%;
      position: relative; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      background: radial-gradient(circle at 30% 30%, rgba(var(--ds-periwinkle-rgb),0.15), transparent 60%);
    }
    .orb::before {
      content: ""; position: absolute; inset: -2px; border-radius: 50%;
      background: conic-gradient(from 0deg, transparent, var(--ds-accent), var(--ds-iris, #9a8cff), transparent);
      opacity: 0.25;
      animation: spin-slow 4s linear infinite;
      -webkit-mask: radial-gradient(circle, transparent 62%, black 64%);
      mask: radial-gradient(circle, transparent 62%, black 64%);
    }
    .orb::after {
      content: ""; position: absolute; inset: -6px; border-radius: 50%;
      border: 1px solid rgba(var(--ds-periwinkle-rgb), 0.15);
      transition: all 0.4s ease;
    }

    .orb-inner {
      width: 22px; height: 22px; border-radius: 50%;
      background: var(--ds-accent);
      transition: all 0.4s ease;
      box-shadow: 0 0 12px var(--ds-accent);
    }

    /* IDLE — dim breathing pulse */
    .state-idle .orb-inner { opacity: 0.3; }
    .state-idle .orb { animation: breathe 3s ease-in-out infinite; }
    /* WAKE — quick bright pulse */
    .state-wake .orb-inner { opacity: 1; transform: scale(1.3); box-shadow: 0 0 24px var(--ds-accent); }
    .state-wake .orb { animation: wakePulse 0.5s ease-out; }
    @keyframes wakePulse {
      0% { transform: scale(0.8); opacity: 0.5; }
      50% { transform: scale(1.2); opacity: 1; }
      100% { transform: scale(1); opacity: 1; }
    }
    /* LISTENING — expanding rings */
    .state-listening .orb-inner { opacity: 1; width: 26px; height: 26px; background: var(--ds-success); box-shadow: 0 0 24px var(--ds-success); }
    .state-listening .orb { animation: listeningWave 1.2s ease-in-out infinite; }
    @keyframes listeningWave {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.15); }
    }
    .state-listening .orb::after {
      animation: ring-expand 1.5s ease-out infinite;
      border-color: var(--ds-success);
    }
    /* THINKING — chaotic spin + color cycle */
    .state-thinking .orb-inner {
      opacity: 1; animation: thinkCycle 0.8s linear infinite;
      background: linear-gradient(90deg, var(--ds-accent), var(--ds-success), var(--ds-warning), var(--ds-accent));
      background-size: 300% 100%;
      box-shadow: 0 0 20px var(--ds-accent);
    }
    @keyframes thinkCycle {
      0% { background-position: 0% 50%; }
      100% { background-position: 300% 50%; }
    }
    .state-thinking .orb { animation: spin-slow 2s linear infinite; }
    .state-thinking .orb::before { opacity: 0.5; animation-duration: 1s; }
    /* ACTING — strobes */
    .state-acting .orb-inner { opacity: 1; animation: actStrobe 0.3s ease-in-out infinite alternate; box-shadow: 0 0 20px var(--ds-accent); }
    @keyframes actStrobe {
      0% { opacity: 0.6; transform: scale(1); }
      100% { opacity: 1; transform: scale(1.2); }
    }
    /* SPEAKING — waveform bars */
    .state-speaking .orb-inner { opacity: 0; width: 0; height: 0; }
    .state-speaking .waveform {
      display: flex; align-items: flex-end; gap: 2px;
      height: 20px;
    }
    .waveform .bar {
      width: 3px; border-radius: 2px;
      background: var(--ds-accent);
      animation: bar-bounce 0.5s ease-in-out infinite alternate;
      box-shadow: 0 0 4px var(--ds-accent);
    }
    .waveform .bar:nth-child(2) { animation-delay: 0.08s; height: 14px; }
    .waveform .bar:nth-child(3) { animation-delay: 0.16s; height: 10px; }
    .waveform .bar:nth-child(4) { animation-delay: 0.12s; height: 16px; }
    .waveform .bar:nth-child(5) { animation-delay: 0.04s; height: 12px; }
    .state-speaking .orb::after { border-color: var(--ds-accent); animation: ring-expand 1.2s ease-out infinite; }
    /* COOLDOWN — gentle fade */
    .state-cooldown .orb-inner { opacity: 0.5; transform: scale(0.9); }
    /* CONFIRMING — amber slow pulse */
    .state-confirming .orb-inner { background: var(--ds-warning); opacity: 1; box-shadow: 0 0 20px var(--ds-warning); }
    .state-confirming .orb { animation: confirmPulse 1.5s ease-in-out infinite; }
    @keyframes confirmPulse {
      0%, 100% { transform: scale(1); opacity: 0.8; }
      50% { transform: scale(1.12); opacity: 1; }
    }
    /* ALERT — red flashes */
    .state-alert .orb-inner { background: var(--ds-danger); opacity: 1; box-shadow: 0 0 24px var(--ds-danger); }
    .state-alert .orb { animation: alertFlash 0.4s ease-in-out 3; }
    @keyframes alertFlash {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.3; transform: scale(1.3); }
    }
    /* Muted overlay */
    .muted .orb-inner { background: var(--ds-text-faint) !important; opacity: 0.3 !important; box-shadow: none !important; }
    .muted .orb { animation: none !important; }
    .muted .waveform { display: none !important; }

    /* Tooltip */
    .tooltip {
      position: absolute; bottom: 68px; right: 0;
      background: var(--ds-surface-1); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md); padding: var(--ds-space-3);
      min-width: 220px; font-size: var(--ds-text-sm);
      color: var(--ds-text); box-shadow: var(--ds-elev-3);
      opacity: 0; transform: translateY(8px); pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    .orb:hover .tooltip, .tooltip.show {
      opacity: 1; transform: translateY(0); pointer-events: auto;
    }
    .tooltip .state-label { font-size: var(--ds-text-xs); color: var(--ds-accent); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); font-weight: 600; }
    .tooltip .transcript { color: var(--ds-text-muted); margin-top: var(--ds-space-1); font-style: italic; max-width: 260px; word-break: break-word; }
    .tooltip .actions { display: flex; gap: var(--ds-space-2); margin-top: var(--ds-space-2); }
    .tooltip .actions button {
      background: var(--ds-surface-2); border: 1px solid var(--ds-border);
      color: var(--ds-text); padding: 2px 10px; border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-xs); cursor: pointer;
    }
    .tooltip .actions button:hover { background: var(--ds-surface-3); }
    .connection-dot { position: absolute; top: 2px; right: 2px; width: 8px; height: 8px; border-radius: 50%; }
    .connection-dot.connected { background: var(--ds-success); box-shadow: 0 0 4px var(--ds-success); }
    .connection-dot.disconnected { background: var(--ds-danger); }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this._connectWs();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.ws) { this.ws.close(); this.ws = null; }
  }

  private _connectWs(): void {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws/voice`;
    try {
      this.ws = new WebSocket(url);
      this.ws.onopen = () => { this.connected = true; };
      this.ws.onclose = () => { this.connected = false; setTimeout(() => this._connectWs(), 3000); };
      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "state" && msg.state) {
            this.voiceState = msg.state;
            this.transcript = msg.transcript || "";
          }
        } catch { /* noop */ }
      };
    } catch { /* noop */ }
  }

  render() {
    const stateClass = `state-${this.voiceState.toLowerCase()}`;
    const mutedClass = this.muted ? "muted" : "";
    const connClass = this.connected ? "connected" : "disconnected";

    const stateLabels: Record<string, string> = {
      IDLE: "DEEP is listening…", WAKE: "Wake detected!", LISTENING: "Listening…",
      THINKING: "Thinking…", ACTING: "Taking action…", SPEAKING: "Speaking…",
      COOLDOWN: "Cooling down…", CONFIRMING: "Confirm?", ALERT: "Alert!",
    };

    const isSpeaking = this.voiceState === "SPEAKING";
    return html`
      <div class="wrap ${stateClass} ${mutedClass}">
        ${this.transcript ? html`
          <div class="transcript-bubble show">
            <div class="state-label">${stateLabels[this.voiceState] || this.voiceState}</div>
            <div>${this.transcript}</div>
          </div>
        ` : ""}
        <div class="orb" @click=${() => { this.muted = !this.muted; }}>
          <div class="connection-dot ${connClass}"></div>
          <div class="orb-inner"></div>
          ${isSpeaking ? html`
            <div class="waveform">
              <div class="bar" style="height:8px"></div>
              <div class="bar" style="height:14px"></div>
              <div class="bar" style="height:10px"></div>
              <div class="bar" style="height:16px"></div>
              <div class="bar" style="height:12px"></div>
            </div>
          ` : ""}
          <div class="tooltip">
            <div class="state-label">${stateLabels[this.voiceState] || this.voiceState}</div>
            ${this.transcript ? html`<div class="transcript">"${this.transcript}"</div>` : ""}
            <div class="actions">
              <button @click=${(e: Event) => { e.stopPropagation(); this._sendCommand("stop"); }}>Stop</button>
              <button @click=${(e: Event) => { e.stopPropagation(); this.muted = !this.muted; }}>${this.muted ? "Unmute" : "Mute"}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private _sendCommand(cmd: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "command", command: cmd }));
    }
  }
}
