/* ============================================================================
 * DEEP — MOTION SYSTEM (runtime)
 * ----------------------------------------------------------------------------
 * Pairs with deep-motion.css. Provides:
 *   • Calm / reduced-motion mode (persisted; honours prefers-reduced-motion;
 *     toggle with Ctrl+Alt+M or window.DeepMotion.toggleCalm()).
 *   • Delegated click ripples on interactive HUD chrome.
 *   • window.DeepMotion.countUp(el, value, opts) — eased number tweening with a
 *     value-change pulse, used by other modules for live stats.
 * Classic script. Safe no-ops if elements are absent.
 * ========================================================================== */
(function () {
  "use strict";

  const KEY = "deep_calm";

  // ── Calm / reduced-motion mode ────────────────────────────────────────────
  function applyCalm(on) {
    document.documentElement.dataset.calm = on ? "1" : "";
    window.__deepCalm = !!on;
  }
  function initCalm() {
    let on = false;
    try {
      const saved = localStorage.getItem(KEY);
      on = saved != null ? saved === "1"
        : (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (_) {}
    applyCalm(on);
  }
  function setCalm(on) { applyCalm(on); try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (_) {} }
  function toggleCalm() { setCalm(!window.__deepCalm); try { window.SFX && SFX.play("blip"); } catch (_) {} }

  // ── Delegated click ripple ────────────────────────────────────────────────
  const RIPPLE_SEL = ".sci-icbtn,.sci-chip,.sci-seg,.sci-fnadd,.hud-btn,.sr-ack,.hud-bar-btn";
  document.addEventListener("pointerdown", (e) => {
    if (window.__deepCalm) return;
    const t = e.target.closest && e.target.closest(RIPPLE_SEL);
    if (!t) return;
    const r = t.getBoundingClientRect();
    if (!r.width) return;
    t.classList.add("dpx-rippling");
    const size = Math.max(r.width, r.height) * 1.7;
    const s = document.createElement("span");
    s.className = "dpx-ripple";
    s.style.width = s.style.height = size + "px";
    s.style.left = (e.clientX - r.left) + "px";
    s.style.top = (e.clientY - r.top) + "px";
    t.appendChild(s);
    setTimeout(() => s.remove(), 580);
  }, true);

  // ── Eased count-up with value-change pulse ────────────────────────────────
  function countUp(el, to, opts) {
    if (!el) return;
    opts = opts || {};
    const dec = opts.dec || 0, prefix = opts.prefix || "", suffix = opts.suffix || "";
    const fmt = (v) => prefix + (dec ? v.toFixed(dec) : Math.round(v).toLocaleString()) + suffix;
    const from = parseFloat(String(el.textContent).replace(/[^0-9.\-]/g, "")) || 0;
    if (window.__deepCalm || from === to || !isFinite(to)) {
      el.textContent = fmt(to);
      return;
    }
    const dur = opts.dur || 700, t0 = performance.now();
    (function step(t) {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(from + (to - from) * e);
      if (k < 1) requestAnimationFrame(step);
      else { el.textContent = fmt(to); el.classList.remove("dpx-bump"); void el.offsetWidth; el.classList.add("dpx-bump"); }
    })(t0);
  }

  // ── Skeletonize / unskeletonize a loading element ─────────────────────────
  function skeleton(el, on) { if (el) el.classList.toggle("dpx-skel", on !== false); }

  // ── Keyboard shortcut: Ctrl+Alt+M toggles calm mode ───────────────────────
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.altKey && (e.key === "m" || e.key === "M")) {
      e.preventDefault(); toggleCalm();
    }
  });

  // ── Ambient aurora (depth) ────────────────────────────────────────────────
  function mountAurora() {
    if (document.querySelector(".deep-aurora")) return;
    const a = document.createElement("div");
    a.className = "deep-aurora";
    a.setAttribute("aria-hidden", "true");
    (document.body || document.documentElement).appendChild(a);
  }

  // ── Pointer parallax (sets --px/--py on :root, eased) ─────────────────────
  function initParallax() {
    let px = 0, py = 0, tx = 0, ty = 0, raf = 0;
    function tick() {
      raf = 0;
      tx += (px - tx) * 0.08; ty += (py - ty) * 0.08;
      const root = document.documentElement.style;
      root.setProperty("--px", tx.toFixed(3));
      root.setProperty("--py", ty.toFixed(3));
      if (Math.abs(px - tx) > 0.001 || Math.abs(py - ty) > 0.001) raf = requestAnimationFrame(tick);
    }
    window.addEventListener("pointermove", (e) => {
      if (window.__deepCalm) return;
      px = e.clientX / window.innerWidth - 0.5;
      py = e.clientY / window.innerHeight - 0.5;
      if (!raf) raf = requestAnimationFrame(tick);
    }, { passive: true });
  }

  // ── Magnetic hover on chrome controls ─────────────────────────────────────
  function initMagnetic() {
    const SEL = ".hud-dock-btn,.cmd-send,.sb-icon-btn,.cmd-icon";
    let last = null;
    document.addEventListener("pointermove", (e) => {
      if (window.__deepCalm) { if (last) { last.style.transform = ""; last = null; } return; }
      const el = e.target.closest && e.target.closest(SEL);
      if (last && last !== el) { last.style.transform = ""; last = null; }
      if (!el) return;
      const r = el.getBoundingClientRect();
      if (!r.width) return;
      const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
      const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
      if (!isFinite(dx) || !isFinite(dy)) return;
      el.style.transform = `translate(${(dx * 6).toFixed(1)}px, ${(dy * 6 - 2).toFixed(1)}px) scale(1.08)`;
      last = el;
    }, { passive: true });
    document.addEventListener("pointerleave", () => { if (last) { last.style.transform = ""; last = null; } }, true);
  }

  initCalm();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountAurora);
  else mountAurora();
  initParallax();
  initMagnetic();
  window.DeepMotion = { countUp, skeleton, setCalm, toggleCalm, mountAurora, get calm() { return !!window.__deepCalm; } };
  console.log("[DEEP] Motion system online ✓  (Ctrl+Alt+M = calm mode · aurora + parallax + magnetic)");
})();
