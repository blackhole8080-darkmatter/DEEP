/* ============================================================================
 * DEEP — UX ELEMENTS  (Notification Center · Self-Diagnostics · Focus mode ·
 *                       Security weather)
 * ========================================================================== */
(function () {
  "use strict";
  const $ = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  async function getJSON(u) { try { const r = await fetch(u); return r.ok ? await r.json() : null; } catch (_) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
  function ago(iso) { if (!iso) return ""; const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 60) return Math.round(s) + "s"; if (s < 3600) return Math.round(s / 60) + "m"; if (s < 86400) return Math.round(s / 3600) + "h"; return Math.round(s / 86400) + "d"; }
  function sfx(n) { try { window.SFX && SFX.play(n); } catch (_) {} }

  /* ═══ NOTIFICATION CENTER — scrollable history of everything ═══════════ */
  const NICE = {
    unknown_device_detected: ["◈", "Device joined network"], unknown_tracker_following: ["◬", "Tracker nearby"],
    device_unusual_time: ["◷", "Unusual-hour device"], threat_detected: ["⚠", "Threat"],
    open_network_nearby: ["≈", "Open Wi-Fi nearby"], known_device_joined: ["✓", "Known device joined"],
    research_finding: ["≈", "Research finding"], audit_integrity_failed: ["⛓", "Audit integrity"],
    system_snapshot_collected: ["▤", "System snapshot"], agent_task_started: ["❖", "Agent started"],
    agent_task_done: ["❖", "Agent done"], evil_twin_detected: ["⚠", "Evil-twin AP"],
  };
  function summarize(ev) {
    const p = ev.payload || {};
    if (ev.event === "unknown_device_detected") return `${p.ip || p.mac || ""}${p.vendor ? " · " + p.vendor : ""}`;
    if (ev.event === "system_snapshot_collected") return `CPU ${Math.round(p.cpu_percent || 0)}% · RAM ${Math.round(p.ram_percent || 0)}%`;
    if (ev.event === "device_unusual_time" || ev.event === "unknown_tracker_following") return p.name || p.id || p.mac || "";
    return (p.text || p.title || p.description || p.name || p.ip || "").toString().slice(0, 60);
  }
  function buildNotifs(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML = `<div class="dm-toolbar"><span class="dm-stat" id="ntStat">…</span><span style="flex:1"></span><button class="hud-btn" id="ntRefresh">↻</button></div>
      <div class="dm-list" id="ntList"><div class="dm-empty">Loading event history…</div></div>`;
    const list = body.querySelector("#ntList"), statEl = body.querySelector("#ntStat");
    async function load() {
      const d = await getJSON("/debug/events");
      let hist = (d && d.history) || [];
      hist = hist.slice().reverse();   // newest first
      statEl.innerHTML = `<b>${hist.length}</b> recent events`;
      if (!hist.length) { list.innerHTML = `<div class="dm-empty">No events yet.</div>`; return; }
      list.innerHTML = "";
      hist.slice(0, 60).forEach((ev) => {
        const [ic, label] = NICE[ev.event] || ["·", ev.event.replace(/_/g, " ")];
        const row = $("div", "nt-row");
        row.innerHTML = `<span class="nt-ico">${ic}</span><span class="nt-main"><span class="nt-label">${esc(label)}</span><span class="nt-sub">${esc(summarize(ev))}</span></span><span class="nt-time">${ago(ev.timestamp)}</span>`;
        list.appendChild(row);
      });
    }
    body.querySelector("#ntRefresh").addEventListener("click", () => { sfx("blip"); load(); });
    load(); const t = setInterval(load, 8000); win._stop = () => clearInterval(t);
  }

  /* ═══ SELF-DIAGNOSTICS — DEEP watching itself ═════════════════════════ */
  async function buildDiag(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML = `<div class="dm-list" id="dgList" style="padding-top:12px"><div class="dm-empty">Running self-check…</div></div>`;
    const list = body.querySelector("#dgList");
    async function load() {
      const [health, plugins, agents, ev] = await Promise.all([
        getJSON("/api/health"), getJSON("/api/plugins/stats"), getJSON("/api/agents/stats"), getJSON("/debug/events"),
      ]);
      const rows = [];
      const ok = health && health.status === "healthy";
      rows.push(["Core", ok ? "ok" : "warn", ok ? "operational" : (health && health.status || "unknown")]);
      if (health && health.brain) rows.push(["Brain", health.brain.status === "ok" ? "ok" : "warn",
        (health.brain.model || "?") + (health.brain.latency_ms ? " · " + Math.round(health.brain.latency_ms) + "ms" : "")]);
      if (plugins) rows.push(["Plugins", "ok", `${plugins.total_plugins ?? 0} loaded`]);
      if (agents) rows.push(["Agents", "ok", `${agents.agents_alive ?? 0} alive · ${agents.total_tasks_completed ?? 0} done`]);
      if (ev && ev.history) rows.push(["Event bus", "ok", `${ev.history.length} recent events`]);
      list.innerHTML = rows.map(([k, lvl, v]) =>
        `<div class="dg-row"><span class="dg-dot ${lvl}"></span><span class="dg-k">${esc(k)}</span><span class="dg-v">${esc(v)}</span></div>`).join("");
    }
    load(); const t = setInterval(load, 10000); win._stop = () => clearInterval(t);
  }

  /* ═══ SECURITY WEATHER — glanceable posture ════════════════════════════ */
  let weatherEl;
  function buildWeather() {
    weatherEl = $("div", "deep-weather", `<span class="dw-ico">🛡</span><span class="dw-txt">SECURE</span>`);
    weatherEl.title = "Security posture";
    weatherEl.addEventListener("click", () => { try { window.HUD && HUD.open("threat"); } catch (_) {} });
    document.body.appendChild(weatherEl);
    async function tick() {
      const [sec, an, pr] = await Promise.all([getJSON("/api/security/status"), getJSON("/anomaly/recent"), getJSON("/threat/predictions")]);
      const susp = (sec && sec.summary && sec.summary.suspicious) || 0;
      const anoms = (an && an.anomalies || []).length;
      const threats = (pr && pr.predictions || []).length;
      const bodyThreat = document.body.dataset.threat;
      let level = "secure", txt = "SECURE";
      if (bodyThreat === "alert" || threats > 0 || susp > 0) { level = "alert"; txt = susp > 0 ? susp + " FLAGGED" : "THREAT"; }
      else if (bodyThreat === "warn" || anoms > 0) { level = "elevated"; txt = "ELEVATED"; }
      weatherEl.className = "deep-weather " + level;
      weatherEl.querySelector(".dw-txt").textContent = txt;
    }
    tick(); setInterval(tick, 12000);
  }

  /* ═══ FOCUS / ZEN MODE — strip the HUD to orb + chat ══════════════════ */
  function initFocus() {
    function toggle() {
      const on = document.body.classList.toggle("deep-focus");
      try { localStorage.setItem("deep_focus", on ? "1" : "0"); } catch (_) {}
      sfx(on ? "close" : "open");
      if (window.DeepToast) DeepToast.show({ level: "info", icon: on ? "☾" : "☀", title: on ? "Focus mode" : "Focus off", body: on ? "HUD hidden — just you and DEEP. (Ctrl+. to exit)" : "HUD restored.", ttl: 3500 });
    }
    addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === ".") { e.preventDefault(); toggle(); } });
    try { if (localStorage.getItem("deep_focus") === "1") document.body.classList.add("deep-focus"); } catch (_) {}
    window.DeepFocus = { toggle };
  }

  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    const dist = Math.min(innerWidth, innerHeight) * 0.34;
    HUD.registerApp({ id: "notifications", title: "Notifications", icon: "✦", anchor: "core", anchorAngle: Math.PI * 1.15, anchorDist: dist,
      width: 420, height: 440, minWidth: 300, minHeight: 240,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
      build: buildNotifs, onClose: (w) => w._stop && w._stop() });
    HUD.registerApp({ id: "diagnostics", title: "Self-Diagnostics", icon: "✚", anchor: "core", anchorAngle: Math.PI * 0.85, anchorDist: dist,
      width: 380, height: 320, minWidth: 280, minHeight: 200,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 12h4l2 6 4-12 2 6h6"/></svg>',
      build: buildDiag, onClose: (w) => w._stop && w._stop() });
    buildWeather();
    initFocus();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", register);
  else register();
  console.log("[DEEP] UX elements online ✓ (notifications · diagnostics · weather · focus)");
})();
