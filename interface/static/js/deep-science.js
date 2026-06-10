/* ============================================================================
 * DEEP — SCIENCE STUDIO
 * ----------------------------------------------------------------------------
 * A modern, interactive scientific surface registered as a HUD app:
 *
 *   • GRAPHER  — a real graphing calculator. Multiple colour-coded functions
 *                y = f(x), a from-scratch safe expression compiler, infinite
 *                pan (drag), wheel zoom about the cursor, live trace readout,
 *                adaptive 1-2-5 grid. Fully client-side / offline.
 *
 *   • ENGINE   — natural-language access to DEEP's 16-domain compute engine via
 *                POST /api/science/compute. Renders the spoken answer, any
 *                generated plot/animation media, and a compact result inspector.
 *                Preset chips showcase calculus, physics, chemistry, astro, ML…
 *
 * Classic script. Uses window.HUD, window.SFX, window.DeckFX when present.
 * ========================================================================== */
(function () {
  "use strict";

  const COLORS = ["#38e8ff", "#ff5bbd", "#ffd166", "#7CFFB2", "#b98bff", "#ff8c5a"];
  const $ = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  const sfx = (n) => { try { window.SFX && SFX.play(n); } catch (_) {} };

  /* ═══════════════════════════════════════════════════════════════════════
   * SAFE EXPRESSION COMPILER  (tokenize → shunting-yard → RPN evaluator)
   * ═════════════════════════════════════════════════════════════════════ */
  const FUNCS = {
    sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos,
    atan: Math.atan, sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh,
    exp: Math.exp, sqrt: Math.sqrt, cbrt: Math.cbrt, abs: Math.abs, sign: Math.sign,
    floor: Math.floor, ceil: Math.ceil, round: Math.round,
    ln: Math.log, log: (x) => Math.log10(x), log2: Math.log2,
    sec: (x) => 1 / Math.cos(x), csc: (x) => 1 / Math.sin(x), cot: (x) => 1 / Math.tan(x),
  };
  const CONSTS = { pi: Math.PI, e: Math.E, tau: Math.PI * 2, phi: (1 + Math.sqrt(5)) / 2 };
  const OPS = { "+": [1, "L"], "-": [1, "L"], "*": [2, "L"], "/": [2, "L"], "%": [2, "L"], "^": [4, "R"] };

  function tokenize(s) {
    const out = []; let i = 0;
    const isd = (c) => c >= "0" && c <= "9";
    const isa = (c) => /[a-zA-Z_]/.test(c);
    while (i < s.length) {
      const c = s[i];
      if (c === " ") { i++; continue; }
      if (isd(c) || (c === "." && isd(s[i + 1]))) {
        let j = i + 1;
        while (j < s.length && (isd(s[j]) || s[j] === "." || s[j] === "e" || s[j] === "E" ||
               ((s[j] === "+" || s[j] === "-") && (s[j - 1] === "e" || s[j - 1] === "E")))) j++;
        out.push({ t: "num", v: parseFloat(s.slice(i, j)) }); i = j; continue;
      }
      if (isa(c)) {
        let j = i + 1; while (j < s.length && (isa(s[j]) || isd(s[j]))) j++;
        out.push({ t: "name", v: s.slice(i, j) }); i = j; continue;
      }
      if (c in OPS || c === "(" || c === ")" || c === ",") { out.push({ t: "op", v: c }); i++; continue; }
      throw new Error("bad char '" + c + "'");
    }
    return out;
  }

  function toRPN(toks) {
    const out = [], stack = [];
    let prev = null;
    for (let k = 0; k < toks.length; k++) {
      const tk = toks[k];
      if (tk.t === "num") { out.push(tk); }
      else if (tk.t === "name") {
        if (FUNCS[tk.v]) stack.push({ t: "func", v: tk.v });
        else out.push({ t: "var", v: tk.v });
      } else if (tk.v === ",") {
        while (stack.length && stack[stack.length - 1].v !== "(") out.push(stack.pop());
      } else if (tk.v in OPS) {
        // unary minus/plus detection
        const unary = (!prev || (prev.t === "op" && prev.v !== ")"));
        if ((tk.v === "-" || tk.v === "+") && unary) {
          out.push({ t: "num", v: 0 });
        }
        const [p1, a1] = OPS[tk.v];
        while (stack.length) {
          const top = stack[stack.length - 1];
          if (top.t === "op" && top.v in OPS) {
            const [p2] = OPS[top.v];
            if ((a1 === "L" && p1 <= p2) || (a1 === "R" && p1 < p2)) out.push(stack.pop());
            else break;
          } else if (top.t === "func") { out.push(stack.pop()); }
          else break;
        }
        stack.push({ t: "op", v: tk.v });
      } else if (tk.v === "(") { stack.push(tk); }
      else if (tk.v === ")") {
        while (stack.length && stack[stack.length - 1].v !== "(") out.push(stack.pop());
        if (!stack.length) throw new Error("mismatched )");
        stack.pop();
        if (stack.length && stack[stack.length - 1].t === "func") out.push(stack.pop());
      }
      prev = tk;
    }
    while (stack.length) { const s = stack.pop(); if (s.v === "(") throw new Error("mismatched ("); out.push(s); }
    return out;
  }

  // Returns f(...vars) or throws on parse error. `vars` lists the free
  // variables in order (defaults to ['x']); call the result positionally,
  // e.g. compile("x*y",["x","y"])(2,3).
  function compile(expr, vars) {
    vars = vars || ["x"];
    const idx = {};
    vars.forEach((v, i) => { idx[v] = i; idx[v.toUpperCase()] = i; });
    const rpn = toRPN(tokenize(expr));
    return function () {
      const args = arguments;
      const st = [];
      for (const tk of rpn) {
        if (tk.t === "num") st.push(tk.v);
        else if (tk.t === "var") {
          if (tk.v in idx) st.push(args[idx[tk.v]]);
          else if (tk.v in CONSTS) st.push(CONSTS[tk.v]);
          else throw new Error("unknown '" + tk.v + "'");
        } else if (tk.t === "func") { st.push(FUNCS[tk.v](st.pop())); }
        else {
          const b = st.pop(), a = st.pop();
          st.push(tk.v === "+" ? a + b : tk.v === "-" ? a - b : tk.v === "*" ? a * b :
                  tk.v === "/" ? a / b : tk.v === "%" ? a % b : Math.pow(a, b));
        }
      }
      return st[0];
    };
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * GRAPHER
   * ═════════════════════════════════════════════════════════════════════ */
  function buildGrapher(root, win) {
    const view = { xmin: -10, xmax: 10, ymin: -6, ymax: 6 };
    const fns = [];   // { expr, color, fn, err, on }

    root.innerHTML =
      `<div class="sci-fnbar" id="sciFns"></div>
       <div class="sci-graphwrap">
         <canvas class="sci-canvas" id="sciCanvas"></canvas>
         <div class="sci-readout" id="sciReadout"></div>
         <div class="sci-gtools">
           <button class="sci-icbtn" id="sciHome" title="Reset view">⌂</button>
           <button class="sci-icbtn" id="sciZin" title="Zoom in">＋</button>
           <button class="sci-icbtn" id="sciZout" title="Zoom out">－</button>
         </div>
       </div>`;
    const fnbar = root.querySelector("#sciFns");
    const canvas = root.querySelector("#sciCanvas");
    const readout = root.querySelector("#sciReadout");
    const ctx = canvas.getContext("2d");
    let dpr = Math.min(devicePixelRatio || 1, 2), W = 0, H = 0;

    function addFn(expr) {
      const row = { expr: expr || "", color: COLORS[fns.length % COLORS.length], fn: null, err: false, on: true };
      fns.push(row);
      renderFnBar(); recompile(row); draw();
    }
    function renderFnBar() {
      fnbar.innerHTML = "";
      fns.forEach((r, i) => {
        const el = $("div", "sci-fnrow" + (r.err ? " err" : ""));
        el.innerHTML =
          `<button class="sci-swatch" style="--c:${r.color}" title="Toggle"></button>
           <span class="sci-fnlabel">y=</span>
           <input class="sci-fninput" spellcheck="false" value="${r.expr.replace(/"/g, "&quot;")}" placeholder="sin(x)·…">
           <button class="sci-fndel" title="Remove">✕</button>`;
        const inp = el.querySelector(".sci-fninput");
        inp.addEventListener("input", () => { r.expr = inp.value; recompile(r); el.classList.toggle("err", r.err); draw(); });
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter" && i === fns.length - 1) addFn(""); });
        el.querySelector(".sci-swatch").addEventListener("click", () => { r.on = !r.on; el.classList.toggle("off", !r.on); draw(); });
        el.querySelector(".sci-fndel").addEventListener("click", () => { fns.splice(i, 1); if (!fns.length) addFn(""); else { renderFnBar(); draw(); } });
        el.classList.toggle("off", !r.on);
        fnbar.appendChild(el);
      });
      const add = $("button", "sci-fnadd", "＋ function");
      add.addEventListener("click", () => addFn(""));
      fnbar.appendChild(add);
    }
    function recompile(r) {
      const e = (r.expr || "").trim();
      if (!e) { r.fn = null; r.err = false; return; }
      try { r.fn = compile(e); r.fn(0.1); r.err = false; } catch (_) { r.fn = null; r.err = true; }
    }

    // ── geometry ──
    const X2px = (x) => (x - view.xmin) / (view.xmax - view.xmin) * W;
    const Y2px = (y) => H - (y - view.ymin) / (view.ymax - view.ymin) * H;
    const px2X = (px) => view.xmin + px / W * (view.xmax - view.xmin);
    const px2Y = (py) => view.ymin + (H - py) / H * (view.ymax - view.ymin);

    function niceStep(range, target) {
      const raw = range / target, mag = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / mag;
      return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
    }

    function size() {
      W = canvas.clientWidth; H = canvas.clientHeight;
      canvas.width = W * dpr; canvas.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }

    function draw() {
      if (!W) return;
      ctx.clearRect(0, 0, W, H);
      const sx = niceStep(view.xmax - view.xmin, 10), sy = niceStep(view.ymax - view.ymin, 8);
      // grid
      ctx.lineWidth = 1; ctx.font = "10px 'JetBrains Mono', monospace"; ctx.textBaseline = "top";
      for (let gx = Math.ceil(view.xmin / sx) * sx; gx <= view.xmax; gx += sx) {
        const px = X2px(gx); const axis = Math.abs(gx) < sx / 1e6;
        ctx.strokeStyle = axis ? "rgba(150,180,210,0.5)" : "rgba(120,150,190,0.10)";
        ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, H); ctx.stroke();
        if (!axis) { ctx.fillStyle = "rgba(170,195,225,0.45)"; ctx.fillText(fmt(gx), px + 3, Y2px(0) + 3); }
      }
      for (let gy = Math.ceil(view.ymin / sy) * sy; gy <= view.ymax; gy += sy) {
        const py = Y2px(gy); const axis = Math.abs(gy) < sy / 1e6;
        ctx.strokeStyle = axis ? "rgba(150,180,210,0.5)" : "rgba(120,150,190,0.10)";
        ctx.beginPath(); ctx.moveTo(0, py); ctx.lineTo(W, py); ctx.stroke();
        if (!axis) { ctx.fillStyle = "rgba(170,195,225,0.45)"; ctx.fillText(fmt(gy), X2px(0) + 4, py + 2); }
      }
      // functions
      for (const r of fns) {
        if (!r.on || !r.fn) continue;
        ctx.strokeStyle = r.color; ctx.lineWidth = 2; ctx.beginPath();
        let pen = false, prevY = 0;
        for (let px = 0; px <= W; px++) {
          const x = px2X(px); let y;
          try { y = r.fn(x); } catch (_) { y = NaN; }
          if (!isFinite(y)) { pen = false; continue; }
          const py = Y2px(y);
          if (pen && Math.abs(py - prevY) > H * 2) pen = false;   // discontinuity guard
          if (pen) ctx.lineTo(px, py); else ctx.moveTo(px, py);
          pen = true; prevY = py;
        }
        ctx.stroke();
      }
    }
    function fmt(v) {
      if (v === 0) return "0";
      const a = Math.abs(v);
      return (a >= 1e4 || a < 1e-3) ? v.toExponential(1) : (Math.round(v * 1000) / 1000).toString();
    }

    // ── interaction ──
    let drag = false, lx = 0, ly = 0;
    canvas.addEventListener("pointerdown", (e) => { drag = true; lx = e.offsetX; ly = e.offsetY; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => {
      if (drag) {
        const dx = (e.offsetX - lx) / W * (view.xmax - view.xmin);
        const dy = (e.offsetY - ly) / H * (view.ymax - view.ymin);
        view.xmin -= dx; view.xmax -= dx; view.ymin += dy; view.ymax += dy;
        lx = e.offsetX; ly = e.offsetY; draw();
      }
      const x = px2X(e.offsetX);
      let s = `x = ${fmt(x)}`;
      fns.forEach((r, i) => { if (r.on && r.fn) { try { const y = r.fn(x); if (isFinite(y)) s += `   <b style="color:${r.color}">y${i + 1}=${fmt(y)}</b>`; } catch (_) {} } });
      readout.innerHTML = s;
    });
    canvas.addEventListener("pointerup", (e) => { drag = false; try { canvas.releasePointerCapture(e.pointerId); } catch (_) {} });
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const f = e.deltaY < 0 ? 0.85 : 1.176;
      const cx = px2X(e.offsetX), cy = px2Y(e.offsetY);
      view.xmin = cx + (view.xmin - cx) * f; view.xmax = cx + (view.xmax - cx) * f;
      view.ymin = cy + (view.ymin - cy) * f; view.ymax = cy + (view.ymax - cy) * f;
      draw();
    }, { passive: false });

    function zoom(f) {
      const cx = (view.xmin + view.xmax) / 2, cy = (view.ymin + view.ymax) / 2;
      view.xmin = cx + (view.xmin - cx) * f; view.xmax = cx + (view.xmax - cx) * f;
      view.ymin = cy + (view.ymin - cy) * f; view.ymax = cy + (view.ymax - cy) * f; draw();
    }
    root.querySelector("#sciHome").addEventListener("click", () => { view.xmin = -10; view.xmax = 10; view.ymin = -6; view.ymax = 6; draw(); sfx("blip"); });
    root.querySelector("#sciZin").addEventListener("click", () => { zoom(0.7); sfx("blip"); });
    root.querySelector("#sciZout").addEventListener("click", () => { zoom(1.4); sfx("blip"); });

    root._resize = () => { dpr = Math.min(devicePixelRatio || 1, 2); size(); };
    addFn("sin(x)"); addFn("0.3*x^2 - 2");
    requestAnimationFrame(size);
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * SHARED — colormap + lightweight plot helpers
   * ═════════════════════════════════════════════════════════════════════ */
  // height t∈[0,1] → cyan→violet→magenta neon ramp
  function heatColor(t, a) {
    t = Math.max(0, Math.min(1, t));
    const h = 190 + t * 130;                 // 190 (cyan) → 320 (magenta)
    const l = 42 + t * 16;
    return `hsla(${h},90%,${l}%,${a == null ? 1 : a})`;
  }
  function hsl2rgb(h, s, l) {                 // h∈[0,360], s,l∈[0,1] → [r,g,b] 0..255
    const c = (1 - Math.abs(2 * l - 1)) * s, hp = h / 60, x = c * (1 - Math.abs(hp % 2 - 1));
    let r = 0, g = 0, b = 0;
    if (hp < 1) [r, g, b] = [c, x, 0]; else if (hp < 2) [r, g, b] = [x, c, 0];
    else if (hp < 3) [r, g, b] = [0, c, x]; else if (hp < 4) [r, g, b] = [0, x, c];
    else if (hp < 5) [r, g, b] = [x, 0, c]; else [r, g, b] = [c, 0, x];
    const m = l - c / 2;
    return [(r + m) * 255, (g + m) * 255, (b + m) * 255];
  }
  function heatRGB(t) { t = Math.max(0, Math.min(1, t)); return hsl2rgb(190 + t * 130, 0.9, (42 + t * 16) / 100); }
  // diffuse + ambient (two-sided) lighting → modulated rgba string
  function shade(rgb, lambert, a) {
    const k = 0.32 + 0.78 * Math.abs(lambert);
    return `rgba(${Math.min(255, rgb[0] * k) | 0},${Math.min(255, rgb[1] * k) | 0},${Math.min(255, rgb[2] * k) | 0},${a == null ? 1 : a})`;
  }
  function niceStep(range, target) {
    const raw = range / target, mag = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / mag;
    return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
  }
  function fmtNum(v) {
    if (v === 0) return "0";
    const a = Math.abs(v);
    return (a >= 1e4 || a < 1e-3) ? v.toExponential(1) : (Math.round(v * 1000) / 1000).toString();
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * PARAMETRIC / POLAR  (2D)
   * ═════════════════════════════════════════════════════════════════════ */
  function buildParametric(root, win) {
    root.innerHTML =
      `<div class="sci-fnbar">
         <div class="sci-segrow">
           <button class="sci-seg active" data-m="param">x(t), y(t)</button>
           <button class="sci-seg" data-m="polar">r(θ)</button>
         </div>
         <div id="pParam">
           <div class="sci-fnrow"><span class="sci-fnlabel">x=</span><input class="sci-fninput" id="pX" spellcheck="false" value="cos(t)*(1+0.5*cos(5*t))"></div>
           <div class="sci-fnrow"><span class="sci-fnlabel">y=</span><input class="sci-fninput" id="pY" spellcheck="false" value="sin(t)*(1+0.5*cos(5*t))"></div>
         </div>
         <div id="pPolar" style="display:none">
           <div class="sci-fnrow"><span class="sci-fnlabel">r=</span><input class="sci-fninput" id="pR" spellcheck="false" value="cos(4*theta)"></div>
         </div>
         <div class="sci-rangerow">
           <span class="sci-fnlabel" id="pLbl">t ∈</span>
           <input class="sci-num" id="pT0" value="0"><span class="sci-dots">…</span><input class="sci-num" id="pT1" value="6.283">
           <button class="sci-fnadd" id="pPlot">▶ plot</button>
         </div>
       </div>
       <div class="sci-graphwrap">
         <canvas class="sci-canvas" id="pCanvas"></canvas>
         <div class="sci-readout" id="pInfo">parametric curve</div>
         <div class="sci-gtools"><button class="sci-icbtn" id="pHome" title="Fit">⌂</button></div>
       </div>`;
    const canvas = root.querySelector("#pCanvas");
    const info = root.querySelector("#pInfo");
    const ctx = canvas.getContext("2d");
    let dpr = Math.min(devicePixelRatio || 1, 2), W = 0, H = 0;
    let mode = "param", pts = [], view = null, err = false;

    const X2px = (x) => (x - view.xmin) / (view.xmax - view.xmin) * W;
    const Y2px = (y) => H - (y - view.ymin) / (view.ymax - view.ymin) * H;
    const px2X = (px) => view.xmin + px / W * (view.xmax - view.xmin);
    const px2Y = (py) => view.ymin + (H - py) / H * (view.ymax - view.ymin);

    function recompute(fit) {
      err = false;
      const t0 = parseFloat(root.querySelector("#pT0").value);
      const t1 = parseFloat(root.querySelector("#pT1").value);
      const N = 2400;
      pts = [];
      try {
        if (mode === "param") {
          const fx = compile(root.querySelector("#pX").value, ["t"]);
          const fy = compile(root.querySelector("#pY").value, ["t"]);
          for (let i = 0; i <= N; i++) { const t = t0 + (t1 - t0) * i / N; pts.push([fx(t), fy(t)]); }
        } else {
          const fr = compile(root.querySelector("#pR").value, ["theta", "t"]);
          for (let i = 0; i <= N; i++) { const th = t0 + (t1 - t0) * i / N; const r = fr(th, th); pts.push([r * Math.cos(th), r * Math.sin(th)]); }
        }
      } catch (_) { err = true; }
      if (fit || !view) fitView();
      draw();
    }
    function fitView() {
      let mnx = Infinity, mxx = -Infinity, mny = Infinity, mxy = -Infinity;
      for (const p of pts) { if (!isFinite(p[0]) || !isFinite(p[1])) continue; mnx = Math.min(mnx, p[0]); mxx = Math.max(mxx, p[0]); mny = Math.min(mny, p[1]); mxy = Math.max(mxy, p[1]); }
      if (!isFinite(mnx)) { view = { xmin: -2, xmax: 2, ymin: -2, ymax: 2 }; return; }
      const px = (mxx - mnx) * 0.12 + 1e-6, py = (mxy - mny) * 0.12 + 1e-6;
      view = { xmin: mnx - px, xmax: mxx + px, ymin: mny - py, ymax: mxy + py };
      // keep aspect square-ish
      const ar = W && H ? W / H : 1.2, vw = view.xmax - view.xmin, vh = view.ymax - view.ymin;
      if (vw / vh < ar) { const c = (view.xmin + view.xmax) / 2, half = vh * ar / 2; view.xmin = c - half; view.xmax = c + half; }
      else { const c = (view.ymin + view.ymax) / 2, half = vw / ar / 2; view.ymin = c - half; view.ymax = c + half; }
    }
    function size() { W = canvas.clientWidth; H = canvas.clientHeight; canvas.width = W * dpr; canvas.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); if (!view) fitView(); draw(); }
    function draw() {
      if (!W || !view) return;
      ctx.clearRect(0, 0, W, H);
      const sx = niceStep(view.xmax - view.xmin, 10), sy = niceStep(view.ymax - view.ymin, 8);
      ctx.lineWidth = 1; ctx.font = "10px 'JetBrains Mono', monospace"; ctx.textBaseline = "top";
      for (let gx = Math.ceil(view.xmin / sx) * sx; gx <= view.xmax; gx += sx) { const px = X2px(gx); const ax = Math.abs(gx) < sx / 1e6; ctx.strokeStyle = ax ? "rgba(150,180,210,0.5)" : "rgba(120,150,190,0.10)"; ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, H); ctx.stroke(); }
      for (let gy = Math.ceil(view.ymin / sy) * sy; gy <= view.ymax; gy += sy) { const py = Y2px(gy); const ax = Math.abs(gy) < sy / 1e6; ctx.strokeStyle = ax ? "rgba(150,180,210,0.5)" : "rgba(120,150,190,0.10)"; ctx.beginPath(); ctx.moveTo(0, py); ctx.lineTo(W, py); ctx.stroke(); }
      if (err) { info.innerHTML = '<b style="color:#ff7a7a">expression error</b>'; return; }
      ctx.lineWidth = 2; ctx.lineJoin = "round"; let pen = false;
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]; if (!isFinite(p[0]) || !isFinite(p[1])) { pen = false; continue; }
        const px = X2px(p[0]), py = Y2px(p[1]);
        if (i % 12 === 0) { ctx.strokeStyle = heatColor(i / pts.length, 0.95); if (pen) { ctx.stroke(); } ctx.beginPath(); ctx.moveTo(px, py); pen = true; }
        else if (pen) ctx.lineTo(px, py);
      }
      if (pen) ctx.stroke();
      info.textContent = mode === "param" ? "parametric (x(t), y(t))" : "polar r(θ)";
    }

    // interaction
    let drag = false, lx = 0, ly = 0;
    canvas.addEventListener("pointerdown", (e) => { drag = true; lx = e.offsetX; ly = e.offsetY; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => { if (!drag || !view) return; const dx = (e.offsetX - lx) / W * (view.xmax - view.xmin); const dy = (e.offsetY - ly) / H * (view.ymax - view.ymin); view.xmin -= dx; view.xmax -= dx; view.ymin += dy; view.ymax += dy; lx = e.offsetX; ly = e.offsetY; draw(); });
    canvas.addEventListener("pointerup", (e) => { drag = false; try { canvas.releasePointerCapture(e.pointerId); } catch (_) {} });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); if (!view) return; const f = e.deltaY < 0 ? 0.85 : 1.176; const cx = px2X(e.offsetX), cy = px2Y(e.offsetY); view.xmin = cx + (view.xmin - cx) * f; view.xmax = cx + (view.xmax - cx) * f; view.ymin = cy + (view.ymin - cy) * f; view.ymax = cy + (view.ymax - cy) * f; draw(); }, { passive: false });

    root.querySelectorAll(".sci-seg").forEach((b) => b.addEventListener("click", () => {
      root.querySelectorAll(".sci-seg").forEach((x) => x.classList.toggle("active", x === b));
      mode = b.dataset.m;
      root.querySelector("#pParam").style.display = mode === "param" ? "" : "none";
      root.querySelector("#pPolar").style.display = mode === "polar" ? "" : "none";
      root.querySelector("#pLbl").textContent = mode === "param" ? "t ∈" : "θ ∈";
      recompute(true); sfx("blip");
    }));
    root.querySelectorAll(".sci-fninput, .sci-num").forEach((i) => i.addEventListener("keydown", (e) => { if (e.key === "Enter") recompute(true); }));
    root.querySelector("#pPlot").addEventListener("click", () => { recompute(true); sfx("blip"); });
    root.querySelector("#pHome").addEventListener("click", () => { fitView(); draw(); sfx("blip"); });

    root._resize = () => { dpr = Math.min(devicePixelRatio || 1, 2); size(); };
    requestAnimationFrame(() => { size(); recompute(true); });
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * 3D  —  surface z=f(x,y) and parametric space curve (custom canvas engine)
   * ═════════════════════════════════════════════════════════════════════ */
  function build3D(root, win) {
    root.innerHTML =
      `<div class="sci-fnbar">
         <div class="sci-segrow">
           <button class="sci-seg active" data-m="surface">z = f(x, y)</button>
           <button class="sci-seg" data-m="curve">space curve</button>
         </div>
         <div id="dSurface">
           <div class="sci-fnrow"><span class="sci-fnlabel">z=</span><input class="sci-fninput" id="dZ" spellcheck="false" value="sin(sqrt(x^2+y^2))"></div>
         </div>
         <div id="dCurve" style="display:none">
           <div class="sci-fnrow"><span class="sci-fnlabel">x=</span><input class="sci-fninput" id="dCx" spellcheck="false" value="cos(t)"></div>
           <div class="sci-fnrow"><span class="sci-fnlabel">y=</span><input class="sci-fninput" id="dCy" spellcheck="false" value="sin(t)"></div>
           <div class="sci-fnrow"><span class="sci-fnlabel">z=</span><input class="sci-fninput" id="dCz" spellcheck="false" value="0.2*t"></div>
         </div>
         <div class="sci-rangerow">
           <span class="sci-fnlabel" id="dLbl">x,y ∈ ±</span><input class="sci-num" id="dDom" value="5">
           <button class="sci-fnadd" id="dPlot">▶ render</button>
           <span class="sci-hint">drag to orbit · wheel to zoom</span>
         </div>
       </div>
       <div class="sci-graphwrap">
         <canvas class="sci-canvas" id="dCanvas" style="cursor:grab"></canvas>
         <div class="sci-readout" id="dInfo">surface</div>
         <div class="sci-gtools">
           <button class="sci-icbtn active" data-shade="shaded" title="Shaded">◑</button>
           <button class="sci-icbtn" data-shade="wire" title="Wireframe">⊞</button>
           <button class="sci-icbtn" data-shade="contour" title="Contour bands">≋</button>
           <button class="sci-icbtn active" id="dRot" title="Auto-rotate">⟳</button>
         </div>
       </div>`;
    const canvas = root.querySelector("#dCanvas");
    const info = root.querySelector("#dInfo");
    const ctx = canvas.getContext("2d");
    let dpr = Math.min(devicePixelRatio || 1, 2), W = 0, H = 0;
    let mode = "surface", shadeMode = "shaded", autoRot = true;
    let yaw = -0.7, pitch = 0.95, scale = 1, err = false;
    let quads = null, curve = null, zmin = 0, zmax = 1;
    let raf = 0, introStart = 0, lastT = 0;
    const RES = 40;
    const LIGHT = (() => { const v = [-0.32, -0.45, 0.83], m = Math.hypot(...v); return v.map((c) => c / m); })();

    const vsub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    const vcross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    function vnorm(a) { const m = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / m, a[1] / m, a[2] / m]; }

    function compute() {
      err = false;
      const dom = Math.max(0.5, Math.abs(parseFloat(root.querySelector("#dDom").value) || 5));
      try {
        if (mode === "surface") {
          const f = compile(root.querySelector("#dZ").value, ["x", "y"]);
          const grid = []; zmin = Infinity; zmax = -Infinity;
          for (let i = 0; i <= RES; i++) {
            const row = [];
            for (let j = 0; j <= RES; j++) {
              const x = -dom + 2 * dom * i / RES, y = -dom + 2 * dom * j / RES;
              let z = f(x, y); if (!isFinite(z)) z = NaN; else { zmin = Math.min(zmin, z); zmax = Math.max(zmax, z); }
              row.push([x, y, z]);
            }
            grid.push(row);
          }
          const zr = (zmax - zmin) || 1;
          quads = [];
          for (let i = 0; i < RES; i++) for (let j = 0; j < RES; j++) {
            const c = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]];
            if (c.some((p) => !isFinite(p[2]))) continue;
            const norm = c.map((p) => [p[0] / dom, p[1] / dom, ((p[2] - zmin) / zr - 0.5) * 1.4]);
            const n = vnorm(vcross(vsub(norm[2], norm[0]), vsub(norm[3], norm[1])));
            const t = (c.reduce((s, p) => s + p[2], 0) / 4 - zmin) / zr;
            quads.push({ p: norm, n, t, rgb: heatRGB(t) });
          }
          curve = null;
        } else {
          const t0 = -Math.PI * 2, t1 = Math.PI * 2;
          const fx = compile(root.querySelector("#dCx").value, ["t"]);
          const fy = compile(root.querySelector("#dCy").value, ["t"]);
          const fz = compile(root.querySelector("#dCz").value, ["t"]);
          const raw = []; let mx = 0;
          for (let i = 0; i <= 1200; i++) { const t = t0 + (t1 - t0) * i / 1200; const p = [fx(t), fy(t), fz(t)]; raw.push(p); for (const v of p) if (isFinite(v)) mx = Math.max(mx, Math.abs(v)); }
          mx = mx || 1;
          curve = raw.map((p) => [p[0] / mx, p[1] / mx, p[2] / mx]);
          quads = null;
        }
      } catch (_) { err = true; }
      introStart = performance.now(); ensureLoop();
    }
    // rotate an object-space vector into view space [right, depth, up]
    function rot(p) {
      const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      const x1 = p[0] * cy - p[1] * sy, y1 = p[0] * sy + p[1] * cy;
      return [x1, y1 * cp - p[2] * sp, y1 * sp + p[2] * cp];
    }
    function project(p) { const r = rot(p), s = Math.min(W, H) * 0.34 * scale; return { x: W / 2 + r[0] * s, y: H / 2 - r[2] * s, depth: r[1] }; }
    function size() { W = canvas.clientWidth; H = canvas.clientHeight; canvas.width = W * dpr; canvas.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); draw(1); }

    function draw(alpha) {
      if (!W) return;
      alpha = alpha == null ? 1 : alpha;
      ctx.clearRect(0, 0, W, H);
      // floor + back walls give the scene a sense of volume
      ctx.lineWidth = 1; ctx.strokeStyle = "rgba(120,150,190,0.16)";
      const floor = [[-1, -1, -0.72], [1, -1, -0.72], [1, 1, -0.72], [-1, 1, -0.72]].map(project);
      ctx.beginPath(); floor.forEach((q, i) => i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y)); ctx.closePath(); ctx.stroke();
      for (let g = -1; g <= 1; g += 0.5) {
        const a = project([g, -1, -0.72]), b = project([g, 1, -0.72]), c = project([-1, g, -0.72]), d = project([1, g, -0.72]);
        ctx.strokeStyle = "rgba(120,150,190,0.07)";
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
      }
      if (err) { info.innerHTML = '<b style="color:#ff7a7a">expression error</b>'; return; }
      ctx.globalAlpha = alpha;
      if (quads) {
        const drawn = quads.map((q) => {
          const sp = q.p.map(project);
          const nv = rot(q.n);
          const lam = nv[0] * LIGHT[0] + nv[1] * LIGHT[1] + nv[2] * LIGHT[2];
          return { sp, depth: (sp[0].depth + sp[1].depth + sp[2].depth + sp[3].depth) / 4, t: q.t, rgb: q.rgb, lam };
        });
        drawn.sort((a, b) => a.depth - b.depth);
        for (const q of drawn) {
          ctx.beginPath(); q.sp.forEach((s, i) => i ? ctx.lineTo(s.x, s.y) : ctx.moveTo(s.x, s.y)); ctx.closePath();
          if (shadeMode === "wire") {
            ctx.strokeStyle = shade(q.rgb, q.lam, 0.85); ctx.lineWidth = 1; ctx.stroke();
          } else if (shadeMode === "contour") {
            const band = Math.floor(q.t * 9) / 9;
            ctx.fillStyle = shade(heatRGB(band), 0.55 + 0.45 * Math.abs(q.lam), 0.95); ctx.fill();
            ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 0.5; ctx.stroke();
          } else {
            ctx.fillStyle = shade(q.rgb, q.lam, 0.96); ctx.fill();
            ctx.strokeStyle = "rgba(2,8,16,0.22)"; ctx.lineWidth = 0.5; ctx.stroke();
          }
        }
        info.textContent = `surface · z∈[${fmtNum(zmin)}, ${fmtNum(zmax)}] · ${shadeMode}`;
      } else if (curve) {
        const n = Math.max(2, Math.floor(curve.length * (introStart ? Math.min(1, (performance.now() - introStart) / 600) : 1)));
        ctx.lineWidth = 2.6; ctx.lineJoin = "round";
        for (let i = 1; i < n; i++) { const a = project(curve[i - 1]), b = project(curve[i]); ctx.strokeStyle = heatColor(i / curve.length, 0.95); ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); }
        info.textContent = "space curve (x(t), y(t), z(t))";
      }
      ctx.globalAlpha = 1;
    }

    // single shared animation loop — drives the reveal fade + idle orbit,
    // throttled to ~33ms and parked whenever the pane is hidden or idle.
    function ensureLoop() { if (!raf) { lastT = 0; raf = requestAnimationFrame(tick); } }
    function tick(ts) {
      if (!root.offsetParent || document.hidden) { raf = 0; return; }
      const dt = ts - lastT; if (dt < 33) { raf = requestAnimationFrame(tick); return; }
      lastT = ts;
      const introT = introStart ? Math.min(1, (ts - introStart) / 460) : 1;
      const easing = 1 - Math.pow(1 - introT, 3);
      if (autoRot && !drag) yaw += 0.006;
      draw(0.15 + 0.85 * easing);
      if (introT >= 1) introStart = 0;
      const animating = (autoRot && !drag) || introStart || (curve && introStart);
      if (animating) raf = requestAnimationFrame(tick); else raf = 0;
    }

    let drag = false, lx = 0, ly = 0;
    canvas.addEventListener("pointerdown", (e) => { drag = true; lx = e.offsetX; ly = e.offsetY; canvas.style.cursor = "grabbing"; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => { if (!drag) return; yaw += (e.offsetX - lx) * 0.01; pitch += (e.offsetY - ly) * 0.01; pitch = Math.max(0.05, Math.min(Math.PI - 0.05, pitch)); lx = e.offsetX; ly = e.offsetY; draw(1); });
    canvas.addEventListener("pointerup", (e) => { drag = false; canvas.style.cursor = "grab"; ensureLoop(); try { canvas.releasePointerCapture(e.pointerId); } catch (_) {} });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); scale *= e.deltaY < 0 ? 1.12 : 0.89; scale = Math.max(0.2, Math.min(6, scale)); draw(1); }, { passive: false });

    root.querySelectorAll(".sci-seg").forEach((b) => b.addEventListener("click", () => {
      root.querySelectorAll(".sci-seg").forEach((x) => x.classList.toggle("active", x === b));
      mode = b.dataset.m;
      root.querySelector("#dSurface").style.display = mode === "surface" ? "" : "none";
      root.querySelector("#dCurve").style.display = mode === "curve" ? "" : "none";
      root.querySelector("#dLbl").textContent = mode === "surface" ? "x,y ∈ ±" : "t ∈ ±2π";
      compute(); sfx("blip");
    }));
    root.querySelectorAll("[data-shade]").forEach((b) => b.addEventListener("click", () => {
      root.querySelectorAll("[data-shade]").forEach((x) => x.classList.toggle("active", x === b));
      shadeMode = b.dataset.shade; draw(1); sfx("blip");
    }));
    root.querySelector("#dRot").addEventListener("click", (e) => { autoRot = !autoRot; e.currentTarget.classList.toggle("active", autoRot); if (autoRot) ensureLoop(); sfx("blip"); });
    root.querySelectorAll(".sci-fninput, .sci-num").forEach((i) => i.addEventListener("keydown", (e) => { if (e.key === "Enter") compute(); }));
    root.querySelector("#dPlot").addEventListener("click", () => { compute(); sfx("blip"); });

    root._resize = () => { dpr = Math.min(devicePixelRatio || 1, 2); size(); ensureLoop(); };
    requestAnimationFrame(() => { size(); compute(); });
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * ENGINE CONSOLE  (16-domain compute via /api/science/compute)
   * ═════════════════════════════════════════════════════════════════════ */
  const PRESETS = [
    "differentiate sin(x)*x^2", "integrate x^2 from 0 to 3", "solve x^2 - 5x + 6 = 0",
    "black hole 10 solar masses", "projectile at 45 degrees, 20 m/s",
    "balance equation C3H8 + O2 -> CO2 + H2O", "binding energy Z=26 A=56",
    "price a call option, stock price 105 strike 100", "animate the Lorenz attractor",
    "run a Grover search for 101", "plot sin(x)*exp(-0.1x)",
  ];

  function buildEngine(root) {
    root.innerHTML =
      `<div class="sci-chips" id="sciChips">${PRESETS.map((p) => `<button class="sci-chip">${p}</button>`).join("")}</div>
       <div class="sci-out" id="sciOut"><div class="sci-empty">Ask DEEP anything across 16 scientific domains — calculus, physics, chemistry, quantum, astro, ML, finance…</div></div>
       <form class="sci-ask" id="sciAsk">
         <input class="sci-askinput" id="sciAskInput" spellcheck="false" placeholder="e.g. integrate x^2 from 0 to 3">
         <button class="sci-asksend" type="submit">▶</button>
       </form>`;
    const out = root.querySelector("#sciOut");
    const input = root.querySelector("#sciAskInput");

    async function ask(q) {
      if (!q || !q.trim()) return;
      out.querySelector(".sci-empty")?.remove();
      const card = $("div", "sci-msg");
      card.innerHTML = `<div class="sci-q">${q}</div><div class="sci-a"><span class="sci-spin"></span> routing…</div>`;
      out.appendChild(card); out.scrollTop = out.scrollHeight; sfx("blip");
      let d;
      try { d = await (await fetch("/api/science/compute", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q }) })).json(); }
      catch (_) { d = { ok: false, verbal: "Request failed — is the server running?" }; }
      const a = card.querySelector(".sci-a");
      const tag = d.module ? `<span class="sci-mod">${d.module}${d.function ? " · " + d.function : ""}</span>` : "";
      let media = "";
      (d.media || []).forEach((m) => {
        if (m.type === "video") media += `<video class="sci-media" src="${m.url}" controls loop muted></video>`;
        else media += `<img class="sci-media" src="${m.url}" alt="${m.name || ""}" loading="lazy">`;
      });
      let detail = "";
      if (d.result != null && typeof d.result === "object") {
        detail = `<pre class="sci-detail">${escapeHtml(JSON.stringify(d.result, null, 2)).slice(0, 1400)}</pre>`;
      } else if (d.result != null && String(d.result) !== (d.verbal || "")) {
        detail = `<div class="sci-resline">${escapeHtml(String(d.result))}</div>`;
      }
      a.innerHTML = `${tag}<div class="sci-verbal">${escapeHtml(d.verbal || "(no answer)")}</div>${media}${detail}`;
      out.scrollTop = out.scrollHeight;
      if (d.ok) sfx("open");
    }
    root.querySelector("#sciAsk").addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); input.value = ""; });
    root.querySelectorAll(".sci-chip").forEach((c) => c.addEventListener("click", () => { input.value = c.textContent; ask(c.textContent); }));
  }
  function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  /* ═══════════════════════════════════════════════════════════════════════
   * SHELL  (tabbed window)
   * ═════════════════════════════════════════════════════════════════════ */
  function buildStudio(body, win) {
    body.style.cssText = "display:flex;flex-direction:column;padding:0";
    body.innerHTML =
      `<div class="sci-tabs">
         <button class="sci-tab active" data-tab="grapher">Grapher</button>
         <button class="sci-tab" data-tab="parametric">Parametric</button>
         <button class="sci-tab" data-tab="threeD">3D</button>
         <button class="sci-tab" data-tab="engine">Engine</button>
       </div>
       <div class="sci-pane" id="sciGrapher"></div>
       <div class="sci-pane" id="sciParametric" style="display:none"></div>
       <div class="sci-pane" id="sci3D" style="display:none"></div>
       <div class="sci-pane" id="sciEngine" style="display:none"></div>`;
    const panes = {
      grapher: body.querySelector("#sciGrapher"),
      parametric: body.querySelector("#sciParametric"),
      threeD: body.querySelector("#sci3D"),
      engine: body.querySelector("#sciEngine"),
    };
    buildGrapher(panes.grapher, win);
    buildParametric(panes.parametric, win);
    build3D(panes.threeD, win);
    buildEngine(panes.engine);

    let active = "grapher";
    // Dispatch HUD resize events to whichever canvas pane is visible.
    win._resize = () => { const p = panes[active]; if (p && p._resize) p._resize(); };

    body.querySelectorAll(".sci-tab").forEach((t) => t.addEventListener("click", () => {
      body.querySelectorAll(".sci-tab").forEach((x) => x.classList.toggle("active", x === t));
      active = t.dataset.tab;
      Object.keys(panes).forEach((k) => { panes[k].style.display = k === active ? "flex" : "none"; });
      const p = panes[active];
      if (p && p._resize) requestAnimationFrame(p._resize);
      sfx("blip");
    }));
  }

  /* ═══════════════════════════════════════════════════════════════════════
   * REGISTER
   * ═════════════════════════════════════════════════════════════════════ */
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    HUD.registerApp({
      id: "science", title: "Science Studio", icon: "∿", anchor: "core",
      anchorAngle: -Math.PI * 0.72, anchorDist: Math.min(innerWidth, innerHeight) * 0.34,
      width: 560, height: 520, minWidth: 380, minHeight: 340,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 17c3 0 3-10 6-10s3 10 6 10 3-7 6-7"/><path d="M3 21h18"/></svg>',
      build: buildStudio,
      onResize: (a, b, w) => w._resize && w._resize(),
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", register);
  else register();

  window.DeepScience = { compile };
  console.log("[DEEP] Science Studio online ✓");
})();
