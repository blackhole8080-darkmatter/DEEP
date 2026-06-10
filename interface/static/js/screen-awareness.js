/* ============================================================================
 * DEEP — SCREEN AWARENESS  (new element)
 * ----------------------------------------------------------------------------
 * Lets DEEP see Aryan's screen: POSTs /api/vision/screen (local capture →
 * moondream) and drops the description into the chat feed. Exposed on the
 * command palette as "Describe my screen".
 * ========================================================================== */
(function () {
  "use strict";

  async function describeScreen(q) {
    const say = (t, who) => {
      if (typeof window.addMessage === "function") window.addMessage(t, who || "ai");
      else console.log("[screen]", t);
    };
    say("*(DEEP is looking at your screen…)*", "ai");
    try {
      const r = await fetch("/api/vision/screen", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ q: q || "Describe what's on this screen for Aryan, concisely." }),
      });
      const d = await r.json();
      if (d.ok) say(d.description || "(nothing legible on screen)", "ai");
      else say("I couldn't read the screen: " + (d.error || "unknown error"), "ai");
    } catch (e) {
      say("Screen read failed: " + e.message, "ai");
    }
  }

  window.ScreenAwareness = { describe: describeScreen };

  (function register() {
    if (typeof PALETTE_COMMANDS !== "undefined" && Array.isArray(PALETTE_COMMANDS)) {
      if (!PALETTE_COMMANDS.some((c) => c.label === "Describe my screen")) {
        PALETTE_COMMANDS.push({
          icon: "▣", label: "Describe my screen", cat: "intel",
          run: () => window.ScreenAwareness.describe(),
        });
      }
      return;
    }
    setTimeout(register, 300);
  })();
})();
