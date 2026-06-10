/* ============================================================================
 * DEEP CORE MENU — radial command ring on the yantra bindu
 * ----------------------------------------------------------------------------
 * Replaces the old left nav rail. Clicking the living core (or pressing M) fans
 * a cockpit-style radial menu out of the bindu: views (Console / Chat / Neural),
 * the Memory Graph, the System panel and the agent swarm. Items arc around the
 * core, materialize with a spring stagger, and retract on select / Esc / blur.
 *
 * Reads shared globals from app.js: ngCx, ngCy, ngCoreR. Uses window.HUD,
 * window.setView, window.togglePanel, window.SFX when present.
 * ========================================================================== */
(function () {
  "use strict";

  function core() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }
  function coreR() { return (typeof ngCoreR === "number" && ngCoreR) || Math.min(window.innerWidth, window.innerHeight) * 0.04; }

  // Menu items — arced across the upper hemisphere so they clear the comms feed.
  const ITEMS = [
    { id: "console", label: "Console", svg: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>', act: () => window.setView && setView("console") },
    { id: "chat",    label: "Chat",    svg: '<path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 17 0z"/>', act: () => window.setView && setView("chat") },
    { id: "neural",  label: "Neural",  svg: '<circle cx="5" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="12" cy="12" r="2.4"/><circle cx="19" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6.6l3 4M7 17.4l3-4M14 11l3-4M14 13l3 4"/>', act: () => window.setView && setView("neural") },
    { id: "memory",  label: "Memory",  svg: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="3" r="1.4" fill="currentColor"/><circle cx="20" cy="16" r="1.2" fill="currentColor"/>', act: () => window.HUD && HUD.open("memory-ring") },
    { id: "system",  label: "System",  svg: '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>', act: () => window.togglePanel && togglePanel() },
    { id: "swarm",   label: "Swarm",   svg: '<circle cx="12" cy="5" r="2.2"/><circle cx="5" cy="17" r="2.2"/><circle cx="19" cy="17" r="2.2"/><path d="M12 7.2v3M10.5 14l-3 1.5M13.5 14l3 1.5"/>', act: () => window.toggleAgentSwarm && toggleAgentSwarm() },
  ];

  let layer, hint, open = false;

  function build() {
    layer = document.createElement("div");
    layer.className = "core-menu";
    layer.id = "coreMenu";
    layer.setAttribute("aria-hidden", "true");

    ITEMS.forEach((it) => {
      const b = document.createElement("button");
      b.className = "core-menu-item";
      b.dataset.id = it.id;
      b.innerHTML =
        `<span class="cm-glyph"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">${it.svg}</svg></span>
         <span class="cm-label">${it.label}</span>`;
      b.addEventListener("click", (e) => { e.stopPropagation(); it.act(); close(); });
      layer.appendChild(b);
    });

    // small affordance ring drawn at the core so users discover the gesture
    hint = document.createElement("div");
    hint.className = "core-menu-hint";
    hint.id = "coreMenuHint";
    hint.title = "Command menu (M)";

    document.body.appendChild(hint);
    document.body.appendChild(layer);

    positionHint();
    window.addEventListener("resize", positionHint);
    requestAnimationFrame(tickHint);
  }

  // keep the discovery ring glued to the live bindu
  function positionHint() { /* handled per-frame in tickHint */ }
  function tickHint() {
    requestAnimationFrame(tickHint);
    if (!hint || open) { if (hint) hint.style.opacity = "0"; return; }
    const { x, y } = core();
    const r = coreR();
    hint.style.left = x + "px";
    hint.style.top = y + "px";
    hint.style.width = hint.style.height = (r * 3.4) + "px";
    hint.style.opacity = "1";
  }

  function layout() {
    const { x, y } = core();
    const R = Math.min(window.innerWidth, window.innerHeight) * 0.17;
    const n = ITEMS.length;
    // fan across the top arc: from ~200° to ~340° (upper hemisphere, screen coords)
    const a0 = Math.PI * 1.18, a1 = Math.PI * 1.82;
    [...layer.children].forEach((el, i) => {
      const a = a0 + (a1 - a0) * (n === 1 ? 0.5 : i / (n - 1));
      const px = x + Math.cos(a) * R;
      const py = y + Math.sin(a) * R;
      el.style.left = px + "px";
      el.style.top = py + "px";
      el.style.transitionDelay = (open ? i * 34 : (n - i) * 18) + "ms";
    });
  }

  function show() {
    open = true;
    layout();
    layer.classList.add("open");
    layer.setAttribute("aria-hidden", "false");
    document.body.classList.add("core-menu-active");
    window.SFX && SFX.play("open");
    const first = layer.querySelector(".core-menu-item");
    if (first) setTimeout(() => first.focus(), 60);   // a11y: focus into menu
  }
  function focusStep(dir) {
    const items = [...layer.querySelectorAll(".core-menu-item")];
    if (!items.length) return;
    const cur = items.indexOf(document.activeElement);
    items[(cur + dir + items.length) % items.length].focus();
  }
  function close() {
    if (!open) return;
    open = false;
    layout();
    layer.classList.remove("open");
    layer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("core-menu-active");
    window.SFX && SFX.play("close");
  }
  function toggle() { open ? close() : show(); }

  // ── Gesture detection: click the core (on empty background) opens the menu ──
  function onBackground(t) {
    return t === document.body ||
      (t && (t.id === "deep-graph-canvas" || t.id === "memory-ring-canvas" ||
             t.id === "deck-fx-canvas" || t.id === "aegis-canvas" || t.id === "orb-container"));
  }
  function nearCore(mx, my) {
    const { x, y } = core();
    return Math.hypot(mx - x, my - y) < coreR() * 2.4;
  }

  function wire() {
    // capture-phase so we beat the graph canvas, but yield to the memory ring band
    window.addEventListener("click", (e) => {
      if (open && !e.target.closest(".core-menu-item")) { close(); return; }
      if (onBackground(e.target) && nearCore(e.clientX, e.clientY)) {
        e.stopPropagation(); e.preventDefault();
        toggle();
      }
    }, true);

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && open) { close(); return; }
      if (open && (e.key === "ArrowRight" || e.key === "ArrowDown")) { e.preventDefault(); focusStep(1); return; }
      if (open && (e.key === "ArrowLeft" || e.key === "ArrowUp")) { e.preventDefault(); focusStep(-1); return; }
      if ((e.key === "m" || e.key === "M") && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = (document.activeElement && document.activeElement.tagName) || "";
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        e.preventDefault(); toggle();
      }
    });
  }

  function boot() { build(); wire(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.CoreMenu = { open: show, close, toggle };
  console.log("[DEEP] Core radial menu initialised ✓");
})();
