/* ============================================================================
 * DEEP — INTELLIGENCE MODULES II
 * ----------------------------------------------------------------------------
 *   5. Proximity Sensor  — sonar of nearby Wi-Fi / Bluetooth (/network/proximity)
 *   6. Audit Ledger       — tamper-evident hash-chain log (/audit/*)
 *   7. Approval Queue      — human-in-the-loop requests (/api/interactive/*)
 *
 * Same Abyssal idiom as deep-modules.js. Registers as HUD apps (right dock).
 * ========================================================================== */
(function () {
  "use strict";

  const $ = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  async function getJSON(u, o) { try { const r = await fetch(u, o); return r.ok ? await r.json() : null; } catch (_) { return null; } }
  function strip(s) { const d = document.createElement("div"); d.innerHTML = s || ""; return (d.textContent || "").replace(/\s+/g, " ").trim(); }
  function ago(iso) { if (!iso) return ""; const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 60) return Math.round(s) + "s"; if (s < 3600) return Math.round(s / 60) + "m"; if (s < 86400) return Math.round(s / 3600) + "h"; return Math.round(s / 86400) + "d"; }
  function reveal(c) { [...c.children].forEach((row, i) => { row.style.opacity = "0"; requestAnimationFrame(() => { row.style.transition = "opacity .4s ease, transform .45s cubic-bezier(.2,1.2,.3,1)"; row.style.transitionDelay = (i * 45) + "ms"; row.style.transform = "translateY(8px)"; requestAnimationFrame(() => { row.style.opacity = "1"; row.style.transform = "translateY(0)"; }); }); }); }
  function sfx(n) { try { window.SFX && SFX.play(n); } catch (_) {} }

  /* ═══ DEVICE DOSSIER — click a blip/row → /api/investigate drill-down ═══ */
  let _dossierWin = null;
  function openDossier(target, label) {
    if (!window.HUD || !target) return;
    try { if (_dossierWin) _dossierWin.close(); } catch (_) {}
    sfx("open");
    _dossierWin = HUD.spawn({
      id: "dossier", title: "DOSSIER · " + (label || target), icon: "❂",
      width: 360, height: 360, minWidth: 280, minHeight: 220, anchor: "core",
      anchorAngle: -Math.PI * 0.5, anchorDist: Math.min(innerWidth, innerHeight) * 0.3,
      build: (b) => renderDossier(b, target, label),
    });
  }
  async function renderDossier(body, target, label) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML = `<div class="dm-dos-loading">Investigating <b>${strip(label || target)}</b><span class="dm-dos-dots"></span><div class="dm-dos-scan"></div></div>`;
    const d = await getJSON("/api/investigate?target=" + encodeURIComponent(target));
    if (!d || d.error) { body.innerHTML = `<div class="dm-empty">Could not investigate ${strip(target)}.</div>`; return; }
    const rows = (d.findings || []).map((f) =>
      `<div class="dm-dos-row"><span class="dm-dos-k">${f.label}</span><span class="dm-dos-v">${String(f.value).replace(/</g, "&lt;")}</span></div>`).join("");
    body.innerHTML =
      `<div class="dm-dos-head${d.risk === "elevated" ? " risk" : ""}">
         <div class="dm-dos-target">${strip(label || d.target)}</div>
         <div class="dm-dos-summary">${String(d.summary || "").replace(/</g, "&lt;")}</div>
       </div>
       <div class="dm-dos-body">${rows || '<div class="dm-empty">No further detail.</div>'}</div>`;
    reveal(body.querySelector(".dm-dos-body"));
    sfx("blip");
  }
  window.DeepDossier = { open: openDossier };

  // Make any IP / MAC shown in a panel click-to-investigate (shares one dossier
  // window). Click-only — never auto-investigates (avoids burst external lookups).
  const _TARGET_RE = /\b((?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})\b/g;
  function linkifyTargets(scope) {
    if (!scope) return;
    scope.querySelectorAll(".dm-audit-act, .dm-threat-t").forEach((el) => {
      if (el.dataset.linked) return;
      const html = el.innerHTML;
      _TARGET_RE.lastIndex = 0;
      if (_TARGET_RE.test(html)) {
        _TARGET_RE.lastIndex = 0;
        el.innerHTML = html.replace(_TARGET_RE, (m) => `<span class="dm-investigate" data-target="${m}" title="Investigate ${m}">${m}</span>`);
      }
      el.dataset.linked = "1";
    });
  }
  // one delegated handler for every linkified target, anywhere in the UI
  document.addEventListener("click", (e) => {
    const t = e.target.closest(".dm-investigate");
    if (t && t.dataset.target) { e.stopPropagation(); openDossier(t.dataset.target, t.dataset.target); }
  }, true);
  window.DeepInvestigate = { linkify: linkifyTargets };

  /* ═══ 5) PROXIMITY SONAR ═══════════════════════════════════════════════ */
  function buildProximity(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-sonar"><canvas id="pxSonar"></canvas></div>
       <div class="dm-toolbar"><span class="dm-stat" id="pxStat">scanning…</span></div>
       <div class="dm-list" id="pxList"><div class="dm-empty">Listening for nearby signals…</div></div>`;
    const canvas = body.querySelector("#pxSonar"), ctx = canvas.getContext("2d");
    const list = body.querySelector("#pxList"), stat = body.querySelector("#pxStat");
    let raf = 0, sweep = 0, dpr = Math.min(devicePixelRatio || 1, 2), blips = [];

    function size() { const w = canvas.clientWidth || 240, h = canvas.clientHeight || 150; canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    function draw() {
      raf = requestAnimationFrame(draw);
      const w = canvas.clientWidth, h = canvas.clientHeight; if (!w) return;
      const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 6;
      ctx.clearRect(0, 0, w, h);
      for (let i = 1; i <= 3; i++) { ctx.strokeStyle = "rgba(0,229,255,0.14)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(cx, cy, R * i / 3, 0, Math.PI * 2); ctx.stroke(); }
      sweep += 0.02;
      const grad = ctx.createLinearGradient(cx, cy, cx + Math.cos(sweep) * R, cy + Math.sin(sweep) * R);
      grad.addColorStop(0, "rgba(0,255,209,0.4)"); grad.addColorStop(1, "rgba(0,255,209,0)");
      ctx.strokeStyle = grad; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(sweep) * R, cy + Math.sin(sweep) * R); ctx.stroke();
      const t = performance.now() / 1000;
      blips.forEach((b) => {
        const bx = cx + Math.cos(b.a) * b.r * R, by = cy + Math.sin(b.a) * b.r * R;
        const near = Math.cos(sweep - b.a); const lit = Math.max(0, near) * 0.8 + 0.2;
        if (b.tracker) {
          const pulse = 0.5 + 0.5 * Math.sin(t * 4);
          ctx.fillStyle = `rgba(255,90,90,${0.5 + pulse * 0.5})`;
          ctx.beginPath(); ctx.arc(bx, by, 3.5, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = `rgba(255,90,90,${pulse * 0.6})`; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.arc(bx, by, 4 + pulse * 5, 0, Math.PI * 2); ctx.stroke();
        } else {
          ctx.fillStyle = b.mine ? `rgba(0,255,209,${lit})` : `rgba(0,229,255,${lit * 0.8})`;
          ctx.beginPath(); ctx.arc(bx, by, b.mine ? 3 : 2, 0, Math.PI * 2); ctx.fill();
        }
      });
    }
    async function load() {
      const [sum, wifi, bt] = await Promise.all([getJSON("/network/proximity"), getJSON("/network/proximity/wifi"), getJSON("/network/proximity/bt")]);
      if (sum) stat.innerHTML = `<b>${sum.wifi ? sum.wifi.total_nearby : 0}</b> wifi · <b>${sum.bluetooth ? sum.bluetooth.total_nearby : 0}</b> bt · ${sum.recurring_unknowns ?? 0} recurring · ${sum.alerts_today ?? 0} alerts`;
      const aps = (wifi && wifi.aps) || [], bts = (bt && bt.devices) || [];
      const all = aps.map((a) => ({ name: a.ssid || a.bssid, target: a.bssid, sig: a.signal_dbm, mine: a.is_yours, type: "WIFI", enc: a.encryption, vendor: a.vendor, band: a.band, hidden: a.hidden }))
        .concat(bts.map((d) => ({ name: d.name || d.mac, target: d.mac, sig: d.rssi, mine: d.is_yours, type: "BT", vendor: d.vendor, dist: d.distance_m, services: d.services, tracker: d.is_tracker, trackerKind: d.tracker_kind })));
      // sonar blips: radius from signal (strong=center), angle stable per name
      blips = all.slice(0, 60).map((d) => { let hash = 0; const s = String(d.name); for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) & 0xffff; const sig = d.sig == null ? -90 : d.sig; return { a: (hash / 0xffff) * Math.PI * 2, r: Math.min(0.95, 1 - (sig + 100) / 70), mine: d.mine, tracker: d.tracker }; });
      const sorted = all.sort((a, b) => (b.tracker ? 1 : 0) - (a.tracker ? 1 : 0) || (b.sig || -120) - (a.sig || -120)).slice(0, 40);
      if (!sorted.length) { list.innerHTML = `<div class="dm-empty">Nothing nearby. You're alone in the deep.</div>`; return; }
      list.innerHTML = "";
      sorted.forEach((d) => {
        const bars = Math.max(1, Math.min(4, Math.round((d.sig + 100) / 17)));
        const meta = [];
        if (d.vendor) meta.push(d.vendor);
        meta.push(d.type + (d.band ? " " + d.band : ""));
        if (d.dist != null) meta.push("~" + d.dist + "m");
        if (d.enc && d.enc !== "UNKNOWN") meta.push(d.enc);
        if (d.mine) meta.push("yours");
        const row = $("div", "dm-prox" + (d.mine ? " mine" : "") + (d.tracker ? " tracker" : ""));
        row.innerHTML =
          `<span class="dm-prox-sig s${bars}"><i></i><i></i><i></i><i></i></span>
           <span class="dm-prox-name">${strip(d.name).slice(0, 30) || "(hidden)"}${d.tracker ? ` <span class="dm-prox-tracker">⚠ ${d.trackerKind || "TRACKER"}</span>` : ""}</span>
           <span class="dm-prox-meta">${meta.join(" · ")}</span>`;
        if (d.target) {
          row.style.cursor = "pointer";
          row.title = "Investigate " + d.target;
          row.addEventListener("click", () => openDossier(d.target, d.name));
        }
        list.appendChild(row);
      });
      reveal(list);
    }
    size(); draw(); load();
    const t = setInterval(load, 15000);
    win._stop = () => { clearInterval(t); cancelAnimationFrame(raf); };
    win._resize = size;
  }

  /* ═══ 6) AUDIT LEDGER ══════════════════════════════════════════════════ */
  function buildAudit(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-audit-head">
         <div class="dm-chain" id="auChain">checking integrity…</div>
         <div class="dm-toolbar" style="border:0;padding:0;background:none">
           <span class="dm-stat" id="auStat"></span><span style="flex:1"></span>
           <button class="hud-btn" id="auVerify">⛓ Verify chain</button>
         </div>
       </div>
       <div class="dm-list" id="auList"><div class="dm-empty">Reading the ledger…</div></div>`;
    const chainEl = body.querySelector("#auChain"), statEl = body.querySelector("#auStat"), list = body.querySelector("#auList");
    const TYPE = { THREAT_DETECTED: "alert", INTEGRITY_FAIL: "alert", DEVICE_JOINED: "warn", SYSTEM_START: "ok", SYSTEM_STOP: "ok" };
    async function load() {
      const [st, log] = await Promise.all([getJSON("/audit/stats"), getJSON("/audit/log")]);
      if (st) {
        statEl.textContent = `${st.total_entries ?? 0} entries · ${st.entries_today ?? 0} today · ${st.threat_count_today ?? 0} threats`;
        const intact = st.chain_intact;
        chainEl.className = "dm-chain " + (intact ? "ok" : "broken");
        chainEl.innerHTML = intact
          ? `<span class="dm-chain-icon">⛓</span> HASH CHAIN INTACT · ${st.db_size_mb ?? 0} MB`
          : `<span class="dm-chain-icon">⛓</span> CHAIN COMPROMISED — integrity failures detected`;
      }
      const entries = (log && log.entries) || [];
      if (!entries.length) { list.innerHTML = `<div class="dm-empty">Ledger is empty.</div>`; return; }
      list.innerHTML = "";
      entries.slice(0, 50).forEach((e) => {
        const sev = TYPE[e.entry_type] || "ok";
        const row = $("div", "dm-audit sev-" + sev);
        row.innerHTML = `<span class="dm-audit-type">${(e.entry_type || "").replace(/_/g, " ")}</span>
          <span class="dm-audit-act">${strip(e.action).slice(0, 80)}</span>
          <span class="dm-audit-meta"><code>${(e.entry_hash || "").slice(0, 8)}</code> · ${ago(e.timestamp)} ago</span>`;
        list.appendChild(row);
      });
      reveal(list);
      linkifyTargets(list);   // IPs/MACs in entries become click-to-investigate
    }
    body.querySelector("#auVerify").addEventListener("click", async (ev) => {
      const b = ev.currentTarget; b.disabled = true; b.textContent = "verifying…"; sfx("blip");
      const r = await getJSON("/audit/verify", { method: "POST" });
      await load();
      b.disabled = false; b.textContent = "⛓ Verify chain";
      if (r) { chainEl.classList.add("flash"); setTimeout(() => chainEl.classList.remove("flash"), 600); }
    });
    load();
    const t = setInterval(load, 20000);
    win._stop = () => clearInterval(t);
  }

  /* ═══ 7) APPROVAL QUEUE (HITL) ═════════════════════════════════════════ */
  function buildApprovals(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML = `<div class="dm-list" id="apList" style="padding-top:12px"><div class="dm-empty">Loading…</div></div>`;
    const list = body.querySelector("#apList");
    async function respond(id, decision) {
      sfx(decision === "approve" ? "blip" : "close");
      await fetch("/api/interactive/respond", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: id, decision: decision }) }).catch(() => {});
      load();
    }
    async function respondAction(id, approve) {
      sfx(approve ? "blip" : "close");
      const r = await getJSON("/api/actions/respond", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: id, approve: approve }) });
      if (approve && r && r.result && window.DeepToast) DeepToast.show({ level: "success", icon: "✓", title: "Action executed", body: String(r.result).slice(0, 100) });
      load();
    }
    async function load() {
      const [d, a] = await Promise.all([getJSON("/api/interactive/pending"), getJSON("/api/actions/pending")]);
      const items = (d && d.pending) || [];
      const actions = (a && a.pending) || [];
      const total = items.length + actions.length;
      try { window.HUD && HUD.setDockStatus("approvals", total ? "warn" : "ok"); } catch (_) {}
      if (!total) { list.innerHTML = `<div class="dm-empty">No pending approvals. DEEP is acting within bounds.</div>`; return; }
      list.innerHTML = "";
      // destructive actions awaiting confirmation (highlighted)
      actions.forEach((it) => {
        const card = $("div", "dm-approval dm-ap-action");
        card.innerHTML =
          `<div class="dm-ap-q">⚠ ${strip(it.label || "DEEP requests permission to act")}</div>
           ${it.detail ? `<div class="dm-ap-detail">${strip(it.detail)}</div>` : ""}
           <div class="dm-ap-btns"><button class="dm-ap-yes">Approve &amp; run</button><button class="dm-ap-no">Deny</button></div>`;
        card.querySelector(".dm-ap-yes").addEventListener("click", () => respondAction(it.id, true));
        card.querySelector(".dm-ap-no").addEventListener("click", () => respondAction(it.id, false));
        list.appendChild(card);
      });
      items.forEach((it) => {
        const card = $("div", "dm-approval");
        card.innerHTML =
          `<div class="dm-ap-q">${strip(it.question || it.prompt || it.action || "DEEP requests permission")}</div>
           ${it.detail ? `<div class="dm-ap-detail">${strip(it.detail)}</div>` : ""}
           <div class="dm-ap-btns"><button class="dm-ap-yes">Approve</button><button class="dm-ap-no">Deny</button></div>`;
        card.querySelector(".dm-ap-yes").addEventListener("click", () => respond(it.id, "approve"));
        card.querySelector(".dm-ap-no").addEventListener("click", () => respond(it.id, "deny"));
        list.appendChild(card);
      });
      reveal(list);
    }
    load();
    const t = setInterval(load, 6000);
    win._stop = () => clearInterval(t);
  }

  /* ═══ REGISTER ═════════════════════════════════════════════════════════ */
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    const dist = Math.min(innerWidth, innerHeight) * 0.36;
    HUD.registerApp({ id: "proximity", title: "Proximity", icon: "◎", anchor: "core", anchorAngle: -Math.PI * 0.5, anchorDist: dist,
      width: 420, height: 460, minWidth: 300, minHeight: 280,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="2"/><path d="M7.8 16.2a6 6 0 0 1 0-8.4M16.2 7.8a6 6 0 0 1 0 8.4M5 19a10 10 0 0 1 0-14M19 5a10 10 0 0 1 0 14"/></svg>',
      build: buildProximity, onClose: (w) => w._stop && w._stop(), onResize: (a, b, w) => w._resize && w._resize() });
    HUD.registerApp({ id: "audit", title: "Audit Ledger", icon: "⛓", anchor: "core", anchorAngle: Math.PI * 0.5, anchorDist: dist,
      width: 480, height: 460, minWidth: 340, minHeight: 280,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>',
      build: buildAudit, onClose: (w) => w._stop && w._stop() });
    HUD.registerApp({ id: "approvals", title: "Approvals", icon: "✓", anchor: "core", anchorAngle: Math.PI * 0.9, anchorDist: dist,
      width: 400, height: 380, minWidth: 300, minHeight: 220,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
      build: buildApprovals, onClose: (w) => w._stop && w._stop() });
    // light a dock badge + toast when approvals/actions are waiting (even closed)
    let _lastActionIds = "";
    setInterval(async () => {
      const [d, a] = await Promise.all([getJSON("/api/interactive/pending"), getJSON("/api/actions/pending")]);
      const inter = (d && d.pending) || [];
      const acts = (a && a.pending) || [];
      try { HUD.setDockStatus("approvals", (inter.length + acts.length) ? "warn" : "ok"); } catch (_) {}
      const ids = acts.map((x) => x.id).join(",");
      if (acts.length && ids !== _lastActionIds && window.DeepToast) {
        DeepToast.show({ level: "approval", icon: "✓", title: "Approval needed: " + (acts[0].label || "action"),
          body: "DEEP is waiting for your confirmation.", ttl: 15000, onClick: () => window.HUD && HUD.open("approvals") });
      }
      _lastActionIds = ids;
    }, 8000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", register);
  else register();
  console.log("[DEEP] Intelligence modules II online ✓");
})();
