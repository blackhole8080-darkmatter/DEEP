// Grouped navigation model. Top level = groups; each group holds tabs (routes).
// Chat is the standalone primary. This replaces the flat tab bar so the nav
// stays calm as the app grows.

export interface Tab { route: string; label: string; }
export interface Group { id: string; label: string; tabs: Tab[]; }

export const GROUPS: Group[] = [
  {
    id: "life",
    label: "Life",
    tabs: [
      { route: "finance", label: "finance" },
      { route: "email", label: "email" },
    ],
  },
  {
    id: "network",
    label: "Network",
    tabs: [
      { route: "network", label: "devices" },
      { route: "connections", label: "connections" },
      { route: "system", label: "system" },
      { route: "stack", label: "stack" },
      { route: "audit", label: "audit" },
      { route: "memory", label: "memory" },
      { route: "agents", label: "agents" },
      { route: "ops", label: "ops" },
      { route: "missions", label: "missions" },
    ],
  },
  {
    id: "knowledge",
    label: "Knowledge",
    tabs: [
      { route: "calc", label: "calc" },
      { route: "research", label: "research" },
    ],
  },
];

/** Which group (if any) owns a given route. null = standalone chat/home. */
export function groupForRoute(route: string): Group | null {
  for (const g of GROUPS) if (g.tabs.some((t) => t.route === route)) return g;
  return null;
}
