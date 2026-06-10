/* ============================================================================
 * DEEP — EMPATHY LAYER  (mood + ambient toasts)
 * ----------------------------------------------------------------------------
 * Gives DEEP the "E" in its name. Two parts:
 *   • MOOD — a global affective state (calm | focus | warn | alert) derived from
 *     threat level + the sentiment of DEEP's latest reply. It tints the Liquid
 *     Orb (via body[data-mood]) and changes its churn speed (deep-orb reads
 *     window.DeepMood).
 *   • TOASTS — bioluminescent notifications that "surface from the deep" when
 *     real events fire (new research finding, threat/anomaly, approval needed),
 *     then sink away. Other modules can call window.DeepToast.show(...).
 *
 * Classic script. Polls the same REST surface the windows use, comparing deltas.
 * ========================================================================== */
(function () {
  "use strict";

  async function getJSON(u) { try { const r = await fetch(u); return r.ok ? await r.json() : null; } catch (_) { return null; } }
  function sfx(n) { try { window.SFX && SFX.play(n); } catch (_) {} }

  /* ── MOOD ────────────────────────────────────────────────────────────────── */
  let moodTimer = 0;
  function setMood(m, ttl) {
    const rank = { calm: 0, focus: 1, warn: 2, alert: 3 };
    m = m in rank ? m : "calm";
    window.DeepMood = m;
    document.body.dataset.mood = m;
    clearTimeout(moodTimer);
    if (ttl && m !== "calm") moodTimer = setTimeout(() => setMood("calm"), ttl);
  }
  setMood("calm");

  const NEG = /\b(alert|warning|threat|danger|critical|error|fail|breach|suspicious|unable|cannot|sorry|apolog|problem|issue|down|offline)\b/i;
  const POS = /\b(done|complete|success|ready|nominal|secure|all clear|great|excellent|certainly|of course|happy|glad|sure)\b/i;

  function classify(text) {
    if (!text) return null;
    if (NEG.test(text)) return "warn";
    if (POS.test(text)) return "calm";
    return "focus";
  }

  // Watch DEEP's replies and reflect their tone in the core.
  function watchChat() {
    const box = document.getElementById("chatContainer");
    if (!box) return setTimeout(watchChat, 500);
    const obs = new MutationObserver((muts) => {
      for (const mu of muts) {
        for (const node of mu.addedNodes) {
          if (node.nodeType !== 1) continue;
          const el = node;
          const isAssistant = el.className && /assistant|ai|deep|message-ai|msg-ai/i.test(el.className) && !/user/i.test(el.className);
          if (isAssistant || (el.querySelector && el.querySelector(".message-ai, .msg-ai"))) {
            const txt = (el.textContent || "").slice(0, 600);
            const mood = classify(txt);
            if (mood && (window.__deepThreat || "ok") === "ok") setMood(mood, 12000);
          }
        }
      }
    });
    obs.observe(box, { childList: true, subtree: true });
  }

  // Threat level (set by the Threat console) always wins.
  function pollThreat() {
    const t = window.__deepThreat;
    if (t === "alert") setMood("alert");
    else if (t === "warn" && (window.DeepMood !== "alert")) setMood("warn");
  }

  /* ── TOASTS ──────────────────────────────────────────────────────────────── */
  let layer;
  function ensureLayer() {
    if (layer) return layer;
    layer = document.createElement("div");
    layer.className = "deep-toasts";
    layer.id = "deepToasts";
    layer.setAttribute("role", "status");
    layer.setAttribute("aria-live", "polite");
    document.body.appendChild(layer);
    return layer;
  }
  const ICONS = { info: "≈", research: "≈", threat: "◬", alert: "◬", approval: "✓", success: "✦" };
  function show(opts) {
    opts = opts || {};
    ensureLayer();
    const t = document.createElement("div");
    t.className = "deep-toast lvl-" + (opts.level || "info");
    t.innerHTML =
      `<span class="dt-icon">${opts.icon || ICONS[opts.level] || ICONS[opts.kind] || "≈"}</span>
       <div class="dt-body"><div class="dt-title">${(opts.title || "").replace(/</g, "&lt;")}</div>
       ${opts.body ? `<div class="dt-text">${String(opts.body).replace(/</g, "&lt;").slice(0, 120)}</div>` : ""}</div>`;
    if (opts.onClick) { t.style.cursor = "pointer"; t.addEventListener("click", () => { try { opts.onClick(); } catch (_) {} dismiss(); }); }
    layer.appendChild(t);
    requestAnimationFrame(() => t.classList.add("show"));
    sfx(opts.level === "alert" ? "alert" : "blip");
    const ttl = opts.ttl || 7000;
    const timer = setTimeout(dismiss, ttl);
    function dismiss() { clearTimeout(timer); t.classList.remove("show"); t.classList.add("sink"); setTimeout(() => t.remove(), 600); }
    t.addEventListener("pointerenter", () => clearTimeout(timer));
    return t;
  }

  /* ── EVENT POLLING → toasts ──────────────────────────────────────────────── */
  const seen = { findings: -1, threats: -1, approvals: -1 };
  async function poll() {
    pollThreat();

    const rs = await getJSON("/api/research/stats");
    if (rs && typeof rs.total_findings === "number") {
      if (seen.findings >= 0 && rs.total_findings > seen.findings) {
        const d = await getJSON("/api/research/findings");
        const newest = d && d.findings && d.findings[0];
        show({ level: "research", title: (rs.total_findings - seen.findings) + " new finding(s)", body: newest && newest.title, onClick: () => window.HUD && HUD.open("research") });
      }
      seen.findings = rs.total_findings;
    }

    const ap = await getJSON("/api/interactive/pending");
    const apN = (ap && ap.pending || []).length;
    if (seen.approvals >= 0 && apN > seen.approvals) {
      show({ level: "approval", title: "DEEP requests your approval", body: "An action is awaiting your decision.", ttl: 15000, onClick: () => window.HUD && HUD.open("approvals") });
    }
    seen.approvals = apN;

    const an = await getJSON("/anomaly/recent");
    const pr = await getJSON("/threat/predictions");
    const threatN = ((an && an.anomalies || []).length) + ((pr && pr.predictions || []).length);
    if (seen.threats >= 0 && threatN > seen.threats) {
      setMood("alert", 20000);
      show({ level: "alert", title: "Anomaly detected", body: "DEEP flagged unusual activity.", ttl: 12000, onClick: () => window.HUD && HUD.open("threat") });
    }
    seen.threats = threatN;
  }

  function boot() {
    watchChat();
    poll();
    setInterval(poll, 12000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.DeepToast = { show };
  window.DeepMoodSet = setMood;
  console.log("[DEEP] Empathy layer (mood + toasts) online ✓");
})();
