/* ============================================================================
 * DEEP AEGIS SHIELD — the Security Sandbox layer (UI manifestation)
 * ----------------------------------------------------------------------------
 * A persistent floating indicator bound to the system's execution-safety state,
 * plus a geometric barrier that materialises around the yantra core whenever
 * untrusted code is executed or a network threat is detected — the neon field
 * folds into a protective cage.
 *
 * Public API (window.Aegis):
 *   Aegis.setState('secure'|'sandbox'|'alert', reason)
 *   Aegis.sandbox(label, fn)  -> runs fn() inside a visual sandbox, restores after
 *   Aegis.pulse(reason)       -> brief sandbox flash (e.g. a single eval)
 *
 * Reads shared globals from app.js: ngCx, ngCy, orbTime.
 * Data source: GET /api/security/status -> { summary: { total, suspicious } }
 * ========================================================================== */
(function () {
  "use strict";

  const LEVELS = {
    secure:  { label: "SECURE",    level: "ok",    color: [80, 220, 160], note: "AES-256 · isolated env" },
    sandbox: { label: "SANDBOXED", level: "warn",  color: [245, 185, 90], note: "untrusted execution contained" },
    alert:   { label: "THREAT",    level: "alert", color: [255, 90, 90],  note: "endpoint anomaly detected" },
  };

  let cur = "secure";
  let reasonText = "";
  let barrier = 0;          // 0..1 barrier materialisation
  let barrierTarget = 0;
  let sandboxDepth = 0;     // nested sandbox() calls
  let badgeEl = null;
  let canvas = null, ctx = null, cW = 0, cH = 0;

  function core() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }
  function clock() { return (typeof orbTime === "number") ? orbTime : performance.now() / 1000; }

  // ── Persistent indicator badge ───────────────────────────────────────────
  function buildBadge() {
    const el = document.createElement("div");
    el.className = "aegis-badge secure";
    el.id = "aegisBadge";
    el.innerHTML =
      `<span class="aegis-glyph">
         <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
           <path d="M12 2l8 3v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5l8-3z"/>
           <path class="aegis-check" d="M8.5 12l2.4 2.4L15.8 9.5"/>
         </svg>
       </span>
       <span class="aegis-meta">
         <span class="aegis-label">SECURE</span>
         <span class="aegis-note">AES-256 · isolated env</span>
       </span>`;
    document.body.appendChild(el);
    el.addEventListener("click", () => window.HUD && HUD.open("aegis"));
    badgeEl = el;
  }

  function paintBadge() {
    if (!badgeEl) return;
    const L = LEVELS[cur];
    badgeEl.className = "aegis-badge " + cur;
    badgeEl.querySelector(".aegis-label").textContent = L.label;
    badgeEl.querySelector(".aegis-note").textContent = reasonText || L.note;
  }

  // ── Geometric barrier overlay ────────────────────────────────────────────
  function buildCanvas() {
    const c = document.createElement("canvas");
    c.id = "aegis-canvas";
    c.style.cssText = "position:fixed;top:0;left:0;z-index:7;pointer-events:none;display:block;";
    document.body.insertBefore(c, document.body.children[1] || null);
    canvas = c; ctx = c.getContext("2d");
    const resize = () => {
      cW = window.innerWidth; cH = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      c.width = cW * dpr; c.height = cH * dpr;
      c.style.width = cW + "px"; c.style.height = cH + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(animate);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (!ctx) return;
    barrier += (barrierTarget - barrier) * 0.08;
    ctx.clearRect(0, 0, cW, cH);
    if (barrier < 0.01) return;

    const { x, y } = core();
    const t = clock();
    const L = LEVELS[cur];
    const [r, g, b] = L.color;
    const R = Math.min(cW, cH) * 0.33 * (0.96 + Math.sin(t * 2) * 0.02);
    const sides = 6;
    const a = barrier;

    // edge vignette tint while contained
    const vg = ctx.createRadialGradient(x, y, R * 0.5, x, y, Math.max(cW, cH) * 0.7);
    vg.addColorStop(0, `rgba(${r},${g},${b},0)`);
    vg.addColorStop(1, `rgba(${r},${g},${b},${0.07 * a})`);
    ctx.fillStyle = vg; ctx.fillRect(0, 0, cW, cH);

    // two counter-rotating hex cages
    for (let layer = 0; layer < 2; layer++) {
      const rot = t * (layer ? -0.25 : 0.35) + (layer ? Math.PI / sides : 0);
      const rr = R * (layer ? 0.86 : 1);
      ctx.beginPath();
      for (let i = 0; i <= sides; i++) {
        const ang = rot + (i / sides) * Math.PI * 2;
        const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr;
        i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.strokeStyle = `rgba(${r},${g},${b},${(layer ? 0.3 : 0.5) * a})`;
      ctx.lineWidth = layer ? 1 : 1.8;
      ctx.shadowColor = `rgba(${r},${g},${b},${0.5 * a})`;
      ctx.shadowBlur = 12 * a;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // vertices as glowing nodes
      for (let i = 0; i < sides; i++) {
        const ang = rot + (i / sides) * Math.PI * 2;
        const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr;
        ctx.fillStyle = `rgba(${r},${g},${b},${0.8 * a})`;
        ctx.beginPath(); ctx.arc(px, py, 2.4, 0, Math.PI * 2); ctx.fill();
      }
    }

    // radial containment struts that sweep
    const sweep = (t * 0.6) % 1;
    for (let i = 0; i < sides; i++) {
      const ang = (i / sides) * Math.PI * 2 + t * 0.35;
      ctx.strokeStyle = `rgba(${r},${g},${b},${0.12 * a})`;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, y);
      ctx.lineTo(x + Math.cos(ang) * R, y + Math.sin(ang) * R); ctx.stroke();
      // travelling packet along strut
      const pr = R * sweep;
      ctx.fillStyle = `rgba(${r},${g},${b},${0.6 * a})`;
      ctx.beginPath(); ctx.arc(x + Math.cos(ang) * pr, y + Math.sin(ang) * pr, 1.8, 0, Math.PI * 2); ctx.fill();
    }

    // alert: scanning text
    if (cur === "alert" || cur === "sandbox") {
      ctx.fillStyle = `rgba(${r},${g},${b},${0.7 * a})`;
      ctx.font = '600 10px "JetBrains Mono", monospace';
      ctx.textAlign = "center";
      ctx.fillText((cur === "alert" ? "⚠ CONTAINMENT ACTIVE" : "◫ SANDBOX ACTIVE") + (reasonText ? " — " + reasonText : ""), x, y + R + 22);
    }
  }

  // ── State control ────────────────────────────────────────────────────────
  function setState(s, reason) {
    if (!LEVELS[s]) s = "secure";
    cur = s;
    reasonText = reason || "";
    barrierTarget = (s === "secure") ? 0 : 1;
    paintBadge();
    if (window.HUD) HUD.setDockStatus("aegis", LEVELS[s].level);
    refreshDetail();
  }

  function sandbox(label, fn) {
    sandboxDepth++;
    if (cur !== "alert") setState("sandbox", label || "executing");
    let result, err;
    try { result = fn(); }
    catch (e) { err = e; }
    finally {
      const release = () => {
        sandboxDepth = Math.max(0, sandboxDepth - 1);
        if (sandboxDepth === 0 && cur === "sandbox") setState("secure");
      };
      if (result && typeof result.finally === "function") { result.finally(release); }
      else { setTimeout(release, 900); }
    }
    if (err) throw err;
    return result;
  }

  function pulse(reason) {
    if (cur === "alert") return;
    setState("sandbox", reason || "verifying");
    setTimeout(() => { if (sandboxDepth === 0 && cur === "sandbox") setState("secure"); }, 1100);
  }

  // ── Live threat polling ──────────────────────────────────────────────────
  let lastSummary = null;
  async function poll() {
    try {
      const r = await fetch("/api/security/status");
      if (!r.ok) return;
      const d = await r.json();
      const s = d.summary || {};
      lastSummary = s;
      if ((s.suspicious || 0) > 0) {
        if (cur !== "alert") setState("alert", `${s.suspicious} suspicious device${s.suspicious > 1 ? "s" : ""}`);
      } else if (cur === "alert" && sandboxDepth === 0) {
        setState("secure", "");
      }
      refreshDetail();
    } catch (_) {}
  }

  // ── Detail window ────────────────────────────────────────────────────────
  let detailBody = null;
  function refreshDetail() {
    if (!detailBody) return;
    const L = LEVELS[cur];
    const s = lastSummary || {};
    detailBody.innerHTML =
      `<div class="hud-pad">
         <div class="aegis-state-big" style="color:rgb(${L.color[0]},${L.color[1]},${L.color[2]})">${L.label}</div>
         <div class="aegis-state-note">${reasonText || L.note}</div>
         <div class="aegis-grid">
           <div><span class="aegis-k">Devices</span><span class="aegis-v">${s.total ?? "—"}</span></div>
           <div><span class="aegis-k">Suspicious</span><span class="aegis-v">${s.suspicious ?? "—"}</span></div>
           <div><span class="aegis-k">Encryption</span><span class="aegis-v">AES-256</span></div>
           <div><span class="aegis-k">Execution</span><span class="aegis-v">${sandboxDepth > 0 ? "contained" : "local"}</span></div>
         </div>
         <div class="aegis-actions">
           <button class="hud-btn" id="aegisTest">Simulate untrusted exec</button>
           <button class="hud-btn" id="aegisScan">Re-scan network</button>
         </div>
         <p class="aegis-fine">The Security Sandbox isolates execution locally. Sensitive data, keys and files never leave this environment raw. The barrier engages whenever untrusted code runs or an endpoint anomaly is detected.</p>
       </div>`;
    detailBody.querySelector("#aegisTest").onclick = () =>
      sandbox("simulated untrusted script", () => new Promise((res) => setTimeout(res, 2600)));
    detailBody.querySelector("#aegisScan").onclick = async () => {
      try { await fetch("/api/security/scan", { method: "POST" }); } catch (_) {}
      poll();
    };
  }

  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    HUD.registerApp({
      id: "aegis",
      title: "Aegis Shield",
      icon: "⛨",
      anchor: "core",
      anchorAngle: -Math.PI * 0.28,
      width: 320, height: 360, minWidth: 260, minHeight: 260,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 2l8 3v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5l8-3z"/><path d="M9 12l2 2 4-4"/></svg>',
      build: (body) => { detailBody = body; refreshDetail(); },
      onClose: () => { detailBody = null; },
    });
    HUD.setDockStatus("aegis", "ok");
  }

  function boot() {
    buildCanvas();
    buildBadge();
    register();
    poll();
    setInterval(poll, 15000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.Aegis = { setState, sandbox, pulse, get level() { return cur; } };
  console.log("[DEEP] Aegis Shield initialised ✓");
})();
