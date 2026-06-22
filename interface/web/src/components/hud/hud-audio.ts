// hud-audio.ts — Web Audio API singleton for procedural HUD sound design
// Widget focus pings, alert shepard tones, mode-switch whooshes.
// All gated behind reduced-motion and a user mute toggle.

let _ctx: AudioContext | null = null;
let _muted = false;
let _reducedMotion = false;

function getCtx(): AudioContext | null {
  if (_muted || _reducedMotion) return null;
  if (!_ctx) {
    try {
      _ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    } catch {
      return null;
    }
  }
  if (_ctx.state === "suspended") _ctx.resume();
  return _ctx;
}

export function setHudMute(v: boolean): void {
  _muted = v;
}

export function isHudMuted(): boolean {
  return _muted;
}

export function setReducedMotion(v: boolean): void {
  _reducedMotion = v;
}

/** 1200 Hz 50 ms sine ping, panned to widget screen position (-1..1) */
export function playFocusPing(panX: number): void {
  const ctx = getCtx();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const pan = ctx.createStereoPanner();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(1200, ctx.currentTime);
  pan.pan.setValueAtTime(Math.max(-1, Math.min(1, panX)), ctx.currentTime);
  gain.gain.setValueAtTime(0.08, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
  osc.connect(pan).connect(gain).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.05);
}

/** Descending shepard tone for alert spawn */
export function playAlertTone(): void {
  const ctx = getCtx();
  if (!ctx) return;
  for (let i = 0; i < 3; i++) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(880 * Math.pow(2, i), ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440 * Math.pow(2, i), ctx.currentTime + 1.5);
    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.5);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 1.5);
  }
}

/** 200 ms filtered noise whoosh for mode switch */
export function playWhoosh(): void {
  const ctx = getCtx();
  if (!ctx) return;
  const bufferSize = ctx.sampleRate * 0.2;
  const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
  const noise = ctx.createBufferSource();
  noise.buffer = buffer;
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(2000, ctx.currentTime);
  filter.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.2);
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.06, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
  noise.connect(filter).connect(gain).connect(ctx.destination);
  noise.start();
}
