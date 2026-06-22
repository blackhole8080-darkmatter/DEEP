// <neural-sphere> — DEEP's centerpiece: a noise-displaced WIREFRAME sphere with
// multi-layer bloom, frequency-band audio reactivity, geodesic ripples, enhanced
// fresnel rim, hot-spot flares, depth-of-field, magnetic cursor denting, and a
// gesture system (click/double-click/hold).
//
// Pure Canvas 2D. Half-res glow buffer + dual-blur bloom. Adaptive quality tier.
// Modular render pipeline. Idle-throttled, reduced-motion aware, DPR capped.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { particleBudget, qualityTier, canvasFilterSupported, type QualityTier } from "../../core/perf";
import type { AudioLevels } from "../../core/audio";

// ── Types ──
type Status = "idle" | "active" | "speaking" | "thinking" | "warning" | "indexing";

interface MorphProfile {
  noiseFreq: number;
  noiseOctaves: number;
  noiseAmp: number;
  timeSpeed: number;
  rotSpeed: number;
  lineWidth: number;
  particleSpeed: number;
  hueShift: number;
  rimPower: number;
}

interface Particle { x: number; y: number; z: number; vx: number; vy: number; }

interface Ripple {
  age: number;
  life: number;
  origin: { dx: number; dy: number; dz: number };
  speed: number;
  color: number;
  intensity: number;
}

// ── Constants ──
const LAT = 26;
const LON = 46;
const VERTS = LAT * LON;

const PROFILES: Record<Status, MorphProfile> = {
  idle:     { noiseFreq: 1.7, noiseOctaves: 3, noiseAmp: 0.15, timeSpeed: 0.15, rotSpeed: 0.001, lineWidth: 0.7, particleSpeed: 1.0, hueShift: 212, rimPower: 2.8 },
  thinking: { noiseFreq: 2.8, noiseOctaves: 4, noiseAmp: 0.28, timeSpeed: 0.50, rotSpeed: 0.004, lineWidth: 0.6, particleSpeed: 2.5, hueShift: 280, rimPower: 2.0 },
  speaking: { noiseFreq: 1.4, noiseOctaves: 3, noiseAmp: 0.22, timeSpeed: 0.30, rotSpeed: 0.002, lineWidth: 1.0, particleSpeed: 1.5, hueShift: 35,  rimPower: 3.2 },
  active:   { noiseFreq: 2.0, noiseOctaves: 3, noiseAmp: 0.20, timeSpeed: 0.35, rotSpeed: 0.003, lineWidth: 0.8, particleSpeed: 1.8, hueShift: 190, rimPower: 2.5 },
  warning:  { noiseFreq: 3.5, noiseOctaves: 2, noiseAmp: 0.35, timeSpeed: 0.70, rotSpeed: 0.006, lineWidth: 0.5, particleSpeed: 3.0, hueShift: 0,   rimPower: 1.5 },
  indexing: { noiseFreq: 2.2, noiseOctaves: 3, noiseAmp: 0.18, timeSpeed: 0.25, rotSpeed: 0.002, lineWidth: 0.7, particleSpeed: 1.3, hueShift: 270, rimPower: 2.8 },
};

const RIM_HUE: Record<Status, number> = {
  idle: 190, active: 190, speaking: 35, thinking: 280, warning: 0, indexing: 270,
};

// ── Utilities ──
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const smoothstep = (e0: number, e1: number, x: number) => {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};
const easeInOutCubic = (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

@customElement("neural-sphere")
export class NeuralSphere extends LitElement {
  @property({ attribute: false }) activity = 0;
  @property({ attribute: false }) status: Status = "idle";
  @property({ attribute: false }) micLevels: AudioLevels | null = null;
  @property({ attribute: false }) ttsLevels: AudioLevels | null = null;

  // ── Canvas state ──
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private glow!: HTMLCanvasElement;
  private gctx!: CanvasRenderingContext2D;
  private raf = 0;
  private dpr = 1;
  private reduced = false;
  private filterOk = true;
  private lastDraw = 0;
  private lastTs = 0;
  private w = 0; private h = 0;
  private gw = 0; private gh = 0; // glow buffer (half-res) logical size

  // ── Geometry ──
  private dirs = new Float32Array(0);
  private particles: Particle[] = [];
  private perm = new Uint8Array(512);
  private rot = 0;

  // ── State interpolation ──
  private _prevProfile: MorphProfile = { ...PROFILES.idle };
  private _currentProfile: MorphProfile = { ...PROFILES.idle };
  private _targetProfile: MorphProfile = { ...PROFILES.idle };
  private _transProgress = 1;
  private _transDuration = 400;

  // ── Ripples ──
  private ripples: Ripple[] = [];

  // ── Cursor ──
  private mx = 0; private my = 0;
  private _smoothMx = 0; private _smoothMy = 0;
  private _mouseVelX = 0; private _mouseVelY = 0;
  private _prevMx = 0; private _prevMy = 0;

  // ── Gesture ──
  private _ptrDownTime = 0;
  private _ptrDownPos = { x: 0, y: 0 };
  private _clickCount = 0;
  private _clickTimer = 0;

  // ── Adaptive quality ──
  private _effectiveTier: QualityTier = "high";
  private _frameTimes: number[] = [];

  // ── Voice synth fallback ──
  private voicePhase = 0;

  // ── Debug ──
  private _debug = false;
  private _lastFrameMs = 0;
  private _hotCount = 0;

  // ── Resize observer ──
  private _ro?: ResizeObserver;

  // ── Preallocated vertex buffers ──
  private SX = new Float32Array(VERTS);
  private SY = new Float32Array(VERTS);
  private SZ = new Float32Array(VERTS);
  private HU = new Float32Array(VERTS);
  private RIM = new Float32Array(VERTS);
  private DISP = new Float32Array(VERTS);

  static styles = css`
    :host { display: block; width: 100%; height: 100%; pointer-events: auto; cursor: pointer; }
    canvas { width: 100%; height: 100%; display: block; }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.filterOk = canvasFilterSupported();
    this._effectiveTier = qualityTier();
    this._debug = new URLSearchParams(location.search).has("debug");
    window.addEventListener("mousemove", this._onMouse, { passive: true });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    this._ro?.disconnect();
    window.removeEventListener("mousemove", this._onMouse);
  }

  updated(changed: Map<string, unknown>): void {
    if (changed.has("status")) {
      this._prevProfile = { ...this._currentProfile };
      this._targetProfile = PROFILES[this.status] ?? PROFILES.idle;
      this._transProgress = 0;
      // Trigger ripple on meaningful state changes
      if (this.status === "speaking" || this.status === "active") {
        this.triggerRipple({ dx: 0, dy: 0, dz: 1 }, 2.0, 0, 1.0);
      } else if (this.status === "warning") {
        this.triggerRipple({ dx: 0, dy: 1, dz: 0 }, 3.0, 0, 1.0);
      }
    }
  }

  /** Trigger a geodesic ripple from an arbitrary origin on the sphere. */
  triggerRipple(
    origin: { dx: number; dy: number; dz: number },
    speed = 2.0, color = 0, intensity = 1.0
  ): void {
    const max = this._effectiveTier === "low" ? 1 : this._effectiveTier === "medium" ? 3 : 6;
    if (this.ripples.length >= max) this.ripples.shift();
    this.ripples.push({ age: 0, life: 1.6, origin, speed, color, intensity });
  }

  /** Legacy API compat. */
  pulse(): void { this.triggerRipple({ dx: 0, dy: 0, dz: 1 }, 2.0, 0, 0.8); }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.ctx = this.canvas.getContext("2d")!;
    this.glow = document.createElement("canvas");
    this.gctx = this.glow.getContext("2d")!;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this._seedGrid(); this._seedNoise(); this._seedParticles();
    // Gesture listeners
    this.canvas.addEventListener("pointerdown", this._onPtrDown);
    this.canvas.addEventListener("pointerup", this._onPtrUp);
    // Observe the HOST element (not canvas) — it gets position:absolute inset:0
    // from the parent stylesheet so ResizeObserver fires with reliable dimensions
    // once the browser finishes layout, before the first rAF.
    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(this);
    if (!this.reduced) { this.lastTs = performance.now(); this.raf = requestAnimationFrame(this._loop); }
  }

  // ── Input ──
  private _onMouse = (e: MouseEvent) => {
    this.mx = (e.clientX / window.innerWidth - 0.5) * 2;
    this.my = (e.clientY / window.innerHeight - 0.5) * 2;
  };

  private _onPtrDown = (e: PointerEvent) => {
    this._ptrDownTime = performance.now();
    this._ptrDownPos = { x: e.offsetX, y: e.offsetY };
  };

  private _onPtrUp = (e: PointerEvent) => {
    const held = performance.now() - this._ptrDownTime;
    const moved = Math.hypot(e.offsetX - this._ptrDownPos.x, e.offsetY - this._ptrDownPos.y);
    if (moved > 20) return;
    if (held > 400) {
      this.dispatchEvent(new CustomEvent("sphere-listen", { bubbles: true, composed: true }));
      this.triggerRipple({ dx: 0, dy: -1, dz: 0 }, 2.0, 150, 0.9);
      return;
    }
    this._clickCount++;
    clearTimeout(this._clickTimer);
    this._clickTimer = window.setTimeout(() => {
      if (this._clickCount >= 2) {
        this.dispatchEvent(new CustomEvent("sphere-command", { bubbles: true, composed: true }));
      } else {
        this.dispatchEvent(new CustomEvent("sphere-activate", { bubbles: true, composed: true }));
        this.triggerRipple({ dx: 0, dy: 0, dz: 1 }, 4.0, 0, 1.2);
      }
      this._clickCount = 0;
    }, 250);
  };

  // ── Resize ──
  private _resize = () => {
    if (!this.canvas) return;
    // Prefer host element dimensions (set by absolute inset:0 from parent)
    this.w = this.clientWidth || this.offsetWidth || this.canvas.clientWidth;
    this.h = this.clientHeight || this.offsetHeight || this.canvas.clientHeight;
    if (!this.w || !this.h) return;
    const W = this.w * this.dpr, H = this.h * this.dpr;
    this.canvas.width = W; this.canvas.height = H;
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    // Half-res glow buffer. Its logical space is (w/2, h/2) — vertices, particles
    // and clearRect all draw in half-coordinates — so the transform maps that
    // logical space onto the half-size pixel buffer (W/2): scale = dpr.
    this.gw = Math.ceil(this.w / 2); this.gh = Math.ceil(this.h / 2);
    this.glow.width = Math.ceil(W / 2); this.glow.height = Math.ceil(H / 2);
    this.gctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  };

  // ── Seeding ──
  private _seedGrid(): void {
    this.dirs = new Float32Array(VERTS * 3);
    let k = 0;
    for (let i = 0; i < LAT; i++) {
      const phi = (i / (LAT - 1)) * Math.PI;
      const sp = Math.sin(phi), cp = Math.cos(phi);
      for (let j = 0; j < LON; j++) {
        const th = (j / LON) * Math.PI * 2;
        this.dirs[k++] = sp * Math.cos(th); this.dirs[k++] = cp; this.dirs[k++] = sp * Math.sin(th);
      }
    }
  }
  private _seedNoise(): void {
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    for (let i = 255; i > 0; i--) { const r = (Math.random() * (i + 1)) | 0; [p[i], p[r]] = [p[r], p[i]]; }
    for (let i = 0; i < 512; i++) this.perm[i] = p[i & 255];
  }
  private _seedParticles(): void {
    const n = particleBudget();
    this.particles = Array.from({ length: n }, () => ({
      x: (Math.random() - 0.5) * 2.4, y: (Math.random() - 0.5) * 2.4, z: (Math.random() - 0.5) * 2.4,
      vx: (Math.random() - 0.5) * 0.002, vy: (Math.random() - 0.5) * 0.002,
    }));
  }

  // ── Noise ──
  private _n3(x: number, y: number, z: number): number {
    const P = this.perm;
    const xi = Math.floor(x) & 255, yi = Math.floor(y) & 255, zi = Math.floor(z) & 255;
    const xf = x - Math.floor(x), yf = y - Math.floor(y), zf = z - Math.floor(z);
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
    const h = (a: number, b: number, c: number) => P[(P[(P[a & 255] + b) & 255] + c) & 255] / 255;
    const c000 = h(xi, yi, zi), c100 = h(xi + 1, yi, zi), c010 = h(xi, yi + 1, zi), c110 = h(xi + 1, yi + 1, zi);
    const c001 = h(xi, yi, zi + 1), c101 = h(xi + 1, yi, zi + 1), c011 = h(xi, yi + 1, zi + 1), c111 = h(xi + 1, yi + 1, zi + 1);
    const lx0 = c000 + (c100 - c000) * u, lx1 = c010 + (c110 - c010) * u;
    const lx2 = c001 + (c101 - c001) * u, lx3 = c011 + (c111 - c011) * u;
    const ly0 = lx0 + (lx1 - lx0) * v, ly1 = lx2 + (lx3 - lx2) * v;
    return ly0 + (ly1 - ly0) * w;
  }
  private _fbm(x: number, y: number, z: number, octaves: number): number {
    let val = 0, amp = 0.5;
    for (let o = 0; o < octaves; o++) { val += amp * this._n3(x, y, z); x *= 2.03; y *= 2.03; z *= 2.03; amp *= 0.5; }
    return val;
  }

  // ── Voice synthesized fallback ──
  private _synthVoice(t: number): number {
    if (this.status === "speaking") {
      this.voicePhase += 0.25;
      return 0.45 + 0.4 * Math.abs(Math.sin(this.voicePhase) * Math.sin(this.voicePhase * 0.37 + 1));
    }
    if (this.status === "active") return 0.15 + 0.1 * Math.abs(Math.sin(t * 6));
    return 0;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER PIPELINE
  // ═══════════════════════════════════════════════════════════════════════════

  private _loop = (ts: number) => {
    this.raf = requestAnimationFrame(this._loop);
    // Safety: if _resize hasn't run yet (e.g. first frame before ResizeObserver fires)
    if (!this.w || !this.h) { this._resize(); if (!this.w || !this.h) return; }
    const dt = ts - this.lastTs;
    this.lastTs = ts;
    const interval = this.activity >= 0.5 || this.ripples.length ? 0 : this.activity > 0.1 ? 33 : 50;
    if (ts - this.lastDraw < interval) return;
    this.lastDraw = ts;
    const start = performance.now();
    this._updateState(dt);
    this._draw(ts);
    this._measureFrame(start);
  };

  // ── Step 1: Update state (lerp profiles, smooth cursor, advance ripples) ──
  private _updateState(dt: number): void {
    // Profile transition
    if (this._transProgress < 1) {
      this._transProgress = Math.min(1, this._transProgress + dt / this._transDuration);
      const t = easeInOutCubic(this._transProgress);
      const cur = this._currentProfile as unknown as Record<string, number>;
      const prev = this._prevProfile as unknown as Record<string, number>;
      const tgt = this._targetProfile as unknown as Record<string, number>;
      for (const key of Object.keys(this._currentProfile)) {
        cur[key] = lerp(prev[key], tgt[key], t);
      }
    }
    // Smooth cursor
    const rate = 1 - Math.pow(0.05, dt / 16);
    this._smoothMx += (this.mx - this._smoothMx) * rate;
    this._smoothMy += (this.my - this._smoothMy) * rate;
    this._mouseVelX = (this.mx - this._prevMx) / Math.max(dt, 1);
    this._mouseVelY = (this.my - this._prevMy) / Math.max(dt, 1);
    this._prevMx = this.mx; this._prevMy = this.my;
    // Advance ripples
    for (const r of this.ripples) r.age += dt * 0.001;
    this.ripples = this.ripples.filter((r) => r.age < r.life);
  }

  // ── Main draw ──
  private _draw(ts: number): void {
    const main = this.ctx, g = this.gctx;
    if (!main || !g) return;
    const w = this.w, h = this.h, t = ts / 1000;
    const cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.34;
    const prof = this._currentProfile;
    const tier = this._effectiveTier;

    // Audio levels (real or synthesized)
    const audio = this.micLevels ?? this.ttsLevels;
    const bass = audio ? audio.bass : this._synthVoice(t);
    const mid = audio ? audio.mid : (this.status === "thinking" ? 0.4 : 0);
    const high = audio ? audio.high : 0;
    const energy = Math.min(1, this.activity + bass);

    // Rotation
    this.rot += prof.rotSpeed + energy * 0.002 + mid * 0.002;
    const syR = Math.sin(this.rot + this._smoothMx * 0.5), cyR = Math.cos(this.rot + this._smoothMx * 0.5);
    const tilt = 0.35 + this._smoothMy * 0.3;
    const sxR = Math.sin(tilt), cxR = Math.cos(tilt);

    // Noise params from profile
    const amp = prof.noiseAmp + bass * 0.15;
    const nf = prof.noiseFreq;
    const octaves = tier === "low" ? Math.min(prof.noiseOctaves, 2) : tier === "medium" ? Math.min(prof.noiseOctaves, 3) : prof.noiseOctaves;
    const tSpeed = prof.timeSpeed;

    // Cursor direction
    const cdLen = Math.hypot(this._smoothMx, -this._smoothMy, 1.2);
    const cdx = this._smoothMx / cdLen, cdy = -this._smoothMy / cdLen, cdz = 1.2 / cdLen;
    const mouseSpeed = Math.hypot(this._mouseVelX, this._mouseVelY);

    // ── Compute vertices ──
    this._computeVertices(t, tSpeed, nf, amp, octaves, cx, cy, R, syR, cyR, sxR, cxR, cdx, cdy, cdz, mouseSpeed);

    // ── Clear buffers ──
    main.clearRect(0, 0, w, h);
    g.clearRect(0, 0, this.gw, this.gh);

    // ── Render to glow buffer (half-res) ──
    this._renderMesh(g, prof, tier, t);
    this._renderRim(g, tier, t);
    this._renderHotSpots(g, tier);
    this._renderParticles(g, prof, cx / 2, cy / 2, R / 2, syR, cyR, sxR, cxR);

    // ── Composite to main canvas ──
    this._renderBackdrop(main, cx, cy, R, energy, prof.hueShift);
    this._compositeBloom(main, w, h, energy, tier);
    this._compositeCrisp(main, w, h);
    this._renderCursorGlow(main, cx, cy, R, prof.hueShift);
    this._toneClamp(main, w, h);

    // ── Debug overlay ──
    if (this._debug) this._renderDebug(main, bass, mid, high);
  }

  // ── Vertex computation ──
  private _computeVertices(
    t: number, tSpeed: number, nf: number, amp: number, octaves: number,
    cx: number, cy: number, R: number,
    syR: number, cyR: number, sxR: number, cxR: number,
    cdx: number, cdy: number, cdz: number, mouseSpeed: number
  ): void {
    const halfCx = cx / 2, halfCy = cy / 2, halfR = R / 2;
    for (let idx = 0; idx < VERTS; idx++) {
      const dx = this.dirs[idx * 3], dy = this.dirs[idx * 3 + 1], dz = this.dirs[idx * 3 + 2];
      let disp = 1 + amp * (this._fbm(dx * nf + t * tSpeed, dy * nf, dz * nf - t * tSpeed * 0.7, octaves) - 0.5) * 2;

      // Geodesic ripples
      for (const r of this.ripples) {
        const dot = dx * r.origin.dx + dy * r.origin.dy + dz * r.origin.dz;
        const geoDist = Math.acos(Math.max(-1, Math.min(1, dot)));
        const front = r.age * r.speed;
        const ring = Math.exp(-((geoDist - front) ** 2) / 0.04) * r.intensity;
        const trail = Math.exp(-((geoDist - front * 0.7) ** 2) / 0.12) * r.intensity * 0.4;
        disp += (ring + trail) * 0.2 * (1 - r.age / r.life);
      }

      // Magnetic cursor dent
      const facing = dx * cdx + dy * cdy + dz * cdz;
      if (facing > 0.55) {
        const strength = (facing - 0.55) * (0.6 + mouseSpeed * 2.0);
        disp -= strength * 0.35;
      } else if (facing > 0.3) {
        disp += (facing - 0.3) * 0.12;
      }

      this.DISP[idx] = disp;
      const x = dx * disp, y = dy * disp, z = dz * disp;
      let rx = x * cyR - z * syR, rz = x * syR + z * cyR;
      let ry = y * cxR - rz * sxR; rz = y * sxR + rz * cxR;
      const persp = 1 / (2.0 - rz);
      // Store in half-res coords for glow buffer
      this.SX[idx] = halfCx + rx * halfR * persp * 2.2;
      this.SY[idx] = halfCy + ry * halfR * persp * 2.2;
      this.SZ[idx] = rz;
      this.HU[idx] = this._currentProfile.hueShift + ((rx + 1) / 2) * 110 + 16 * Math.sin(t * 0.4 + ry * 1.8);
      // Enhanced Fresnel rim
      const viewDot = Math.abs(rz);
      this.RIM[idx] = Math.pow(1 - Math.min(1, viewDot / 0.55), this._currentProfile.rimPower);
    }
  }

  // ── Mesh rendering (to half-res glow buffer) ──
  private _renderMesh(g: CanvasRenderingContext2D, prof: MorphProfile, tier: QualityTier, _t: number): void {
    g.globalCompositeOperation = "lighter";
    for (let i = 0; i < LAT; i++) {
      for (let j = 0; j < LON; j++) {
        const a = i * LON + j;
        const right = i * LON + ((j + 1) % LON);
        const down = (i + 1) * LON + j;
        const depthFade = smoothstep(-0.6, 0.05, this.SZ[a]);
        const alpha = 0.03 + depthFade * depthFade * 0.5 + this.RIM[a] * 0.3;
        const lw = (0.3 + depthFade * 0.5) * prof.lineWidth;
        g.lineWidth = lw;
        g.strokeStyle = `hsla(${this.HU[a]},95%,${50 + depthFade * 30 + this.RIM[a] * 12}%,${alpha})`;
        g.beginPath(); g.moveTo(this.SX[a], this.SY[a]); g.lineTo(this.SX[right], this.SY[right]); g.stroke();
        if (i < LAT - 1) { g.beginPath(); g.moveTo(this.SX[a], this.SY[a]); g.lineTo(this.SX[down], this.SY[down]); g.stroke(); }
      }
    }
    // Vertex dots
    for (let idx = 0; idx < VERTS; idx++) {
      const depthFade = smoothstep(-0.6, 0.05, this.SZ[idx]);
      if (depthFade < 0.1 && this.RIM[idx] < 0.4) continue;
      const r = (0.3 + depthFade * 1.2 + this.RIM[idx] * 1.0) * (tier === "low" ? 0.7 : 1);
      g.beginPath(); g.arc(this.SX[idx], this.SY[idx], r, 0, Math.PI * 2);
      g.fillStyle = `hsla(${this.HU[idx]},100%,${65 + depthFade * 25}%,${0.2 + depthFade * 0.5 + this.RIM[idx] * 0.3})`;
      g.fill();
    }
    g.globalCompositeOperation = "source-over";
  }

  // ── Enhanced rim pass ──
  private _renderRim(g: CanvasRenderingContext2D, tier: QualityTier, t: number): void {
    if (tier === "low") return;
    const rimHue = RIM_HUE[this.status] ?? 190;
    g.globalCompositeOperation = "lighter";
    g.lineWidth = 1.8;
    for (let i = 0; i < LAT; i++) {
      for (let j = 0; j < LON; j++) {
        const a = i * LON + j;
        if (this.RIM[a] < 0.55) continue;
        const right = i * LON + ((j + 1) % LON);
        if (this.RIM[right] < 0.45) continue;
        const shimmer = 0.7 + 0.3 * Math.sin(t * 3.5 + a * 0.08);
        // Iridescent rim: drift through a cyan → violet → pink spectrum over time + position
        const iridHue = rimHue + 55 + 55 * Math.sin(t * 0.5 + a * 0.11);
        g.strokeStyle = `hsla(${iridHue},100%,82%,${this.RIM[a] * 0.7 * shimmer})`;
        g.beginPath(); g.moveTo(this.SX[a], this.SY[a]); g.lineTo(this.SX[right], this.SY[right]); g.stroke();
      }
    }
    g.globalCompositeOperation = "source-over";
  }

  // ── Hot-spot flares ──
  private _renderHotSpots(g: CanvasRenderingContext2D, tier: QualityTier): void {
    if (tier !== "high") { this._hotCount = 0; return; }
    const HOT_THRESHOLD = 1.18;
    const HOT_MAX = 12;
    let count = 0;
    g.globalCompositeOperation = "lighter";
    for (let idx = 0; idx < VERTS && count < HOT_MAX; idx++) {
      if (this.DISP[idx] < HOT_THRESHOLD || this.SZ[idx] < -0.3) continue;
      count++;
      const intensity = Math.min(1, (this.DISP[idx] - HOT_THRESHOLD) / 0.25);
      const r = 4 + intensity * 5;
      const grad = g.createRadialGradient(this.SX[idx], this.SY[idx], 0, this.SX[idx], this.SY[idx], r);
      grad.addColorStop(0, `hsla(${280 + intensity * 80},100%,75%,${0.5 * intensity})`);
      grad.addColorStop(1, `hsla(${280 + intensity * 80},100%,60%,0)`);
      g.fillStyle = grad;
      g.fillRect(this.SX[idx] - r, this.SY[idx] - r, r * 2, r * 2);
    }
    g.globalCompositeOperation = "source-over";
    this._hotCount = count;
  }

  // ── Particles ──
  private _renderParticles(
    g: CanvasRenderingContext2D, prof: MorphProfile,
    cx: number, cy: number, R: number,
    syR: number, cyR: number, sxR: number, cxR: number
  ): void {
    const speed = prof.particleSpeed;
    g.globalCompositeOperation = "lighter";
    for (const p of this.particles) {
      p.x += p.vx * speed; p.y += p.vy * speed;
      if (p.x < -1.4 || p.x > 1.4) p.vx *= -1;
      if (p.y < -1.4 || p.y > 1.4) p.vy *= -1;
      let rx = p.x * cyR - p.z * syR, rz = p.x * syR + p.z * cyR;
      let ry = p.y * cxR - rz * sxR; rz = p.y * sxR + rz * cxR;
      const persp = 1 / (2.0 - rz);
      const px = cx + rx * R * persp * 2.4, py = cy + ry * R * persp * 2.4;
      const za = (rz + 1.4) / 2.8;
      g.beginPath(); g.arc(px, py, 0.4 + za * 0.8, 0, Math.PI * 2);
      g.fillStyle = `hsla(${prof.hueShift + ((rx + 1) / 2) * 80},100%,80%,${0.12 + za * 0.4})`;
      g.fill();
    }
    g.globalCompositeOperation = "source-over";
  }

  // ── Backdrop radial glow ──
  private _renderBackdrop(main: CanvasRenderingContext2D, cx: number, cy: number, R: number, energy: number, hue: number): void {
    const bgg = main.createRadialGradient(cx, cy, 0, cx, cy, R * 2.2);
    bgg.addColorStop(0, `hsla(${hue},90%,50%,${0.04 + 0.12 * energy})`);
    bgg.addColorStop(1, "hsla(0,0%,0%,0)");
    main.fillStyle = bgg;
    main.fillRect(0, 0, this.w, this.h);
  }

  // ── Bloom composite (dual-pass, half-res upscaled) ──
  private _compositeBloom(main: CanvasRenderingContext2D, w: number, h: number, energy: number, tier: QualityTier): void {
    if (tier === "low") return;
    main.globalCompositeOperation = "lighter";
    if (this.filterOk) {
      // Pass 1: tight glow
      try {
        main.filter = `blur(${3 + energy * 3}px)`;
        main.globalAlpha = 0.65;
        main.drawImage(this.glow, 0, 0, w, h);
        main.filter = "none"; main.globalAlpha = 1;
      } catch { main.filter = "none"; main.globalAlpha = 1; }
      // Pass 2: wide bloom (high tier only)
      if (tier === "high") {
        try {
          main.filter = `blur(${10 + energy * 8}px)`;
          main.globalAlpha = 0.3;
          main.drawImage(this.glow, 0, 0, w, h);
          main.filter = "none"; main.globalAlpha = 1;
        } catch { main.filter = "none"; main.globalAlpha = 1; }
      }
    } else {
      // Safari fallback: offset-draw approximation
      main.globalAlpha = 0.2;
      const s = 2;
      main.drawImage(this.glow, -s, 0, w, h);
      main.drawImage(this.glow, s, 0, w, h);
      main.drawImage(this.glow, 0, -s, w, h);
      main.drawImage(this.glow, 0, s, w, h);
      main.globalAlpha = 1;
    }
    main.globalCompositeOperation = "source-over";
  }

  // ── Crisp pass (sharp glow buffer composited on top) ──
  private _compositeCrisp(main: CanvasRenderingContext2D, w: number, h: number): void {
    main.globalCompositeOperation = "lighter";
    main.drawImage(this.glow, 0, 0, w, h);
    main.globalCompositeOperation = "source-over";
  }

  // ── Cursor glow at sphere intersection ──
  private _renderCursorGlow(main: CanvasRenderingContext2D, cx: number, cy: number, R: number, hue: number): void {
    if (this._effectiveTier === "low") return;
    const curX = cx + this._smoothMx * R * 0.7;
    const curY = cy - this._smoothMy * R * 0.7;
    const dist = Math.hypot(curX - cx, curY - cy);
    if (dist > R * 1.2) return;
    const grad = main.createRadialGradient(curX, curY, 0, curX, curY, 28);
    grad.addColorStop(0, `hsla(${hue},90%,80%,0.2)`);
    grad.addColorStop(1, `hsla(${hue},90%,60%,0)`);
    main.fillStyle = grad;
    main.fillRect(curX - 28, curY - 28, 56, 56);
  }

  // ── Tone clamping (prevent white washout) ──
  private _toneClamp(main: CanvasRenderingContext2D, w: number, h: number): void {
    main.fillStyle = "rgba(2,6,14,0.05)";
    main.fillRect(0, 0, w, h);
  }

  // ── Adaptive quality measurement ──
  private _measureFrame(startTs: number): void {
    const elapsed = performance.now() - startTs;
    this._lastFrameMs = elapsed;
    this._frameTimes.push(elapsed);
    if (this._frameTimes.length > 30) this._frameTimes.shift();
    if (this._frameTimes.length < 10) return;
    const avg = this._frameTimes.reduce((a, b) => a + b, 0) / this._frameTimes.length;
    if (avg > 12 && this._effectiveTier === "high") this._effectiveTier = "medium";
    else if (avg > 12 && this._effectiveTier === "medium") this._effectiveTier = "low";
    else if (avg < 6 && this._frameTimes.length >= 30) {
      const base = qualityTier();
      if (this._effectiveTier === "low" && base !== "low") this._effectiveTier = "medium";
      else if (this._effectiveTier === "medium" && base === "high") this._effectiveTier = "high";
    }
  }

  // ── Debug overlay ──
  private _renderDebug(main: CanvasRenderingContext2D, bass: number, mid: number, high: number): void {
    main.fillStyle = "rgba(0,0,0,0.75)";
    main.fillRect(8, 8, 210, 100);
    main.font = "11px monospace"; main.fillStyle = "#0f0";
    main.fillText(`frame: ${this._lastFrameMs.toFixed(1)}ms`, 14, 24);
    main.fillText(`tier: ${this._effectiveTier} (base: ${qualityTier()})`, 14, 38);
    main.fillText(`ripples: ${this.ripples.length}`, 14, 52);
    main.fillText(`hot-spots: ${this._hotCount}`, 14, 66);
    main.fillText(`audio: B${bass.toFixed(2)} M${mid.toFixed(2)} H${high.toFixed(2)}`, 14, 80);
    main.fillText(`status: ${this.status} | activity: ${this.activity.toFixed(2)}`, 14, 94);
  }

  render() { return html`<canvas></canvas>`; }
}

declare global {
  interface HTMLElementTagNameMap { "neural-sphere": NeuralSphere; }
}
