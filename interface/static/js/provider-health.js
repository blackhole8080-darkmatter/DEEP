/* ============================================================================
 * DEEP — PROVIDER HEALTH  (new element)
 * ----------------------------------------------------------------------------
 * Surfaces /api/providers/health so a dead/invalid AI key never degrades DEEP
 * silently. On load it quietly checks; if a configured key is down it raises a
 * dismissible toast. A token-styled panel (palette: "Provider Health") lists
 * every provider's status on demand.
 * ========================================================================== */
(function () {
  "use strict";

  async function fetchHealth(force) {
    try {
      const r = await fetch("/api/providers/health" + (force ? "?force=true" : ""));
      return await r.json();
    } catch (_) { return null; }
  }

  function dot(ok) {
    return `<span class="ph-dot ${ok ? "ok" : "bad"}"></span>`;
  }

  function renderPanel(data) {
    let el = document.getElementById("provider-health-panel");
    if (el) el.remove();
    el = document.createElement("div");
    el.id = "provider-health-panel";
    el.className = "ph-panel";
    const rows = (data && data.providers || []).map((p) =>
      `<div class="ph-row">
         ${dot(p.ok)}
         <span class="ph-name">${p.provider}</span>
         <span class="ph-detail ${p.ok ? "" : "bad"}">${p.detail}</span>
       </div>`).join("");
    el.innerHTML =
      `<div class="ph-head">
         <span>AI Provider Health</span>
         <button class="ph-x" aria-label="Close">✕</button>
       </div>
       <div class="ph-body">${rows || "<div class='ph-row'>No data</div>"}</div>
       <div class="ph-foot">${data ? `${data.healthy}/${data.total} keys valid · ${data.note}` : ""}</div>`;
    document.body.appendChild(el);
    el.querySelector(".ph-x").onclick = () => el.remove();
  }

  async function open() {
    renderPanel(await fetchHealth(true));
  }

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "ph-toast";
    t.innerHTML = `${dot(false)}<span>${msg}</span><button class="ph-x" aria-label="Dismiss">✕</button>`;
    document.body.appendChild(t);
    t.querySelector(".ph-x").onclick = () => t.remove();
    setTimeout(() => t.remove(), 12000);
  }

  // Quiet check on load → warn only if a configured key is down.
  async function boot() {
    const data = await fetchHealth(false);
    if (!data) return;
    const down = data.providers.filter((p) => p.configured && !p.ok);
    if (down.length) {
      toast(`${down.length} AI provider key${down.length > 1 ? "s" : ""} down: ` +
            down.map((d) => `${d.provider} (${d.detail})`).join(", "));
    }
  }

  window.ProviderHealth = { open, refresh: () => fetchHealth(true) };

  // Register a command-palette entry once app.js's palette exists.
  (function register() {
    if (typeof PALETTE_COMMANDS !== "undefined" && Array.isArray(PALETTE_COMMANDS)) {
      if (!PALETTE_COMMANDS.some((c) => c.label === "Check AI Provider Health")) {
        PALETTE_COMMANDS.push({
          icon: "⚡", label: "Check AI Provider Health", cat: "system",
          run: () => window.ProviderHealth.open(),
        });
      }
      return;
    }
    setTimeout(register, 300);
  })();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
