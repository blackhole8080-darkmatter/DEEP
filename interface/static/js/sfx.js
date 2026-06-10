/* ============================================================================
 * DEEP SFX — synthesized UI sound effects
 * ----------------------------------------------------------------------------
 * A tiny WebAudio instrument that voices the interface: holographic blips,
 * clicks, hums and alerts. Nothing is loaded from disk — every sound is
 * synthesized on the fly, so it costs zero bandwidth and always works offline.
 *
 * Browsers block audio until the first user gesture, so the AudioContext is
 * created lazily on the first interaction. Respects prefers-reduced-motion and
 * a persisted mute flag (deep_sfx = "off").
 *
 * Public API (window.SFX):
 *   SFX.play(name)   name ∈ blip|click|hover|open|close|send|alert|boot|toggle
 *   SFX.mute(bool)   SFX.enabled()
 * ========================================================================== */
(function () {
  "use strict";

  let ctx = null, master = null;
  let muted = (function () { try { return localStorage.getItem("deep_sfx") === "off"; } catch (_) { return false; } })();
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function ensure() {
    if (ctx) return ctx;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      master = ctx.createGain();
      master.gain.value = 0.16;            // keep the UI voice subtle
      master.connect(ctx.destination);
    } catch (_) { ctx = null; }
    return ctx;
  }

  // One synth "voice": an oscillator sweeping f0→f1 through a short AD envelope.
  function tone(o) {
    if (!ensure() || muted) return;
    if (ctx.state === "suspended") ctx.resume();
    const t0 = ctx.currentTime + (o.delay || 0);
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = o.type || "sine";
    osc.frequency.setValueAtTime(o.f0, t0);
    if (o.f1 != null) osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.f1), t0 + o.dur);
    const peak = (o.gain != null ? o.gain : 1);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(peak, t0 + (o.attack || 0.008));
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + o.dur);
    // optional gentle low-pass to round off harsh edges
    if (o.lp) {
      const lp = ctx.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.value = o.lp;
      osc.connect(lp); lp.connect(gain);
    } else {
      osc.connect(gain);
    }
    gain.connect(master);
    osc.start(t0);
    osc.stop(t0 + o.dur + 0.02);
  }

  // Sound design — short, glassy, sci-fi. Each is one or two stacked voices.
  const VOICES = {
    hover:  () => tone({ f0: 1320, f1: 1760, dur: 0.05, type: "sine", gain: 0.4, lp: 4000 }),
    click:  () => tone({ f0: 880,  f1: 540,  dur: 0.06, type: "triangle", gain: 0.7 }),
    blip:   () => tone({ f0: 1480, f1: 2100, dur: 0.07, type: "sine", gain: 0.6, lp: 5200 }),
    toggle: () => { tone({ f0: 660, f1: 990, dur: 0.07, type: "square", gain: 0.35, lp: 2600 }); },
    send:   () => { tone({ f0: 720, f1: 1280, dur: 0.10, type: "sawtooth", gain: 0.45, lp: 3200 });
                    tone({ f0: 1440, f1: 2400, dur: 0.12, type: "sine", gain: 0.35, delay: 0.02, lp: 6000 }); },
    open:   () => { tone({ f0: 540, f1: 1080, dur: 0.16, type: "sine", gain: 0.5, lp: 4200 });
                    tone({ f0: 810, f1: 1620, dur: 0.18, type: "sine", gain: 0.28, delay: 0.03, lp: 6000 }); },
    close:  () => { tone({ f0: 1080, f1: 460, dur: 0.14, type: "sine", gain: 0.45, lp: 3600 }); },
    alert:  () => { tone({ f0: 880, f1: 880, dur: 0.10, type: "square", gain: 0.5, lp: 2400 });
                    tone({ f0: 660, f1: 660, dur: 0.10, type: "square", gain: 0.5, delay: 0.13, lp: 2400 }); },
    boot:   () => { [392, 523, 659, 784].forEach((f, i) =>
                    tone({ f0: f, f1: f * 1.5, dur: 0.4, type: "sine", gain: 0.3, delay: i * 0.09, lp: 5000 })); },
  };

  function play(name) {
    if (muted || reduce) return;
    const v = VOICES[name];
    if (v) { try { v(); } catch (_) {} }
  }

  function mute(on) {
    muted = !!on;
    try { localStorage.setItem("deep_sfx", muted ? "off" : "on"); } catch (_) {}
  }

  // ── Auto-wire common controls so the whole UI gains a voice for free ───────
  function wire() {
    document.addEventListener("pointerover", (e) => {
      const t = e.target.closest(".hud-dock-btn, .sb-icon-btn, .cmd-icon, .core-menu-item, .deck-mod, .sp-action");
      if (t) play("hover");
    }, { passive: true });

    document.addEventListener("click", (e) => {
      const t = e.target;
      if (t.closest(".cmd-send")) return play("send");
      if (t.closest(".hud-bar-btn.close, .viz-close, .sp-close")) return play("close");
      if (t.closest(".hud-dock-btn, .core-menu-item")) return play("open");
      if (t.closest("button, .chip, .sp-pill, .sp-chip")) return play("click");
    }, { passive: true, capture: true });

    // first gesture unlocks audio
    const unlock = () => { ensure(); if (ctx && ctx.state === "suspended") ctx.resume(); window.removeEventListener("pointerdown", unlock); };
    window.addEventListener("pointerdown", unlock, { once: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();

  window.SFX = { play, mute, enabled: () => !muted, _ctx: () => ctx };
  console.log("[DEEP] SFX synth voice initialised ✓");
})();
