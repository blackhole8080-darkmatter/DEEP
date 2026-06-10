/* ============================================================================
 * DEEP — WINDOW MANAGEMENT + PERFORMANCE
 * ----------------------------------------------------------------------------
 *   • LAYOUT MEMORY — remembers each HUD window's position/size and which were
 *     open, restoring them across reloads (wraps HUD.open; samples geometry).
 *   • TIDY — DeepWindows.tidy() arranges all open windows in a neat ring around
 *     the core (also on the palette + a hotkey).
 *   • PERF — pauses CSS animations while the tab is hidden (rAF is already
 *     throttled by the browser) to save battery.
 *
 * Non-invasive: never edits hud-core.js. Classic script.
 * ========================================================================== */
(function () {
  "use strict";

  var LKEY = "deep_win_layout";   // { id: {l,t,w,h} }
  var OKEY = "deep_win_open";      // [id, ...]

  function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (_) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} }

  var layout = load(LKEY, {});
  var restoring = false;

  function winEl(id) { return document.querySelector('.hud-win[data-app="' + CSS.escape(id) + '"]'); }

  function applySaved(id, el) {
    var g = layout[id];
    if (!g || !el) return;
    // clamp into viewport
    var w = Math.min(g.w || el.offsetWidth, window.innerWidth - 16);
    var h = Math.min(g.h || el.offsetHeight, window.innerHeight - 16);
    var l = Math.max(8, Math.min(g.l, window.innerWidth - 60));
    var t = Math.max(56, Math.min(g.t, window.innerHeight - 40));
    el.style.left = l + "px"; el.style.top = t + "px";
    if (g.w) el.style.width = w + "px";
    if (g.h) el.style.height = h + "px";
  }

  function sampleOpen() {
    var open = [];
    document.querySelectorAll(".hud-win").forEach(function (el) {
      if (el.classList.contains("minimized")) return;
      var id = el.dataset.app; if (!id) return;
      open.push(id);
      var r = el.getBoundingClientRect();
      layout[id] = { l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
    });
    save(LKEY, layout);
    save(OKEY, open);
  }

  function wrapHUD() {
    if (!window.HUD || !HUD.open) return setTimeout(wrapHUD, 120);
    var origOpen = HUD.open.bind(HUD);
    HUD.open = function (id) {
      var w = origOpen(id);
      if (w && w.el && !restoring) requestAnimationFrame(function () { applySaved(id, w.el); });
      return w;
    };

    // NOTE: we deliberately do NOT auto-reopen previously-open windows on load —
    // doing so stacked windows over the command bar / chat input. We only
    // remember each window's geometry and re-apply it when YOU open the window.

    setInterval(sampleOpen, 2500);
    window.addEventListener("beforeunload", sampleOpen);
  }

  /* ── TIDY: ring-arrange open windows around the core ─────────────────────── */
  function tidy() {
    var wins = [].slice.call(document.querySelectorAll(".hud-win")).filter(function (el) { return !el.classList.contains("minimized"); });
    if (!wins.length) return;
    var c = (window.HUD && HUD.coreCenter) ? HUD.coreCenter() : { x: innerWidth / 2, y: innerHeight * 0.46 };
    var R = Math.min(innerWidth, innerHeight) * 0.32;
    var n = wins.length;
    wins.forEach(function (el, i) {
      var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
      var w = el.offsetWidth, h = el.offsetHeight;
      var l = Math.max(8, Math.min(c.x + Math.cos(a) * R - w / 2, innerWidth - w - 8));
      var t = Math.max(56, Math.min(c.y + Math.sin(a) * R - h / 2, innerHeight - h - 8));
      el.style.transition = "left .5s cubic-bezier(.2,1,.3,1), top .5s cubic-bezier(.2,1,.3,1)";
      el.style.left = l + "px"; el.style.top = t + "px";
      setTimeout(function () { el.style.transition = ""; }, 600);
    });
    try { window.SFX && SFX.play("toggle"); } catch (_) {}
    setTimeout(sampleOpen, 700);
  }

  /* ── PERF: pause CSS animation while hidden ──────────────────────────────── */
  function visibility() {
    document.addEventListener("visibilitychange", function () {
      document.body.classList.toggle("deep-hidden", document.hidden);
    });
  }

  /* ── hotkey: Ctrl+Shift+T tidies ─────────────────────────────────────────── */
  function keys() {
    window.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.shiftKey && (e.key === "T" || e.key === "t")) { e.preventDefault(); tidy(); }
    });
  }

  function boot() { wrapHUD(); visibility(); keys(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.DeepWindows = { tidy: tidy, sample: sampleOpen, reset: function () { layout = {}; save(LKEY, {}); save(OKEY, []); } };
  console.log("[DEEP] Window manager online ✓");
})();
