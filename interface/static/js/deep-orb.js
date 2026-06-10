/* ============================================================================
 * DEEP — LIQUID INTELLIGENCE ORB
 * ----------------------------------------------------------------------------
 * The hero of the "Abyssal Tech" identity. A morphing sphere of bio-luminescent
 * fluid built from layered SVG: a feTurbulence + feDisplacementMap distorts the
 * orb's edges into liquid, while stacked radial gradients give it depth and an
 * inner light. It tracks the live core (ngCx / ngCy / ngCoreR) and reacts to the
 * assistant's state:
 *   idle      → slow breathing, deep teal
 *   listening → high-frequency ripples scaled by mic amplitude
 *   thinking  → faster churn, rotation, shift toward vibrant cyan
 *   speaking  → pulses with the TTS envelope
 *
 * Classic (non-module) script — shares app.js's lexical globals: state, ngCx,
 * ngCy, ngCoreR, ngCore, orbMicAmplitude, ttsAmplitude.
 * ========================================================================== */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  let host, svg, turb, disp, gMorph, ringGroup, raf;
  let energy = 0;          // smoothed 0..1 reactive drive
  let churn = 0;           // animated turbulence phase
  let rot = 0;

  // NOTE: app.js declares ngCx/ngCy/state/etc with `let` at top level, which does
  // NOT expose them on `window`. As classic scripts we share the global lexical
  // scope, so we read the bare identifiers (guarded with typeof) instead.
  function coreX() { return (typeof ngCx === "number" && ngCx) || window.innerWidth / 2; }
  function coreY() { return (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46; }
  function coreR() { return (typeof ngCoreR === "number" && ngCoreR) || Math.min(window.innerWidth, window.innerHeight) * 0.04; }
  function sysState() { return (typeof state === "string") ? state : "idle"; }
  function drive() {
    const a = (typeof ngCore !== "undefined" && ngCore && ngCore.act) || 0;
    const m = (typeof orbMicAmplitude === "number") ? orbMicAmplitude : 0;
    const t = (typeof ttsAmplitude === "number") ? ttsAmplitude : 0;
    return Math.min(1, Math.max(a, m * 0.5, t * 0.5));
  }

  function build() {
    host = document.createElement("div");
    host.id = "deep-orb";
    host.setAttribute("aria-hidden", "true");

    // viewBox is a fixed 200×200 design space; we scale the host in CSS px.
    svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    svg.innerHTML = `
      <defs>
        <filter id="deepLiquid" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.011 0.014" numOctaves="2" seed="4" result="noise">
            <animate attributeName="baseFrequency" dur="18s" repeatCount="indefinite"
                     values="0.010 0.013; 0.016 0.011; 0.010 0.013"/>
          </feTurbulence>
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="16"
                             xChannelSelector="R" yChannelSelector="G"/>
          <feGaussianBlur stdDeviation="0.4"/>
        </filter>

        <radialGradient id="deepCore" cx="42%" cy="38%" r="68%">
          <stop offset="0%"  stop-color="#9bfff0"/>
          <stop offset="28%" stop-color="#00ffd1"/>
          <stop offset="62%" stop-color="#00b8e6"/>
          <stop offset="100%" stop-color="#003a66"/>
        </radialGradient>
        <radialGradient id="deepRim" cx="50%" cy="50%" r="50%">
          <stop offset="60%" stop-color="rgba(0,229,255,0)"/>
          <stop offset="88%" stop-color="rgba(0,229,255,0.55)"/>
          <stop offset="100%" stop-color="rgba(0,255,209,0)"/>
        </radialGradient>
        <radialGradient id="deepGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%"  stop-color="rgba(0,255,209,0.45)"/>
          <stop offset="45%" stop-color="rgba(0,150,220,0.18)"/>
          <stop offset="100%" stop-color="rgba(0,30,60,0)"/>
        </radialGradient>
      </defs>

      <!-- ambient bloom (unfiltered, sits behind) -->
      <circle class="orb-bloom" cx="100" cy="100" r="92" fill="url(#deepGlow)"/>

      <!-- the liquid body -->
      <g class="orb-morph" filter="url(#deepLiquid)">
        <circle cx="100" cy="100" r="62" fill="url(#deepCore)"/>
        <circle cx="100" cy="100" r="62" fill="none" stroke="url(#deepRim)" stroke-width="6"/>
        <ellipse class="orb-spec" cx="82" cy="78" rx="20" ry="13" fill="rgba(255,255,255,0.28)"/>
      </g>

      <!-- bio-luminescent orbit rings (rotate as a group) -->
      <g class="orb-rings">
        <circle cx="100" cy="100" r="78" fill="none" stroke="rgba(0,229,255,0.30)" stroke-width="0.8"
                stroke-dasharray="2 7"/>
        <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(0,255,209,0.18)" stroke-width="0.6"
                stroke-dasharray="1 11"/>
      </g>`;

    host.appendChild(svg);
    // sit just above the (now-dim) yantra substrate, below HUD windows
    document.body.appendChild(host);

    turb = svg.querySelector("feTurbulence");
    disp = svg.querySelector("feDisplacementMap");
    gMorph = svg.querySelector(".orb-morph");
    ringGroup = svg.querySelector(".orb-rings");

    window.addEventListener("resize", place);
    raf = requestAnimationFrame(frame);
  }

  function place() {
    if (!host) return;
    const r = coreR();
    // orb visual radius ~ 5.4× the bindu radius → fills the old core ring nicely
    const size = Math.max(180, r * 11);
    host.style.width = host.style.height = size + "px";
    host.style.left = coreX() + "px";
    host.style.top = coreY() + "px";
  }

  function frame() {
    raf = requestAnimationFrame(frame);
    if (!host) return;
    place();

    const st = sysState();
    host.dataset.state = st;

    // ease the reactive energy toward the live drive
    const target = drive();
    energy += (target - energy) * 0.12;

    // per-state liquid behaviour
    let baseDisp, dRate, glow;
    if (st === "listening")      { baseDisp = 24; dRate = 0.06; glow = 0.55; }
    else if (st === "processing"){ baseDisp = 20; dRate = 0.045; glow = 0.42; }
    else if (st === "speaking")  { baseDisp = 18; dRate = 0.05; glow = 0.5; }
    else                         { baseDisp = 13; dRate = 0.018; glow = 0.3; }

    // empathic mood biases the liquid's tempo (calm slower, alert agitated)
    const mood = window.DeepMood || "calm";
    const moodRate = mood === "alert" ? 1.7 : mood === "warn" ? 1.3 : mood === "focus" ? 1.12 : 0.85;
    churn += dRate * moodRate;
    // displacement ripples with energy; a slow sine keeps it alive when idle
    const moodDisp = mood === "alert" ? 8 : mood === "warn" ? 4 : 0;
    const scaleVal = baseDisp + moodDisp + energy * 26 + Math.sin(churn * 1.7) * 2.5;
    if (disp) disp.setAttribute("scale", scaleVal.toFixed(1));

    // breathing + listening throb on the morph body
    const breathe = 1 + Math.sin(churn * 0.9) * 0.035 + energy * 0.14;
    if (gMorph) gMorph.setAttribute("transform", `translate(100 100) scale(${breathe.toFixed(3)}) translate(-100 -100)`);

    // thinking rotates the orbit rings faster
    rot += (st === "processing" ? 0.5 : 0.12) + energy * 0.3;
    if (ringGroup) ringGroup.setAttribute("transform", `rotate(${rot.toFixed(2)} 100 100)`);

    // expose energy + glow to CSS for the outer halo
    host.style.setProperty("--orb-energy", energy.toFixed(3));
    host.style.setProperty("--orb-glow", (glow + energy * 0.4).toFixed(3));
  }

  function boot() {
    if (document.getElementById("deep-orb")) return;
    build();
    place();
    console.log("[DEEP] Liquid Intelligence Orb online ✓");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.DeepOrb = { el: () => host };
})();
