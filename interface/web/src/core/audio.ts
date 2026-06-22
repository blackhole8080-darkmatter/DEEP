// DEEP AudioAnalyser — frequency-band audio analysis for the neural sphere.
// Connects to mic (MediaStream) or TTS (HTMLAudioElement) and produces per-frame
// bass/mid/high/rms levels that drive sphere displacement, rotation, and glow.
//
// Usage:
//   const analyser = new AudioAnalyser();
//   await analyser.connectMic();       // requires user gesture + permission
//   analyser.connectElement(audioEl);  // for TTS playback
//   // In rAF loop:
//   analyser.update();
//   const { bass, mid, high, rms } = analyser.levels;

export interface AudioLevels {
  bass: number;    // 0..1 — drives displacement amplitude
  mid: number;     // 0..1 — drives particle speed + rotation
  high: number;    // 0..1 — drives rim intensity + hot-spot threshold
  rms: number;     // 0..1 — overall level (fallback)
}

export class AudioAnalyser {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private data = new Uint8Array(0) as Uint8Array<ArrayBuffer>;
  private smoothBass = 0;
  private smoothMid = 0;
  private smoothHigh = 0;
  private smoothRms = 0;

  levels: AudioLevels = { bass: 0, mid: 0, high: 0, rms: 0 };
  connected = false;

  private ensureCtx(): AudioContext {
    if (!this.ctx) {
      this.ctx = new AudioContext();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.7;
      this.data = new Uint8Array(this.analyser.frequencyBinCount);
    }
    return this.ctx;
  }

  /** Connect to the user's microphone. Requires user gesture. Returns false if denied. */
  async connectMic(): Promise<boolean> {
    try {
      const ctx = this.ensureCtx();
      if (ctx.state === "suspended") await ctx.resume();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = ctx.createMediaStreamSource(stream);
      source.connect(this.analyser!);
      this.connected = true;
      return true;
    } catch {
      return false;
    }
  }

  /** Connect to an HTMLAudioElement (for TTS playback analysis). */
  connectElement(el: HTMLAudioElement): void {
    try {
      const ctx = this.ensureCtx();
      const source = ctx.createMediaElementSource(el);
      source.connect(this.analyser!);
      this.analyser!.connect(ctx.destination); // pass through to speakers
      this.connected = true;
    } catch {
      // Element may already be connected — ignore
    }
  }

  /** Call once per frame to update levels. Cheap: reads existing FFT buffer. */
  update(): void {
    if (!this.analyser) return;
    this.analyser.getByteFrequencyData(this.data);
    const bins = this.data.length; // 128 bins for fftSize=256

    // Frequency band split:
    // Bass: bins 0-5 (~0-250Hz)
    // Mid:  bins 6-35 (~250-3kHz)
    // High: bins 36+ (>3kHz)
    let bass = 0, mid = 0, high = 0, total = 0;
    const bassEnd = 6, midEnd = 36;

    for (let i = 0; i < bins; i++) {
      const v = this.data[i] / 255;
      total += v;
      if (i < bassEnd) bass += v;
      else if (i < midEnd) mid += v;
      else high += v;
    }

    const rawBass = Math.min(1, bass / bassEnd);
    const rawMid = Math.min(1, mid / (midEnd - bassEnd));
    const rawHigh = Math.min(1, high / Math.max(1, bins - midEnd));
    const rawRms = Math.min(1, (total / bins) * 2.5);

    // Exponential smoothing (decay 0.85 = responsive but not jittery)
    const decay = 0.82;
    this.smoothBass = this.smoothBass * decay + rawBass * (1 - decay);
    this.smoothMid = this.smoothMid * decay + rawMid * (1 - decay);
    this.smoothHigh = this.smoothHigh * decay + rawHigh * (1 - decay);
    this.smoothRms = this.smoothRms * decay + rawRms * (1 - decay);

    this.levels.bass = this.smoothBass;
    this.levels.mid = this.smoothMid;
    this.levels.high = this.smoothHigh;
    this.levels.rms = this.smoothRms;
  }

  /** Disconnect and release resources. */
  destroy(): void {
    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
      this.analyser = null;
    }
    this.connected = false;
  }
}
