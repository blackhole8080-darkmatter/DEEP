// Lightweight device quality tiering for the HUD's always-on visual layers.
// Heuristic + synchronous (no async battery wait): CPU cores, device memory,
// coarse pointer (mobile), and reduced-motion. Lets heavy effects (200-particle
// field, chromatic-aberration filter) scale down on weak hardware so the
// default-on HUD stays smooth.

export type QualityTier = "high" | "medium" | "low";

let _cached: QualityTier | null = null;

export function qualityTier(): QualityTier {
  if (_cached) return _cached;
  let tier: QualityTier = "high";
  try {
    const nav = navigator as Navigator & { deviceMemory?: number };
    const cores = nav.hardwareConcurrency ?? 8;
    const mem = nav.deviceMemory ?? 8;          // GiB (Chromium only; defaults high elsewhere)
    const mobile = matchMedia("(pointer: coarse)").matches;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (cores <= 2 || mem <= 2 || reduced) tier = "low";
    else if (cores <= 4 || mem <= 4 || mobile) tier = "medium";
  } catch {
    /* keep high on any detection failure */
  }
  _cached = tier;
  return tier;
}

// Suggested ambient particle count for the current tier.
export function particleBudget(): number {
  const t = qualityTier();
  if (t === "low") return 40;
  if (t === "medium") return 80;
  return 160;
}

// Detect Canvas 2D filter support (Safari < 16.4 lacks it).
let _filterSupported: boolean | null = null;
export function canvasFilterSupported(): boolean {
  if (_filterSupported !== null) return _filterSupported;
  try {
    const c = document.createElement("canvas").getContext("2d")!;
    c.filter = "blur(1px)";
    _filterSupported = c.filter === "blur(1px)";
  } catch { _filterSupported = false; }
  return _filterSupported;
}
