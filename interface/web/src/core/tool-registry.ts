// DEEP tool registry — the single source of truth for the Elements panel.
//
// To add a tool to the interface "steadily", append ONE entry here:
//   - load():   lazy-imports the view's module (registers its custom element)
//   - render(): returns the element's template (fixed tag — no static-html needed)
// The Elements panel renders this list; clicking a tool opens its view in the
// console's focus surface. This is how the interface grows without touching layout.
import { html, type TemplateResult } from "lit";

export interface ToolDef {
  id: string;
  label: string;
  icon: string;            // unicode glyph (swap for SVG later)
  group: "core" | "intelligence" | "system" | "personal";
  load: () => Promise<unknown>;
  render: () => TemplateResult;
}

export const TOOL_REGISTRY: ToolDef[] = [
  // ── Intelligence ──
  { id: "memory",   label: "Knowledge", icon: "◐", group: "intelligence",
    load: () => import("../components/memory/memory-graph"), render: () => html`<memory-graph></memory-graph>` },
  { id: "science",  label: "Science",   icon: "∿", group: "intelligence",
    load: () => import("../components/science/science-view"), render: () => html`<science-view></science-view>` },

  // ── System ──
  { id: "telemetry",label: "Telemetry", icon: "⎈", group: "system",
    load: () => import("../components/dashboard-view"),     render: () => html`<dashboard-view></dashboard-view>` },
  { id: "network",  label: "Network",   icon: "◎", group: "system",
    load: () => import("../components/ops/network-view"),   render: () => html`<network-view></network-view>` },
  { id: "etis",     label: "ETIS",      icon: "🛡", group: "system",
    load: () => import("../components/ops/etis-hud"),       render: () => html`<etis-hud></etis-hud>` },
  { id: "audit",    label: "Audit",     icon: "❖", group: "system",
    load: () => import("../components/ops/audit-view"),     render: () => html`<audit-view></audit-view>` },


  // ── Personal ──
  { id: "projects", label: "Projects",  icon: "◇", group: "personal",
    load: () => import("../components/knowledge/projects-view"), render: () => html`<projects-view></projects-view>` },
];

export function toolById(id: string): ToolDef | undefined {
  return TOOL_REGISTRY.find((t) => t.id === id);
}
