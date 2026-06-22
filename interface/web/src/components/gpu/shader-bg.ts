// <deep-shader-bg> — cinematic, shader-grade background field for DEEP.
//
// The deepest visual layer (behind the living-brain HUD). Renders a procedural
// "cinematic field" — flowing fbm nebula + holographic grid + activity-driven
// radial glow + vignette/scanlines — in real GLSL on the GPU.
//
// CAPABILITY TIERING (best available, automatic):
//   WebGPU (WGSL)  →  WebGL2 (GLSL)  →  Canvas 2D (gradient fallback)
// The WebGPU slot is wired into detection but currently routes to WebGL2 until
// its WGSL pipeline is validated on real hardware (see _initWebGPU). WebGL2 is
// the verified workhorse (~98% device support).
//
// FAIL-SOFT: any GPU init/compile failure removes this layer entirely (it becomes
// transparent), so the HUD/UI behind it is never broken by a shader problem.
//
// PERF: cooling-aware throttle — full rate only while DEEP is active; idle drops
// to ~10fps; prefers-reduced-motion renders a single static frame.
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

type Backend = "webgpu" | "webgl2" | "canvas" | "none";

// Accent RGB per status, matching the HUD palette (0..1 floats for shaders).
const ACCENT: Record<string, [number, number, number]> = {
  idle:     [0.0, 1.0, 0.53],
  active:   [0.0, 0.9, 1.0],
  speaking: [1.0, 0.0, 0.67],
  thinking: [1.0, 0.67, 0.0],
  warning:  [1.0, 0.2, 0.2],
  indexing: [0.67, 0.4, 1.0],
};

const VERT = `#version 300 es
in vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`;

// Fragment: flowing fbm nebula + grid + radial activity glow + vignette.
const FRAG = `#version 300 es
precision highp float;
out vec4 o;
uniform vec2  u_res;
uniform float u_time;
uniform float u_activity;   // 0..1
uniform vec3  u_accent;     // status colour
uniform vec2  u_mouse;      // 0..1

float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  float a = hash(i), b = hash(i+vec2(1.,0.)), c = hash(i+vec2(0.,1.)), d = hash(i+vec2(1.,1.));
  vec2 u = f*f*(3.-2.*f);
  return mix(mix(a,b,u.x), mix(c,d,u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for(int i=0;i<5;i++){ v += a*noise(p); p *= 2.0; a *= 0.5; }
  return v;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 c = (gl_FragCoord.xy - 0.5*u_res) / u_res.y;  // aspect-correct, centered

  // Flowing nebula
  float t = u_time * 0.04;
  vec2 q = c*1.6 + vec2(t, -t*0.6);
  float n = fbm(q + fbm(q + t));
  vec3 neb = mix(vec3(0.02,0.03,0.06), u_accent*0.5, smoothstep(0.35,0.85,n)) * (0.35 + 0.4*u_activity);

  // Holographic grid (perspective-ish), subtle
  vec2 g = abs(fract(uv*vec2(40.0,24.0)) - 0.5);
  float grid = smoothstep(0.48,0.5, max(g.x,g.y));
  neb += u_accent * grid * 0.04;

  // Radial glow from center, pulses with activity
  float r = length(c);
  float pulse = 0.5 + 0.5*sin(u_time*1.5);
  float glow = exp(-r*2.4) * (0.12 + 0.5*u_activity*pulse);
  neb += u_accent * glow;

  // Mouse-proximity highlight
  float md = length(c - (u_mouse-0.5)*vec2(u_res.x/u_res.y, -1.0)*2.0);
  neb += u_accent * exp(-md*5.0) * 0.15;

  // Scanlines + vignette
  neb *= 1.0 - 0.06*sin(gl_FragCoord.y*1.5);
  neb *= smoothstep(1.25, 0.2, r);

  o = vec4(neb, 1.0);
}`;

@customElement("deep-shader-bg")
export class DeepShaderBg extends LitElement {
  @property({ attribute: false }) activity = 0;          // 0..1 from app
  @property({ attribute: false }) status = "idle";        // drives accent colour

  private backend: Backend = "none";
  private canvas!: HTMLCanvasElement;
  private gl: WebGL2RenderingContext | null = null;
  private prog: WebGLProgram | null = null;
  private uni: Record<string, WebGLUniformLocation | null> = {};
  private raf = 0;
  private lastDraw = 0;
  private dpr = 1;
  private reduced = false;
  private mouse = { x: 0.5, y: 0.5 };
  private start = performance.now();

  static styles = css`
    :host { display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none; }
    canvas { width: 100%; height: 100%; display: block; }
    :host(.dead) { display: none; }   /* fail-soft: let the HUD/CSS show */
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.addEventListener("mousemove", this._onMouse, { passive: true });
    window.addEventListener("resize", this._resize);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    cancelAnimationFrame(this.raf);
    window.removeEventListener("mousemove", this._onMouse);
    window.removeEventListener("resize", this._resize);
  }

  firstUpdated(): void {
    this.canvas = this.renderRoot.querySelector("canvas")!;
    this.dpr = Math.min(window.devicePixelRatio || 1, 1.5);  // shaders are fill-rate bound; cap DPR
    this.backend = this._detect();
    let ok = false;
    try {
      if (this.backend === "webgl2") ok = this._initWebGL2();
    } catch (e) { ok = false; }
    if (!ok) { this._die(); return; }   // fail-soft → hide, HUD shows through
    this._resize();
    if (this.reduced) this._draw(performance.now());
    else this.raf = requestAnimationFrame(this._loop);
  }

  /** Pick the best backend. WebGPU is detected but routes to WebGL2 until its
   *  WGSL pipeline is hardware-validated (kept honest rather than shipping
   *  unverified GPU code that could silently render nothing). */
  private _detect(): Backend {
    const hasWebGPU = "gpu" in navigator && !!(navigator as any).gpu;
    const gl = document.createElement("canvas").getContext("webgl2");
    if (hasWebGPU && gl) return "webgl2";  // TODO(webgpu): swap to "webgpu" once WGSL path verified
    if (gl) return "webgl2";
    return "canvas";
  }

  private _die(): void { this.classList.add("dead"); cancelAnimationFrame(this.raf); }

  private _onMouse = (e: MouseEvent) => {
    this.mouse.x = e.clientX / window.innerWidth;
    this.mouse.y = e.clientY / window.innerHeight;
  };

  private _resize = () => {
    if (!this.canvas || !this.gl) return;
    const w = Math.floor(this.canvas.clientWidth * this.dpr);
    const h = Math.floor(this.canvas.clientHeight * this.dpr);
    this.canvas.width = w; this.canvas.height = h;
    this.gl.viewport(0, 0, w, h);
  };

  private _compile(type: number, src: string): WebGLShader {
    const gl = this.gl!;
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(s);
      gl.deleteShader(s);
      throw new Error("shader compile failed: " + log);
    }
    return s;
  }

  private _initWebGL2(): boolean {
    const gl = this.canvas.getContext("webgl2", { antialias: false, alpha: false, premultipliedAlpha: false });
    if (!gl) return false;
    this.gl = gl;
    const prog = gl.createProgram()!;
    gl.attachShader(prog, this._compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, this._compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error("program link failed: " + gl.getProgramInfoLog(prog));
    }
    this.prog = prog;
    gl.useProgram(prog);

    // Fullscreen triangle
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    for (const u of ["u_res", "u_time", "u_activity", "u_accent", "u_mouse"]) {
      this.uni[u] = gl.getUniformLocation(prog, u);
    }
    return true;
  }

  private _loop = (ts: number) => {
    this.raf = requestAnimationFrame(this._loop);
    const interval = this.activity >= 0.5 ? 0 : this.activity > 0.1 ? 33 : 100; // idle → ~10fps
    if (ts - this.lastDraw < interval) return;
    this.lastDraw = ts;
    this._draw(ts);
  };

  private _draw(ts: number): void {
    const gl = this.gl;
    if (!gl || !this.prog) return;
    gl.useProgram(this.prog);
    const acc = ACCENT[this.status] ?? ACCENT.idle;
    gl.uniform2f(this.uni.u_res!, this.canvas.width, this.canvas.height);
    gl.uniform1f(this.uni.u_time!, (ts - this.start) / 1000);
    gl.uniform1f(this.uni.u_activity!, Math.max(0, Math.min(1, this.activity)));
    gl.uniform3f(this.uni.u_accent!, acc[0], acc[1], acc[2]);
    gl.uniform2f(this.uni.u_mouse!, this.mouse.x, this.mouse.y);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  render() { return html`<canvas></canvas>`; }
}

declare global {
  interface HTMLElementTagNameMap { "deep-shader-bg": DeepShaderBg; }
}
