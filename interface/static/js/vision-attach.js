/* ============================================================================
 * DEEP — VISION ATTACH  (Phase 3b)
 * ----------------------------------------------------------------------------
 * Lets Aryan attach an image to a chat turn (paperclip button, paste, or
 * drag-drop). Images are downscaled client-side, then sendMessage() picks the
 * pending image up via window.DeepVision.consume() and ships it to the server,
 * which routes the turn to Claude's vision endpoint.
 *
 * Self-contained, token-styled, no dependencies on app.js internals beyond the
 * #inputWrap element and the global sendMessage().
 * ========================================================================== */
(function () {
  "use strict";

  let pending = null;            // data URL of the staged image
  const MAX_DIM = 1280;          // downscale ceiling (px)
  const JPEG_Q = 0.85;

  window.DeepVision = {
    has: () => !!pending,
    consume: () => { const p = pending; clearPending(); return p; },
  };

  // ── Downscale via canvas to keep payloads small ──────────────────────────
  function downscale(dataUrl) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        let { width: w, height: h } = img;
        if (Math.max(w, h) > MAX_DIM) {
          const s = MAX_DIM / Math.max(w, h);
          w = Math.round(w * s); h = Math.round(h * s);
        }
        const c = document.createElement("canvas");
        c.width = w; c.height = h;
        c.getContext("2d").drawImage(img, 0, 0, w, h);
        try { resolve(c.toDataURL("image/jpeg", JPEG_Q)); }
        catch (_) { resolve(dataUrl); }   // tainted/odd format → send original
      };
      img.onerror = () => resolve(dataUrl);
      img.src = dataUrl;
    });
  }

  async function stageFile(file) {
    if (!file || !file.type || !file.type.startsWith("image/")) return;
    const raw = await new Promise((res) => {
      const fr = new FileReader();
      fr.onload = () => res(fr.result);
      fr.readAsDataURL(file);
    });
    pending = await downscale(raw);
    renderChip();
  }

  function clearPending() {
    pending = null;
    const chip = document.getElementById("deep-vision-chip");
    if (chip) chip.remove();
  }

  function renderChip() {
    let chip = document.getElementById("deep-vision-chip");
    if (!chip) {
      chip = document.createElement("div");
      chip.id = "deep-vision-chip";
      chip.className = "vision-chip";
      const wrap = document.getElementById("inputWrap");
      if (wrap && wrap.parentNode) wrap.parentNode.insertBefore(chip, wrap);
      else document.body.appendChild(chip);
    }
    chip.innerHTML =
      `<img class="vision-chip-thumb" src="${pending}" alt="staged">` +
      `<span class="vision-chip-label">Image attached · sent to vision</span>` +
      `<button class="vision-chip-x" title="Remove" aria-label="Remove image">✕</button>`;
    chip.querySelector(".vision-chip-x").onclick = clearPending;
  }

  // ── Wiring (defensive: wait for the input shell) ─────────────────────────
  function install() {
    const wrap = document.getElementById("inputWrap");
    if (!wrap) return setTimeout(install, 200);
    if (document.getElementById("deep-vision-btn")) return;

    // Paperclip button inside the input shell
    const btn = document.createElement("button");
    btn.id = "deep-vision-btn";
    btn.className = "vision-attach-btn";
    btn.type = "button";
    btn.title = "Attach an image for DEEP to see";
    btn.setAttribute("aria-label", "Attach image");
    btn.innerHTML =
      `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">` +
      `<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;
    const file = document.createElement("input");
    file.type = "file"; file.accept = "image/*"; file.style.display = "none";
    file.onchange = () => { if (file.files[0]) stageFile(file.files[0]); file.value = ""; };
    btn.onclick = () => file.click();
    wrap.insertBefore(btn, wrap.firstChild);
    wrap.appendChild(file);

    // Paste anywhere → if clipboard has an image, stage it
    document.addEventListener("paste", (e) => {
      const items = (e.clipboardData && e.clipboardData.items) || [];
      for (const it of items) {
        if (it.type && it.type.startsWith("image/")) { stageFile(it.getAsFile()); break; }
      }
    });

    // Drag & drop onto the input shell
    ["dragover", "dragenter"].forEach((ev) =>
      wrap.addEventListener(ev, (e) => { e.preventDefault(); wrap.classList.add("vision-dragover"); }));
    ["dragleave", "drop"].forEach((ev) =>
      wrap.addEventListener(ev, () => wrap.classList.remove("vision-dragover")));
    wrap.addEventListener("drop", (e) => {
      e.preventDefault();
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) stageFile(f);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
