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
  { id: "agents",   label: "Agents",    icon: "✦", group: "intelligence",
    load: () => import("../components/ops/agents-view"),    render: () => html`<agents-view></agents-view>` },
  { id: "memory",   label: "Knowledge", icon: "◐", group: "intelligence",
    load: () => import("../components/memory/memory-graph"), render: () => html`<memory-graph></memory-graph>` },
  { id: "research", label: "Research",  icon: "◑", group: "intelligence",
    load: () => import("../components/knowledge/research-view"), render: () => html`<research-view></research-view>` },
  { id: "science",  label: "Science",   icon: "∿", group: "intelligence",
    load: () => import("../components/science/science-view"), render: () => html`<science-view></science-view>` },
  { id: "calc",     label: "Compute",   icon: "∑", group: "intelligence",
    load: () => import("../components/science/calc-view"),  render: () => html`<calc-view></calc-view>` },
  { id: "missions", label: "Missions",  icon: "➤", group: "intelligence",
    load: () => import("../components/ops/missions-view"),  render: () => html`<missions-view></missions-view>` },

  // ── System ──
  { id: "network",  label: "Network",   icon: "◎", group: "system",
    load: () => import("../components/ops/network-view"),   render: () => html`<network-view></network-view>` },
  { id: "etis",     label: "ETIS",      icon: "🛡", group: "system",
    load: () => import("../components/ops/etis-hud"),       render: () => html`<etis-hud></etis-hud>` },
  { id: "system",   label: "System",    icon: "▦", group: "system",
    load: () => import("../components/system/system-monitor"), render: () => html`<system-monitor></system-monitor>` },
  { id: "geo",      label: "Geo",       icon: "✣", group: "system",
    load: () => import("../components/system/geo-view"),    render: () => html`<geo-view></geo-view>` },
  { id: "audit",    label: "Audit",     icon: "❖", group: "system",
    load: () => import("../components/ops/audit-view"),     render: () => html`<audit-view></audit-view>` },


  // ── Personal ──
  { id: "finance",  label: "Finance",   icon: "₿", group: "personal",
    load: () => import("../components/finance/finance-view"), render: () => html`<finance-view></finance-view>` },
  { id: "email",    label: "Email",     icon: "✉", group: "personal",
    load: () => import("../components/email/email-view"),   render: () => html`<email-view></email-view>` },
  { id: "projects", label: "Projects",  icon: "◇", group: "personal",
    load: () => import("../components/knowledge/projects-view"), render: () => html`<projects-view></projects-view>` },
];

export function toolById(id: string): ToolDef | undefined {
  return TOOL_REGISTRY.find((t) => t.id === id);
}
