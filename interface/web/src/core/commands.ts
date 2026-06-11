// Command registry — the single source for everything the ⌘K palette can do.
// Features register here; the palette just renders + fuzzy-matches.
import { fetchProviderHealth } from "./api";
import { toast } from "../components/primitives/ds-toast";
import { cycleSkin } from "./theme";

export interface Command {
  id: string;
  label: string;
  hint?: string;          // small right-aligned annotation (category/shortcut)
  run: () => void | Promise<void>;
}

const registry: Command[] = [];

export function registerCommand(cmd: Command): void {
  if (!registry.some((c) => c.id === cmd.id)) registry.push(cmd);
}

export function allCommands(): Command[] {
  return registry;
}

/** Fuzzy subsequence score: lower is better; -1 = no match. */
export function fuzzyScore(query: string, text: string): number {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  let ti = 0, score = 0;
  for (const ch of q) {
    const at = t.indexOf(ch, ti);
    if (at === -1) return -1;
    score += at - ti + (at === ti ? 0 : 2);
    ti = at + 1;
  }
  return score;
}

export function matchCommands(query: string): Command[] {
  if (!query.trim()) return registry;
  return registry
    .map((c) => ({ c, s: fuzzyScore(query, c.label) }))
    .filter((x) => x.s >= 0)
    .sort((a, b) => a.s - b.s)
    .map((x) => x.c);
}

// ── Built-in commands ───────────────────────────────────────────────────────
const go = (hash: string) => () => { location.hash = hash; };

registerCommand({ id: "nav.chat", label: "Go to Chat", hint: "nav", run: go("home") });
registerCommand({ id: "nav.gallery", label: "Open Design Gallery", hint: "nav", run: go("gallery") });
registerCommand({ id: "nav.science", label: "Open Science (Periodic Table & Physics)", hint: "nav", run: go("science") });
registerCommand({ id: "nav.ops", label: "Open Ops (Providers · Security · Knowledge)", hint: "nav", run: go("ops") });
registerCommand({ id: "nav.agents", label: "Open Agents Board", hint: "nav", run: go("agents") });
registerCommand({ id: "nav.memory", label: "Open Memory Graph", hint: "nav", run: go("memory") });
registerCommand({ id: "nav.network", label: "Open Network (Devices · Vitals · Proximity)", hint: "nav", run: go("network") });
registerCommand({ id: "nav.audit", label: "Open Audit Ledger", hint: "nav", run: go("audit") });
registerCommand({ id: "nav.legacy", label: "Open Legacy UI (/ai)", hint: "nav", run: () => { location.href = "/ai"; } });

registerCommand({ id: "ui.theme", label: "Toggle Theme (Calm ⇄ Neon)", hint: "ui", run: () => cycleSkin() });

registerCommand({
  id: "sys.providers",
  label: "Check AI Provider Health",
  hint: "system",
  run: async () => {
    try {
      const h = await fetchProviderHealth(true);
      const down = h.providers.filter((p) => p.configured && !p.ok);
      if (down.length) toast(`${down.length} provider(s) down: ${down.map((d) => d.provider).join(", ")}`, "danger", 9000);
      else toast(`All ${h.healthy}/${h.total} provider keys healthy`, "success");
    } catch { toast("Provider health check failed", "danger"); }
  },
});

registerCommand({
  id: "sys.screen",
  label: "Describe My Screen",
  hint: "vision",
  run: async () => {
    toast("DEEP is looking at your screen…", "info");
    try {
      const r = await fetch("/api/vision/screen", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ q: "Describe what's on this screen for Aryan, concisely." }),
      });
      const d = await r.json();
      if (d.ok) toast(String(d.description).slice(0, 280), "success", 14000);
      else toast(`Screen read failed: ${d.error}`, "danger");
    } catch { toast("Screen read failed", "danger"); }
  },
});
