/* ============================================================================
 * DEEP — PERIODIC TABLE  (chemistry oracle UI)
 * ----------------------------------------------------------------------------
 * Renders all 118 elements from /api/chem/table in a proper periodic layout,
 * shaded by category. Click an element → full verified metadata from
 * /api/chem/element/{symbol}. Opened via palette: "Periodic Table".
 * ========================================================================== */
(function () {
  "use strict";

  let cache = null;

  async function getTable() {
    if (cache) return cache;
    const r = await fetch("/api/chem/table");
    const d = await r.json();
    cache = (d && d.elements) || [];
    return cache;
  }

  // f-block (lanthanides/actinides) get their own two rows beneath the table.
  function gridPos(el) {
    const z = el.atomic_number;
    if (z >= 57 && z <= 71) return { row: 9, col: 3 + (z - 57) };   // lanthanides
    if (z >= 89 && z <= 103) return { row: 10, col: 3 + (z - 89) }; // actinides
    if (el.group && el.period) return { row: el.period, col: el.group };
    return null;
  }

  async function open() {
    let el = document.getElementById("periodic-table-panel");
    if (el) { el.remove(); return; }
    const data = await getTable();
    el = document.createElement("div");
    el.id = "periodic-table-panel";
    el.className = "pt-panel";

    const cells = data.map((e) => {
      const p = gridPos(e);
      if (!p) return "";
      return `<button class="pt-cell cat-${e.category}" style="grid-row:${p.row};grid-column:${p.col}"
                data-sym="${e.symbol}" title="${e.name}">
                <span class="pt-z">${e.atomic_number}</span>
                <span class="pt-sym">${e.symbol}</span>
                <span class="pt-mass">${(e.atomic_weight || "").toString().slice(0, 6)}</span>
              </button>`;
    }).join("");

    el.innerHTML =
      `<div class="pt-head">
         <span>Periodic Table <small>· ${data.length} elements · curated data</small></span>
         <button class="pt-x" aria-label="Close">✕</button>
       </div>
       <div class="pt-grid">${cells}</div>
       <div class="pt-detail" id="pt-detail">Select an element for verified data.</div>`;
    document.body.appendChild(el);
    el.querySelector(".pt-x").onclick = () => el.remove();
    el.querySelectorAll(".pt-cell").forEach((c) =>
      c.addEventListener("click", () => showDetail(c.dataset.sym)));
  }

  async function showDetail(sym) {
    const box = document.getElementById("pt-detail");
    if (!box) return;
    box.textContent = "Loading…";
    try {
      const r = await fetch("/api/chem/element/" + encodeURIComponent(sym));
      const d = await r.json();
      if (!d.ok) { box.textContent = d.error || "not found"; return; }
      const e = d.element;
      const row = (k, v) => v == null ? "" : `<div class="pt-d-row"><span>${k}</span><b>${v}</b></div>`;
      box.innerHTML =
        `<div class="pt-d-title">${e.name} (${e.symbol}) · Z=${e.atomic_number}</div>` +
        row("Atomic weight", e.atomic_weight) +
        row("Electron config", e.electron_configuration) +
        row("Electronegativity", e.electronegativity) +
        row("Oxidation states", (e.oxidation_states || []).join(", ")) +
        row("1st ionization (eV)", e.first_ionization_eV) +
        row("Melting point (K)", e.melting_point_K) +
        row("Boiling point (K)", e.boiling_point_K) +
        row("Density (g/cm³)", e.density_g_cm3) +
        row("Category", e.series) +
        row("Discovered", e.discovery_year ? `${e.discovery_year} · ${e.discoverers || ""}` : null) +
        `<div class="pt-d-src">source: ${e.source}</div>`;
    } catch (_) { box.textContent = "lookup failed"; }
  }

  window.PeriodicTable = { open };

  (function register() {
    if (typeof PALETTE_COMMANDS !== "undefined" && Array.isArray(PALETTE_COMMANDS)) {
      if (!PALETTE_COMMANDS.some((c) => c.label === "Periodic Table")) {
        PALETTE_COMMANDS.push({
          icon: "⊞", label: "Periodic Table", cat: "science",
          run: () => window.PeriodicTable.open(),
        });
      }
      return;
    }
    setTimeout(register, 300);
  })();
})();
