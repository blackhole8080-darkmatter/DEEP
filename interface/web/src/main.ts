// DEEP modern frontend — bootstrap.
// Phase 0: mount the shell, load design tokens, prove the WS pipeline.
import "./design/tokens.css";
import "./design/themes.css";
import "./design/base.css";
import "./design/animations.css";
import "./design/utilities.css";
import "./core/theme";
import "./components/deep-app";

// The service worker exists in the tree and shipped for a long time without a
// single caller, so it never installed and its offline cache never held
// anything. Registered at "/" — the scope manifest.webmanifest declares, and
// the one the server now permits via Service-Worker-Allowed.
//
// Guarded because it is a progressive enhancement: unsupported browsers and
// insecure origins (anything but localhost over plain HTTP) must degrade to a
// normal online app rather than throwing on boot.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((err) => {
      console.warn("[deep] service worker did not register", err);
    });
  });
}
