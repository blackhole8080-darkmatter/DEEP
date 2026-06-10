// Typed REST client for DEEP's /api endpoints (the ones the new UI consumes).
async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return (await r.json()) as T;
}

export interface Status {
  deep: string;
  brain: string;
  model: string;
  time: string;
  date: string;
}
export const fetchStatus = () => get<Status>("/api/status");

export interface ProviderHealth {
  providers: { provider: string; configured: boolean; ok: boolean; detail: string }[];
  healthy: number;
  total: number;
}
export const fetchProviderHealth = (force = false) =>
  get<ProviderHealth>(`/api/providers/health${force ? "?force=true" : ""}`);

export interface ElementInfo {
  atomic_number: number;
  symbol: string;
  name: string;
  atomic_weight: number;
  electron_configuration?: string;
  category: string;
  series?: string;
  group?: number;
  period?: number;
  [k: string]: unknown;
}
export const fetchPeriodicTable = () =>
  get<{ ok: boolean; elements: ElementInfo[] }>("/api/chem/table");
export const fetchElement = (q: string | number) =>
  get<{ ok: boolean; element?: ElementInfo; error?: string }>(`/api/chem/element/${q}`);

export const fetchPhysicsConstants = () =>
  get<{ ok: boolean; constants: { name: string; value: number; unit: string; symbol: string }[] }>(
    "/api/physics/constants",
  );
export const fetchPhysicsFormulas = (era?: string) =>
  get<{ ok: boolean; formulas: { name: string; era: string; domain: string; formula: string; desc: string }[] }>(
    `/api/physics/formulas${era ? `?era=${era}` : ""}`,
  );

export const fetchKnowledgeList = () =>
  get<{ ok: boolean; documents: { source: string; chunks: number; doc_id: string }[] }>(
    "/api/knowledge/list",
  );

export async function ingestDocument(file: File): Promise<{ ok: boolean; source?: string; chunks?: number; error?: string }> {
  const fd = new FormData();
  fd.append("file", file, file.name);
  const r = await fetch("/api/knowledge/ingest", { method: "POST", body: fd });
  return (await r.json()) as { ok: boolean; source?: string; chunks?: number; error?: string };
}
