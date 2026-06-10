/* ============================================================================
 * DEEP — "Mind" panels: About You (World Model) + Documents (Personal RAG)
 * ----------------------------------------------------------------------------
 * Surfaces the intelligence built in the backend (core/world_model.py,
 * core/personal_rag.py) — otherwise invisible behind /api/world and /api/docs.
 * Two HUD apps registered on the yantra core, styled via deep-modern.css.
 * ========================================================================== */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function when(iso) {
    if (!iso) return "";
    const d = new Date(iso); if (isNaN(d)) return "";
    const days = Math.floor((Date.now() - d) / 86400000);
    if (days <= 0) return "today";
    if (days === 1) return "yesterday";
    if (days < 7) return days + "d ago";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  const chips = (arr) => (arr && arr.length)
    ? arr.map((x) => `<span class="wm-chip">${esc(x)}</span>`).join("")
    : '<span class="wm-empty">—</span>';

  // ── About You (World Model) ───────────────────────────────────────────────
  function buildAbout(body) {
    body.style.overflow = "auto";
    body.innerHTML = '<div class="wm-wrap"><div class="wm-empty">Synthesising…</div></div>';
    function render(d) {
      d = d || {};
      const eps = (d.episodes || []).slice().reverse();
      body.innerHTML = `
        <div class="wm-wrap deep-stagger">
          <div class="wm-summary">${esc(d.summary || "DEEP is still getting to know you — keep chatting.")}</div>
          ${d.current_focus ? `<div class="wm-focus"><span class="wm-k">Right now</span> ${esc(d.current_focus)}</div>` : ""}
          <div class="wm-sec">Projects</div><div class="wm-chips">${chips(d.projects)}</div>
          <div class="wm-sec">Priorities</div><div class="wm-chips">${chips(d.priorities)}</div>
          <div class="wm-sec">Interests</div><div class="wm-chips">${chips(d.interests)}</div>
          <div class="wm-sec">People</div><div class="wm-chips">${chips(d.people)}</div>
          <div class="wm-sec">Recently</div>
          <div class="wm-timeline">${eps.length ? eps.map((e) =>
            `<div class="wm-ep"><span class="wm-dot"></span><div><div class="wm-ep-t">${esc(e.text)}</div>
             <div class="wm-ep-d">${when(e.at)}</div></div></div>`).join("")
            : '<div class="wm-empty">No episodes yet</div>'}</div>
          <button class="hud-btn wm-refresh">↻ Re-synthesise</button>
          <div class="wm-meta">${d.updated_at ? "updated " + when(d.updated_at) : ""}</div>
        </div>`;
      const rb = body.querySelector(".wm-refresh");
      rb.onclick = () => {
        rb.textContent = "synthesising…"; rb.disabled = true;
        fetch("/api/world/refresh", { method: "POST" })
          .then((r) => r.json()).then(render).catch(() => { rb.textContent = "↻ Re-synthesise"; rb.disabled = false; });
      };
    }
    fetch("/api/world").then((r) => r.json()).then(render)
      .catch(() => { body.innerHTML = '<div class="wm-wrap"><div class="wm-empty">Couldn’t load.</div></div>'; });
  }

  // ── Documents (Personal RAG) ──────────────────────────────────────────────
  function buildDocs(body) {
    body.style.overflow = "auto";
    body.innerHTML = `
      <div class="dr-wrap deep-stagger">
        <label class="dr-drop"><span>⤓ Drop files or click to upload</span>
          <input type="file" multiple hidden accept=".pdf,.docx,.txt,.md,.markdown,.py,.js,.ts,.json,.csv,.log,.rst,.yaml,.yml"></label>
        <input class="hud-input dr-search" placeholder="Search your documents…">
        <div class="dr-results"></div>
        <div class="dr-sec">Ingested <button class="dr-scan" title="Scan watch folder">scan ⟳</button></div>
        <div class="dr-list"><div class="wm-empty">…</div></div>
      </div>`;
    const fileInput = body.querySelector('input[type=file]');
    const drop = body.querySelector(".dr-drop");
    const searchEl = body.querySelector(".dr-search");
    const resultsEl = body.querySelector(".dr-results");
    const listEl = body.querySelector(".dr-list");

    function loadStats() {
      fetch("/api/docs/stats").then((r) => r.json()).then((d) => {
        const docs = d.documents || {};
        const names = Object.keys(docs);
        listEl.innerHTML = names.length
          ? names.map((n) => `<div class="dr-doc"><span class="dr-doc-n">${esc(n)}</span><span class="dr-doc-c">${docs[n]} chunk${docs[n] === 1 ? "" : "s"}</span></div>`).join("")
          : `<div class="wm-empty">No documents yet — drop files above or put them in <code>${esc(d.folder || "data/personal_docs")}</code></div>`;
      }).catch(() => { listEl.innerHTML = '<div class="wm-empty">Couldn’t load.</div>'; });
    }
    function upload(files) {
      [...files].forEach((f) => {
        const fd = new FormData(); fd.append("file", f);
        const row = document.createElement("div"); row.className = "dr-doc"; row.innerHTML = `<span class="dr-doc-n">${esc(f.name)}</span><span class="dr-doc-c">uploading…</span>`;
        listEl.prepend(row);
        fetch("/api/knowledge/ingest", { method: "POST", body: fd })
          .then((r) => r.json()).then((res) => { row.querySelector(".dr-doc-c").textContent = res.ok ? res.chunks + " chunks" : "failed"; window.SFX && SFX.play("blip"); setTimeout(loadStats, 400); })
          .catch(() => { row.querySelector(".dr-doc-c").textContent = "failed"; });
      });
    }
    fileInput.onchange = () => upload(fileInput.files);
    ["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => { if (e.dataTransfer && e.dataTransfer.files) upload(e.dataTransfer.files); });
    body.querySelector(".dr-scan").onclick = (e) => { e.preventDefault(); e.stopPropagation(); const b = e.target; b.textContent = "…"; fetch("/api/docs/scan", { method: "POST" }).then((r) => r.json()).then(() => { b.textContent = "scan ⟳"; loadStats(); }).catch(() => { b.textContent = "scan ⟳"; }); };

    let t = null;
    searchEl.addEventListener("input", () => {
      clearTimeout(t);
      const q = searchEl.value.trim();
      if (!q) { resultsEl.innerHTML = ""; return; }
      t = setTimeout(() => {
        fetch("/api/docs/search?k=4&q=" + encodeURIComponent(q)).then((r) => r.json()).then((d) => {
          const rs = d.results || [];
          resultsEl.innerHTML = rs.length
            ? rs.map((r) => `<div class="dr-hit"><div class="dr-hit-src">📄 ${esc(r.source)}${r.chunk != null ? " · #" + r.chunk : ""}</div><div class="dr-hit-tx">${esc(r.text)}</div></div>`).join("")
            : '<div class="wm-empty">No matches.</div>';
        }).catch(() => { resultsEl.innerHTML = '<div class="wm-empty">Search failed.</div>'; });
      }, 280);
    });
    loadStats();
  }

  // ── Register both on the core ─────────────────────────────────────────────
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    HUD.registerApp({
      id: "about", title: "About You", icon: "☉",
      anchor: "core", anchorAngle: -Math.PI * 0.42,
      width: 440, height: 460, minWidth: 320, minHeight: 280,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></svg>',
      build: buildAbout,
    });
    HUD.registerApp({
      id: "documents", title: "Documents", icon: "❑",
      anchor: "core", anchorAngle: -Math.PI * 0.12,
      width: 480, height: 480, minWidth: 340, minHeight: 300,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 2h8l4 4v16H6z"/><path d="M14 2v4h4M9 13h6M9 17h6"/></svg>',
      build: buildDocs,
    });
  }
  register();

  window.openAboutYou = () => window.HUD && HUD.open("about");
  window.openDocuments = () => window.HUD && HUD.open("documents");
  console.log("[DEEP] Mind panels (About You + Documents) registered ✓");
})();
