// Theme/skin management — persists the selected skin and applies it to the
// document root so all --ds-* token overrides (themes.css) take effect.
import { signal } from "@lit-labs/signals";

// "hacker" (matrix-green CRT terminal, scanlines, grid overlay) was fully
// built in themes.css but never reachable from the UI — missing from this
// type and the cycle below, so data-skin="hacker" could only ever be set by
// hand-editing localStorage. Wired in properly now.
export type Skin = "calm" | "neon" | "etis" | "hacker";
const SKINS: Skin[] = ["calm", "neon", "etis", "hacker"];
const KEY = "deep_skin";

export const skin = signal<Skin>((localStorage.getItem(KEY) as Skin) || "etis");

export function applySkin(next: Skin): void {
  skin.set(next);
  localStorage.setItem(KEY, next);
  if (next === "calm") document.documentElement.removeAttribute("data-skin");
  else document.documentElement.setAttribute("data-skin", next);
}

export function cycleSkin(): void {
  const i = SKINS.indexOf(skin.get());
  applySkin(SKINS[(i + 1) % SKINS.length]);
}

// ── Accent colors ────────────────────────────────────────────────────────────
export type Accent = "cyan" | "pink" | "green" | "orange";
const ACCENTS: Accent[] = ["cyan", "pink", "green", "orange"];
const ACCENT_HEX: Record<Accent, string> = {
  cyan: "#00e5ff", pink: "#d946ef", green: "#10b981", orange: "#f59e0b",
};
const ACCENT_KEY = "deep_accent";

export const accent = signal<Accent>((localStorage.getItem(ACCENT_KEY) as Accent) || "cyan");

export function applyAccent(next: Accent): void {
  accent.set(next);
  localStorage.setItem(ACCENT_KEY, next);
  document.documentElement.style.setProperty("--ds-accent", ACCENT_HEX[next]);
}

export function cycleAccent(): void {
  const i = ACCENTS.indexOf(accent.get());
  applyAccent(ACCENTS[(i + 1) % ACCENTS.length]);
}

// Apply persisted values immediately.
applySkin(skin.get());
applyAccent(accent.get());
