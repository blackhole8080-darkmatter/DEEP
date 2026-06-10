/* ============================================================================
 * DEEP — INTELLIGENCE MODULES
 * ----------------------------------------------------------------------------
 * Four new floating surfaces that expose backend capabilities the UI never
 * showed, all in the Abyssal Tech idiom (rise-from-the-deep entrances, bubbling
 * data, comets to the orb, severity bending the atmosphere):
 *
 *   1. Surface Report   — a boot-time briefing that coalesces after the orb
 *   2. Research Feed     — findings stream  (/api/research/*)
 *   3. Threat & Anomaly  — radar + live anomaly/threat/event stream
 *   4. Evolution Lab     — DEEP rewriting its own mind (/api/evolution/*)
 *
 * Registers 2–4 as HUD apps (they appear in the right dock). Classic script —
 * uses window.HUD, window.DeckFX, window.SFX when present.
 * ========================================================================== */
(function () {
  "use strict";

  // ── helpers ────────────────────────────────────────────────────────────────
  const $ = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  async function getJSON(u, o) { try { const r = await fetch(u, o); return r.ok ? await r.json() : null; } catch (_) { return null; } }
  function strip(html) { const d = document.createElement("div"); d.innerHTML = html || ""; return (d.textContent || "").replace(/\s+/g, " ").trim(); }
  function comet(id) { try { window.DeckFX && DeckFX.comet(id); } catch (_) {} }
  function sfx(n) { try { window.SFX && SFX.play(n); } catch (_) {} }

  // stagger flicker-in for a freshly built list
  function reveal(container) {
    [...container.children].forEach((row, i) => {
      row.style.animation = "none"; row.style.opacity = "0";
      requestAnimationFrame(() => {
        row.style.transition = "opacity .4s ease, transform .45s cubic-bezier(.2,1.2,.3,1)";
        row.style.transitionDelay = (i * 55) + "ms";
        row.style.transform = "translateY(10px)";
        requestAnimationFrame(() => { row.style.opacity = "1"; row.style.transform = "translateY(0)"; });
      });
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * 1) SURFACE REPORT — the boot briefing
   * ═════════════════════════════════════════════════════════════════════ */
  async function surfaceReport() {
    if (sessionStorage.getItem("deep_briefed")) return;
    const [brief, rstats, sec] = await Promise.all([
      getJSON("/api/briefing"), getJSON("/api/research/stats"), getJSON("/api/security/status"),
    ]);
    if (!brief) return;
    sessionStorage.setItem("deep_briefed", "1");

    const panel = $("div", "surface-report");
    const chips = [];
    if (rstats) chips.push(`<span class="sr-chip"><b>${rstats.unread_findings ?? 0}</b> new findings</span>`);
    if (sec && sec.summary) {
      const susp = sec.summary.suspicious || 0;
      chips.push(`<span class="sr-chip ${susp ? "warn" : ""}"><b>${sec.summary.total ?? 0}</b> devices${susp ? ` · ${susp} flagged` : ""}</span>`);
    }
    panel.innerHTML =
      `<div class="sr-head"><span class="sr-pip"></span>SURFACE REPORT</div>
       <div class="sr-greet">${brief.greeting || "Welcome back."}</div>
       <div class="sr-body" id="srBody"></div>
       <div class="sr-chips">${chips.join("")}</div>
       <button class="sr-ack">Acknowledge</button>`;
    document.body.appendChild(panel);
    requestAnimationFrame(() => panel.classList.add("show"));
    sfx("open");

    // typewriter the briefing text
    const body = panel.querySelector("#srBody");
    const text = brief.briefing || "";
    let i = 0;
    (function type() {
      if (i <= text.length) { body.textContent = text.slice(0, i); i += 2; setTimeout(type, 14); }
    })();

    const dismiss = () => { panel.classList.remove("show"); setTimeout(() => panel.remove(), 600); sfx("close"); };
    panel.querySelector(".sr-ack").addEventListener("click", dismiss);
    setTimeout(dismiss, 20000);
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * 2) RESEARCH FEED
   * ═════════════════════════════════════════════════════════════════════ */
  function buildResearch(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-toolbar">
         <span class="dm-stat" id="rfStat">scanning…</span>
         <span style="flex:1"></span>
         <button class="hud-btn" id="rfScan">⟲ Scan</button>
       </div>
       <div class="dm-list" id="rfList"><div class="dm-empty">Surfacing findings…</div></div>`;
    const list = body.querySelector("#rfList");
    const stat = body.querySelector("#rfStat");
    let lastCount = -1, timer = 0;

    async function load(animate) {
      const [d, s] = await Promise.all([getJSON("/api/research/findings"), getJSON("/api/research/stats")]);
      const finds = (d && d.findings) || [];
      if (s) stat.innerHTML = `<b>${s.unread_findings ?? 0}</b> unread · ${s.total_findings ?? 0} total · ${s.last_24h ?? 0} today`;
      if (lastCount >= 0 && finds.length > lastCount) { comet("research"); sfx("blip"); }
      lastCount = finds.length;
      if (!finds.length) { list.innerHTML = `<div class="dm-empty">No findings yet. The currents are calm.</div>`; return; }
      list.innerHTML = "";
      finds.slice(0, 40).forEach((f) => {
        const unread = f.read === false || f.read == null;
        const card = $("div", "dm-card" + (unread ? " unread" : ""));
        card.innerHTML =
          `<div class="dm-card-top"><span class="dm-tag">${(f.source_type || "feed").toUpperCase()}</span>
             <span class="dm-src">${f.source || ""}</span>${unread ? '<span class="dm-newdot"></span>' : ""}</div>
           <div class="dm-card-title">${f.title || "(untitled)"}</div>
           <div class="dm-card-snip">${strip(f.content).slice(0, 160)}…</div>`;
        card.addEventListener("click", async () => {
          if (card.classList.contains("unread")) {
            card.classList.remove("unread");
            const dot = card.querySelector(".dm-newdot"); if (dot) dot.remove();
            await fetch(`/api/research/findings/${encodeURIComponent(f.id)}/read`, { method: "POST" }).catch(() => {});
            load(false);
          }
        });
        list.appendChild(card);
      });
      if (animate) reveal(list);
    }
    body.querySelector("#rfScan").addEventListener("click", async (e) => {
      const b = e.currentTarget; b.disabled = true; b.textContent = "scanning…"; sfx("blip");
      await fetch("/api/research/scan", { method: "POST" }).catch(() => {});
      setTimeout(() => { load(true); b.disabled = false; b.textContent = "⟲ Scan"; }, 1500);
    });

    load(true);
    timer = setInterval(() => load(false), 15000);
    win._stop = () => clearInterval(timer);
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * 3) THREAT & ANOMALY CONSOLE
   * ═════════════════════════════════════════════════════════════════════ */
  function buildThreat(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-radar"><canvas id="thRadar"></canvas><div class="dm-radar-state" id="thState">SCANNING</div></div>
       <div class="dm-list" id="thList"><div class="dm-empty">Reading the deep…</div></div>`;
    const canvas = body.querySelector("#thRadar");
    const cstate = body.querySelector("#thState");
    const list = body.querySelector("#thList");
    const ctx = canvas.getContext("2d");
    let raf = 0, sweep = 0, dpr = Math.min(devicePixelRatio || 1, 2), level = "ok";

    function sizeRadar() {
      const w = canvas.clientWidth || 200, h = canvas.clientHeight || 120;
      canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function drawRadar() {
      raf = requestAnimationFrame(drawRadar);
      const w = canvas.clientWidth, h = canvas.clientHeight; if (!w) return;
      const cx = w / 2, cy = h; const R = h * 0.92;
      ctx.clearRect(0, 0, w, h);
      const col = level === "alert" ? "255,90,90" : level === "warn" ? "245,185,90" : "0,229,255";
      for (let i = 1; i <= 3; i++) { ctx.strokeStyle = `rgba(${col},0.16)`; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(cx, cy, R * i / 3, Math.PI, 0); ctx.stroke(); }
      sweep += 0.012; const a = Math.PI + (Math.sin(sweep) * 0.5 + 0.5) * Math.PI;
      const grad = ctx.createLinearGradient(cx, cy, cx + Math.cos(a) * R, cy + Math.sin(a) * R);
      grad.addColorStop(0, `rgba(${col},0.5)`); grad.addColorStop(1, `rgba(${col},0)`);
      ctx.strokeStyle = grad; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); ctx.stroke();
    }

    function setLevel(l) {
      level = l;
      cstate.textContent = l === "alert" ? "THREAT DETECTED" : l === "warn" ? "ELEVATED" : "ALL CLEAR";
      cstate.className = "dm-radar-state " + l;
      document.body.dataset.threat = l;     // bends the abyssal atmosphere
      window.__deepThreat = l;
    }

    async function load() {
      const [pred, anom, evt] = await Promise.all([
        getJSON("/threat/predictions"), getJSON("/anomaly/recent"), getJSON("/api/security/events"),
      ]);
      const preds = (pred && pred.predictions) || [];
      const anoms = (anom && anom.anomalies) || [];
      const evts = (evt && evt.events) || [];
      const items = []
        .concat(preds.map((p) => ({ k: "PREDICT", t: p.description || p.type || "threat predicted", sev: p.severity || "warn" })))
        .concat(anoms.map((a) => ({ k: "ANOMALY", t: a.description || a.message || a.type || "anomaly", sev: a.severity || "warn" })))
        .concat(evts.map((e) => ({ k: "EVENT", t: e.description || e.message || e.type || "security event", sev: e.severity || "ok" })));
      const sevRank = { critical: 3, alert: 3, high: 2, warn: 2, medium: 2 };
      const worst = items.reduce((m, it) => Math.max(m, sevRank[(it.sev || "").toLowerCase()] || 0), 0);
      setLevel(worst >= 3 ? "alert" : worst >= 2 ? "warn" : "ok");
      if (!items.length) { list.innerHTML = `<div class="dm-empty">The deep is quiet. No anomalies, no threats.</div>`; return; }
      list.innerHTML = "";
      items.slice(0, 40).forEach((it) => {
        const sev = (it.sev || "ok").toLowerCase();
        const row = $("div", "dm-threat sev-" + (sevRank[sev] >= 3 ? "alert" : sevRank[sev] >= 2 ? "warn" : "ok"));
        row.innerHTML = `<span class="dm-threat-k">${it.k}</span><span class="dm-threat-t">${strip(it.t).slice(0, 120)}</span>`;
        list.appendChild(row);
      });
      reveal(list);
      try { window.DeepInvestigate && DeepInvestigate.linkify(list); } catch (_) {}
    }

    sizeRadar(); drawRadar(); load();
    const timer = setInterval(load, 12000);
    win._stop = () => { clearInterval(timer); cancelAnimationFrame(raf); };
    win._resize = sizeRadar;
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * 4) EVOLUTION LAB
   * ═════════════════════════════════════════════════════════════════════ */
  function buildEvolution(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-evo-stats" id="evoStats"></div>
       <div class="dm-sub">CURRENT SELF-PROMPT</div>
       <pre class="dm-prompt" id="evoPrompt">loading…</pre>
       <div class="dm-sub">LESSONS LEARNED</div>
       <div class="dm-lessons" id="evoLessons"></div>`;
    async function load() {
      const [cp, les, st] = await Promise.all([
        getJSON("/api/evolution/current-prompt"), getJSON("/api/evolution/lessons"), getJSON("/api/evolution/stats"),
      ]);
      const stats = body.querySelector("#evoStats");
      if (st) {
        const q = Math.round((st.avg_quality || 0) * 100);
        stats.innerHTML =
          `<div class="dm-gauge"><svg viewBox="0 0 36 36"><circle class="g-bg" cx="18" cy="18" r="15"/><circle class="g-fg" cx="18" cy="18" r="15" stroke-dasharray="${q * 0.942} 999"/></svg><span>${q}<small>%</small></span><label>quality</label></div>
           <div class="dm-kv"><b>${st.total_conversations ?? 0}</b><span>conversations</span></div>
           <div class="dm-kv"><b>${st.total_turns ?? 0}</b><span>turns</span></div>
           <div class="dm-kv"><b>${st.lessons_learned ?? 0}</b><span>lessons</span></div>`;
      }
      // typewriter the prompt
      const pre = body.querySelector("#evoPrompt");
      const txt = (cp && cp.prompt) || "(no prompt)";
      let i = 0; (function type() { if (i <= txt.length) { pre.textContent = txt.slice(0, i); i += 6; pre.scrollTop = pre.scrollHeight; setTimeout(type, 8); } })();
      const lc = body.querySelector("#evoLessons");
      const lessons = (les && les.lessons) || [];
      lc.innerHTML = lessons.length ? lessons.map((l) => `<div class="dm-lesson">✦ ${l}</div>`).join("") : `<div class="dm-empty">No lessons distilled yet.</div>`;
      reveal(lc);
    }
    load();
    win._stop = () => {};
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * REGISTER + BOOT
   * ═════════════════════════════════════════════════════════════════════ */
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    HUD.registerApp({
      id: "research", title: "Research Feed", icon: "≈", anchor: "core",
      anchorAngle: -Math.PI * 0.28, anchorDist: Math.min(innerWidth, innerHeight) * 0.34,
      width: 440, height: 460, minWidth: 320, minHeight: 260,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 7h16M4 12h16M4 17h10"/><circle cx="19" cy="17" r="2.5"/></svg>',
      build: buildResearch, onClose: (w) => w._stop && w._stop(),
    });
    HUD.registerApp({
      id: "threat", title: "Threat · Anomaly", icon: "◬", anchor: "core",
      anchorAngle: Math.PI * 0.28, anchorDist: Math.min(innerWidth, innerHeight) * 0.34,
      width: 420, height: 440, minWidth: 300, minHeight: 260,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M12 8v5M12 16h.01"/></svg>',
      build: buildThreat, onClose: (w) => w._stop && w._stop(), onResize: (a, b, w) => w._resize && w._resize(),
    });
    HUD.registerApp({
      id: "evolution", title: "Evolution Lab", icon: "❖", anchor: "core",
      anchorAngle: Math.PI * 0.72, anchorDist: Math.min(innerWidth, innerHeight) * 0.34,
      width: 480, height: 480, minWidth: 340, minHeight: 300,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3a9 9 0 1 0 9 9"/><path d="M21 3v6h-6"/><circle cx="12" cy="12" r="2.4"/></svg>',
      build: buildEvolution, onClose: (w) => w._stop && w._stop(),
    });
  }

  function boot() {
    register();
    // briefing rises after the orb has coalesced (~boot overlay fade)
    setTimeout(surfaceReport, 3600);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.DeepModules = { briefing: surfaceReport };
  console.log("[DEEP] Intelligence modules online ✓");
})();
