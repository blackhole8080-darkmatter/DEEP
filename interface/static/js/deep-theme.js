/* ============================================================================
 * DEEP — SKIN TOGGLE  (Abyssal ⇄ Gold)
 * ----------------------------------------------------------------------------
 * Flips between the abyssal DEEP identity (deep-abyssal.css + Liquid Orb) and
 * the original temple-gold yantra. Works by enabling/disabling the abyssal
 * stylesheet and showing/hiding the orb — the gold yantra + gold HUD vars are
 * the natural fallback once the abyssal overrides are gone. Persists to
 * localStorage('deep_skin'); a no-FOUC preflight in <head> applies it pre-paint.
 * ========================================================================== */
(function () {
  "use strict";

  var KEY = "deep_skin";
  function saved() { try { return localStorage.getItem(KEY) || "abyssal"; } catch (_) { return "abyssal"; } }
  function store(s) { try { localStorage.setItem(KEY, s); } catch (_) {} }

  function apply(skin) {
    skin = (skin === "gold") ? "gold" : "abyssal";
    document.documentElement.dataset.skin = skin;

    var link = document.getElementById("skin-abyssal");
    if (link) link.disabled = (skin === "gold");

    var orb = document.getElementById("deep-orb");
    if (orb) orb.style.display = (skin === "gold") ? "none" : "";

    // reflect on the button (filled half-moon points to the *active* side)
    var btn = document.getElementById("skinBtn");
    if (btn) btn.title = "Skin: " + (skin === "gold" ? "Gold" : "Abyssal") + " — click to switch";

    document.title = (skin === "gold")
      ? "DEEP — Neural Intelligence"
      : "DEEP — Abyssal Intelligence";

    window.__deepSkin = skin;
  }

  function toggle() {
    var next = (saved() === "gold") ? "abyssal" : "gold";
    store(next);
    apply(next);
    try { window.SFX && SFX.play("toggle"); } catch (_) {}
  }

  function boot() { apply(saved()); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.DeepTheme = { toggle: toggle, apply: apply, current: saved };
  console.log("[DEEP] Skin toggle ready ✓");
})();
