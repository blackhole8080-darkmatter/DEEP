# DEEP — UI Modernization Plan

> **Decisions locked in**
> - **Architecture:** Vite + Web Components (Lit), incremental
> - **Aesthetic:** Calm modern minimal (charcoal + periwinkle; Linear/Arc-like)
> - **Approach:** Focused rewrites allowed (branch + verify before merge)
> - **Priorities:** Visual sophistication · Maintainability · AI-native UX · Performance (all four)

---

## 0. Where we are today (the starting point)

| Fact | Value | Implication |
|------|-------|-------------|
| CSS files | **18**, 3 competing token namespaces (`--abyss-*`, `--color-*`, `--deck-*`) | Incoherent cascade; restyling is risky |
| JS files | **26**, loaded as `<script>` tags sharing one global scope | No modules, no tree-shaking, fragile globals |
| `app.js` | **2,993 lines**, uses `\x00GENUI\x00` null-byte sentinels | Monolith; hard to reason about |
| Build step | none (buildless) | No HMR, no bundling, manual cache-busting (`?v=NN`) |
| Serving | `/static` mount + `/ai` → `ai-system-ui.html` | Build output must land in a served path |
| Tooling | Node v24, npm 11 present | Vite is viable |
| Already done | `tokens.css` (`--ds-*`), `components.css`, token-driven components (vision/provider-health/periodic-table) | Foundation to build on |

**Guiding principle:** the **new (Lit/Vite) UI and the legacy UI coexist** during migration. We build the new app at `/app` (or behind a flag), keep `/ai` working untouched, and cut over only when the new app reaches parity. Nothing breaks at any step.

---

## 1. Target architecture

```
interface/
  web/                      # NEW: Vite + Lit source (TypeScript)
    index.html              # Vite entry (built → dist)
    src/
      main.ts               # bootstrap, mounts <deep-app>
      core/
        ws.ts               # typed WebSocket client (reconnect, backpressure)
        store.ts            # signal-based reactive state (no heavy framework)
        events.ts           # typed event/message protocol (mirrors backend)
        api.ts              # typed REST client (status, chem, physics, knowledge…)
      design/
        tokens.css          # the canonical --ds-* layer (ported + finalized)
        reset.css           # modern reset
        primitives.css      # base element styling on tokens
      components/           # Lit web components, one concern each
        deep-app.ts         # shell / layout orchestrator
        chat/               # message list, composer, streaming, tool-cards
        reasoning/          # reasoning timeline, oracle/symbolic steps
        palette/            # ⌘K command palette
        panels/             # dockable workspace panels
        orb/                # Three.js orb wrapper (kept, isolated)
        science/            # periodic table, formulas, constants
        memory/             # memory graph
        security/           # alerts inbox, network panel
      styles/               # component-scoped styles (or per-component static styles)
    vite.config.ts          # build → interface/static/app-dist/
    package.json
    tsconfig.json
  static/                   # legacy UI stays here, untouched, served at /ai
    app-dist/               # Vite BUILD OUTPUT (served at /static/app-dist)
```

**Stack choices**
- **Lit 3** — tiny (~5KB), standards-based Web Components, reactive properties, scoped styles. No virtual DOM tax; great for a long-lived dashboard.
- **Signals** — `@lit-labs/signals` (or `@preact/signals-core`) for cross-component reactive state (the WS-driven store).
- **TypeScript** — type the WS message protocol end-to-end (the backend already emits structured `{type, ...}` messages; we mirror them).
- **Vite** — dev server with HMR for local work; `vite build` emits hashed assets to `interface/static/app-dist/`, served by the existing FastAPI static mount (no backend changes needed for serving).
- **View Transitions API** + **container queries** + **CSS `@property`** for modern motion/layout.

**Backend touchpoints (minimal)**
1. Add a route `@app.get("/app")` → returns the built `app-dist/index.html` (one new endpoint).
2. (Optional) a typed message schema doc so TS types and Python stay in sync.
3. Everything else (WS `/ws/deep`, all `/api/*`) is reused as-is.

---

## 2. Visual system — "Calm modern minimal"

Direction: the charcoal + periwinkle language already seeded in `base.css`, taken to a Linear/Arc level of restraint and polish. Keep DEEP's soul (the orb, a touch of depth) but dial back neon, raise typographic and spatial quality.

- **Color:** charcoal surfaces (`#0e0f13` → layered `--ds-surface-1..3`), off-white text, **one** restrained periwinkle accent (`#7c93ff`), semantic status (mint/amber/coral/sky). Abyssal neon becomes an *optional skin*, not the default.
- **Type:** Inter (UI) + JetBrains Mono (data) + a defined scale (`--ds-text-xs..3xl`), tight headings, generous body leading.
- **Depth:** soft layered shadows (`--ds-elev-1..4`) + subtle glass (`backdrop-blur`) + 1px inner-glow borders — sparingly.
- **Motion:** spring easings (`--ds-ease-spring`), 120/220/360ms durations, **View Transitions** for panel/route changes, `prefers-reduced-motion` respected.
- **Density:** comfortable default + a compact mode; container-query-driven responsiveness from phone (PWA) to ultrawide.
- **AI-native surfaces:** streaming-first messages, inline collapsible tool-call cards (built), a reasoning timeline (oracle/symbolic steps), generative-UI blocks, citations — all as first-class components.

A single **`tokens.css`** is the only source of truth; every component consumes `--ds-*` and nothing else.

---

## 3. Migration phases (each ships independently, nothing breaks)

### Phase 0 — Scaffolding & safety net  *(0.5–1 day)*
- Create branch `ui-modernization`.
- Scaffold `interface/web/` with Vite + Lit + TS; `vite build` → `interface/static/app-dist/`.
- Add `@app.get("/app")` serving the built shell (legacy `/ai` untouched).
- A `<deep-app>` shell that renders "hello" and connects to `/ws/deep` to prove the pipeline.
- **Verify:** `/ai` unchanged; `/app` loads the new shell; WS connects.

### Phase 1 — Design foundation  *(1–2 days)*
- Port & finalize `tokens.css` as the canonical `--ds-*` layer (already started).
- Add `reset.css` + `primitives.css`.
- Build the **core primitives** as Lit components: `<ds-button>`, `<ds-panel>`, `<ds-icon>`, `<ds-toast>`, `<ds-field>`.
- **Verify:** a component gallery route renders all primitives in light/dark + skins.

### Phase 2 — Core plumbing  *(2–3 days)*
- `ws.ts`: typed, auto-reconnecting WS client with a message bus.
- `store.ts`: signal-based state (connection, messages, reasoning steps, security, providers).
- `events.ts` + `api.ts`: typed protocol + REST client.
- **Verify:** state updates render reactively from live WS events.

### Phase 3 — Chat & AI-native UX (the core)  *(3–5 days)*
- `<deep-chat>`: streaming message list (virtualized), composer with image attach + document drop.
- `<tool-call-card>`, `<reasoning-timeline>` (oracle/symbolic steps), `<gen-ui>` block renderer, citations.
- **Verify:** full conversation parity with `/ai` — streaming, tools, oracles, vision, ingestion.

### Phase 4 — Shell, layout & palette  *(2–3 days)*
- `<deep-app>` layout: command-center grid, dockable/floating panels, focus mode, status bar.
- `<command-palette>` (⌘K) with fuzzy search + all actions registered.
- Orb wrapped in `<deep-orb>` (Three.js isolated, lazy-loaded).
- **Verify:** palette, panels, orb, responsive layout all work.

### Phase 5 — Feature panels  *(3–5 days, parallelizable)*
- Port: periodic table, physics constants/formulas, memory graph, security alerts inbox, provider health, screen awareness, agents board.
- Each as a self-contained component consuming the existing `/api/*`.
- **Verify:** each panel reaches parity with its legacy counterpart.

### Phase 6 — Polish & performance  *(2–3 days)*
- View Transitions, micro-interactions, sound (port `sfx.js`), skeleton/streaming states.
- Performance: code-split (lazy panels), virtualize lists/graph, image downscale, Lighthouse pass.
- A11y: keyboard nav, ARIA, focus management, reduced-motion.
- **Verify:** Lighthouse ≥ 90; 60fps motion; keyboard-only operable.

### Phase 7 — Cutover & cleanup  *(1 day)*
- Point `/ai` (and PWA start_url) at the new app; keep legacy at `/legacy` as fallback for one release.
- Delete superseded CSS/JS once parity is confirmed; collapse 18 CSS → tokens + ~6 component sheets; remove the `\x00GENUI\x00` hack.
- **Verify:** PWA installs, offline works, all features green; then remove `/legacy`.

**Rough total:** ~3–4 focused weeks, but **usable and demoable after Phase 3** (~1.5 weeks).

---

## 4. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Big-bang breakage | Coexistence: legacy `/ai` runs untouched until parity; cut over last |
| Three.js orb integration | Wrap as an isolated lazy-loaded component; reuse existing logic verbatim |
| WS protocol drift | Type it once in `events.ts`; single source mirrored from backend |
| Scope creep (all 4 priorities) | Phase gates with explicit "verify" criteria; ship per phase |
| Build adds deploy complexity | Vite outputs static files into the existing `/static` mount — no new server infra |
| Losing the "DEEP feel" | Keep orb + abyssal as an optional skin; calm-minimal is default, not exclusive |

---

## 5. Open questions for Aryan (non-blocking — sensible defaults chosen)

1. **TypeScript or plain JS** for the new components? (Default: **TypeScript** — pays off for the WS protocol.)
2. **Keep the orb** as the centerpiece, or make it ambient/optional? (Default: keep, but lazy + optional.)
3. **Default skin** post-migration: calm-minimal with abyssal as opt-in? (Default: **yes**.)
4. **Route name** for the new app during migration: `/app` vs a `?next` flag on `/ai`? (Default: `/app`.)
5. Any **brand specifics** (logo, exact accent hue, font licenses) to honor? (Default: current Inter/JetBrains + periwinkle.)

---

## 6. Definition of done

- One design-token system; ≤ 8 CSS files total.
- `app.js` monolith replaced by typed Lit components; no global-scope coupling, no null-byte hacks.
- Vite build pipeline with HMR (dev) and hashed output (prod) served by FastAPI.
- Full feature parity with today + the new AI-native surfaces.
- Lighthouse ≥ 90, 60fps motion, keyboard-accessible, PWA + offline intact.
- Legacy UI removed after one fallback release.
