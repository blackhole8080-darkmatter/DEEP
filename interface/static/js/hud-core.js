/* ============================================================================
 * DEEP HUD CORE — the spatial windowing layer
 * ----------------------------------------------------------------------------
 * A lightweight, dependency-free window manager that powers the floating,
 * draggable, glassmorphic micro-apps (Memory Ring graph, Terminal, Math/Physics
 * simulator) and the Aegis Shield indicator. Classic (non-module) script so it
 * shares the global lexical scope with app.js — it can read ngCx / ngCy /
 * orbTime / ngAccent / state defined there.
 *
 * Public API (window.HUD):
 *   HUD.registerApp({ id, title, icon, anchor, build, onOpen, onClose })
 *   HUD.open(id)            HUD.close(id)        HUD.toggle(id)
 *   HUD.spawn(opts)         -> low-level window factory, returns HudWindow
 *   HUD.setDockStatus(id, 'ok'|'warn'|'alert')
 *   HUD.coreCenter()        -> { x, y } of the live yantra bindu
 * ========================================================================== */
(function () {
  "use strict";

  // ── Live core (bindu) position — falls back to viewport centre ───────────
  function coreCenter() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }

  let zTop = 40;
  const wins = new Map();   // id -> HudWindow
  const apps = new Map();   // id -> app descriptor
  let dockEl = null;

  // ── Layout geometry — keep floating windows clear of the status bar (top)
  //    and the app dock (right), and well-distributed on large/full-screen
  //    viewports instead of clustered around the core. ───────────────────────
  const MARGIN = { top: 72, right: 16, bottom: 16, left: 16 };
  function usableRect() {
    let right = MARGIN.right;
    if (dockEl) { const r = dockEl.getBoundingClientRect(); if (r.width) right = Math.max(right, window.innerWidth - r.left + 14); }
    return { x0: MARGIN.left, y0: MARGIN.top, x1: window.innerWidth - right, y1: window.innerHeight - MARGIN.bottom };
  }
  function rectsOverlap(a, b, pad) { pad = pad || 0; return !(a.left + a.w + pad <= b.left || b.left + b.w + pad <= a.left || a.top + a.h + pad <= b.top || b.top + b.h + pad <= a.top); }
  function openRects(except) {
    const out = [];
    for (const w of wins.values()) {
      if (w.minimized || w === except || !w.el) continue;
      out.push({ left: w.el.offsetLeft, top: w.el.offsetTop, w: w.el.offsetWidth, h: w.el.offsetHeight });
    }
    return out;
  }
  // Find a non-overlapping slot for a w×h window, preferring a spot near `pref`.
  function findSlot(w, h, pref) {
    const R = usableRect();
    const cx = (x) => Math.max(R.x0, Math.min(x, R.x1 - w));
    const cy = (y) => Math.max(R.y0, Math.min(y, R.y1 - h));
    const existing = openRects();
    const fits = (x, y) => !existing.some((e) => rectsOverlap({ left: x, top: y, w, h }, e, 14));
    const cands = [];
    if (pref) cands.push({ x: cx(pref.left), y: cy(pref.top) });
    const cols = 5, rows = 4;
    for (let r = 0; r <= rows; r++) for (let c = 0; c <= cols; c++) {
      cands.push({ x: cx(R.x0 + (R.x1 - R.x0 - w) * c / cols), y: cy(R.y0 + (R.y1 - R.y0 - h) * r / rows) });
    }
    const free = cands.filter((p) => fits(p.x, p.y));
    if (free.length) {
      const tx = pref ? cx(pref.left) : (R.x0 + R.x1 - w) / 2, ty = pref ? cy(pref.top) : (R.y0 + R.y1 - h) / 2;
      free.sort((a, b) => ((a.x - tx) ** 2 + (a.y - ty) ** 2) - ((b.x - tx) ** 2 + (b.y - ty) ** 2));
      return { left: free[0].x, top: free[0].y };
    }
    const n = wins.size;                       // screen full → gentle cascade
    const base = pref || { left: (R.x0 + R.x1 - w) / 2, top: (R.y0 + R.y1 - h) / 2 };
    return { left: cx(base.left + (n % 6) * 30), top: cy(base.top + (n % 6) * 30) };
  }
  // Tidy all open windows into a balanced grid that fills the usable area.
  function arrange() {
    const R = usableRect();
    const list = [...wins.values()].filter((w) => !w.minimized && w.el);
    if (!list.length) return;
    const avgW = list.reduce((s, w) => s + w.el.offsetWidth, 0) / list.length;
    const cols = Math.max(1, Math.min(list.length, Math.floor((R.x1 - R.x0) / (avgW + 18)) || 1));
    const rows = Math.ceil(list.length / cols);
    const cellW = (R.x1 - R.x0) / cols, cellH = (R.y1 - R.y0) / rows;
    list.forEach((w, i) => {
      const c = i % cols, r = Math.floor(i / cols);
      const ww = w.el.offsetWidth, hh = w.el.offsetHeight;
      const x = Math.max(R.x0, Math.min(R.x0 + c * cellW + (cellW - ww) / 2, R.x1 - ww));
      const y = Math.max(R.y0, Math.min(R.y0 + r * cellH + (cellH - hh) / 2, R.y1 - hh));
      w.el.style.transition = "left .36s var(--dpx-ease, ease), top .36s var(--dpx-ease, ease)";
      w.el.style.left = x + "px"; w.el.style.top = y + "px";
      setTimeout(() => { if (w.el) w.el.style.transition = ""; }, 440);
    });
    try { window.SFX && SFX.play("blip"); } catch (_) {}
  }

  // ── Snap zones (drag a window to an edge/corner to tile it) ────────────────
  let snapPreview = null;
  function snapEl() {
    if (!snapPreview) { snapPreview = document.createElement("div"); snapPreview.className = "hud-snap-preview"; document.body.appendChild(snapPreview); }
    return snapPreview;
  }
  function hideSnap() { if (snapPreview) snapPreview.classList.remove("show"); }
  function showSnap(rect) {
    const el = snapEl();
    el.style.left = rect.left + "px"; el.style.top = rect.top + "px";
    el.style.width = rect.w + "px"; el.style.height = rect.h + "px";
    el.classList.add("show");
  }
  // Map a pointer position to a tiling zone within the usable rect.
  function zoneFor(px, py, R) {
    const E = 36, midX = (R.x0 + R.x1) / 2, midY = (R.y0 + R.y1) / 2;
    const halfW = (R.x1 - R.x0) / 2, halfH = (R.y1 - R.y0) / 2, fullW = R.x1 - R.x0, fullH = R.y1 - R.y0;
    const nearL = px <= R.x0 + E, nearR = px >= R.x1 - E, nearT = py <= R.y0 + E, nearB = py >= R.y1 - E;
    const top3 = py < R.y0 + fullH / 3, bot3 = py > R.y1 - fullH / 3;
    if (nearT && !nearL && !nearR) return { key: "max", left: R.x0, top: R.y0, w: fullW, h: fullH };
    if (nearL) {
      if (top3) return { key: "tl", left: R.x0, top: R.y0, w: halfW, h: halfH };
      if (bot3) return { key: "bl", left: R.x0, top: midY, w: halfW, h: halfH };
      return { key: "l", left: R.x0, top: R.y0, w: halfW, h: fullH };
    }
    if (nearR) {
      if (top3) return { key: "tr", left: midX, top: R.y0, w: halfW, h: halfH };
      if (bot3) return { key: "br", left: midX, top: midY, w: halfW, h: halfH };
      return { key: "r", left: midX, top: R.y0, w: halfW, h: fullH };
    }
    if (nearB) return { key: "b", left: R.x0, top: midY, w: fullW, h: halfH };
    return null;
  }

  // ── HudWindow ─────────────────────────────────────────────────────────────
  class HudWindow {
    constructor(opts) {
      this.id = opts.id || "win-" + Math.random().toString(36).slice(2, 8);
      this.opts = opts;
      this.minimized = false;
      this._build();
    }

    _build() {
      const o = this.opts;
      const el = document.createElement("div");
      el.className = "hud-win";
      el.dataset.app = this.id;

      const w = o.width || 420;
      const h = o.height || 320;
      // Preferred spot: 'core' apps aim at a ring around the bindu (radius scaled
      // by the larger viewport axis so they fan out on wide/full-screen displays);
      // others start near the top-left. findSlot then resolves overlaps and keeps
      // the window clear of the status bar + dock.
      let pref;
      if (o.anchor === "core") {
        const c = coreCenter();
        const ang = o.anchorAngle != null ? o.anchorAngle : -Math.PI / 4;
        const spread = Math.max(window.innerWidth, window.innerHeight);
        const dist = o.anchorDist != null ? Math.max(o.anchorDist, spread * 0.28) : spread * 0.3;
        pref = { left: c.x + Math.cos(ang) * dist - w / 2, top: c.y + Math.sin(ang) * dist - h / 2 };
      } else {
        const n = wins.size;
        pref = { left: 90 + (n % 5) * 34, top: 96 + (n % 5) * 34 };
      }
      const slot = findSlot(w, h, pref);
      let left = slot.left, top = slot.top;

      el.style.left = left + "px";
      el.style.top = top + "px";
      el.style.width = w + "px";
      el.style.height = h + "px";
      if (o.minWidth) el.style.minWidth = o.minWidth + "px";
      if (o.minHeight) el.style.minHeight = o.minHeight + "px";

      el.innerHTML =
        `<div class="hud-bar">
           <span class="hud-bar-icon">${o.icon || "◈"}</span>
           <span class="hud-bar-title">${o.title || "WINDOW"}</span>
           <span class="hud-bar-btns">
             <button class="hud-bar-btn min" title="Minimise">–</button>
             <button class="hud-bar-btn close" title="Close">✕</button>
           </span>
         </div>
         <div class="hud-body"></div>
         <div class="hud-resize"></div>`;

      document.body.appendChild(el);
      this.el = el;
      this.bar = el.querySelector(".hud-bar");
      this.body = el.querySelector(".hud-body");

      // one-shot "materialize" scan sweep on open
      const scan = document.createElement("span");
      scan.className = "hud-scan";
      el.appendChild(scan);
      setTimeout(() => scan.remove(), 700);

      el.querySelector(".hud-bar-btn.close").addEventListener("click", (e) => { e.stopPropagation(); this.close(); });
      el.querySelector(".hud-bar-btn.min").addEventListener("click", (e) => { e.stopPropagation(); this.minimize(); });
      el.addEventListener("pointerdown", () => this.focus(), true);

      this._wireDrag();
      this._wireResize();

      // Build content
      if (typeof o.build === "function") {
        try { o.build(this.body, this); } catch (err) { console.error("[HUD] build error", this.id, err); }
      }

      this.focus();
      requestAnimationFrame(() => el.classList.add("open"));
    }

    _wireDrag() {
      let sx, sy, ox, oy, dragging = false, zone = null;
      const down = (e) => {
        if (e.target.closest(".hud-bar-btn")) return;
        dragging = true; zone = null;
        // un-snap a tiled window back to its free size, centred under the cursor
        if (this.snapped && this._restore) {
          this.el.style.width = this._restore.w + "px";
          this.el.style.height = this._restore.h + "px";
          this.el.style.left = (e.clientX - this._restore.w / 2) + "px";
          this.snapped = false;
        }
        const r = this.el.getBoundingClientRect();
        sx = e.clientX; sy = e.clientY; ox = r.left; oy = r.top;
        this.bar.setPointerCapture(e.pointerId);
        this.focus();
      };
      const move = (e) => {
        if (!dragging) return;
        let nl = ox + (e.clientX - sx);
        let nt = oy + (e.clientY - sy);
        const R = usableRect(), ww = this.el.offsetWidth, hh = this.el.offsetHeight;
        // edge magnetism for free placement
        const SNAP = 9;
        if (Math.abs(nl - R.x0) < SNAP) nl = R.x0;
        if (Math.abs(nl + ww - R.x1) < SNAP) nl = R.x1 - ww;
        if (Math.abs(nt - R.y0) < SNAP) nt = R.y0;
        if (Math.abs(nt + hh - R.y1) < SNAP) nt = R.y1 - hh;
        nl = Math.max(-ww + 60, Math.min(nl, window.innerWidth - 60));
        nt = Math.max(0, Math.min(nt, window.innerHeight - 40));
        this.el.style.left = nl + "px";
        this.el.style.top = nt + "px";
        // tiling preview when the cursor reaches an edge/corner
        zone = zoneFor(e.clientX, e.clientY, R);
        if (zone) showSnap(zone); else hideSnap();
      };
      const up = (e) => {
        dragging = false;
        try { this.bar.releasePointerCapture(e.pointerId); } catch (_) {}
        hideSnap();
        if (zone) { this.applySnap(zone); zone = null; }
      };
      this.bar.addEventListener("pointerdown", down);
      this.bar.addEventListener("pointermove", move);
      this.bar.addEventListener("pointerup", up);
      this.bar.addEventListener("pointercancel", up);
    }

    // Tile the window into a snap zone, remembering its prior free size so a
    // later drag can restore it (Windows-style Snap Assist).
    applySnap(z) {
      if (!this.snapped) this._restore = { w: this.el.offsetWidth, h: this.el.offsetHeight };
      this.el.style.transition = "left .2s var(--dpx-ease, ease), top .2s var(--dpx-ease, ease), width .2s var(--dpx-ease, ease), height .2s var(--dpx-ease, ease)";
      this.el.style.left = z.left + "px"; this.el.style.top = z.top + "px";
      this.el.style.width = z.w + "px"; this.el.style.height = z.h + "px";
      this.snapped = true;   // maximised windows are also "snapped" so a drag restores them
      setTimeout(() => {
        if (!this.el) return;
        this.el.style.transition = "";
        if (typeof this.opts.onResize === "function") this.opts.onResize(this.el.offsetWidth, this.el.offsetHeight, this);
      }, 230);
      try { window.SFX && SFX.play("blip"); } catch (_) {}
    }

    _wireResize() {
      const h = this.el.querySelector(".hud-resize");
      let sw, sh, sx, sy, rz = false;
      const down = (e) => {
        rz = true; e.stopPropagation();
        const r = this.el.getBoundingClientRect();
        sw = r.width; sh = r.height; sx = e.clientX; sy = e.clientY;
        h.setPointerCapture(e.pointerId);
      };
      const move = (e) => {
        if (!rz) return;
        const nw = Math.max(this.opts.minWidth || 280, sw + (e.clientX - sx));
        const nh = Math.max(this.opts.minHeight || 160, sh + (e.clientY - sy));
        this.el.style.width = nw + "px";
        this.el.style.height = nh + "px";
        if (typeof this.opts.onResize === "function") this.opts.onResize(nw, nh, this);
      };
      const up = (e) => { rz = false; try { h.releasePointerCapture(e.pointerId); } catch (_) {} };
      h.addEventListener("pointerdown", down);
      h.addEventListener("pointermove", move);
      h.addEventListener("pointerup", up);
      h.addEventListener("pointercancel", up);
    }

    focus() {
      for (const w of wins.values()) w.el.classList.remove("focused");
      this.el.classList.add("focused");
      this.el.style.zIndex = ++zTop;
    }

    minimize() {
      this.minimized = true;
      this.el.classList.add("minimized");
      syncDock();
    }
    restore() {
      this.minimized = false;
      this.el.classList.remove("minimized");
      this.focus();
      syncDock();
    }

    close() {
      this.el.classList.remove("open");
      const app = apps.get(this.id);
      if (app && typeof app.onClose === "function") { try { app.onClose(this); } catch (_) {} }
      setTimeout(() => { this.el.remove(); }, 280);
      wins.delete(this.id);
      syncDock();
    }
  }

  // ── App registry + dock ─────────────────────────────────────────────────
  function registerApp(desc) {
    if (!desc || !desc.id) return;
    apps.set(desc.id, desc);
    buildDock();
  }

  function open(id) {
    const app = apps.get(id);
    if (!app) { console.warn("[HUD] no app", id); return null; }
    let w = wins.get(id);
    if (w) { if (w.minimized) w.restore(); else w.focus(); syncDock(); return w; }
    w = new HudWindow({
      id, title: app.title, icon: app.icon, anchor: app.anchor,
      anchorAngle: app.anchorAngle, anchorDist: app.anchorDist,
      width: app.width, height: app.height,
      minWidth: app.minWidth, minHeight: app.minHeight,
      build: app.build, onResize: app.onResize,
    });
    wins.set(id, w);
    if (typeof app.onOpen === "function") { try { app.onOpen(w); } catch (_) {} }
    syncDock();
    return w;
  }

  function close(id) { const w = wins.get(id); if (w) w.close(); }
  function toggle(id) {
    const w = wins.get(id);
    if (w && !w.minimized) w.close();
    else open(id);
  }

  function spawn(opts) {
    const w = new HudWindow(opts);
    wins.set(w.id, w);
    return w;
  }

  // ── Dock UI ──────────────────────────────────────────────────────────────
  function buildDock() {
    if (!dockEl) {
      dockEl = document.createElement("div");
      dockEl.className = "hud-dock";
      dockEl.id = "hudDock";
      document.body.appendChild(dockEl);
    }
    const items = [...apps.values()].filter((a) => a.dock !== false);
    dockEl.innerHTML = "";
    items.forEach((a) => {
      const b = document.createElement("button");
      b.className = "hud-dock-btn";
      b.dataset.app = a.id;
      b.innerHTML =
        (a.svg || `<span style="font-size:18px">${a.icon || "◈"}</span>`) +
        `<span class="hud-dock-label">${a.title || a.id}</span>` +
        (a.status ? `<span class="hud-dock-stat ${a.statusLevel || ""}"></span>` : "");
      b.addEventListener("click", () => toggle(a.id));
      dockEl.appendChild(b);
    });
    // "Tidy windows" control — only useful with ≥2 windows open, but always shown.
    const sep = document.createElement("span"); sep.className = "hud-dock-sep";
    const tidy = document.createElement("button");
    tidy.className = "hud-dock-btn hud-dock-tidy";
    tidy.title = "Tidy windows (Ctrl+Alt+A)";
    tidy.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span class="hud-dock-label">Tidy windows</span>';
    tidy.addEventListener("click", () => arrange());
    dockEl.appendChild(sep);
    dockEl.appendChild(tidy);
    syncDock();
  }

  function syncDock() {
    if (!dockEl) return;
    dockEl.querySelectorAll(".hud-dock-btn").forEach((b) => {
      const id = b.dataset.app;
      const w = wins.get(id);
      b.classList.toggle("active", !!(w && !w.minimized));
    });
  }

  function setDockStatus(id, level) {
    const app = apps.get(id);
    if (app) { app.status = true; app.statusLevel = level; }
    if (!dockEl) return;
    const b = dockEl.querySelector(`.hud-dock-btn[data-app="${id}"]`);
    if (!b) return;
    let dot = b.querySelector(".hud-dock-stat");
    if (!dot) { dot = document.createElement("span"); dot.className = "hud-dock-stat"; b.appendChild(dot); }
    dot.className = "hud-dock-stat " + (level === "ok" ? "" : level);
  }

  // Keep windows inside the usable area (clear of status bar + dock) after a
  // viewport resize — important when toggling in/out of full-screen.
  let _rzT = 0;
  window.addEventListener("resize", () => {
    clearTimeout(_rzT);
    _rzT = setTimeout(() => {
      const R = usableRect();
      for (const w of wins.values()) {
        if (w.minimized || !w.el) continue;
        const ww = w.el.offsetWidth, hh = w.el.offsetHeight;
        const l = Math.max(R.x0, Math.min(w.el.offsetLeft, R.x1 - ww));
        const t = Math.max(R.y0, Math.min(w.el.offsetTop, R.y1 - hh));
        w.el.style.left = l + "px"; w.el.style.top = t + "px";
      }
    }, 120);
  });

  // Tidy shortcut: Ctrl+Alt+A re-arranges all open windows into a clean grid.
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.altKey && (e.key === "a" || e.key === "A")) { e.preventDefault(); arrange(); }
  });

  window.HUD = {
    registerApp, open, close, toggle, spawn, arrange,
    setDockStatus, coreCenter, usableRect,
    _wins: wins, _apps: apps,
  };

  console.log("[DEEP] HUD layer initialised ✓");
})();
