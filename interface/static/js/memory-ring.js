/* ============================================================================
 * DEEP MEMORY RING — orbital knowledge interface
 * ----------------------------------------------------------------------------
 * Renders a glowing orbital ring around the yantra bindu. The ring carries
 * "memory beads" sized by how connected each entity is. Clicking the ring (or
 * the dock button) opens a draggable HUD window holding a live, interactive
 * force-directed graph of the persistent knowledge base — the cross-disciplinary
 * map of projects, technologies, concepts and people the system has retained.
 *
 * Data source: GET /api/knowledge/vault -> { stats, entities, relationships }
 * Editing:     DELETE /api/knowledge/entity/{name} (forget)
 *
 * Reads shared globals from app.js: ngCx, ngCy, orbTime, ngAccent, ngCore.
 * ========================================================================== */
(function () {
  "use strict";

  // Cohesive "neural" palette — cool cyans/violets/mints that glow on the dark
  // canvas, so the dominant `concept` mass reads as a synaptic network rather
  // than amber dust. A couple of warmer hues stay for human/preference contrast.
  const TYPE_COLOR = {
    person:       [120, 180, 255],   // periwinkle-blue
    technology:   [0, 229, 255],     // bright cyan (primary accent)
    topic:        [150, 130, 240],   // violet
    project:      [86, 220, 180],    // mint
    place:        [90, 160, 240],    // blue
    organization: [200, 120, 230],   // orchid
    preference:   [235, 180, 90],    // warm amber (deliberate contrast)
    action:       [80, 210, 205],    // teal
    concept:      [105, 200, 235],   // soft cyan (the dominant mass)
    unknown:      [150, 165, 205],   // slate
  };
  function typeColor(t) { return TYPE_COLOR[(t || "unknown").toLowerCase()] || TYPE_COLOR.unknown; }

  function core() {
    const x = (typeof ngCx === "number" && ngCx) || window.innerWidth / 2;
    const y = (typeof ngCy === "number" && ngCy) || window.innerHeight * 0.46;
    return { x, y };
  }
  function accent() { return (typeof ngAccent !== "undefined" && ngAccent) || [0, 229, 255]; }
  function clock() { return (typeof orbTime === "number") ? orbTime : performance.now() / 1000; }
  function coreAct() { return (typeof ngCore !== "undefined" && ngCore) ? (ngCore.act || 0) : 0; }

  // ─────────────────────────────────────────────────────────────────────────
  // 1) ORBITAL RING OVERLAY  (decorative + clickable affordance)
  // ─────────────────────────────────────────────────────────────────────────
  let ringCanvas, rctx, rW = 0, rH = 0;
  let beads = [];           // {ent, connections}
  let ringHover = false;
  const TILT = 0.34;        // vertical squash → perspective torus

  function ringRadius() { return Math.min(window.innerWidth, window.innerHeight) * 0.40; }

  function initRingCanvas() {
    const c = document.createElement("canvas");
    c.id = "memory-ring-canvas";
    c.style.cssText = "position:fixed;top:0;left:0;z-index:6;pointer-events:none;display:block;";
    document.body.insertBefore(c, document.body.children[1] || null);
    ringCanvas = c; rctx = c.getContext("2d");

    const resize = () => {
      rW = window.innerWidth; rH = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      c.width = rW * dpr; c.height = rH * dpr;
      c.style.width = rW + "px"; c.style.height = rH + "px";
      rctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    // Only react when the pointer is over empty background (the graph canvas or
    // the body) — never swallow clicks meant for real UI controls.
    const onBackground = (t) => t === document.body || (t && (t.id === "deep-graph-canvas" || t.id === "memory-ring-canvas" || t.id === "aegis-canvas"));

    // Click affordance: capture-phase so we intercept before the graph canvas.
    window.addEventListener("pointermove", (e) => {
      ringHover = onBackground(e.target) && onRingBand(e.clientX, e.clientY);
    }, true);
    window.addEventListener("click", (e) => {
      if (onBackground(e.target) && onRingBand(e.clientX, e.clientY)) {
        e.stopPropagation();
        e.preventDefault();
        window.HUD && HUD.open("memory-ring");
      }
    }, true);

    requestAnimationFrame(animateRing);
  }

  function onRingBand(mx, my) {
    const { x, y } = core();
    const R = ringRadius();
    // distance to the tilted ellipse band
    const dx = mx - x, dy = (my - y) / TILT;
    const d = Math.hypot(dx, dy);
    return Math.abs(d - R) < 16;
  }

  function animateRing() {
    requestAnimationFrame(animateRing);
    if (!rctx) return;
    rctx.clearRect(0, 0, rW, rH);
    const { x, y } = core();
    const R = ringRadius();
    const t = clock();
    const [ar, ag, ab] = accent();
    const act = coreAct();
    const hot = ringHover ? 1 : 0;

    rctx.save();
    rctx.translate(x, y);
    rctx.scale(1, TILT);

    // base orbit ring (back half dimmer for depth)
    for (let pass = 0; pass < 2; pass++) {
      rctx.beginPath();
      rctx.arc(0, 0, R, 0, Math.PI * 2);
      rctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},${0.10 + act * 0.12 + hot * 0.18})`;
      rctx.lineWidth = pass === 0 ? 2.4 : 0.8;
      rctx.stroke();
    }
    // inner+outer faint rails
    rctx.beginPath(); rctx.arc(0, 0, R + 7, 0, Math.PI * 2);
    rctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},${0.05 + hot * 0.1})`; rctx.lineWidth = 1; rctx.stroke();
    rctx.beginPath(); rctx.arc(0, 0, R - 7, 0, Math.PI * 2);
    rctx.strokeStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},${0.05 + hot * 0.1})`; rctx.lineWidth = 1; rctx.stroke();
    rctx.restore();

    // memory beads orbiting (front beads larger via sin depth)
    const n = beads.length || 8;
    for (let i = 0; i < n; i++) {
      const a = t * 0.18 + (i / n) * Math.PI * 2;
      const depth = (Math.sin(a) + 1) / 2;        // 0 back → 1 front
      const bx = x + Math.cos(a) * R;
      const by = y + Math.sin(a) * R * TILT;
      const b = beads[i];
      const col = b ? typeColor(b.ent.type) : [ar, ag, ab];
      const sz = (1.4 + depth * 2.6) * (b ? (1 + Math.min(b.connections, 8) * 0.12) : 1);
      const al = 0.25 + depth * 0.6;
      const grd = rctx.createRadialGradient(bx, by, 0, bx, by, sz * 4);
      grd.addColorStop(0, `rgba(${col[0]},${col[1]},${col[2]},${al})`);
      grd.addColorStop(1, `rgba(${col[0]},${col[1]},${col[2]},0)`);
      rctx.fillStyle = grd; rctx.beginPath(); rctx.arc(bx, by, sz * 4, 0, Math.PI * 2); rctx.fill();
      rctx.fillStyle = `rgba(${col[0]},${col[1]},${col[2]},${al + 0.2})`;
      rctx.beginPath(); rctx.arc(bx, by, sz, 0, Math.PI * 2); rctx.fill();
    }

    // hint label when hovering the band
    if (ringHover) {
      rctx.fillStyle = `rgba(${ar | 0},${ag | 0},${ab | 0},0.85)`;
      rctx.font = '600 10px "JetBrains Mono", monospace';
      rctx.textAlign = "center";
      rctx.fillText("◌ MEMORY RING — open knowledge graph", x, y - R * TILT - 14);
    }
  }

  async function refreshBeads() {
    try {
      const r = await fetch("/api/knowledge/vault?limit=200");
      if (!r.ok) return;
      const d = await r.json();
      const ents = d.entities || [];
      const rels = d.relationships || [];
      // connection count per entity id
      const deg = {};
      rels.forEach((e) => { deg[e.source] = (deg[e.source] || 0) + 1; deg[e.target] = (deg[e.target] || 0) + 1; });
      beads = ents
        .map((ent) => ({ ent, connections: deg[ent.id] || 0 }))
        .sort((a, b) => b.connections - a.connections || (b.ent.mention_count || 0) - (a.ent.mention_count || 0))
        .slice(0, 16);
      _vaultCache = d;
    } catch (_) {}
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 2) INTERACTIVE GRAPH WINDOW  (force-directed)
  // ─────────────────────────────────────────────────────────────────────────
  let _vaultCache = null;

  function buildGraphWindow(body, win) {
    body.style.display = "flex";
    body.style.flexDirection = "column";
    body.innerHTML =
      `<div class="mr-toolbar">
         <input class="hud-input mr-search" placeholder="Search memory…" style="flex:1;min-width:80px">
         <span class="mr-stats">—</span>
         <button class="hud-btn mr-gnn" title="GraphSAGE GNN — predict hidden connections">✦ Predict</button>
         <button class="hud-btn mr-refresh" title="Reload">↻</button>
       </div>
       <div class="mr-legend"></div>
       <div class="mr-stage"><canvas class="mr-canvas"></canvas>
         <div class="mr-detail"></div>
         <div class="mr-status"></div>
       </div>
       <div class="mr-teach">
         <input class="hud-input mr-teach-in" placeholder="Teach DEEP a fact…" style="flex:1;min-width:80px">
         <button class="hud-btn mr-teach-btn">Remember +</button>
       </div>`;

    const stage = body.querySelector(".mr-stage");
    const canvas = body.querySelector(".mr-canvas");
    const detail = body.querySelector(".mr-detail");
    const statsEl = body.querySelector(".mr-stats");
    const searchEl = body.querySelector(".mr-search");
    const teachIn = body.querySelector(".mr-teach-in");
    const teachBtn = body.querySelector(".mr-teach-btn");
    const legendEl = body.querySelector(".mr-legend");
    const statusEl = body.querySelector(".mr-status");
    const ctx = canvas.getContext("2d");

    const G = { nodes: [], edges: [], sel: null, hover: null, filter: "", typeFilter: new Set(), communities: [], showClusters: true, gnnLinks: [] };
    const pinned = new Set();   // node ids pinned in place (excluded from the sim)
    const pulses = [];          // active action-potentials travelling along axons
    let fireQ = [];             // scheduled neuron fires {node, at, intensity, depth}
    let lastSpont = 0;          // throttle for spontaneous background firing

    // ── Neural firing: an activation cascades through the network like a thought ──
    function fireNode(n, intensity, depth) {
      if (!n || intensity < 0.12 || depth > 5) return;
      n.act = Math.min(1.2, Math.max(n.act || 0, intensity));
      if (pulses.length > 240) return;          // safety cap
      const adj = n._edges || [];
      for (const e of adj) {
        if (e.kind === "suggested") continue;   // hints don't conduct
        const other = e.s === n ? e.t : e.s;
        pulses.push({ s: n, t: other, e, t0: clock(), dur: 0.34, intensity });
        fireQ.push({ node: other, at: clock() + 0.32, intensity: intensity * 0.56, depth: depth + 1 });
      }
    }
    function tickFiring() {
      const t = clock();
      if (fireQ.length) {
        const due = fireQ.filter((f) => f.at <= t);
        if (due.length) {
          fireQ = fireQ.filter((f) => f.at > t);
          due.forEach((f) => fireNode(f.node, f.intensity, f.depth));
        }
      }
      // spontaneous background activity — the brain is never fully quiet
      if (G.nodes.length && t - lastSpont > 0.6 && Math.random() < 0.5) {
        lastSpont = t;
        fireNode(G.nodes[(Math.random() * G.nodes.length) | 0], 0.4, 4);
      }
      G.nodes.forEach((n) => { if (n.act) n.act *= 0.94; });   // membrane decay
      for (let i = pulses.length - 1; i >= 0; i--) if (t - pulses[i].t0 > pulses[i].dur) pulses.splice(i, 1);
    }
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0, H = 0, raf = 0, dragNode = null;
    // Camera (synaptic graph is now zoom/pan-able), simulation temperature, and
    // neighbourhood-focus blend.
    const view = { tx: 0, ty: 0, scale: 1 };
    let panning = null;        // {sx, sy, tx, ty}
    let alpha = 1;             // sim "temperature" — cools so the net settles
    let focusT = 0;            // 0..1 ease for neighbourhood focus
    let neigh = null;          // Set<id> of selected node + its 1–2 hop neighbours
    let didFit = false, didFit2 = false;
    let camTween = null;       // {tx,ty,scale} — animated fly-to target

    function reheat(a) { alpha = Math.max(alpha, a == null ? 1 : a); }

    // ── Loading / empty status overlay ────────────────────────────────────────
    function showStatus(msg, spin) {
      statusEl.innerHTML = `${spin ? '<span class="mr-spin"></span>' : ""}<span>${msg}</span>`;
      statusEl.classList.add("show");
    }
    function hideStatus() { statusEl.classList.remove("show"); }

    // ── Camera fly-to (search jumps here) ─────────────────────────────────────
    function flyTo(n, scale) {
      if (!n) return;
      const s = scale || Math.max(view.scale, 1.3);
      camTween = { tx: W / 2 - n.x * s, ty: H / 2 - n.y * s, scale: s };
    }

    // ── Type legend + click-to-filter ─────────────────────────────────────────
    function buildLegend() {
      const counts = {};
      G.nodes.forEach((n) => { const t = (n.type || "unknown"); counts[t] = (counts[t] || 0) + 1; });
      legendEl.innerHTML = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([t, c]) => {
        const [r, g, b] = typeColor(t);
        const off = G.typeFilter.size && !G.typeFilter.has(t);
        return `<button class="mr-leg${off ? " off" : ""}" data-type="${t}">` +
               `<span class="mr-leg-dot" style="background:rgb(${r},${g},${b})"></span>${t} ${c}</button>`;
      }).join("");
    }
    legendEl.addEventListener("click", (e) => {
      const btn = e.target.closest(".mr-leg"); if (!btn) return;
      const t = btn.dataset.type;
      if (G.typeFilter.has(t)) G.typeFilter.delete(t); else G.typeFilter.add(t);
      buildLegend();
    });
    function toWorld(sx, sy) { return { x: (sx - view.tx) / view.scale, y: (sy - view.ty) / view.scale }; }
    function qbez(p, x0, y0, cx, cy, x1, y1) {
      const m = 1 - p;
      return [m*m*x0 + 2*m*p*cx + p*p*x1, m*m*y0 + 2*m*p*cy + p*p*y1];
    }
    function rrect(c, x, y, w, h, r) {
      c.beginPath();
      c.moveTo(x+r, y); c.arcTo(x+w, y, x+w, y+h, r); c.arcTo(x+w, y+h, x, y+h, r);
      c.arcTo(x, y+h, x, y, r); c.arcTo(x, y, x+w, y, r); c.closePath();
    }
    // Community detection via label propagation over ALL edges (relation+semantic).
    const COMMUNITY_COLORS = [
      [0,229,255],[150,130,240],[86,220,180],[255,150,120],
      [120,180,255],[235,180,90],[200,120,230],[80,210,205],
    ];
    function detectCommunities() {
      // Prefer the real (NetworkX modularity) communities from the backend.
      if (G.nodes.some((n) => n.backendComm != null)) {
        const groups = {};
        G.nodes.forEach((n) => { n.community = n.backendComm; if (n.backendComm != null) (groups[n.backendComm] = groups[n.backendComm] || []).push(n); });
        const ranked = Object.entries(groups).filter(([, a]) => a.length >= 3)
          .sort((a, b) => b[1].length - a[1].length).slice(0, 8);
        G.communities = ranked.map(([, arr], i) => ({ nodes: arr, color: COMMUNITY_COLORS[i % COMMUNITY_COLORS.length] }));
        const cidx = {}; ranked.forEach(([cid], i) => { cidx[cid] = i; });
        G.nodes.forEach((n) => { n.commIdx = cidx[n.community]; });
        return;
      }
      const adj = {}, byId = {};
      G.nodes.forEach((n) => { n.community = n.id; adj[n.id] = []; byId[n.id] = n; });
      G.edges.forEach((e) => { adj[e.s.id].push(e.t.id); adj[e.t.id].push(e.s.id); });
      for (let iter = 0; iter < 6; iter++) {
        let changed = false;
        const order = G.nodes.slice().sort(() => Math.random() - 0.5);
        for (const n of order) {
          const counts = {};
          for (const nb of adj[n.id]) { const c = byId[nb].community; counts[c] = (counts[c] || 0) + 1; }
          let best = n.community, bestC = 0;
          for (const c in counts) { if (counts[c] > bestC) { bestC = counts[c]; best = c; } }
          if (best !== n.community) { n.community = best; changed = true; }
        }
        if (!changed) break;
      }
      const groups = {};
      G.nodes.forEach((n) => { (groups[n.community] = groups[n.community] || []).push(n); });
      const ranked = Object.entries(groups).filter(([, a]) => a.length >= 3)
        .sort((a, b) => b[1].length - a[1].length).slice(0, 8);
      G.communities = ranked.map(([, arr], i) => ({ nodes: arr, color: COMMUNITY_COLORS[i % COMMUNITY_COLORS.length] }));
      const cidx = {};
      ranked.forEach(([cid], i) => { cidx[cid] = i; });
      G.nodes.forEach((n) => { n.commIdx = cidx[n.community]; });
    }

    // Lay the detected communities out as spatially-separated brain "lobes",
    // each with a region label (its most-connected neuron).
    function assignRegions() {
      const N = G.communities.length;
      const R = Math.max(300, N * 78);   // wide ring → clusters separate into distinct islands
      G.communities.forEach((cm, i) => {
        const ang = (i / Math.max(1, N)) * Math.PI * 2 - Math.PI / 2;
        const rr = R * (i % 2 ? 0.62 : 1);   // two-ring stagger avoids crowding when many clusters
        cm.cx = W / 2 + Math.cos(ang) * rr;
        cm.cy = H / 2 + Math.sin(ang) * rr * 0.82;
        let best = cm.nodes[0];
        cm.nodes.forEach((n) => { if ((n.deg || 0) > (best.deg || 0)) best = n; });
        cm.label = best ? best.name : "Region";
      });
    }

    function computeNeigh() {
      if (!G.sel) { neigh = null; return; }
      const s = new Set([G.sel.id]);
      G.edges.forEach((e) => { if (e.s === G.sel) s.add(e.t.id); else if (e.t === G.sel) s.add(e.s.id); });
      const one = new Set(s);  // expand to 2 hops
      G.edges.forEach((e) => { if (one.has(e.s.id)) s.add(e.t.id); if (one.has(e.t.id)) s.add(e.s.id); });
      neigh = s;
    }
    // Per-node alpha given search filter + neighbourhood focus.
    function nodeAlpha(n) {
      let a = (!G.filter || n.name.toLowerCase().includes(G.filter)) ? 1 : 0.1;
      if (G.typeFilter.size && !G.typeFilter.has(n.type || "unknown")) a *= 0.07;  // legend filter
      if (neigh && focusT > 0) a *= neigh.has(n.id) ? 1 : (1 - focusT * 0.9);
      return a;
    }
    function fitView() {
      if (!G.nodes.length) return;
      // Frame the node MASS, not the extremes — a few disconnected nodes fly far
      // out and would otherwise blow up the bounding box (the framing glitch).
      const xs = G.nodes.map((n) => n.x).sort((a, b) => a - b);
      const ys = G.nodes.map((n) => n.y).sort((a, b) => a - b);
      const q = (arr, p) => arr[Math.max(0, Math.min(arr.length - 1, Math.floor(p * (arr.length - 1))))];
      const minX = q(xs, 0.04), maxX = q(xs, 0.96), minY = q(ys, 0.04), maxY = q(ys, 0.96);
      const pad = 70, gw = (maxX - minX) || 1, gh = (maxY - minY) || 1;
      const s = Math.min((W - pad) / gw, (H - pad) / gh, 1.8);
      view.scale = Math.max(0.25, s);
      view.tx = W / 2 - ((minX + maxX) / 2) * view.scale;
      view.ty = H / 2 - ((minY + maxY) / 2) * view.scale;
    }

    function sizeCanvas() {
      const r = stage.getBoundingClientRect();
      W = r.width; H = r.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function ingest(vault) {
      const ents = (vault.entities || []);
      const rels = (vault.relationships || []);
      const byId = {};
      const now = Date.now();
      G.nodes = ents.map((e) => {
        const mc = e.mention_count || 1;
        let rec = 1;                                   // recency 0.35..1 (older → dimmer)
        const ls = e.last_seen ? Date.parse(e.last_seen) : NaN;
        if (!isNaN(ls)) rec = Math.max(0.35, Math.min(1, 1 - (now - ls) / 86400000 / 180));
        const node = {
          id: e.id, name: e.name, type: e.type, ent: e,
          x: W / 2 + (Math.random() - 0.5) * W * 0.6,
          y: H / 2 + (Math.random() - 0.5) * H * 0.6,
          vx: 0, vy: 0, deg: 0,
          phase: Math.random() * Math.PI * 2,          // neuron breathing offset
          mentions: mc,
          importance: Math.min(1, Math.log10(mc + 1) / 2),  // fallback: mention_count
          recency: rec,
          pr: (typeof e.pagerank === "number") ? e.pagerank : null,    // network-science importance
          backendComm: (typeof e.community === "number") ? e.community : null,
          betweenness: e.betweenness || 0,
        };
        byId[e.id] = node;
        return node;
      });
      // Importance from PageRank when available (real centrality), normalised 0..1.
      const prs = G.nodes.map((n) => n.pr).filter((v) => v != null);
      if (prs.length) {
        const lo = Math.min(...prs), hi = Math.max(...prs) || 1;
        G.nodes.forEach((n) => { if (n.pr != null) n.importance = (n.pr - lo) / ((hi - lo) || 1); });
      }
      G.edges = rels
        .filter((r) => byId[r.source] && byId[r.target])
        .map((r) => {
          const kind = r.kind || "relation";
          if (kind === "relation") { byId[r.source].deg++; byId[r.target].deg++; }  // size by real links only
          return { s: byId[r.source], t: byId[r.target], rel: r.relation, conf: r.confidence, kind, seed: Math.random() };
        });
      // Per-neuron adjacency (axon list) for fast activation propagation; reset act;
      // and generate dendrite morphology so each node reads as a real neuron.
      G.nodes.forEach((n, i) => {
        n._edges = []; n.act = 0;
        let s = (i * 2654435761) % 233280;
        const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
        const cnt = 4 + Math.min(7, Math.floor((n.deg || 0) / 2) + Math.floor(rnd() * 3));
        n.dendrites = [];
        for (let d = 0; d < cnt; d++) {
          n.dendrites.push({
            ang: (d / cnt) * Math.PI * 2 + (rnd() - 0.5) * 0.7,
            len: 7 + rnd() * 12,
            fork: rnd() > 0.45,
            forkAng: (rnd() - 0.5) * 1.0,
          });
        }
      });
      G.edges.forEach((e) => { e.s._edges.push(e); e.t._edges.push(e); });
      const s = vault.stats || {};
      // Living numbers: count the node/link totals up rather than snapping.
      (function countUp(nodes, links) {
        const t0 = performance.now(), dur = 700;
        (function tick(t) {
          const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
          statsEl.textContent = `${Math.round(nodes * e)} nodes · ${Math.round(links * e)} links`;
          if (p < 1) requestAnimationFrame(tick);
        })(t0);
      })(G.nodes.length, G.edges.length);
      const gm = s.graph || {};
      statsEl.title = gm.communities != null
        ? `${gm.communities} communities · density ${gm.density} · clustering ${gm.avg_clustering} · ${gm.components} components\nmost central: ${(gm.top_central || []).join(", ")}`
        : `entities: ${s.entities ?? "?"} · relationships: ${s.relationships ?? "?"}`;
      if (G.sel) { G.sel = G.nodes.find((n) => n.id === G.sel.id) || null; computeNeigh(); }
      detectCommunities();
      assignRegions();   // lay communities out as labelled brain "lobes"
      addGnnEdges();   // re-overlay GNN-predicted links after a reload
      buildLegend();
      didFit = false; didFit2 = false; reheat(1);   // re-settle + re-fit the new topology
    }

    function visible(n) { return !G.filter || n.name.toLowerCase().includes(G.filter); }

    function step() {
      // Cooling: once settled, stop integrating (saves CPU, kills jitter).
      if (alpha < 0.005 && !dragNode) return;
      const k = 0.012, rep = 2200, spring = 0.04, springLen = 90;
      const cx = W / 2, cy = H / 2;
      for (let i = 0; i < G.nodes.length; i++) {
        const a = G.nodes[i];
        if (a === dragNode) continue;
        // Region gravity: pull toward the node's brain "lobe" centroid (else canvas centre).
        let tx = cx, ty = cy, gk = 0.04;
        const cm = (a.commIdx != null) ? G.communities[a.commIdx] : null;
        if (cm && cm.cx != null) { tx = cm.cx; ty = cm.cy; gk = 0.42; }   // strong pull → distinct cluster islands
        a.vx += (tx - a.x) * k * gk;
        a.vy += (ty - a.y) * k * gk;
        for (let j = i + 1; j < G.nodes.length; j++) {
          const b = G.nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          let d2 = dx * dx + dy * dy || 1;
          const f = rep / d2;
          const d = Math.sqrt(d2);
          const fx = (dx / d) * f, fy = (dy / d) * f;
          a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
        }
      }
      G.edges.forEach((e) => {
        // Semantic (similarity) edges are numerous — give them a longer, softer
        // spring so the dense kNN web SPREADS instead of collapsing into a ball.
        const sem = e.kind === "semantic";
        // Cross-cluster edges get a long, very soft spring so islands stay apart
        // (their edges then bundle through the pinch waypoint); intra-cluster normal.
        const cross = (e.s.commIdx != null && e.t.commIdx != null && e.s.commIdx !== e.t.commIdx);
        const sp = cross ? 0.0016 : (sem ? 0.011 : spring);
        const len = cross ? 360 : (sem ? 190 : springLen);
        const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
        const d = Math.hypot(dx, dy) || 1;
        const f = (d - len) * sp;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        if (e.s !== dragNode) { e.s.vx += fx; e.s.vy += fy; }
        if (e.t !== dragNode) { e.t.vx -= fx; e.t.vy -= fy; }
      });
      const cool = 0.25 + alpha * 0.9;   // movement scales down as it cools
      G.nodes.forEach((n) => {
        if (n === dragNode || pinned.has(n.id)) { n.vx = n.vy = 0; return; }   // pinned stays put
        n.vx *= 0.86; n.vy *= 0.86;
        n.x += n.vx * cool; n.y += n.vy * cool;
      });
      if (!dragNode) alpha *= 0.99;
    }

    function draw() {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.save();
      ctx.translate(view.tx, view.ty);
      ctx.scale(view.scale, view.scale);
      const t = clock();
      const inv = 1 / view.scale;         // keep stroke/text crisp regardless of zoom
      ctx.lineCap = "round";

      // ── Community hulls: soft colour blobs behind each detected cluster ────────
      // Community display centroids (drive edge-bundling pinch points + pill labels).
      G.communities.forEach((cm) => {
        let mx = 0, my = 0, top = Infinity; cm.nodes.forEach((n) => { mx += n.x; my += n.y; top = Math.min(top, n.y); });
        cm._dcx = mx / cm.nodes.length; cm._dcy = my / cm.nodes.length; cm._top = top;
      });
      if (G.showClusters && G.communities.length) {
        ctx.globalCompositeOperation = "lighter";
        G.communities.forEach((cm) => {
          const ns = cm.nodes; if (ns.length < 3) return;
          let cx = 0, cy = 0; ns.forEach((n) => { cx += n.x; cy += n.y; }); cx /= ns.length; cy /= ns.length;
          let rad = 0; ns.forEach((n) => { rad = Math.max(rad, Math.hypot(n.x - cx, n.y - cy)); });
          rad += 34;
          const [r, g, b] = cm.color;
          const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
          grd.addColorStop(0, `rgba(${r},${g},${b},0.11)`);
          grd.addColorStop(0.7, `rgba(${r},${g},${b},0.05)`);
          grd.addColorStop(1, `rgba(${r},${g},${b},0)`);
          ctx.fillStyle = grd; ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2); ctx.fill();
        });
      }

      // ── Synapses: curved, colour-graded, with a signal pulse travelling along ──
      ctx.globalCompositeOperation = "lighter";
      G.edges.forEach((e) => {
        const ea = Math.min(nodeAlpha(e.s), nodeAlpha(e.t));
        if (ea <= 0.02) return;
        const lit = (e.s === G.sel || e.t === G.sel || e.s === G.hover || e.t === G.hover);
        const sem = e.kind === "semantic";       // soft similarity link
        const sugg = e.kind === "suggested";     // network-science link prediction
        const gnn = e.kind === "gnn";            // GraphSAGE-predicted hidden link
        if (sugg && !lit) return;                // suggestions only around the focused node
        const [r1, g1, b1] = typeColor(e.s.type), [r2, g2, b2] = typeColor(e.t.type);
        const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y, len = Math.hypot(dx, dy) || 1;
        // Edge bundling: route inter-cluster edges through the shared waypoint between
        // their two community centroids → elegant pinched "rope" bundles.
        const cs = (e.s.commIdx != null) ? G.communities[e.s.commIdx] : null;
        const ctg = (e.t.commIdx != null) ? G.communities[e.t.commIdx] : null;
        let cxp, cyp;
        if (cs && ctg && e.s.commIdx !== e.t.commIdx && cs._dcx != null && ctg._dcx != null) {
          cxp = (cs._dcx + ctg._dcx) / 2; cyp = (cs._dcy + ctg._dcy) / 2;   // pinch point
        } else {
          const off = Math.min(len * 0.16, 46);
          cxp = (e.s.x + e.t.x) / 2 + (-dy / len) * off;
          cyp = (e.s.y + e.t.y) / 2 + (dx / len) * off;
        }
        if (gnn) {
          // GraphSAGE prediction: bright cyan-white "marching-ants" arc with a glow.
          ctx.strokeStyle = `rgba(120,235,255,${0.95 * ea})`;
          ctx.lineWidth = 1.7 * inv; ctx.setLineDash([7 * inv, 5 * inv]);
          ctx.lineDashOffset = (-t * 22) % 1000;
          ctx.shadowColor = "rgba(120,235,255,0.85)"; ctx.shadowBlur = 7;
        } else if (sugg) {
          // network-science link-prediction hint: dotted mint "could-connect" arc
          ctx.strokeStyle = `rgba(86,220,180,${0.7 * ea})`;
          ctx.lineWidth = 1.2 * inv; ctx.setLineDash([1.5 * inv, 6 * inv]);
        } else {
          // Neurotransmitter coding: excitatory (amber) along explicit relations,
          // modulatory (violet) along semantic-similarity axons.
          const nt = sem ? [40, 170, 210] : [25, 215, 255];   // cyan synapse family
          const fire = Math.max(e.s.act || 0, e.t.act || 0);   // active conduction brightens
          const baseA = ((lit ? 0.75 : (sem ? 0.07 : 0.2)) + fire * 0.5) * ea;
          ctx.strokeStyle = `rgba(${nt[0]},${nt[1]},${nt[2]},${Math.min(0.95, baseA)})`;
          ctx.lineWidth = (lit ? 1.9 : (sem ? 0.5 : 1.0)) * (0.5 + (e.conf || 0.5)) * (1 + fire) * inv;
          ctx.setLineDash(sem && !lit ? [4 * inv, 5 * inv] : []);
          if (lit || fire > 0.3) { ctx.shadowColor = `rgba(${nt[0]},${nt[1]},${nt[2]},0.85)`; ctx.shadowBlur = 6; }  // myelin glow
        }
        ctx.beginPath(); ctx.moveTo(e.s.x, e.s.y); ctx.quadraticCurveTo(cxp, cyp, e.t.x, e.t.y); ctx.stroke();
        ctx.setLineDash([]); ctx.lineDashOffset = 0; ctx.shadowBlur = 0;
        // travelling signal pulse — on explicit synapses, or any lit synapse
        if (ea > 0.22 && !sugg && !gnn && (!sem || lit)) {
          const p = (t * (lit ? 0.6 : 0.32) + e.seed) % 1;
          const pt = qbez(p, e.s.x, e.s.y, cxp, cyp, e.t.x, e.t.y);
          const pr = (lit ? 3.4 : 2.2) * inv;
          const pg = ctx.createRadialGradient(pt[0], pt[1], 0, pt[0], pt[1], pr * 2.2);
          pg.addColorStop(0, `rgba(${r2},${g2},${b2},${0.9 * ea})`);
          pg.addColorStop(1, `rgba(${r2},${g2},${b2},0)`);
          ctx.fillStyle = pg; ctx.beginPath(); ctx.arc(pt[0], pt[1], pr * 2.2, 0, Math.PI * 2); ctx.fill();
        }
      });

      // ── Action potentials: bright signals racing along axons when neurons fire ──
      for (const ap of pulses) {
        const p = Math.min(1, (t - ap.t0) / ap.dur);
        const dx = ap.t.x - ap.s.x, dy = ap.t.y - ap.s.y, len = Math.hypot(dx, dy) || 1;
        const off = Math.min(len * 0.16, 46);
        const cxp = (ap.s.x + ap.t.x) / 2 + (-dy / len) * off;
        const cyp = (ap.s.y + ap.t.y) / 2 + (dx / len) * off;
        const pt = qbez(p, ap.s.x, ap.s.y, cxp, cyp, ap.t.x, ap.t.y);
        const rr = 3.2 * (ap.intensity || 0.6) * inv * (1 - p * 0.4);
        const pg = ctx.createRadialGradient(pt[0], pt[1], 0, pt[0], pt[1], rr * 3);
        pg.addColorStop(0, `rgba(235,250,255,${0.95 * (1 - p)})`);
        pg.addColorStop(0.4, `rgba(120,210,255,${0.7 * (1 - p)})`);
        pg.addColorStop(1, "rgba(120,210,255,0)");
        ctx.fillStyle = pg; ctx.beginPath(); ctx.arc(pt[0], pt[1], rr * 3, 0, Math.PI * 2); ctx.fill();
      }

      // ── Neurons: layered bloom + bright core, gently breathing ─────────────────
      G.nodes.forEach((n) => {
        // Recency dims older memories; never fully — keep the net coherent.
        const a = nodeAlpha(n) * (0.5 + 0.5 * (n.recency != null ? n.recency : 1));
        if (a <= 0.015) return;
        let [r, g, b] = typeColor(n.type);
        // Blend toward the node's brain-region (lobe) hue.
        const cm = (n.commIdx != null) ? G.communities[n.commIdx] : null;
        if (cm && cm.color) { r = (r * 0.6 + cm.color[0] * 0.4) | 0; g = (g * 0.6 + cm.color[1] * 0.4) | 0; b = (b * 0.6 + cm.color[2] * 0.4) | 0; }
        // Activity heat: a firing neuron flashes toward hot white and swells.
        const act = Math.min(1, n.act || 0);
        if (act > 0.01) { r = (r + (255 - r) * act * 0.85) | 0; g = (g + (255 - g) * act * 0.85) | 0; b = (b + (255 - b) * act * 0.85) | 0; }
        const sel = n === G.sel, hov = n === G.hover;
        const breathe = 1 + 0.1 * Math.sin(t * 1.5 + n.phase) + act * 0.5;
        const imp = n.importance || 0;                  // PageRank/mention importance
        const rad = (4 + Math.min(n.deg, 12) * 1.05 + imp * 4 + act * 5 + (sel ? 3 : 0)) * breathe;
        const bloom = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, rad * 4);
        bloom.addColorStop(0, `rgba(${r},${g},${b},${0.4 * a + imp * 0.18 + act * 0.55 + (sel || hov ? 0.35 : 0)})`);
        bloom.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = bloom; ctx.beginPath(); ctx.arc(n.x, n.y, rad * 4, 0, Math.PI * 2); ctx.fill();
        // Dendrites — short branching fibres radiating from the soma; brighten when firing.
        if (a > 0.22 && n.dendrites) {
          ctx.strokeStyle = `rgba(${r},${g},${b},${(0.3 + act * 0.6) * a})`;
          ctx.lineWidth = (0.8 + act) * inv; ctx.lineCap = "round";
          for (const d of n.dendrites) {
            const gl = (d.len * (1 + act * 0.4)) * breathe;
            const x0 = n.x + Math.cos(d.ang) * rad, y0 = n.y + Math.sin(d.ang) * rad;
            const x1 = n.x + Math.cos(d.ang) * (rad + gl), y1 = n.y + Math.sin(d.ang) * (rad + gl);
            const mx = (x0 + x1) / 2 + Math.cos(d.ang + 1.57) * 2.2, my = (y0 + y1) / 2 + Math.sin(d.ang + 1.57) * 2.2;
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo(mx, my, x1, y1); ctx.stroke();
            if (d.fork) {
              const fa = d.ang + d.forkAng;
              ctx.beginPath(); ctx.moveTo(x1, y1);
              ctx.lineTo(x1 + Math.cos(fa) * gl * 0.5, y1 + Math.sin(fa) * gl * 0.5); ctx.stroke();
            }
          }
        }
        ctx.fillStyle = `rgba(${r},${g},${b},${0.95 * a})`;
        ctx.beginPath(); ctx.arc(n.x, n.y, rad, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = `rgba(255,255,255,${0.8 * a})`;
        ctx.beginPath(); ctx.arc(n.x, n.y, rad * 0.42, 0, Math.PI * 2); ctx.fill();
        // Importance halo ring on the most-mentioned neurons.
        if (imp > 0.5) {
          ctx.strokeStyle = `rgba(${r},${g},${b},${0.35 * a * imp})`;
          ctx.lineWidth = 1 * inv;
          ctx.beginPath(); ctx.arc(n.x, n.y, rad + 3 * inv, 0, Math.PI * 2); ctx.stroke();
        }
        if (sel || hov) {
          ctx.strokeStyle = `rgba(${r},${g},${b},0.9)`;
          ctx.lineWidth = (sel ? 2 : 1.4) * inv;
          ctx.beginPath(); ctx.arc(n.x, n.y, rad + 5 * inv, 0, Math.PI * 2); ctx.stroke();
        }
      });

      // ── Cluster pill labels — blue {count, weight} badges (reference style) ─────
      ctx.globalCompositeOperation = "source-over";
      if (G.showClusters) {
        ctx.textAlign = "center";
        G.communities.forEach((cm) => {
          if (cm._dcx == null) return;
          let wt = 0; cm.nodes.forEach((nd) => { wt += (nd.importance || 0); });
          wt = Math.round(wt * 60 + cm.nodes.length * 4);
          const label = `{${cm.nodes.length}, ${wt}}`;
          const fs = 12 * inv;
          ctx.font = `600 ${fs}px "JetBrains Mono", monospace`;
          ctx.textBaseline = "middle";
          const tw = ctx.measureText(label).width, padX = 9 * inv, padY = 5 * inv;
          const w = tw + padX * 2, h = fs + padY * 2, px = cm._dcx, py = cm._top - 16 * inv;
          ctx.fillStyle = "rgba(46,86,235,0.92)";                       // blue pill
          rrect(ctx, px - w / 2, py - h / 2, w, h, h / 2); ctx.fill();
          ctx.fillStyle = "rgba(255,255,255,0.97)";
          ctx.fillText(label, px, py + 0.5 * inv);
        });
        ctx.textBaseline = "alphabetic";
      }

      // ── Labels (drawn last, no additive blend, with a legibility halo) ─────────
      G.nodes.forEach((n) => {
        const a = nodeAlpha(n);
        const sel = n === G.sel, hov = n === G.hover;
        if (a <= 0.3 || !(sel || hov || n.deg >= 2)) return;
        const rad = 4 + Math.min(n.deg, 12) * 1.05;
        const fs = (sel ? 10.5 : 9) * inv;
        ctx.font = `${sel ? 600 : 500} ${fs}px "JetBrains Mono", monospace`;
        ctx.textAlign = "center"; ctx.textBaseline = "top";
        const tw = ctx.measureText(n.name).width;
        const ly = n.y + rad + 5 * inv;
        ctx.fillStyle = `rgba(8,12,20,${0.55 * a})`;
        rrect(ctx, n.x - tw / 2 - 4 * inv, ly - 2 * inv, tw + 8 * inv, fs + 5 * inv, 4 * inv); ctx.fill();
        ctx.fillStyle = `rgba(234,246,255,${0.95 * a})`;
        ctx.fillText(n.name, n.x, ly);
      });
      ctx.textBaseline = "alphabetic";
      ctx.restore();
    }

    function loop() {
      step();
      tickFiring();   // propagate neural activation + spontaneous firing
      focusT += ((G.sel ? 1 : 0) - focusT) * 0.12;   // smooth neighbourhood focus
      // Animated fly-to (search jump): ease the camera toward the target.
      if (camTween) {
        view.tx += (camTween.tx - view.tx) * 0.14;
        view.ty += (camTween.ty - view.ty) * 0.14;
        view.scale += (camTween.scale - view.scale) * 0.14;
        if (Math.hypot(camTween.tx - view.tx, camTween.ty - view.ty) < 0.6 &&
            Math.abs(camTween.scale - view.scale) < 0.004) camTween = null;
      }
      // Auto-frame the layout: an early fit, then a re-fit once the lobes settle
      // (region-gravity keeps moving nodes after the first fit, hence the second).
      if (!didFit && G.nodes.length && alpha < 0.3) { fitView(); didFit = true; }
      if (!didFit2 && G.nodes.length && alpha < 0.045) { fitView(); didFit2 = true; }
      draw();
      drawMini();
      raf = requestAnimationFrame(loop);
    }

    // mx,my are WORLD coords; tolerance grows when zoomed out so small nodes stay clickable.
    function nodeAt(mx, my) {
      const tol = 6 / view.scale;
      for (let i = G.nodes.length - 1; i >= 0; i--) {
        const n = G.nodes[i];
        const rad = 6 + Math.min(n.deg, 12) * 1.05;
        if (Math.hypot(mx - n.x, my - n.y) < rad + tol) return n;
      }
      return null;
    }

    function fmtDate(s) {
      if (!s) return "—";
      const d = new Date(s);
      return isNaN(d) ? "—" : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    }
    function esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    }

    function showDetail(n) {
      if (!n) { detail.classList.remove("open"); return; }
      const [r, g, b] = typeColor(n.type);
      const e = n.ent || {};
      const incident = G.edges.filter((ed) => ed.s === n || ed.t === n);
      const rel = incident.filter((ed) => ed.kind !== "semantic");
      const sim = incident.filter((ed) => ed.kind === "semantic");
      const relTags = rel.slice(0, 8).map((ed) => {
        const o = ed.s === n ? ed.t : ed.s;
        return `<span class="mr-tag">${esc(ed.rel || "~")} → ${esc(o.name)}</span>`;
      }).join("");
      const simTags = sim.slice(0, 10).map((ed) => {
        const o = ed.s === n ? ed.t : ed.s;
        return `<span class="mr-tag mr-tag-sim">≈ ${esc(o.name)}</span>`;
      }).join("");
      const aliases = (e.aliases || []).filter((a) => a && a.toLowerCase() !== (n.name || "").toLowerCase());
      const ctx = (e.context || []).slice(0, 3);

      detail.innerHTML =
        `<div class="mr-d-head" style="color:rgb(${r},${g},${b})">${esc(n.name)}</div>
         <div class="mr-d-type">${esc((n.type || "unknown").toUpperCase())} · ${rel.length} link${rel.length === 1 ? "" : "s"}${sim.length ? ` · ${sim.length} similar` : ""} · seen ${e.mention_count || 1}×</div>
         <div class="mr-d-meta">first ${fmtDate(e.first_seen)} · last ${fmtDate(e.last_seen)}</div>
         ${aliases.length ? `<div class="mr-d-meta">also known as: ${aliases.slice(0, 5).map(esc).join(", ")}</div>` : ""}
         ${e.description ? `<div class="mr-d-desc">${esc(e.description)}</div>` : ""}
         ${ctx.length ? `<div class="mr-d-ctx">${ctx.map((s) => `<div class="mr-d-quote">“${esc(s)}”</div>`).join("")}</div>` : ""}
         ${relTags ? `<div class="mr-d-sec">Relations</div><div class="mr-d-links">${relTags}</div>` : ""}
         ${simTags ? `<div class="mr-d-sec">Semantically similar</div><div class="mr-d-links">${simTags}</div>` : ""}
         ${(!relTags && !simTags) ? `<div class="mr-d-links"><span style="opacity:.5">no connections yet</span></div>` : ""}
         <button class="mr-forget">Forget this</button>`;
      detail.classList.add("open");
      detail.querySelector(".mr-forget").onclick = async () => {
        if (!confirm(`Forget "${n.name}" and its relationships?`)) return;
        try {
          await fetch("/api/knowledge/entity/" + encodeURIComponent(n.name), { method: "DELETE" });
          await load();
          showDetail(null);
          refreshBeads();
        } catch (_) {}
      };
    }

    // interaction — drag a neuron, pan empty space, wheel-zoom, dbl-click to reframe
    let down = null;
    function rel(e) { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
    function select(n) { G.sel = n; computeNeigh(); showDetail(n); if (n) fireNode(n, 1.1, 0); }

    canvas.addEventListener("pointerdown", (e) => {
      camTween = null;   // user takes the wheel
      const s = rel(e), m = toWorld(s.x, s.y), n = nodeAt(m.x, m.y);
      down = { x: m.x, y: m.y, moved: false };
      if (n) { dragNode = n; n.vx = n.vy = 0; reheat(0.5); canvas.setPointerCapture(e.pointerId); }
      else { panning = { sx: s.x, sy: s.y, tx: view.tx, ty: view.ty }; canvas.setPointerCapture(e.pointerId); }
    });
    canvas.addEventListener("pointermove", (e) => {
      const s = rel(e), m = toWorld(s.x, s.y);
      if (dragNode) { dragNode.x = m.x; dragNode.y = m.y; reheat(0.5); if (down) down.moved = true; }
      else if (panning) { view.tx = panning.tx + (s.x - panning.sx); view.ty = panning.ty + (s.y - panning.sy); canvas.style.cursor = "grabbing"; }
      else { G.hover = nodeAt(m.x, m.y); canvas.style.cursor = G.hover ? "pointer" : "grab"; }
    });
    canvas.addEventListener("pointerup", (e) => {
      const s = rel(e), m = toWorld(s.x, s.y);
      if (dragNode && down && !down.moved) { select(G.sel === dragNode ? null : dragNode); }
      else if (panning && down && !down.moved) { const n = nodeAt(m.x, m.y); if (!n) select(null); }
      dragNode = null; panning = null; down = null;
      canvas.style.cursor = "grab";
    });
    // Zoom toward the cursor.
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      camTween = null;
      const s = rel(e), w = toWorld(s.x, s.y);
      const ns = Math.max(0.2, Math.min(5, view.scale * Math.exp(-e.deltaY * 0.0014)));
      view.tx = s.x - w.x * ns; view.ty = s.y - w.y * ns; view.scale = ns;
    }, { passive: false });
    canvas.addEventListener("dblclick", () => { fitView(); });

    // ── Right-click node menu: pin / focus / find / forget ────────────────────
    const ctxMenu = document.createElement("div");
    ctxMenu.className = "mr-ctx"; ctxMenu.style.display = "none";
    stage.appendChild(ctxMenu);
    const hideCtx = () => { ctxMenu.style.display = "none"; };
    window.addEventListener("click", hideCtx);
    win._mrCleanup = () => window.removeEventListener("click", hideCtx);
    canvas.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      const s = rel(e), m = toWorld(s.x, s.y), n = nodeAt(m.x, m.y);
      if (!n) { hideCtx(); return; }
      const isPinned = pinned.has(n.id);
      ctxMenu.innerHTML =
        `<div class="mr-ctx-h">${esc(n.name)}</div>
         <button data-a="pin">${isPinned ? "📌 Unpin" : "📌 Pin in place"}</button>
         <button data-a="expand">⊙ Focus neighbourhood</button>
         <button data-a="find">💬 Ask DEEP about this</button>
         <button data-a="forget" class="mr-ctx-danger">✕ Forget</button>`;
      ctxMenu.style.left = Math.min(s.x, stage.clientWidth - 180) + "px";
      ctxMenu.style.top = s.y + "px";
      ctxMenu.style.display = "block";
      ctxMenu.querySelectorAll("button").forEach((b) => b.onclick = (ev) => {
        ev.stopPropagation(); hideCtx();
        const a = b.dataset.a;
        if (a === "pin") { isPinned ? pinned.delete(n.id) : pinned.add(n.id); reheat(0.4); }
        else if (a === "expand") { select(n); flyTo(n, Math.max(view.scale, 1.7)); }
        else if (a === "find") { const ci = document.querySelector(".cmd-input"); if (ci) { ci.value = "Tell me what you know about " + n.name; ci.focus(); } }
        else if (a === "forget") { if (confirm(`Forget "${n.name}" and its links?`)) fetch("/api/knowledge/entity/" + encodeURIComponent(n.name), { method: "DELETE" }).then(() => { load(); refreshBeads(); }); }
      });
    });

    // ── Mini-map: overview + click-to-recentre ────────────────────────────────
    const mini = document.createElement("canvas");
    mini.className = "mr-minimap";
    stage.appendChild(mini);
    const mctx = mini.getContext("2d");
    const mW = 124, mH = 86;
    function drawMini() {
      const d2 = Math.min(window.devicePixelRatio || 1, 2);
      if (mini.width !== mW * d2) { mini.width = mW * d2; mini.height = mH * d2; mini.style.width = mW + "px"; mini.style.height = mH + "px"; }
      mctx.setTransform(d2, 0, 0, d2, 0, 0);
      mctx.clearRect(0, 0, mW, mH);
      if (!G.nodes.length) return;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      G.nodes.forEach((n) => { minX = Math.min(minX, n.x); minY = Math.min(minY, n.y); maxX = Math.max(maxX, n.x); maxY = Math.max(maxY, n.y); });
      const gw = (maxX - minX) || 1, gh = (maxY - minY) || 1, pad = 7;
      const sc = Math.min((mW - pad * 2) / gw, (mH - pad * 2) / gh);
      const ox = pad - minX * sc, oy = pad - minY * sc;
      G.nodes.forEach((n) => { const [r, g, b] = typeColor(n.type); mctx.fillStyle = `rgba(${r},${g},${b},0.7)`; mctx.fillRect(n.x * sc + ox, n.y * sc + oy, 1.5, 1.5); });
      const w0 = (0 - view.tx) / view.scale, h0 = (0 - view.ty) / view.scale, w1 = (W - view.tx) / view.scale, h1 = (H - view.ty) / view.scale;
      mctx.strokeStyle = "rgba(234,246,255,0.55)"; mctx.lineWidth = 1;
      mctx.strokeRect(w0 * sc + ox, h0 * sc + oy, (w1 - w0) * sc, (h1 - h0) * sc);
      mini._map = { sc, ox, oy };
    }
    mini.addEventListener("click", (e) => {
      const r = mini.getBoundingClientRect(), map = mini._map; if (!map) return;
      const wx = (e.clientX - r.left - map.ox) / map.sc, wy = (e.clientY - r.top - map.oy) / map.sc;
      view.tx = W / 2 - wx * view.scale; view.ty = H / 2 - wy * view.scale; camTween = null;
    });

    function bestMatch() {
      if (!G.filter) return null;
      return G.nodes
        .filter((n) => n.name.toLowerCase().includes(G.filter))
        .sort((a, b) => b.deg - a.deg || (b.importance || 0) - (a.importance || 0))[0] || null;
    }
    searchEl.addEventListener("input", () => {
      G.filter = searchEl.value.toLowerCase().trim();
      if (G.filter) { const m = bestMatch(); if (m) { G.hover = m; flyTo(m, Math.max(view.scale, 1.4)); } }
      else { G.hover = null; camTween = null; }
    });
    searchEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { const m = bestMatch(); if (m) { select(m); flyTo(m, Math.max(view.scale, 1.6)); } }
    });
    body.querySelector(".mr-refresh").addEventListener("click", () => { load(); refreshBeads(); });

    // ── GNN: train a GraphSAGE and overlay its predicted hidden connections ────
    function addGnnEdges() {
      if (!G.gnnLinks || !G.gnnLinks.length) return;
      const byId = {}; G.nodes.forEach((n) => { byId[n.id] = n; });
      G.edges = G.edges.filter((e) => e.kind !== "gnn");   // avoid dupes on re-ingest
      G.gnnLinks.forEach((p) => {
        const s = byId[p.source], t = byId[p.target];
        if (s && t) G.edges.push({ s, t, rel: "predicted", conf: p.score, kind: "gnn", seed: Math.random() });
      });
    }
    const gnnBtn = body.querySelector(".mr-gnn");
    gnnBtn.addEventListener("click", async () => {
      const prev = gnnBtn.textContent; gnnBtn.textContent = "training…"; gnnBtn.disabled = true;
      showStatus("training GraphSAGE GNN…", true);
      try {
        const r = await fetch("/api/knowledge/gnn?epochs=80", { method: "POST" });
        const d = await r.json();
        G.gnnLinks = d.predicted_links || [];
        addGnnEdges();
        reheat(0.5);
        hideStatus();
        gnnBtn.classList.add("on");
        gnnBtn.textContent = `✦ ${G.gnnLinks.length}`;
        window.SFX && SFX.play("blip");
      } catch (_) { gnnBtn.textContent = prev; hideStatus(); }
      finally { gnnBtn.disabled = false; }
    });

    // Teach — ingest a free-text fact into the persistent knowledge base, then
    // reload so the new entity/relationships appear live in the graph + ring.
    async function teach() {
      const text = (teachIn.value || "").trim();
      if (!text) return;
      teachIn.disabled = true; teachBtn.disabled = true;
      const prev = teachBtn.textContent; teachBtn.textContent = "…";
      try {
        await fetch("/api/knowledge/teach", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        teachIn.value = "";
        _vaultCache = null;
        await load();
        refreshBeads();
        window.SFX && SFX.play("blip");
      } catch (_) {}
      finally { teachIn.disabled = false; teachBtn.disabled = false; teachBtn.textContent = prev; teachIn.focus(); }
    }
    teachBtn.addEventListener("click", teach);
    teachIn.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); teach(); } });

    async function load() {
      if (!_vaultCache) showStatus("building connections…", true);   // cold load embeds entities (~20s)
      let vault = _vaultCache;
      try { const r = await fetch("/api/knowledge/vault?limit=200"); if (r.ok) { vault = await r.json(); _vaultCache = vault; } } catch (_) {}
      if (!vault || vault.error) {
        statsEl.textContent = "memory empty"; G.nodes = []; G.edges = []; legendEl.innerHTML = "";
        showStatus("Couldn’t reach memory.", false); return;
      }
      ingest(vault);
      if (!G.nodes.length) showStatus("No memories yet — teach DEEP a fact below ↓", false);
      else hideStatus();
    }

    win._mrResize = () => sizeCanvas();
    win._mrStop = () => cancelAnimationFrame(raf);

    sizeCanvas();
    load();
    loop();
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 3) REGISTER WITH HUD + boot
  // ─────────────────────────────────────────────────────────────────────────
  function register() {
    if (!window.HUD) { return setTimeout(register, 120); }
    HUD.registerApp({
      id: "memory-ring",
      title: "Neural Memory",
      icon: "◌",
      anchor: "core",
      anchorAngle: -Math.PI * 0.72,
      width: 560, height: 440, minWidth: 360, minHeight: 280,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="3" r="1.4" fill="currentColor"/><circle cx="20" cy="16" r="1.2" fill="currentColor"/><circle cx="5" cy="17" r="1.2" fill="currentColor"/></svg>',
      build: buildGraphWindow,
      onResize: (w, h, win) => win._mrResize && win._mrResize(),
      onClose: (win) => win._mrStop && win._mrStop(),
    });
  }

  function boot() {
    initRingCanvas();
    refreshBeads();
    setInterval(refreshBeads, 20000);
    register();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  // Expose for command palette / external triggers
  window.openMemoryRing = () => window.HUD && HUD.open("memory-ring");
  console.log("[DEEP] Memory Ring initialised ✓");
})();
