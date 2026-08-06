# Archived frontend modules

These 34 modules were reachable from no entry point — a build's sourcemaps
listed none of them, so they shipped in zero bundles. They are kept here
rather than deleted, matching how `archive/domains` and `archive/engine`
handle retired backend subsystems.

Nothing in this directory is compiled, typechecked, or served. Restoring a
module means moving it back under `interface/web/src/` and importing it from
something the entry graph actually reaches (`main.ts` → `deep-app` →
`deep-console`, plus the lazy views in `core/tool-registry.ts`).

## What's here and why it stopped being reachable

**The superseded JARVIS HUD** (`components/hud/*`, 12 files) — `deep-hud`,
`jarvis-core`, `jarvis-radar`, `jarvis-orbs`, `jarvis-telemetry`,
`jarvis-systems`, `jarvis-stream`, `jarvis-chat`, `jarvis-floating-labels`,
`hud-layout-engine`, `hud-ambient-canvas`, `hud-audio`. `<deep-console>`
replaced this whole surface; the HUD kept building but nothing mounted it.

**Console pieces the current layout dropped** — `neural-sphere` (the console's
header comment still described it as the centrepiece long after it stopped
being rendered) and `elements-panel` (superseded by `tool-dock`).

**Chat shell** — `deep-chat` and `composer`. Note that `chat-message`, which
these used, is *not* archived: it is now imported directly by
`<deep-console>`, which had been printing message text into a bare div.

**Standalone views never wired into the tool registry** — `gallery`,
`ops-view`, `etis-hud`, `projects-view`, `deep-predictive`, `deep-welcome`,
`inference-trace`, `thought-stream`.

**Decorative and utility modules with no remaining caller** —
`deep-cortex-bg`, `deep-orb`, `holo-panel`, `sidebar-nav`, `spark-line`,
`ds-field`, `core/audio`, `core/events`, `core/nav`, `core/perf`.

`core/nav.ts` is worth a specific note: it defined the navigation model
(groups "Life → finance, email", "Knowledge → calc, research") for a routed
layout the app no longer has. The console reaches every surface through
`core/tool-registry.ts` instead, so restoring `nav.ts` would mean rebuilding
routing, not just re-importing a file.
