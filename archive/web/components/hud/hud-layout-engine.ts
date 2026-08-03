// hud-layout-engine.ts — Cognitive mode derivation & zone assignment
// Maps BrainState + Store signals → grid-area placements + widget visibility.
// Emits CustomEvents that widgets listen to for resize/hero/collapse.

import type { BrainState } from "../deep-cortex-bg";

export type HudMode = "idle" | "listening" | "thinking" | "speaking" | "alert" | "hero";

export interface HeroTarget {
  zone: 1 | 2 | 3 | 4;
  widget: string;
}

export interface LayoutState {
  mode: HudMode;
  prevMode: HudMode;
  assignments: Record<string, string>; // widgetName → gridArea
  visible: string[];
  heroTarget?: HeroTarget;
}

export interface ModeTransition {
  from: HudMode;
  to: HudMode;
  duration: number; // ms
}

const TRANSITIONS: Record<string, ModeTransition> = {
  "idle→listening": { from: "idle", to: "listening", duration: 600 },
  "idle→thinking": { from: "idle", to: "thinking", duration: 800 },
  "idle→speaking": { from: "idle", to: "speaking", duration: 600 },
  "idle→alert": { from: "idle", to: "alert", duration: 400 },
  "alert→idle": { from: "alert", to: "idle", duration: 600 },
  "listening→thinking": { from: "listening", to: "thinking", duration: 500 },
  "thinking→speaking": { from: "thinking", to: "speaking", duration: 500 },
  "any→hero": { from: "idle", to: "hero", duration: 500 },
  "hero→idle": { from: "hero", to: "idle", duration: 500 },
};

// Default idle assignments
const IDLE_LAYOUT: Record<string, string> = {
  telemetry: "tl",
  orb: "mc",
  stream: "bl",
  knowledge: "br",
};

const MODE_LAYOUTS: Record<HudMode, Record<string, string>> = {
  idle: IDLE_LAYOUT,
  listening: {
    orb: "tc",
    stream: "bl / bc / br", // spans 3 columns
    telemetry: "tr",
    knowledge: "mr",
  },
  thinking: {
    orb: "tc",
    thoughtViz: "mc",
    telemetry: "tl",
    stream: "bl",
    knowledge: "br",
  },
  speaking: {
    orb: "mc",
    transcriptRibbon: "tl / tc / tr",
    knowledge: "mr",
    stream: "bl",
    telemetry: "ml",
  },
  alert: {
    predictionPanel: "tc",
    telemetry: "tl",
    orb: "mc",
    stream: "bl",
    knowledge: "br",
  },
  hero: {}, // computed dynamically
};

export function deriveMode(
  orbState: "idle" | "listening" | "thinking" | "speaking",
  brainState: BrainState,
  heroTarget?: HeroTarget
): HudMode {
  if (heroTarget) return "hero";
  if (brainState.system === "warning" || brainState.predictive) return "alert";
  if (orbState === "speaking") return "speaking";
  if (orbState === "thinking") return "thinking";
  if (orbState === "listening") return "listening";
  return "idle";
}

export function computeLayout(
  mode: HudMode,
  heroTarget?: HeroTarget
): LayoutState {
  const assignments: Record<string, string> = {};
  const visible: string[] = [];

  if (mode === "hero" && heroTarget) {
    // Hero: target widget spans its column
    const zoneMap: Record<number, string> = { 1: "tl", 2: "tc", 3: "bl", 4: "br" };
    const zone = zoneMap[heroTarget.zone];
    if (zone) {
      const col = zone.charAt(0); // t or b
      assignments[heroTarget.widget] = `${col}l / ${col}c / ${col}r`;
      visible.push(heroTarget.widget);
    }
  } else {
    const layout = MODE_LAYOUTS[mode] || MODE_LAYOUTS.idle;
    for (const [widget, area] of Object.entries(layout)) {
      assignments[widget] = area;
      visible.push(widget);
    }
  }

  return {
    mode,
    prevMode: "idle",
    assignments,
    visible,
    heroTarget,
  };
}

export function getTransitionDuration(from: HudMode, to: HudMode): number {
  const key = `${from}→${to}`;
  if (TRANSITIONS[key]) return TRANSITIONS[key].duration;
  const fallback = TRANSITIONS[`any→${to}`];
  if (fallback) return fallback.duration;
  return 600; // default
}

// Event helpers
export function dispatchModeChange(
  target: EventTarget,
  mode: HudMode,
  prevMode: HudMode
): void {
  target.dispatchEvent(
    new CustomEvent("hud-mode-changed", {
      detail: { mode, prevMode },
      bubbles: true,
      composed: true,
    })
  );
}
