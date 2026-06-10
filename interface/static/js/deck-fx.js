/* ============================================================================
 * DEEP DECK FX — futuristic effects engine
 * ----------------------------------------------------------------------------
 * A single full-screen additive overlay (above the yantra graph, below the HUD
 * windows) driven by the system's real activity. Effects are organised into
 * "sets" that share one canvas + one rAF loop for performance.
 *
 *   SET 1 — Subsystem spokes + orbiting event comets
 *           Amplified energy beams from the bindu to each subsystem petal, plus
 *           comets that fire along a beam whenever that subsystem emits a real
 *           event (hooked off the global ngActivate, which app.js calls with a
 *           large amplitude on every /debug/events tick).
 *
 * Reads shared globals from app.js: ngCx, ngCy, ngCoreR, orbTime, NG_NODES,
 * ngAccent, ngCore, ngActivate.
 * ========================================================================== */
(function () {
  "use strict";

  // ── Shared overlay canvas + loop ──────────────────────────────────────────
  let canvas, ctx, W = 0, H = 0, last = performance.now();
  const layers = [];   // { update(dt), draw() }

  function core() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }
  function coreR() { return (typeof ngCoreR === "number" && ngCoreR) || 26; }
  function clock() { return (typeof orbTime === "number") ? orbTime : performance.now() / 1000; }
  function nodes() { return (typeof NG_NODES !== "undefined" && Array.isArray(NG_NODES)) ? NG_NODES : []; }
  function nodeById(id) { return nodes().find((n) => n.id === id) || null; }

  function init() {
    canvas = document.createElement("canvas");
    canvas.id = "deck-fx-canvas";
    canvas.style.cssText = "position:fixed;top:0;left:0;z-index:4;pointer-events:none;display:block;";
    document.body.insertBefore(canvas, document.body.children[1] || null);
    ctx = canvas.getContext("2d");

    // SET 4 — atmosphere pass: CRT scanlines + reactive vignette bloom
    const atmos = document.createElement("div");
    atmos.className = "deck-atmos";
    atmos.innerHTML = `<div class="deck-scanlines"></div><div class="deck-vignette"></div><div class="deck-poweron"></div>`;
    document.body.appendChild(atmos);

    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(frame);
  }

  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function frame() {
    requestAnimationFrame(frame);
    if (!ctx) return;
    const now = performance.now();
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = "lighter";  // additive glow
    for (const L of layers) { try { L.update(dt); L.draw(); } catch (_) {} }
    ctx.globalCompositeOperation = "source-over";

    // drive the reactive vignette bloom from live core activity + comet flashes
    const act = (typeof ngCore !== "undefined" && ngCore) ? (ngCore.act || 0) : 0;
    const bloom = Math.min(1, act + coreFlash * 0.8);
    document.documentElement.style.setProperty("--deck-bloom", bloom.toFixed(3));
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SET 1 — Subsystem spokes + orbiting event comets
  // ═══════════════════════════════════════════════════════════════════════
  const comets = [];   // { node, t, speed, life }
  const pulses = [];   // { x, y, r, life, color }
  let coreFlash = 0;

  function spawnComet(id) {
    const n = nodeById(id);
    const { x, y } = core();
    if (n && n.x != null) {
      comets.push({ node: n, t: 0, speed: 1.05 + Math.random() * 0.35, color: n.color || ngAccent });
      pulses.push({ x: n.x, y: n.y, r: 6, life: 1, color: n.color || ngAccent });
    } else {
      // core-level event → ripple from the bindu
      pulses.push({ x, y, r: coreR(), life: 1, color: (typeof ngAccent !== "undefined" && ngAccent) || [232, 185, 116] });
    }
  }

  // Hook the global event activator. app.js calls ngActivate(id, ~0.85) on each
  // real event; small continuous activations (<0.5) are ignored so we only fire
  // comets on genuine subsystem events.
  function installHook() {
    if (typeof window.ngActivate !== "function") return setTimeout(installHook, 150);
    if (window.__deckFxHooked) return;
    const orig = window.ngActivate;
    window.ngActivate = function (id, amt) {
      orig.apply(this, arguments);
      if (id && amt != null && amt >= 0.5) {
        if (id === "core") { coreFlash = Math.min(1, coreFlash + 0.6); }
        else spawnComet(id);
      }
    };
    window.__deckFxHooked = true;
  }

  layers.push({
    update(dt) {
      const { x, y } = core();
      // advance comets toward the bindu
      for (let i = comets.length - 1; i >= 0; i--) {
        const c = comets[i];
        c.t += dt * c.speed;
        if (c.t >= 1) { coreFlash = Math.min(1, coreFlash + 0.5); comets.splice(i, 1); }
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.life -= dt * 1.6; p.r += dt * 90;
        if (p.life <= 0) pulses.splice(i, 1);
      }
      coreFlash = Math.max(0, coreFlash - dt * 1.4);
    },
    draw() {
      const { x, y } = core();
      const t = clock();
      const ns = nodes();

      // 1) Energized spokes — amplify whatever activity each petal carries.
      for (const n of ns) {
        if (n.x == null) continue;
        const act = Math.max(n.act || 0, n.exp || 0);
        if (act < 0.04) continue;
        const [r, g, b] = n.color || [232, 185, 116];
        const grad = ctx.createLinearGradient(x, y, n.x, n.y);
        grad.addColorStop(0, `rgba(${r},${g},${b},0)`);
        grad.addColorStop(0.5, `rgba(${r},${g},${b},${0.05 + act * 0.22})`);
        grad.addColorStop(1, `rgba(${r},${g},${b},${0.12 + act * 0.4})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 0.8 + act * 2.2;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(n.x, n.y); ctx.stroke();
      }

      // 2) Comets travelling petal → bindu, with a tapering tail.
      for (const c of comets) {
        const n = c.node;
        const [r, g, b] = c.color;
        const ease = c.t * c.t * (3 - 2 * c.t);       // smoothstep
        const hx = n.x + (x - n.x) * ease;
        const hy = n.y + (y - n.y) * ease;
        const TAIL = 7, dt2 = 0.045;
        for (let k = TAIL; k >= 0; k--) {
          const tt = Math.max(0, ease - k * dt2);
          const tx = n.x + (x - n.x) * tt;
          const ty = n.y + (y - n.y) * tt;
          const a = (1 - k / TAIL) * (1 - c.t * 0.3);
          ctx.fillStyle = `rgba(${r},${g},${b},${a * 0.5})`;
          ctx.beginPath(); ctx.arc(tx, ty, (1 - k / TAIL) * 2.6, 0, Math.PI * 2); ctx.fill();
        }
        // bright head + halo
        const halo = ctx.createRadialGradient(hx, hy, 0, hx, hy, 12);
        halo.addColorStop(0, `rgba(${r},${g},${b},0.9)`);
        halo.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = halo;
        ctx.beginPath(); ctx.arc(hx, hy, 12, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "rgba(255,250,240,0.95)";
        ctx.beginPath(); ctx.arc(hx, hy, 2.4, 0, Math.PI * 2); ctx.fill();
      }

      // 3) Petal-launch ripples.
      for (const p of pulses) {
        const [r, g, b] = p.color;
        ctx.strokeStyle = `rgba(${r},${g},${b},${p.life * 0.5})`;
        ctx.lineWidth = 1.4 * p.life;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke();
      }

      // 4) Core arrival flash — a burst when comets reach the bindu.
      if (coreFlash > 0.01) {
        const cr = coreR();
        const fl = ctx.createRadialGradient(x, y, 0, x, y, cr * 6 * (0.6 + coreFlash));
        fl.addColorStop(0, `rgba(255,240,210,${coreFlash * 0.5})`);
        fl.addColorStop(0.5, `rgba(232,185,116,${coreFlash * 0.22})`);
        fl.addColorStop(1, "rgba(232,185,116,0)");
        ctx.fillStyle = fl;
        ctx.beginPath(); ctx.arc(x, y, cr * 6 * (0.6 + coreFlash), 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = `rgba(255,244,224,${coreFlash * 0.6})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(x, y, cr * (2 + coreFlash * 2), 0, Math.PI * 2); ctx.stroke();
      }
    },
  });

  // ═══════════════════════════════════════════════════════════════════════
  // SET 2 — rotating tick-gauge (subsystem scanner) + core readout caption
  // ═══════════════════════════════════════════════════════════════════════
  let sweepAng = 0;
  const CAPTIONS = {
    brain: "REASONING", memory: "MEMORY · STORING", knowledge: "GRAPH · LINKING",
    research: "RESEARCH · INGEST", predictive: "PATTERN · LEARNING", agents: "AGENT · DISPATCH",
    security: "PERIMETER · SCAN", voice: "VOICE · CHANNEL", core: "CORE · PULSE",
  };
  let capEl = null, capText = "", capTarget = "ALL SYSTEMS NOMINAL", capShown = "", capTimer = 0, capHold = 0;

  function buildCaption() {
    capEl = document.createElement("div");
    capEl.id = "deck-core-caption";
    capEl.className = "deck-caption";
    capEl.innerHTML = `<span class="deck-cap-pip"></span><span class="deck-cap-txt"></span><span class="deck-cap-caret">▮</span>`;
    document.body.appendChild(capEl);
  }
  function setCaption(label) {
    if (!label || label === capTarget) { capHold = 4; return; }
    capTarget = label; capShown = ""; capTimer = 0; capHold = 4;
  }

  // radar gauge + caption layer
  layers.push({
    update(dt) {
      const act = (typeof ngCore !== "undefined" && ngCore) ? (ngCore.act || 0) : 0;
      sweepAng += dt * (0.25 + act * 1.1);

      // caption typewriter
      capHold -= dt;
      if (capShown.length < capTarget.length) {
        capTimer += dt;
        if (capTimer > 0.028) { capTimer = 0; capShown = capTarget.slice(0, capShown.length + 1); if (capEl) capEl.querySelector(".deck-cap-txt").textContent = capShown; }
      } else if (capHold <= 0 && capTarget !== "ALL SYSTEMS NOMINAL") {
        setCaption("ALL SYSTEMS NOMINAL");
      }
    },
    draw() {
      const { x, y } = core();
      const md = Math.min(W, H);
      const gR = md * 0.288;            // gauge radius, between mid & outer rings
      const [ar, ag, ab] = (typeof ngAccent !== "undefined" && ngAccent) || [232, 185, 116];

      // fine tick dial
      ctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},0.10)`;
      ctx.lineWidth = 1;
      for (let i = 0; i < 120; i++) {
        const a = (i / 120) * Math.PI * 2;
        const long = i % 10 === 0;
        const r0 = gR, r1 = gR + (long ? 6 : 3);
        ctx.beginPath();
        ctx.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0);
        ctx.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1);
        ctx.stroke();
      }

      // sweeping wedge (the scanner head trailing a fade)
      const span = 0.7;
      for (let s = 0; s < 14; s++) {
        const a = sweepAng - s * 0.05;
        const al = (1 - s / 14) * 0.10;
        ctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},${al})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x + Math.cos(a) * (md * 0.05), y + Math.sin(a) * (md * 0.05));
        ctx.lineTo(x + Math.cos(a) * gR, y + Math.sin(a) * gR);
        ctx.stroke();
      }
      // bright leading needle + node on the dial
      const hx = x + Math.cos(sweepAng) * gR, hy = y + Math.sin(sweepAng) * gR;
      ctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},0.45)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(hx, hy); ctx.stroke();
      const nd = ctx.createRadialGradient(hx, hy, 0, hx, hy, 7);
      nd.addColorStop(0, `rgba(255,244,224,0.9)`);
      nd.addColorStop(1, `rgba(${ar | 0},${ag | 0},${ab | 0},0)`);
      ctx.fillStyle = nd; ctx.beginPath(); ctx.arc(hx, hy, 7, 0, Math.PI * 2); ctx.fill();

      // position the DOM caption just below the bindu
      if (capEl) {
        const cy2 = y + md * 0.052 + 18;
        capEl.style.left = x + "px";
        capEl.style.top = cy2 + "px";
        capEl.classList.toggle("alert", (typeof window.Aegis !== "undefined" && window.Aegis.level === "alert"));
      }
    },
  });

  // feed captions from the same event stream (extend the hook installed in Set 1)
  function installCaptionFeed() {
    if (typeof window.ngActivate !== "function") return setTimeout(installCaptionFeed, 150);
    const prev = window.ngActivate;
    window.ngActivate = function (id, amt) {
      prev.apply(this, arguments);
      if (id && amt != null && amt >= 0.5) setCaption(CAPTIONS[id] || (id.toUpperCase() + " · ACTIVE"));
    };
  }

  // ── Boot ────────────────────────────────────────────────────────────────
  function boot() { init(); buildCaption(); installHook(); installCaptionFeed(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  // expose a manual trigger (useful for demos / other modules)
  window.DeckFX = { comet: spawnComet };
  console.log("[DEEP] Deck FX · Set 1 (spokes + event comets) initialised ✓");
})();
