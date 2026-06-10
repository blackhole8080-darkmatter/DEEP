/* ============================================================================
 * DEEP — VITALS RING
 * ----------------------------------------------------------------------------
 * Concentric instrument arcs that orbit the Liquid Orb, showing the machine's
 * live load: CPU, memory, and network throughput. The core literally breathes
 * with the system. Reads ngCx/ngCy/ngCoreR from app.js; polls /api/vitals.
 * ========================================================================== */
(function () {
  "use strict";
  function g(n, f) { const v = window[n]; return (typeof v === "number") ? v : (typeof window[n] === "number" ? window[n] : f); }
  function cx() { return (typeof ngCx === "number" && ngCx) || innerWidth / 2; }
  function cy() { return (typeof ngCy === "number" && ngCy) || innerHeight * 0.46; }
  function coreR() { return (typeof ngCoreR === "number" && ngCoreR) || Math.min(innerWidth, innerHeight) * 0.04; }

  const RINGS = [
    { key: "cpu", label: "CPU", color: [0, 229, 255] },
    { key: "ram", label: "MEM", color: [0, 255, 209] },
    { key: "net", label: "NET", color: [150, 140, 230] },
  ];
  const val = { cpu: 0, ram: 0, net: 0 };   // eased 0..1
  const tgt = { cpu: 0, ram: 0, net: 0 };
  const meta = { cpu: "", ram: "", net: "" };
  let cv, ctx, W = 0, H = 0, raf = 0, enabled = true;

  function build() {
    cv = document.createElement("canvas");
    cv.id = "deep-vitals";
    cv.style.cssText = "position:fixed;top:0;left:0;z-index:6;pointer-events:none;display:block;";
    document.body.insertBefore(cv, document.body.children[1] || null);
    ctx = cv.getContext("2d");
    resize(); addEventListener("resize", resize);
    poll(); setInterval(poll, 2200);
    raf = requestAnimationFrame(frame);
  }
  function resize() {
    W = innerWidth; H = innerHeight; const d = Math.min(devicePixelRatio || 1, 2);
    cv.width = W * d; cv.height = H * d; cv.style.width = W + "px"; cv.style.height = H + "px"; ctx.setTransform(d, 0, 0, d, 0, 0);
  }
  async function poll() {
    if (document.hidden) return;
    try {
      const d = await (await fetch("/api/vitals")).json();
      if (!d || d.error) return;
      tgt.cpu = Math.min(1, (d.cpu || 0) / 100);
      tgt.ram = Math.min(1, (d.ram || 0) / 100);
      const net = (d.net_sent_mbs || 0) + (d.net_recv_mbs || 0);
      tgt.net = Math.min(1, net / 8);   // 8 MB/s ≈ full
      meta.cpu = (d.cpu || 0) + "%";
      meta.ram = (d.ram || 0) + "% · " + (d.ram_used_gb || "?") + "/" + (d.ram_total_gb || "?") + "G";
      meta.net = "↓" + (d.net_recv_mbs || 0) + " ↑" + (d.net_sent_mbs || 0) + " MB/s";
    } catch (_) {}
  }
  function frame() {
    raf = requestAnimationFrame(frame);
    if (!ctx || !enabled) { if (ctx) ctx.clearRect(0, 0, W, H); return; }
    ctx.clearRect(0, 0, W, H);
    const x = cx(), y = cy();
    const orbR = Math.max(90, coreR() * 5.5);     // approx orb visual radius
    const base = orbR + 16;
    const gap = 13;
    RINGS.forEach((r, i) => {
      val[r.key] += (tgt[r.key] - val[r.key]) * 0.08;
      const R = base + i * gap;
      const [cr, cg, cb] = r.color;
      const a0 = -Math.PI * 0.5 - Math.PI * 0.75;   // start (top-left)
      const span = Math.PI * 1.5;                    // 270° gauge
      // faint track
      ctx.strokeStyle = `rgba(${cr},${cg},${cb},0.10)`; ctx.lineWidth = 3; ctx.lineCap = "round";
      ctx.beginPath(); ctx.arc(x, y, R, a0, a0 + span); ctx.stroke();
      // value arc
      const a1 = a0 + span * val[r.key];
      const grad = ctx.createLinearGradient(x - R, y, x + R, y);
      grad.addColorStop(0, `rgba(${cr},${cg},${cb},0.4)`); grad.addColorStop(1, `rgba(${cr},${cg},${cb},0.95)`);
      ctx.strokeStyle = grad; ctx.lineWidth = 3.2; ctx.shadowColor = `rgba(${cr},${cg},${cb},0.6)`; ctx.shadowBlur = 8;
      ctx.beginPath(); ctx.arc(x, y, R, a0, a1); ctx.stroke(); ctx.shadowBlur = 0;
      // head dot
      const hx = x + Math.cos(a1) * R, hy = y + Math.sin(a1) * R;
      ctx.fillStyle = `rgba(255,255,255,0.95)`; ctx.beginPath(); ctx.arc(hx, hy, 2, 0, Math.PI * 2); ctx.fill();
      // label at the gauge gap (bottom)
      const la = a0 + span + 0.12;
      const lx = x + Math.cos(la) * R, ly = y + Math.sin(la) * R;
      ctx.fillStyle = `rgba(${cr},${cg},${cb},0.9)`; ctx.font = '600 9px "JetBrains Mono",monospace'; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(`${r.label} ${meta[r.key]}`, lx + 6, ly);
    });
  }

  window.DeepVitals = { setEnabled: (b) => { enabled = !!b; } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
  console.log("[DEEP] Vitals ring online ✓");
})();
