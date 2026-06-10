/* ============================================================================
 * DEEP COMMAND DECK — orbiting telemetry instruments
 * ----------------------------------------------------------------------------
 * Anchors a set of live glass readout modules around the yantra bindu and
 * draws containment beams from each instrument back to the core, turning the
 * whole screen into a spatial command deck. Modules track the bindu every
 * frame (reading ngCx / ngCy / orbTime from app.js) and refresh their values
 * from the real REST surface.
 *
 * Data sources:
 *   /api/status            -> active model / state
 *   /api/knowledge/stats   -> entities / relationships
 *   /api/agents/tasks      -> active agent tasks
 *   /api/security/status   -> devices / suspicious
 * ========================================================================== */
(function () {
  "use strict";

  function core() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }
  function clock() { return (typeof orbTime === "number") ? orbTime : performance.now() / 1000; }
  function minDim() { return Math.min(window.innerWidth, window.innerHeight); }

  // Instrument definitions. dx/dy are fractions of the smaller viewport dim,
  // measured from the bindu (y positive = downward). Positions sit in the
  // left/right bands, clear of the top status bar and the lower comms feed.
  const MODS = [
    { id: "core",   label: "Core",      dot: "ok",   dx: -0.47, dy: -0.12 },
    { id: "memory", label: "Memory",    dot: "cyan", dx: -0.40, dy: 0.17 },
    { id: "agents", label: "Agents",    dot: "",     dx: 0.40,  dy: -0.12 },
    { id: "shield", label: "Security",  dot: "ok",   dx: 0.47,  dy: 0.17 },
  ];

  let layer, linkCanvas, lctx, lW = 0, lH = 0;
  const els = {};
  const hist = {};
  const SPARK_COLOR = { core: [232, 185, 116], memory: [120, 200, 255], agents: [220, 140, 185], shield: [120, 230, 180] };

  function build() {
    layer = document.createElement("div");
    layer.className = "deck-telemetry-layer";
    layer.id = "deckTelemetry";

    linkCanvas = document.createElement("canvas");
    linkCanvas.className = "deck-link-canvas";
    linkCanvas.id = "deckLinks";
    lctx = linkCanvas.getContext("2d");

    document.body.appendChild(linkCanvas);
    document.body.appendChild(layer);

    MODS.forEach((m) => {
      const el = document.createElement("div");
      el.className = "deck-mod";
      el.dataset.id = m.id;
      el.innerHTML =
        `<div class="deck-mod-key"><span class="deck-mod-dot ${m.dot}"></span>${m.label}</div>
         <div class="deck-mod-val" data-f="val">—</div>
         <div class="deck-mod-sub" data-f="sub">connecting…</div>
         <canvas class="deck-mod-spark" data-f="spark"></canvas>`;
      layer.appendChild(el);
      els[m.id] = el;
      hist[m.id] = [];
      el._tilt = { rx: 0, ry: 0, tx: 0, ty: 0, lift: 0 };
      wireTilt(el);
      requestAnimationFrame(() => el.classList.add("show"));
    });

    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(frame);
  }

  // Pointer-tracked 3D tilt — the module leans toward the cursor and lifts, so
  // hovering an instrument makes it feel like a physical pane of holo-glass.
  function wireTilt(el) {
    const MAX = 9; // degrees
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) return;
      const px = (e.clientX - r.left) / r.width - 0.5;   // -0.5..0.5
      const py = (e.clientY - r.top) / r.height - 0.5;
      if (!isFinite(px) || !isFinite(py)) return;        // ignore malformed events
      el._tilt.ry = px * MAX * 2;
      el._tilt.rx = -py * MAX * 2;
      el._tilt.lift = 1;
      el.classList.add("tilt");
    });
    el.addEventListener("pointerleave", () => {
      el._tilt.rx = el._tilt.ry = 0;
      el._tilt.lift = 0;
      el.classList.remove("tilt");
    });
  }

  function resize() {
    lW = window.innerWidth; lH = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    linkCanvas.width = lW * dpr; linkCanvas.height = lH * dpr;
    linkCanvas.style.width = lW + "px"; linkCanvas.style.height = lH + "px";
    lctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function frame() {
    requestAnimationFrame(frame);
    if (!lctx) return;
    const { x, y } = core();
    const t = clock();
    const md = minDim();
    lctx.clearRect(0, 0, lW, lH);

    MODS.forEach((m, i) => {
      const el = els[m.id];
      if (!el) return;
      const breathe = 1 + Math.sin(t * 0.8 + i) * 0.02;
      let mx = x + m.dx * md * breathe;
      let my = y + m.dy * md * breathe;
      // keep instruments on-screen and clear of rails / comms feed
      mx = Math.max(96, Math.min(mx, lW - 96));
      my = Math.max(78, Math.min(my, lH - 150));
      el.style.left = mx + "px";
      el.style.top = my + "px";
      // ease the live tilt/lift toward its target for buttery motion
      const tl = el._tilt || (el._tilt = { rx: 0, ry: 0, tx: 0, ty: 0, lift: 0 });
      if (!isFinite(tl.rx) || !isFinite(tl.ry)) { tl.rx = tl.ry = 0; }
      if (!isFinite(tl.tx) || !isFinite(tl.ty)) { tl.tx = tl.ty = 0; }
      tl.tx += (tl.ry - tl.tx) * 0.18;
      tl.ty += (tl.rx - tl.ty) * 0.18;
      const liftZ = tl.lift ? 22 : 0;
      el.style.transform =
        `translate(-50%, -50%) perspective(700px) rotateX(${tl.ty.toFixed(2)}deg) rotateY(${tl.tx.toFixed(2)}deg) translateZ(${liftZ}px)`;

      // containment beam back to the bindu
      const grad = lctx.createLinearGradient(x, y, mx, my);
      grad.addColorStop(0, "rgba(232,185,116,0.02)");
      grad.addColorStop(1, "rgba(232,185,116,0.22)");
      lctx.strokeStyle = grad;
      lctx.lineWidth = 1;
      lctx.beginPath(); lctx.moveTo(x, y); lctx.lineTo(mx, my); lctx.stroke();
      // travelling packet
      const p = (t * 0.35 + i * 0.25) % 1;
      const px = x + (mx - x) * p, py = y + (my - y) * p;
      lctx.fillStyle = "rgba(232,185,116,0.6)";
      lctx.beginPath(); lctx.arc(px, py, 1.8, 0, Math.PI * 2); lctx.fill();
    });
  }

  function set(id, val, sub) {
    const el = els[id]; if (!el) return;
    el.querySelector('[data-f="val"]').innerHTML = val;
    el.querySelector('[data-f="sub"]').textContent = sub;
  }
  function dot(id, level) {
    const el = els[id]; if (!el) return;
    const d = el.querySelector(".deck-mod-dot");
    if (d) d.className = "deck-mod-dot " + level;
  }

  // push a numeric sample and redraw the module's mini line-chart
  function spark(id, num) {
    if (num == null || isNaN(num)) return;
    const arr = hist[id] || (hist[id] = []);
    arr.push(Number(num));
    if (arr.length > 40) arr.shift();
    const el = els[id]; if (!el) return;
    const cv = el.querySelector('[data-f="spark"]'); if (!cv) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth || 130, h = cv.clientHeight || 18;
    if (cv.width !== w * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
    const c = cv.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    if (arr.length < 2) return;
    const mn = Math.min(...arr), mx = Math.max(...arr), rng = (mx - mn) || 1;
    const [r, g, b] = SPARK_COLOR[id] || [232, 185, 116];
    const xs = (i) => (i / (arr.length - 1)) * w;
    const ys = (v) => h - 2 - ((v - mn) / rng) * (h - 4);
    // area fill
    const grad = c.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, `rgba(${r},${g},${b},0.28)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
    c.fillStyle = grad;
    c.beginPath(); c.moveTo(0, h);
    arr.forEach((v, i) => c.lineTo(xs(i), ys(v)));
    c.lineTo(w, h); c.closePath(); c.fill();
    // line
    c.strokeStyle = `rgba(${r},${g},${b},0.9)`; c.lineWidth = 1.3;
    c.beginPath(); arr.forEach((v, i) => i ? c.lineTo(xs(i), ys(v)) : c.moveTo(xs(i), ys(v))); c.stroke();
    // head dot
    c.fillStyle = `rgba(255,250,240,0.95)`;
    c.beginPath(); c.arc(xs(arr.length - 1), ys(arr[arr.length - 1]), 1.8, 0, Math.PI * 2); c.fill();
  }

  async function refresh() {
    // Core / model
    try {
      const d = await (await fetch("/api/status")).json();
      const model = d.model || "DEEP";
      const state = d.brain || d.deep || "online";
      const lat = d.latency_ms != null ? ` · ${Math.round(d.latency_ms)}ms` : "";
      set("core", String(model).split(":")[0], String(state).toUpperCase() + lat);
      dot("core", (state === "ok" || state === "online") ? "ok" : "warn");
      spark("core", d.latency_ms != null ? d.latency_ms : (parseFloat((document.getElementById("tokens") || {}).textContent) || 0));
    } catch (_) { set("core", "DEEP", "offline"); dot("core", "warn"); }

    // Memory graph
    try {
      const d = await (await fetch("/api/knowledge/stats")).json();
      set("memory", (d.entities ?? 0), `${d.relationships ?? 0} links`);
      spark("memory", d.entities ?? 0);
    } catch (_) { set("memory", "—", "unavailable"); }

    // Agents
    try {
      const d = await (await fetch("/api/agents/tasks")).json();
      const tasks = d.tasks || [];
      const active = tasks.filter((t) => (t.status || "running") === "running").length;
      set("agents", active, `${tasks.length} total`);
      dot("agents", active > 0 ? "warn" : "ok");
      spark("agents", tasks.length);
    } catch (_) { set("agents", "0", "idle"); }

    // Security
    try {
      const d = await (await fetch("/api/security/status")).json();
      const s = d.summary || {};
      const susp = s.suspicious || 0;
      set("shield", `${s.total ?? 0}<small> dev</small>`, susp > 0 ? `${susp} suspicious` : "all clear");
      dot("shield", susp > 0 ? "alert" : "ok");
      spark("shield", s.total ?? 0);
    } catch (_) { set("shield", "—", "scanning"); }
  }

  function boot() {
    build();
    refresh();
    setInterval(refresh, 5000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  console.log("[DEEP] Command Deck telemetry initialised ✓");
})();
