// Theme/skin management — persists the selected skin and applies it to the
// document root so all --ds-* token overrides (themes.css) take effect.
import { signal } from "@lit-labs/signals";

export type Skin = "calm" | "neon";
const KEY = "deep_skin";

export const skin = signal<Skin>((localStorage.getItem(KEY) as Skin) || "calm");

export function applySkin(next: Skin): void {
  skin.set(next);
  localStorage.setItem(KEY, next);
  if (next === "calm") document.documentElement.removeAttribute("data-skin");
  else document.documentElement.setAttribute("data-skin", next);
}

export function cycleSkin(): void {
  applySkin(skin.get() === "calm" ? "neon" : "calm");
}

// Apply the saved skin immediately on import (before first paint where possible).
applySkin(skin.get());
