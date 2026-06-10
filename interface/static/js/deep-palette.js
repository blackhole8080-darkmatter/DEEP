/* ============================================================================
 * DEEP — COMMAND PALETTE EXTENSIONS
 * ----------------------------------------------------------------------------
 * app.js already ships a Ctrl+K palette (PALETTE_COMMANDS + openCommandPalette).
 * Rather than duplicate it, we (1) register the new HUD apps + skin/briefing
 * actions into the shared PALETTE_COMMANDS array, and (2) upgrade matching with
 * fuzzy subsequence scoring and live "jump to memory entity" results.
 *
 * Classic script — shares app.js's global lexical scope (PALETTE_COMMANDS,
 * renderPalette, _paletteFiltered, escapeHtml, runPaletteItem).
 * ========================================================================== */
(function () {
  "use strict";

  const EXTRA = [
    { icon: "✲", label: "Open Neural Memory", cat: "intel", run: () => window.HUD && HUD.open("memory-ring") },
    { icon: "☉", label: "Open About You (what DEEP knows)", cat: "intel", run: () => window.HUD && HUD.open("about") },
    { icon: "❑", label: "Open Documents (your files)", cat: "intel", run: () => window.HUD && HUD.open("documents") },
    { icon: "≈", label: "Open Research Feed", cat: "intel", run: () => window.HUD && HUD.open("research") },
    { icon: "◬", label: "Open Threat · Anomaly console", cat: "security", run: () => window.HUD && HUD.open("threat") },
    { icon: "❖", label: "Open Evolution Lab", cat: "system", run: () => window.HUD && HUD.open("evolution") },
    { icon: "◎", label: "Open Proximity sensor", cat: "network", run: () => window.HUD && HUD.open("proximity") },
    { icon: "⛓", label: "Open Audit Ledger", cat: "security", run: () => window.HUD && HUD.open("audit") },
    { icon: "✓", label: "Open Approval Queue", cat: "system", run: () => window.HUD && HUD.open("approvals") },
    { icon: "◐", label: "Toggle skin (Abyssal / Gold)", cat: "ui", run: () => window.DeepTheme && DeepTheme.toggle() },
    { icon: "◉", label: "Show Surface Report (briefing)", cat: "intel", run: () => { try { sessionStorage.removeItem("deep_briefed"); } catch (_) {} window.DeepModules && DeepModules.briefing(); } },
    { icon: "♪", label: "Toggle UI sound effects", cat: "ui", run: () => window.SFX && SFX.mute(SFX.enabled()) },
    { icon: "◌", label: "Tidy windows around the core", cat: "ui", run: () => window.DeepWindows && DeepWindows.tidy() },
    { icon: "◉", label: "Speak my briefing", cat: "intel", run: () => fetch("/api/briefing/speak", { method: "POST" }).catch(() => {}) },
    { icon: "☾", label: "Toggle Focus / Zen mode", cat: "ui", run: () => window.DeepFocus && DeepFocus.toggle() },
    { icon: "✦", label: "Open Notification Center", cat: "ui", run: () => window.HUD && HUD.open("notifications") },
    { icon: "✚", label: "Open Self-Diagnostics", cat: "system", run: () => window.HUD && HUD.open("diagnostics") },
    { icon: "▦", label: "Open Presence Timeline", cat: "intel", run: () => window.HUD && HUD.open("timeline") },
    { icon: "▮", label: "Open RF Spectrum", cat: "network", run: () => window.HUD && HUD.open("spectrum") },
    { icon: "◉", label: "Open Proximity Globe", cat: "network", run: () => window.HUD && HUD.open("globe") },
    { icon: "⊕", label: "Open Geo-Intel Map", cat: "network", run: () => window.HUD && HUD.open("geomap") },
  ];

  // Fuzzy subsequence score: lower = better; -1 = no match.
  function fuzzy(q, text) {
    text = text.toLowerCase();
    let ti = 0, score = 0, streak = 0;
    for (const ch of q) {
      const at = text.indexOf(ch, ti);
      if (at === -1) return -1;
      score += (at - ti) + (at === ti ? 0 : 2);   // reward contiguous matches
      streak = (at === ti) ? streak + 1 : 0;
      ti = at + 1;
    }
    return score;
  }

  function install() {
    // Need the palette internals to exist (defined while app.js runs).
    if (typeof PALETTE_COMMANDS === "undefined" || typeof renderPalette !== "function") {
      return setTimeout(install, 150);
    }

    // 1) add the new commands (idempotent)
    const have = new Set(PALETTE_COMMANDS.map((c) => c.label));
    EXTRA.forEach((c) => { if (!have.has(c.label)) PALETTE_COMMANDS.push(c); });

    // 2) upgrade renderPalette with fuzzy ranking + async memory-entity jumps,
    //    by wrapping the original.
    const orig = renderPalette;
    let entityReqId = 0;
    window.renderPalette = renderPalette = function (q) {
      q = (q || "").toLowerCase().trim();
      if (!q) return orig("");

      // rank commands by fuzzy score
      const scored = [];
      PALETTE_COMMANDS.forEach((c) => {
        const s = Math.min(...[c.label, c.cat].map((t) => { const v = fuzzy(q, t); return v < 0 ? Infinity : v; }));
        if (s !== Infinity) scored.push({ c, s });
      });
      scored.sort((a, b) => a.s - b.s);
      _paletteFiltered = scored.map((x) => x.c);
      _paletteIdx = 0;
      paint(q);

      // live memory-entity jumps (debounced, async appended)
      if (q.length >= 2) {
        const rid = ++entityReqId;
        fetch("/api/knowledge/search?q=" + encodeURIComponent(q) + "&limit=6")
          .then((r) => r.ok ? r.json() : null)
          .then((d) => {
            if (!d || rid !== entityReqId) return;
            const ents = d.entities || d.results || [];
            if (!ents.length) return;
            ents.slice(0, 6).forEach((e) => {
              const name = e.name || e.id || "";
              if (!name) return;
              _paletteFiltered.push({
                icon: "✦", label: "Jump to memory: " + name, cat: "entity",
                run: () => { if (window.HUD) { HUD.open("memory-ring"); setTimeout(() => { const s = document.querySelector(".mr-search"); if (s) { s.value = name; s.dispatchEvent(new Event("input")); } }, 200); } },
              });
            });
            paint(q);
          })
          .catch(() => {});
      }
    };

    function paint(q) {
      const list = document.getElementById("cmdPaletteList");
      if (!list) return;
      if (!_paletteFiltered.length) {
        list.innerHTML = `<div class="cmd-palette-empty">Press Enter to search history for “${escapeHtml(q)}”</div>`;
        return;
      }
      list.innerHTML = _paletteFiltered.map((c, i) =>
        `<div class="cmd-palette-item${i === 0 ? " active" : ""}" data-i="${i}">`
        + `<span class="cpi-icon">${c.icon}</span><span>${escapeHtml(c.label)}</span>`
        + `<span class="cpi-cat">${c.cat}</span></div>`).join("");
      list.querySelectorAll(".cmd-palette-item").forEach((el) => {
        el.addEventListener("click", () => runPaletteItem(parseInt(el.dataset.i)));
      });
    }

    console.log("[DEEP] Command palette extended ✓ (" + EXTRA.length + " actions + fuzzy + entity jumps)");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
})();
