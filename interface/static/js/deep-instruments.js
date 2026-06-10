/* ============================================================================
 * DEEP — CINEMATIC INSTRUMENTS
 * ----------------------------------------------------------------------------
 *   8. RF Spectrum Analyzer — live Wi-Fi channel spectrum (2.4 / 5 GHz), each
 *      AP a glowing bell at its channel, height = signal, congestion heat.
 *   9. Proximity Globe — you at the centre, nearby Wi-Fi/BT devices orbiting in
 *      a rotating 3D sphere; trackers flare red; signal beams to the core.
 *  10. Geo-Intel Map — investigated public IPs plotted on a world graticule with
 *      light-arcs from your location.
 *
 * All canvas, abyssal palette, real data, _stop on close. HUD apps.
 * ========================================================================== */
(function () {
  "use strict";
  async function getJSON(u, o) { try { const r = await fetch(u, o); return r.ok ? await r.json() : null; } catch (_) { return null; } }
  function dpr() { return Math.min(window.devicePixelRatio || 1, 2); }
  function sizeCanvas(cv, stage) { const r = stage.getBoundingClientRect(); const d = dpr(); cv.width = r.width * d; cv.height = r.height * d; cv.style.width = r.width + "px"; cv.style.height = r.height + "px"; const c = cv.getContext("2d"); c.setTransform(d, 0, 0, d, 0, 0); return { w: r.width, h: r.height, c }; }

  /* ═══ 8) RF SPECTRUM ANALYZER ═══════════════════════════════════════════ */
  const CH_24 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];
  const CH_5 = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161, 165];
  function buildSpectrum(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-toolbar"><span class="dm-stat" id="rfStat">scanning…</span><span style="flex:1"></span>
         <button class="hud-btn rf-band" data-band="2.4">2.4 GHz</button>
         <button class="hud-btn rf-band active" data-band="5">5 GHz</button></div>
       <div class="ins-stage" style="flex:1;position:relative"><canvas></canvas></div>`;
    const stage = body.querySelector(".ins-stage"), cv = stage.querySelector("canvas");
    const statEl = body.querySelector("#rfStat");
    let W = 0, H = 0, c = null, raf = 0, band = "5", aps = [], t0 = performance.now();
    function size() { const s = sizeCanvas(cv, stage); W = s.w; H = s.h; c = s.c; }
    body.querySelectorAll(".rf-band").forEach((b) => b.addEventListener("click", () => {
      band = b.dataset.band; body.querySelectorAll(".rf-band").forEach((x) => x.classList.toggle("active", x === b));
    }));
    async function load() {
      const d = await getJSON("/network/proximity/wifi");
      aps = (d && d.aps || []).filter((a) => a.channel > 0);
      const n24 = aps.filter((a) => a.channel <= 14).length, n5 = aps.length - n24;
      statEl.innerHTML = `<b>${aps.length}</b> APs · 2.4: ${n24} · 5: ${n5}`;
    }
    function draw() {
      raf = requestAnimationFrame(draw); if (!c) return;
      const t = (performance.now() - t0) / 1000;
      c.clearRect(0, 0, W, H);
      const chans = band === "2.4" ? CH_24 : CH_5;
      const padL = 8, padR = 8, padB = 22, top = 10;
      const plotW = W - padL - padR, plotH = H - padB - top;
      const x = (i) => padL + (plotW) * (i / (chans.length - 1));
      const teal = band === "2.4" ? "0,255,209" : "0,229,255";
      // grid + channel labels
      c.strokeStyle = "rgba(0,229,255,0.08)"; c.lineWidth = 1; c.fillStyle = "rgba(190,240,255,0.4)"; c.font = '600 8px "JetBrains Mono",monospace'; c.textAlign = "center";
      chans.forEach((ch, i) => { const xx = x(i); c.beginPath(); c.moveTo(xx, top); c.lineTo(xx, top + plotH); c.stroke(); if (i % (band === "2.4" ? 1 : 2) === 0) c.fillText(ch, xx, H - 8); });
      c.strokeStyle = "rgba(0,229,255,0.16)"; c.beginPath(); c.moveTo(padL, top + plotH); c.lineTo(W - padR, top + plotH); c.stroke();
      // congestion: sum bells per channel
      const apsB = aps.filter((a) => band === "2.4" ? a.channel <= 14 : a.channel > 14);
      // draw each AP as a gaussian bell at its channel
      apsB.forEach((a) => {
        const idx = chans.indexOf(a.channel); if (idx < 0) return;
        const cx = x(idx);
        const lvl = Math.max(0, Math.min(1, (a.signal_dbm + 100) / 65));   // -100..-35 → 0..1
        const peak = top + plotH - lvl * plotH * 0.92;
        const width = plotW / chans.length * (band === "2.4" ? 2.2 : 1.4);
        const pulse = 1 + Math.sin(t * 2 + idx) * 0.03;
        const grad = c.createLinearGradient(0, peak, 0, top + plotH);
        grad.addColorStop(0, `rgba(${teal},${0.5 + lvl * 0.4})`); grad.addColorStop(1, `rgba(${teal},0.02)`);
        c.fillStyle = grad; c.beginPath(); c.moveTo(cx - width, top + plotH);
        for (let dx = -width; dx <= width; dx += 3) { const yy = (top + plotH) - (lvl * plotH * 0.92) * Math.exp(-(dx * dx) / (2 * (width / 2.4) * (width / 2.4))) * pulse; c.lineTo(cx + dx, yy); }
        c.lineTo(cx + width, top + plotH); c.closePath(); c.fill();
        // crest glow
        c.fillStyle = `rgba(255,255,255,0.9)`; c.beginPath(); c.arc(cx, peak, 1.6, 0, Math.PI * 2); c.fill();
        c.fillStyle = `rgba(${teal},0.8)`; c.font = '500 7px "JetBrains Mono",monospace';
        const name = (a.ssid && !a.ssid.includes(":")) ? a.ssid : (a.vendor || "");
        if (lvl > 0.45 && name) c.fillText(String(name).slice(0, 10), cx, peak - 5);
      });
      // sweep line
      const sx = padL + ((t * 60) % plotW);
      c.strokeStyle = `rgba(${teal},0.25)`; c.lineWidth = 1; c.beginPath(); c.moveTo(sx, top); c.lineTo(sx, top + plotH); c.stroke();
    }
    size(); load(); draw();
    const tm = setInterval(load, 8000);
    win._stop = () => { clearInterval(tm); cancelAnimationFrame(raf); };
    win._resize = size;
  }

  /* ═══ 9) PROXIMITY GLOBE ═══════════════════════════════════════════════ */
  function buildGlobe(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML = `<div class="dm-toolbar"><span class="dm-stat" id="glStat">scanning…</span></div>
      <div class="ins-stage" style="flex:1;position:relative"><canvas></canvas></div>`;
    const stage = body.querySelector(".ins-stage"), cv = stage.querySelector("canvas");
    const statEl = body.querySelector("#glStat");
    let W = 0, H = 0, c = null, raf = 0, pts = [], rot = 0;
    function size() { const s = sizeCanvas(cv, stage); W = s.w; H = s.h; c = s.c; }
    function hash(s) { let h = 0; s = String(s); for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffff; return h / 0xffff; }
    async function load() {
      const [wifi, bt] = await Promise.all([getJSON("/network/proximity/wifi"), getJSON("/network/proximity/bt")]);
      const aps = (wifi && wifi.aps || []), bts = (bt && bt.devices || []);
      const all = aps.map((a) => ({ id: a.bssid, name: a.ssid || a.bssid, sig: a.signal_dbm, kind: "wifi", mine: a.is_yours }))
        .concat(bts.map((d) => ({ id: d.mac, name: d.name || d.mac, sig: d.rssi, kind: "bt", tracker: d.is_tracker, mine: d.is_yours })));
      pts = all.slice(0, 80).map((d) => { const a = hash(d.id) * Math.PI * 2, ph = (hash(d.id + "p") - 0.5) * Math.PI; const depth = Math.min(1, Math.max(0.15, 1 - (d.sig + 100) / 70)); return { a, ph, depth, d }; });
      statEl.innerHTML = `<b>${aps.length}</b> wifi · <b>${bts.length}</b> bt orbiting`;
    }
    function draw() {
      raf = requestAnimationFrame(draw); if (!c) return;
      rot += 0.0035; c.clearRect(0, 0, W, H);
      const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.4, tilt = 0.55;
      // sphere wireframe
      c.strokeStyle = "rgba(0,229,255,0.10)"; c.lineWidth = 1;
      for (let i = 1; i <= 3; i++) { c.beginPath(); c.ellipse(cx, cy, R * i / 3, R * i / 3 * tilt, 0, 0, Math.PI * 2); c.stroke(); }
      for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI + rot; c.beginPath(); c.ellipse(cx, cy, R, R * tilt, 0, 0, Math.PI * 2); c.stroke(); }
      c.beginPath(); c.ellipse(cx, cy, R * 0.02, R * 0.02, 0, 0, Math.PI * 2); c.fillStyle = "rgba(0,255,209,0.9)"; c.fill();
      // points (sorted back→front)
      const proj = pts.map((p) => { const a = p.a + rot; const X = Math.cos(p.ph) * Math.sin(a), Z = Math.cos(p.ph) * Math.cos(a), Y = Math.sin(p.ph); const rr = R * (0.45 + p.depth * 0.55); return { x: cx + X * rr, y: cy + Y * rr * tilt, z: Z, p }; }).sort((u, v) => u.z - v.z);
      proj.forEach((o) => {
        const front = (o.z + 1) / 2, alpha = 0.25 + front * 0.7, sz = 1.5 + front * 2.5;
        const tr = o.p.d.tracker, col = tr ? "255,90,90" : o.p.d.kind === "bt" ? "0,255,209" : "0,229,255";
        c.strokeStyle = `rgba(${col},${alpha * 0.18})`; c.lineWidth = 0.6; c.beginPath(); c.moveTo(cx, cy); c.lineTo(o.x, o.y); c.stroke();
        if (tr) { const pl = 0.5 + 0.5 * Math.sin(performance.now() / 120); c.strokeStyle = `rgba(255,90,90,${pl * alpha})`; c.beginPath(); c.arc(o.x, o.y, sz + 3 + pl * 3, 0, Math.PI * 2); c.stroke(); }
        const g = c.createRadialGradient(o.x, o.y, 0, o.x, o.y, sz * 3); g.addColorStop(0, `rgba(${col},${alpha})`); g.addColorStop(1, `rgba(${col},0)`);
        c.fillStyle = g; c.beginPath(); c.arc(o.x, o.y, sz * 3, 0, Math.PI * 2); c.fill();
        c.fillStyle = `rgba(${col},${alpha})`; c.beginPath(); c.arc(o.x, o.y, sz, 0, Math.PI * 2); c.fill();
      });
    }
    size(); load(); draw();
    const tm = setInterval(load, 10000);
    win._stop = () => { clearInterval(tm); cancelAnimationFrame(raf); };
    win._resize = size;
  }

  /* ═══ 10) GEO-INTEL MAP ════════════════════════════════════════════════ */
  function buildGeo(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-toolbar"><input class="hud-input" id="geoIn" placeholder="Plot an IP / host…" style="flex:1;min-width:60px">
         <button class="hud-btn" id="geoAdd">Trace ▸</button></div>
       <div class="ins-stage" style="flex:1;position:relative"><canvas></canvas></div>`;
    const stage = body.querySelector(".ins-stage"), cv = stage.querySelector("canvas");
    let W = 0, H = 0, c = null, raf = 0, home = null, marks = [];
    function size() { const s = sizeCanvas(cv, stage); W = s.w; H = s.h; c = s.c; }
    const X = (lon) => ((lon + 180) / 360) * W, Y = (lat) => ((90 - lat) / 180) * H;
    async function setHome() { const d = await getJSON("/api/geo/self"); if (d && d.lat != null) home = { lat: d.lat, lon: d.lon, label: d.city || d.country || "HOME" }; }
    async function plot(target) {
      const d = await getJSON("/api/investigate?target=" + encodeURIComponent(target));
      if (d && d.geo && d.geo.lat != null) marks.push({ lat: d.geo.lat, lon: d.geo.lon, label: target, sub: (d.geo.city || "") + " · " + (d.geo.isp || d.geo.org || ""), born: performance.now(), risk: d.risk === "elevated" });
    }
    body.querySelector("#geoAdd").addEventListener("click", () => { const v = body.querySelector("#geoIn").value.trim(); if (v) { plot(v); body.querySelector("#geoIn").value = ""; } });
    body.querySelector("#geoIn").addEventListener("keydown", (e) => { if (e.key === "Enter") body.querySelector("#geoAdd").click(); });
    function draw() {
      raf = requestAnimationFrame(draw); if (!c) return;
      const t = performance.now(); c.clearRect(0, 0, W, H);
      // graticule
      c.strokeStyle = "rgba(0,229,255,0.08)"; c.lineWidth = 1;
      for (let lon = -180; lon <= 180; lon += 30) { c.beginPath(); c.moveTo(X(lon), 0); c.lineTo(X(lon), H); c.stroke(); }
      for (let lat = -60; lat <= 60; lat += 30) { c.beginPath(); c.moveTo(0, Y(lat)); c.lineTo(W, Y(lat)); c.stroke(); }
      c.strokeStyle = "rgba(0,229,255,0.18)"; c.beginPath(); c.moveTo(0, Y(0)); c.lineTo(W, Y(0)); c.stroke();
      // home
      if (home) { const hx = X(home.lon), hy = Y(home.lat); const pl = 0.5 + 0.5 * Math.sin(t / 500); c.fillStyle = "rgba(0,255,209,0.95)"; c.beginPath(); c.arc(hx, hy, 3, 0, Math.PI * 2); c.fill(); c.strokeStyle = `rgba(0,255,209,${pl * 0.6})`; c.beginPath(); c.arc(hx, hy, 4 + pl * 8, 0, Math.PI * 2); c.stroke(); c.fillStyle = "rgba(0,255,209,0.85)"; c.font = '600 8px "JetBrains Mono",monospace'; c.textAlign = "center"; c.fillText("◆ " + (home.label || "HOME"), hx, hy - 12); }
      // marks + arcs
      marks.forEach((m) => {
        const mx = X(m.lon), my = Y(m.lat); const col = m.risk ? "255,90,90" : "0,229,255";
        if (home) { const hx = X(home.lon), hy = Y(home.lat); const grow = Math.min(1, (t - m.born) / 900); const midx = (hx + mx) / 2, midy = Math.min(hy, my) - Math.abs(mx - hx) * 0.28; c.strokeStyle = `rgba(${col},0.5)`; c.lineWidth = 1.2; c.beginPath(); c.moveTo(hx, hy); for (let s = 0; s <= grow; s += 0.04) { const ix = (1 - s) * (1 - s) * hx + 2 * (1 - s) * s * midx + s * s * mx; const iy = (1 - s) * (1 - s) * hy + 2 * (1 - s) * s * midy + s * s * my; c.lineTo(ix, iy); } c.stroke(); const pp = (t / 1400) % 1; const px = (1 - pp) * (1 - pp) * hx + 2 * (1 - pp) * pp * midx + pp * pp * mx, py = (1 - pp) * (1 - pp) * hy + 2 * (1 - pp) * pp * midy + pp * pp * my; c.fillStyle = `rgba(255,255,255,0.9)`; c.beginPath(); c.arc(px, py, 1.6, 0, Math.PI * 2); c.fill(); }
        const pl = 0.5 + 0.5 * Math.sin(t / 400); const g = c.createRadialGradient(mx, my, 0, mx, my, 9); g.addColorStop(0, `rgba(${col},0.7)`); g.addColorStop(1, `rgba(${col},0)`); c.fillStyle = g; c.beginPath(); c.arc(mx, my, 9, 0, Math.PI * 2); c.fill();
        c.fillStyle = `rgba(${col},0.95)`; c.beginPath(); c.arc(mx, my, 2.4, 0, Math.PI * 2); c.fill();
        c.fillStyle = `rgba(214,247,255,0.85)`; c.font = '600 8px "JetBrains Mono",monospace'; c.textAlign = "left"; c.fillText(m.label, mx + 7, my - 4); c.fillStyle = "rgba(190,240,255,0.45)"; c.font = '400 7px "JetBrains Mono",monospace'; c.fillText(String(m.sub).slice(0, 28), mx + 7, my + 5);
      });
    }
    size(); setHome(); draw();
    [["8.8.8.8"], ["1.1.1.1"]].forEach((x, i) => setTimeout(() => plot(x[0]), 600 + i * 500));
    win._stop = () => cancelAnimationFrame(raf);
    win._resize = size;
  }

  /* ═══ 11) PRESENCE TIMELINE — when each device is around (hour-of-day heatmap) ═══ */
  function strip(h) { const d = document.createElement("div"); d.innerHTML = h || ""; return (d.textContent || "").trim(); }
  function esc(s) { return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
  function buildTimeline(body, win) {
    body.style.cssText = "display:flex;flex-direction:column";
    body.innerHTML =
      `<div class="dm-toolbar"><span class="dm-stat" id="tlStat">reading presence history…</span></div>
       <div id="tlStage" style="flex:1;overflow:auto;padding:8px 10px 12px">
         <div class="dm-empty">Loading…</div></div>`;
    const stage = body.querySelector("#tlStage"), statEl = body.querySelector("#tlStat");
    let timer = 0;
    async function load() {
      const d = await getJSON("/network/proximity/timeline?limit=22");
      const devs = (d && d.devices) || [];
      const cur = (d && typeof d.current_hour === "number") ? d.current_hour : -1;
      statEl.innerHTML = `<b>${devs.length}</b> devices · presence by hour (UTC)${cur >= 0 ? " · now " + cur + ":00" : ""}`;
      if (!devs.length) { stage.innerHTML = `<div class="dm-empty">No presence history yet — DEEP is still learning your environment.</div>`; return; }
      let html = '<div class="tl-grid">';
      html += '<div class="tl-row tl-head"><div class="tl-label"></div>' +
        Array.from({ length: 24 }, (_, h) => `<div class="tl-hh${h === cur ? " now" : ""}">${h % 6 === 0 ? h : ""}</div>`).join("") + "</div>";
      devs.forEach((dev) => {
        const max = Math.max.apply(null, dev.hours.concat([1]));
        html += `<div class="tl-row"><div class="tl-label" title="${esc(dev.id)} · ${esc(dev.vendor || "")} · seen ${dev.seen_count}×">${esc(strip(dev.name)).slice(0, 18) || "(hidden)"}</div>`;
        html += dev.hours.map((v, h) => `<div class="tl-cell${h === cur ? " now" : ""}" style="--a:${(v / max).toFixed(2)}" title="${v}× at ${h}:00"></div>`).join("");
        html += "</div>";
      });
      html += "</div>";
      stage.innerHTML = html;
    }
    load(); timer = setInterval(load, 30000);
    win._stop = () => clearInterval(timer);
  }

  /* ═══ REGISTER ═════════════════════════════════════════════════════════ */
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    const dist = Math.min(innerWidth, innerHeight) * 0.34;
    HUD.registerApp({ id: "spectrum", title: "RF Spectrum", icon: "▮", anchor: "core", anchorAngle: -Math.PI * 0.34, anchorDist: dist,
      width: 500, height: 360, minWidth: 340, minHeight: 240,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 18l3-6 3 3 3-9 3 12 3-6 3 4"/></svg>',
      build: buildSpectrum, onClose: (w) => w._stop && w._stop(), onResize: (a, b, w) => w._resize && w._resize() });
    HUD.registerApp({ id: "globe", title: "Proximity Globe", icon: "◉", anchor: "core", anchorAngle: Math.PI * 0.34, anchorDist: dist,
      width: 420, height: 420, minWidth: 300, minHeight: 300,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="9" ry="3.6"/><path d="M12 3v18"/></svg>',
      build: buildGlobe, onClose: (w) => w._stop && w._stop(), onResize: (a, b, w) => w._resize && w._resize() });
    HUD.registerApp({ id: "geomap", title: "Geo-Intel Map", icon: "⊕", anchor: "core", anchorAngle: Math.PI * 0.66, anchorDist: dist,
      width: 560, height: 380, minWidth: 380, minHeight: 240,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>',
      build: buildGeo, onClose: (w) => w._stop && w._stop(), onResize: (a, b, w) => w._resize && w._resize() });
    HUD.registerApp({ id: "timeline", title: "Presence Timeline", icon: "▦", anchor: "core", anchorAngle: -Math.PI * 0.66, anchorDist: dist,
      width: 560, height: 400, minWidth: 380, minHeight: 240,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 12h4M3 7h4M3 17h4"/><rect x="9" y="5" width="12" height="3" rx="1"/><rect x="9" y="10.5" width="8" height="3" rx="1"/><rect x="9" y="16" width="10" height="3" rx="1"/></svg>',
      build: buildTimeline, onClose: (w) => w._stop && w._stop() });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", register);
  else register();
  console.log("[DEEP] Cinematic instruments online ✓");
})();
