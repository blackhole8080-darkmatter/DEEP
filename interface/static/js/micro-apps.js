/* ============================================================================
 * DEEP MICRO-APPS — the Multi-Modal I/O Mesh (UI manifestation)
 * ----------------------------------------------------------------------------
 * Independent, draggable micro-apps that live in the HUD layer:
 *   • Terminal — a command console wired to DEEP's real REST surface, with
 *     untrusted-execution routed through the Aegis sandbox.
 *   • Math/Physics — an interactive function plotter + physics simulators
 *     (projectile, pendulum, two-body orbit), using a safe expression evaluator
 *     (no eval/Function — a hand-rolled shunting-yard parser).
 *
 * Depends on window.HUD (hud-core.js). Optionally uses window.Aegis.
 * ========================================================================== */
(function () {
  "use strict";

  // ───────────────────────────────────────────────────────────────────────
  // Safe math expression evaluator (tokenize → RPN → eval). Variable: x.
  // ───────────────────────────────────────────────────────────────────────
  const FUNCS = {
    sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos,
    atan: Math.atan, sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh,
    sqrt: Math.sqrt, cbrt: Math.cbrt, exp: Math.exp, ln: Math.log,
    log: (v) => Math.log10 ? Math.log10(v) : Math.log(v) / Math.LN10,
    abs: Math.abs, sign: Math.sign, floor: Math.floor, ceil: Math.ceil, round: Math.round,
  };
  const CONSTS = { pi: Math.PI, e: Math.E, tau: Math.PI * 2 };
  const OPS = {
    "+": { p: 2, f: (a, b) => a + b }, "-": { p: 2, f: (a, b) => a - b },
    "*": { p: 3, f: (a, b) => a * b }, "/": { p: 3, f: (a, b) => a / b },
    "%": { p: 3, f: (a, b) => a % b }, "^": { p: 4, f: (a, b) => Math.pow(a, b), right: true },
  };

  function tokenize(s) {
    const out = []; let i = 0;
    while (i < s.length) {
      const c = s[i];
      if (c === " ") { i++; continue; }
      if (/[0-9.]/.test(c)) { let j = i + 1; while (j < s.length && /[0-9.eE]/.test(s[j])) { if ((s[j] === "e" || s[j] === "E") && (s[j + 1] === "+" || s[j + 1] === "-")) j++; j++; } out.push({ t: "num", v: parseFloat(s.slice(i, j)) }); i = j; continue; }
      if (/[a-zA-Z_]/.test(c)) { let j = i + 1; while (j < s.length && /[a-zA-Z0-9_]/.test(s[j])) j++; out.push({ t: "name", v: s.slice(i, j) }); i = j; continue; }
      if (c in OPS) {
        // unary minus / plus
        const prev = out[out.length - 1];
        if ((c === "-" || c === "+") && (!prev || prev.t === "op" || prev.v === "(" || prev.v === ",")) { out.push({ t: "num", v: 0 }); }
        out.push({ t: "op", v: c }); i++; continue;
      }
      if (c === "(" || c === ")" || c === ",") { out.push({ t: "paren", v: c }); i++; continue; }
      throw new Error("bad char '" + c + "'");
    }
    return out;
  }

  function toRPN(tokens) {
    const out = [], stack = [];
    for (const tk of tokens) {
      if (tk.t === "num") out.push(tk);
      else if (tk.t === "name") { if (tk.v in FUNCS) stack.push(tk); else out.push(tk); }
      else if (tk.t === "op") {
        while (stack.length) {
          const top = stack[stack.length - 1];
          if (top.t === "op" && (OPS[top.v].p > OPS[tk.v].p || (OPS[top.v].p === OPS[tk.v].p && !OPS[tk.v].right))) out.push(stack.pop());
          else break;
        }
        stack.push(tk);
      } else if (tk.v === "(") stack.push(tk);
      else if (tk.v === ",") { while (stack.length && stack[stack.length - 1].v !== "(") out.push(stack.pop()); }
      else if (tk.v === ")") {
        while (stack.length && stack[stack.length - 1].v !== "(") out.push(stack.pop());
        stack.pop();
        if (stack.length && stack[stack.length - 1].t === "name") out.push(stack.pop());
      }
    }
    while (stack.length) out.push(stack.pop());
    return out;
  }

  function compile(expr) {
    const rpn = toRPN(tokenize(expr));
    return function (x) {
      const st = [];
      for (const tk of rpn) {
        if (tk.t === "num") st.push(tk.v);
        else if (tk.t === "name") {
          if (tk.v === "x") st.push(x);
          else if (tk.v in CONSTS) st.push(CONSTS[tk.v]);
          else if (tk.v in FUNCS) st.push(FUNCS[tk.v](st.pop()));
          else throw new Error("unknown '" + tk.v + "'");
        } else if (tk.t === "op") { const b = st.pop(), a = st.pop(); st.push(OPS[tk.v].f(a, b)); }
      }
      return st.pop();
    };
  }

  // ───────────────────────────────────────────────────────────────────────
  // TERMINAL micro-app
  // ───────────────────────────────────────────────────────────────────────
  function buildTerminal(body) {
    body.style.display = "flex"; body.style.flexDirection = "column";
    body.innerHTML =
      `<div class="term-out" tabindex="0"></div>
       <div class="term-inline">
         <span class="term-ps1">deep&gt;</span>
         <input class="term-in" spellcheck="false" autocomplete="off" placeholder="type 'help'">
       </div>`;
    const out = body.querySelector(".term-out");
    const input = body.querySelector(".term-in");
    const hist = []; let hi = 0;

    function print(html, cls) {
      const d = document.createElement("div");
      d.className = "term-line " + (cls || "");
      d.innerHTML = html;
      out.appendChild(d);
      out.scrollTop = out.scrollHeight;
    }
    function esc(s) { return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

    async function getJSON(url, opts) {
      const r = await fetch(url, opts);
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }
    function dump(obj) { return `<pre class="term-json">${esc(JSON.stringify(obj, null, 2))}</pre>`; }

    const CMDS = {
      help: () => print(
        "Commands:\n" +
        "  help            this list\n" +
        "  clear           clear screen\n" +
        "  status          DEEP core / active model\n" +
        "  mem             knowledge graph stats\n" +
        "  net             security / network summary\n" +
        "  scan            trigger a network re-scan\n" +
        "  agents          list agent tasks\n" +
        "  research        research subsystem stats\n" +
        "  calc <expr>     evaluate math (sandboxed)\n" +
        "  ask <prompt>    send a prompt to DEEP chat\n" +
        "  ring | math | shield   open a micro-app", "term-dim"),
      clear: () => { out.innerHTML = ""; },
      status: async () => { print(dump(await getJSON("/api/status"))); },
      mem: async () => { print(dump(await getJSON("/api/knowledge/stats"))); },
      net: async () => { print(dump(await getJSON("/api/security/status"))); },
      research: async () => { print(dump(await getJSON("/api/research/stats"))); },
      agents: async () => { const d = await getJSON("/api/agents/tasks"); print(dump(d.tasks || d)); },
      scan: async () => { print("dispatching network scan…", "term-dim"); try { await getJSON("/api/security/scan", { method: "POST" }); print("scan dispatched ✓", "term-ok"); } catch (e) { print("scan endpoint unavailable", "term-err"); } },
      ring: () => window.HUD && HUD.open("memory-ring"),
      math: () => window.HUD && HUD.open("math-sim"),
      shield: () => window.HUD && HUD.open("aegis"),
      calc: (args) => {
        const expr = args.join(" ");
        if (!expr) return print("usage: calc <expression>", "term-err");
        const run = () => { const f = compile(expr); const v = f(0); print(`= ${v}`, "term-ok"); };
        if (window.Aegis) Aegis.sandbox("calc: " + expr, run); else run();
      },
      ask: async (args) => {
        const q = args.join(" ");
        if (!q) return print("usage: ask <prompt>", "term-err");
        if (typeof window.sendMessage === "function") {
          const box = document.getElementById("aiInput");
          if (box) { box.value = q; window.sendMessage(); print("→ sent to DEEP chat", "term-ok"); }
          else print("chat input unavailable", "term-err");
        } else print("chat bridge unavailable", "term-err");
      },
    };

    async function run(raw) {
      const line = raw.trim();
      print(`<span class="term-ps1">deep&gt;</span> ${esc(line)}`);
      if (!line) return;
      hist.push(line); hi = hist.length;
      const [cmd, ...args] = line.split(/\s+/);
      const fn = CMDS[cmd.toLowerCase()];
      if (window.Aegis && cmd.toLowerCase() !== "calc") Aegis.pulse("cmd: " + cmd);
      if (!fn) return print(`unknown command: ${esc(cmd)} (try 'help')`, "term-err");
      try { await fn(args); } catch (e) { print("error: " + esc(e.message || e), "term-err"); }
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { const v = input.value; input.value = ""; run(v); }
      else if (e.key === "ArrowUp") { if (hi > 0) { hi--; input.value = hist[hi] || ""; e.preventDefault(); } }
      else if (e.key === "ArrowDown") { if (hi < hist.length) { hi++; input.value = hist[hi] || ""; e.preventDefault(); } }
    });
    body.addEventListener("click", () => input.focus());

    print("DEEP terminal · isolated local context. Type <b>help</b>.", "term-dim");
    setTimeout(() => input.focus(), 50);
  }

  // ───────────────────────────────────────────────────────────────────────
  // MATH / PHYSICS micro-app
  // ───────────────────────────────────────────────────────────────────────
  function buildMath(body, win) {
    body.style.display = "flex"; body.style.flexDirection = "column";
    body.innerHTML =
      `<div class="math-toolbar">
         <select class="hud-select math-mode">
           <option value="plot">Plot ƒ(x)</option>
           <option value="projectile">Projectile</option>
           <option value="pendulum">Pendulum</option>
           <option value="orbit">Two-body orbit</option>
         </select>
         <input class="hud-input math-expr" value="sin(x) * exp(-x*x/8)" spellcheck="false">
         <button class="hud-btn math-go">Run</button>
       </div>
       <div class="math-stage"><canvas class="math-canvas"></canvas><div class="math-readout"></div></div>`;

    const stage = body.querySelector(".math-stage");
    const canvas = body.querySelector(".math-canvas");
    const ctx = canvas.getContext("2d");
    const modeSel = body.querySelector(".math-mode");
    const exprEl = body.querySelector(".math-expr");
    const readout = body.querySelector(".math-readout");
    let W = 0, H = 0, dpr = 1, raf = 0, t0 = 0, sim = null;

    function size() {
      const r = stage.getBoundingClientRect();
      W = r.width; H = r.height; dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    win._mathResize = size;
    win._mathStop = () => cancelAnimationFrame(raf);

    function grid(xc, yc, scale) {
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(232,185,116,0.07)"; ctx.lineWidth = 1;
      const step = scale;
      for (let gx = xc % step; gx < W; gx += step) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
      for (let gy = yc % step; gy < H; gy += step) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
      ctx.strokeStyle = "rgba(232,185,116,0.3)"; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(0, yc); ctx.lineTo(W, yc); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(xc, 0); ctx.lineTo(xc, H); ctx.stroke();
    }

    function drawPlot() {
      cancelAnimationFrame(raf);
      const xc = W / 2, yc = H / 2, scale = 36; // px per unit
      let f;
      const render = () => {
        try { f = compile(exprEl.value); } catch (e) { readout.textContent = "parse error: " + e.message; return; }
        grid(xc, yc, scale);
        ctx.strokeStyle = "rgba(120,200,255,0.95)"; ctx.lineWidth = 2;
        ctx.shadowColor = "rgba(120,200,255,0.5)"; ctx.shadowBlur = 8;
        ctx.beginPath();
        let started = false;
        for (let px = 0; px <= W; px++) {
          const xv = (px - xc) / scale;
          let yv; try { yv = f(xv); } catch (_) { yv = NaN; }
          if (!isFinite(yv)) { started = false; continue; }
          const py = yc - yv * scale;
          if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
        }
        ctx.stroke(); ctx.shadowBlur = 0;
        readout.textContent = "y = " + exprEl.value;
      };
      if (window.Aegis) Aegis.sandbox("plot: " + exprEl.value, render); else render();
    }

    // Physics simulators -----------------------------------------------------
    function startSim(kind) {
      cancelAnimationFrame(raf);
      t0 = performance.now();
      if (kind === "projectile") sim = { x: 0, y: 0, vx: 9, vy: 16, g: 9.81, trail: [] };
      else if (kind === "pendulum") sim = { a: Math.PI / 2.2, av: 0, len: 1.4, g: 9.81 };
      else if (kind === "orbit") sim = {
        bodies: [
          { x: 0, y: 0, vx: 0, vy: 0, m: 1200, fixed: true },
          { x: 2.4, y: 0, vx: 0, vy: 22, m: 1, trail: [] },
        ], G: 12,
      };
      loop(kind);
    }

    function loop(kind) {
      const now = performance.now();
      const dt = Math.min((now - (loop._last || now)) / 1000, 0.033);
      loop._last = now;
      const xc = W / 2, yc = H * 0.5, scale = Math.min(W, H) / 7;

      if (kind === "projectile") {
        const s = sim, h = dt;
        s.vy -= s.g * h; s.x += s.vx * h; s.y += s.vy * h;
        if (s.y < 0) { s.y = 0; s.vy = -s.vy * 0.62; s.vx *= 0.82; }
        s.trail.push([s.x, s.y]); if (s.trail.length > 220) s.trail.shift();
        grid(40, H - 30, scale * 0.5);
        const ox = 40, oy = H - 30, sc = scale * 0.5;
        ctx.strokeStyle = "rgba(245,200,150,0.6)"; ctx.lineWidth = 1.6; ctx.beginPath();
        s.trail.forEach((p, i) => { const X = ox + p[0] * sc, Y = oy - p[1] * sc; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); ctx.stroke();
        ctx.fillStyle = "#f5c896"; ctx.beginPath(); ctx.arc(ox + s.x * sc, oy - s.y * sc, 6, 0, Math.PI * 2); ctx.fill();
        readout.textContent = `t=${((now - t0) / 1000).toFixed(1)}s  v=(${s.vx.toFixed(1)}, ${s.vy.toFixed(1)})  h=${s.y.toFixed(2)}m`;
      } else if (kind === "pendulum") {
        const s = sim;
        const acc = -(s.g / s.len) * Math.sin(s.a);
        s.av += acc * dt; s.av *= 0.999; s.a += s.av * dt;
        grid(xc, yc * 0.5, scale);
        const ox = xc, oy = H * 0.22, L = scale * 1.6;
        const bx = ox + Math.sin(s.a) * L, by = oy + Math.cos(s.a) * L;
        ctx.strokeStyle = "rgba(232,185,116,0.7)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(bx, by); ctx.stroke();
        ctx.fillStyle = "rgba(232,185,116,0.4)"; ctx.beginPath(); ctx.arc(ox, oy, 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#78c8ff"; ctx.shadowColor = "rgba(120,200,255,0.6)"; ctx.shadowBlur = 12;
        ctx.beginPath(); ctx.arc(bx, by, 13, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
        readout.textContent = `θ=${(s.a * 180 / Math.PI).toFixed(1)}°  ω=${s.av.toFixed(2)} rad/s  L=${s.len}m`;
      } else if (kind === "orbit") {
        const s = sim, sub = 4, h = dt / sub;
        for (let k = 0; k < sub; k++) {
          const sun = s.bodies[0], p = s.bodies[1];
          const dx = sun.x - p.x, dy = sun.y - p.y; const r2 = dx * dx + dy * dy; const r = Math.sqrt(r2) || 1e-3;
          const a = (s.G * sun.m) / r2; p.vx += (dx / r) * a * h; p.vy += (dy / r) * a * h;
          p.x += p.vx * h; p.y += p.vy * h;
        }
        const p = s.bodies[1]; p.trail.push([p.x, p.y]); if (p.trail.length > 400) p.trail.shift();
        grid(xc, yc, scale);
        ctx.strokeStyle = "rgba(180,160,230,0.5)"; ctx.lineWidth = 1.2; ctx.beginPath();
        p.trail.forEach((pt, i) => { const X = xc + pt[0] * scale, Y = yc + pt[1] * scale; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); ctx.stroke();
        ctx.fillStyle = "#f5d28a"; ctx.shadowColor = "rgba(245,210,138,0.7)"; ctx.shadowBlur = 16;
        ctx.beginPath(); ctx.arc(xc, yc, 10, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
        ctx.fillStyle = "#b8a0e6"; ctx.beginPath(); ctx.arc(xc + p.x * scale, yc + p.y * scale, 5, 0, Math.PI * 2); ctx.fill();
        const speed = Math.hypot(p.vx, p.vy);
        readout.textContent = `r=${Math.hypot(p.x, p.y).toFixed(2)}  v=${speed.toFixed(2)}`;
      }
      raf = requestAnimationFrame(() => loop(kind));
    }

    function apply() {
      const mode = modeSel.value;
      exprEl.style.display = mode === "plot" ? "" : "none";
      if (mode === "plot") drawPlot(); else startSim(mode);
    }

    modeSel.addEventListener("change", apply);
    body.querySelector(".math-go").addEventListener("click", apply);
    exprEl.addEventListener("keydown", (e) => { if (e.key === "Enter") apply(); });

    size(); apply();
  }

  // ───────────────────────────────────────────────────────────────────────
  // Register apps
  // ───────────────────────────────────────────────────────────────────────
  function register() {
    if (!window.HUD) return setTimeout(register, 120);
    HUD.registerApp({
      id: "terminal", title: "Terminal", icon: ">_",
      anchor: "core", anchorAngle: Math.PI * 0.78,
      width: 460, height: 320, minWidth: 320, minHeight: 200,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12.5 15H17"/></svg>',
      build: buildTerminal,
    });
    HUD.registerApp({
      id: "math-sim", title: "Math / Physics", icon: "∫",
      anchor: "core", anchorAngle: Math.PI * 0.32,
      width: 520, height: 400, minWidth: 340, minHeight: 260,
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 19c4 0 4-14 8-14M4 12h7M14 7l6 10M20 7l-6 10"/></svg>',
      build: buildMath,
      onResize: (w, h, win) => win._mathResize && win._mathResize(),
      onClose: (win) => win._mathStop && win._mathStop(),
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", register);
  else register();

  window.openTerminal = () => window.HUD && HUD.open("terminal");
  window.openMathSim = () => window.HUD && HUD.open("math-sim");
  console.log("[DEEP] Micro-apps (Terminal, Math/Physics) initialised ✓");
})();
