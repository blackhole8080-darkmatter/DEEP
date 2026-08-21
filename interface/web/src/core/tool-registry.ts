// DEEP tool registry — the single source of truth for the Elements panel.
//
// To add a tool to the interface "steadily", append ONE entry here:
//   - load():   lazy-imports the view's module (registers its custom element)
//   - render(): returns the element's template (fixed tag — no static-html needed)
// The Elements panel renders this list; clicking a tool opens its view in the
// console's focus surface. This is how the interface grows without touching layout.
import { html, type TemplateResult } from "lit";
import { pendingApprovals } from "./store";

export interface ToolDef {
  id: string;
  label: string;
  icon: string;            // unicode glyph (swap for SVG later)
  group: "core" | "intelligence" | "system" | "personal";
  load: () => Promise<unknown>;
  render: () => TemplateResult;
  /** Live count for the dock badge, e.g. actions waiting on a decision. */
  badge?: () => number;
}

export const TOOL_REGISTRY: ToolDef[] = [
  // ── Intelligence ──
  { id: "terminal", label: "Terminal",  icon: "❯", group: "intelligence",
    load: () => import("../components/console/ops-terminal"), render: () => html`<ops-terminal></ops-terminal>` },
  { id: "intel",    label: "Intel",     icon: "◈", group: "intelligence",
    load: () => import("../components/ops/intel-stats-view"), render: () => html`<intel-stats-view></intel-stats-view>` },
  { id: "memory",   label: "Knowledge", icon: "◐", group: "intelligence",
    load: () => import("../components/memory/memory-graph"), render: () => html`<memory-graph></memory-graph>` },

  // ── System ──
  // Approvals carries a badge because it is the one tool the user has to be
  // told about: a parked action expires in 15 minutes, and one nobody notices
  // reads as DEEP quietly ignoring the request that produced it.
  { id: "approvals", label: "Approvals", icon: "⧗", group: "system",
    load: () => import("../components/ops/approvals-view"),
    render: () => html`<approvals-view></approvals-view>`,
    badge: () => pendingApprovals.get().length },
  { id: "telemetry",label: "Telemetry", icon: "⎈", group: "system",
    load: () => import("../components/dashboard-view"),     render: () => html`<dashboard-view></dashboard-view>` },
  { id: "network",  label: "Network",   icon: "◎", group: "system",
    load: () => import("../components/ops/network-view"),   render: () => html`<network-view></network-view>` },
  { id: "security-timeline", label: "Security", icon: "🛰", group: "system",
    load: () => import("../components/ops/security-timeline-view"),
    render: () => html`<security-timeline-view></security-timeline-view>` },
  { id: "audit",    label: "Audit",     icon: "❖", group: "system",
    load: () => import("../components/ops/audit-view"),     render: () => html`<audit-view></audit-view>` },
];

export function toolById(id: string): ToolDef | undefined {
  return TOOL_REGISTRY.find((t) => t.id === id);
}
