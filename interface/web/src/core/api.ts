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
  get<{ ok: boolean; formulas: { name: string; era: string; domain: string; formula: string; desc: string; latex?: string | null }[] }>(
    `/api/physics/formulas${era ? `?era=${era}` : ""}`,
  );

export const fetchKnowledgeList = () =>
  get<{ ok: boolean; documents: { source: string; chunks: number; doc_id: string }[] }>(
    "/api/knowledge/list",
  );

export interface Vitals {
  cpu: number; ram: number; disk: number; ram_used_gb: number; ram_total_gb: number;
  net_sent_mbs: number; net_recv_mbs: number; cores: number;
}
export const fetchVitals = () => get<Vitals>("/api/vitals");

export interface Display { name: string; width: number; height: number; x: number; y: number; primary: boolean; }
export interface SystemInfo {
  hostname: string; os: string; arch: string; uptime_s: number;
  cpu_model: string; cores_physical: number; cores_logical: number; cpu_freq_mhz: number | null;
  per_core: number[];
  battery?: { percent: number; plugged: boolean; secs_left: number | null };
  displays: Display[];
  gpu?: unknown;
}
export const fetchSystemInfo = () => get<SystemInfo>("/api/system/info");

export interface GeoPeer { ip: string; lat: number; lon: number; city: string; region: string; country: string; isp: string; asn: string; proxy: boolean; hosting: boolean; risk: "elevated" | "normal"; connections: number; processes: string[]; }
export interface GeoOrigin { ip: string; lat: number; lon: number; city: string; country: string; isp: string; }
export const fetchNetworkGeo = () => get<{ count: number; elevated?: number; countries?: string[]; processes?: string[]; origin?: GeoOrigin | null; peers: GeoPeer[]; note?: string; error?: string }>("/api/network/geo");


export interface MathSolveResult { ok: boolean; kind?: string; expression?: string; result?: string; engine?: string; latex?: string | null; latex_expr?: string | null; }
export async function mathSolve(query: string): Promise<MathSolveResult> {
  const r = await fetch("/api/math/solve", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return (await r.json()) as MathSolveResult;
}

export interface ScienceComputeResult { ok: boolean; verbal: string; result: unknown; media: unknown[]; latex?: string | null; symbolic?: string | null; numeric?: number | string | null; }
export async function scienceCompute(query: string): Promise<ScienceComputeResult> {
  const r = await fetch("/api/science/compute", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return (await r.json()) as ScienceComputeResult;
}

export async function ingestDocument(file: File): Promise<{ ok: boolean; source?: string; chunks?: number; error?: string }> {
  const fd = new FormData();
  fd.append("file", file, file.name);
  const r = await fetch("/api/knowledge/ingest", { method: "POST", body: fd });
  return (await r.json()) as { ok: boolean; source?: string; chunks?: number; error?: string };
}

// ── Finance ────────────────────────────────────────────────────────────────
export interface Transaction { id: number; date: string; amount: number; currency: string; description: string; category: string; source: string; account: string; }
export interface BudgetStatus { category: string; limit: number; spent: number; remaining: number; percent: number; currency: string; }
export interface Bill { id: number; name: string; amount: number; currency: string; frequency: string; next_due: string; active: number; }
export interface Account { name: string; balance: number; currency: string; type: string; }
export interface Anomaly { transaction_id: number; date: string; description: string; amount: number; category: string; z_score: number; verbal: string; }

export const fetchFinanceSummary = (months = 1) => get<{ period_months: number; total_spent: number; total_income: number; net: number; by_category: { category: string; total: number; count: number }[]; verbal: string }>(`/api/finance/summary?months=${months}`);
export const fetchFinanceTransactions = (params?: { start?: string; end?: string; category?: string; limit?: number }) => {
  const qs = new URLSearchParams();
  if (params?.start) qs.set("start", params.start);
  if (params?.end) qs.set("end", params.end);
  if (params?.category) qs.set("category", params.category);
  if (params?.limit) qs.set("limit", String(params.limit));
  return get<{ transactions: Transaction[] }>(`/api/finance/transactions?${qs}`);
};
export const fetchFinanceBudgets = () => get<{ budgets: BudgetStatus[] }>("/api/finance/budgets");
export const fetchFinanceBills = () => get<{ bills: Bill[] }>("/api/finance/bills");
export const fetchFinanceUpcomingBills = (days = 14) => get<{ bills: Bill[] }>(`/api/finance/bills/upcoming?days=${days}`);
export const fetchFinanceAnomalies = (category?: string) => get<{ anomalies: Anomaly[] }>(`/api/finance/anomalies${category ? `?category=${category}` : ""}`);
export const fetchFinanceAccounts = () => get<{ accounts: Account[] }>("/api/finance/accounts");

export async function addFinanceTransaction(data: { date: string; amount: number; description: string; category?: string; currency?: string; account?: string }) {
  const r = await fetch("/api/finance/transaction", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
  return r.json();
}
export async function setFinanceBudget(data: { category: string; limit: number; currency?: string }) {
  const r = await fetch("/api/finance/budget", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
  return r.json();
}
export async function addFinanceBill(data: { name: string; amount: number; frequency?: string; next_due?: string; currency?: string }) {
  const r = await fetch("/api/finance/bill", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
  return r.json();
}

// ── Email ──────────────────────────────────────────────────────────────────
export interface EmailMsg { id: string; subject: string; sender: string; date: string; unread?: boolean; }
export interface TrackedThread { msg_id: string; sender: string; subject: string; received_at: string; needs_reply: number; priority: number; notes: string; }

export const fetchEmailInbox = (limit = 20) => get<{ ok: boolean; unread_count: number; recent: EmailMsg[]; verbal: string }>(`/api/email/inbox?limit=${limit}`);
export const fetchEmailSearch = (q: string, limit = 10) => get<{ ok: boolean; results: EmailMsg[]; count: number; verbal: string }>(`/api/email/search?q=${encodeURIComponent(q)}&limit=${limit}`);
export const fetchEmailAwaiting = () => get<{ threads: TrackedThread[] }>("/api/email/awaiting");

export async function sendEmail(data: { to: string; subject: string; body: string }) {
  const r = await fetch("/api/email/send", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
  return r.json();
}

// ── Missions ─────────────────────────────────────────────────────────────────
export interface Mission { id: string; goal: string; status: string; progress_pct: number; created_at: string; updated_at: string; error?: string; }
export interface Subtask { id: string; mission_id: string; description: string; status: string; order_index: number; result?: string; error?: string; retry_count: number; started_at?: string; completed_at?: string; }

export async function createMission(goal: string): Promise<{ mission_id: string; goal: string; status: string } | { error: string }> {
  const r = await fetch("/api/missions", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ goal }) });
  return r.json();
}
export const fetchMissions = (status?: string, limit = 20) => get<{ missions: Mission[] }>(`/api/missions${status ? `?status=${status}&limit=${limit}` : `?limit=${limit}`}`);
export const fetchMissionDetail = (id: string) => get<{ mission: Mission; subtasks: Subtask[] }>(`/api/missions/${id}`);
export async function cancelMission(id: string) {
  const r = await fetch(`/api/missions/${id}/cancel`, { method: "POST" });
  return r.json();
}

// ── Network / Security ─────────────────────────────────────────────────────
export interface SecurityDevice {
  mac: string; ip: string; hostname: string | null; vendor: string | null;
  trust_status: "trusted" | "unknown" | "suspicious" | "blocked";
  is_gateway: boolean; last_seen: string; ports?: number[];
}
export interface SecurityStatus {
  status: string; score: number; devices_total: number; devices_trusted: number;
  devices_unknown: number; devices_suspicious: number; threats_24h: number;
  evil_twin_active: boolean; tailscale_connected: boolean;
}
export interface SecurityEvent {
  id: string; type: string; severity: "info" | "warning" | "critical";
  message: string; timestamp: string; device_mac?: string; acknowledged: boolean;
}
export interface Threat {
  id: string; type: string; confidence: number; detected_at: string;
  source_ip?: string; details: string;
}
export interface NetworkSnapshot {
  devices: SecurityDevice[]; events: SecurityEvent[]; threats: Threat[];
  wifi_aps: { ssid: string; bssid: string; channel: number; signal: number; rogue: boolean }[];
}

export const fetchSecurityStatus = () => get<SecurityStatus>("/api/security/status");
export const fetchSecurityDevices = () => get<{ devices: SecurityDevice[] }>("/api/security/devices");
export const fetchSecurityEvents = (limit = 50) => get<{ events: SecurityEvent[] }>(`/api/security/events?limit=${limit}`);
export const fetchSecuritySnapshot = () => get<NetworkSnapshot>("/api/security/snapshot");
export const fetchNetworkThreats = (hours = 24) => get<{ threats: Threat[] }>(`/network/threats?hours=${hours}`);
export async function trustDevice(mac: string) {
  const r = await fetch("/api/security/trust", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mac }) });
  return r.json();
}
export async function blockDevice(mac: string) {
  const r = await fetch("/api/security/block", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mac }) });
  return r.json();
}
export async function acknowledgeSecurityEvent(eventId: string) {
  const r = await fetch("/api/security/acknowledge", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ event_id: eventId }) });
  return r.json();
}
export async function scanTarget(ip: string) {
  const r = await fetch(`/network/scan/${encodeURIComponent(ip)}`, { method: "POST" });
  return r.json();
}
export const fetchWifiStatus = () => get<{ aps: NetworkSnapshot["wifi_aps"]; evil_twin_detected: boolean }>("/network/wifi");

// ── Network Topology Graph (v3) ──────────────────────────────────────────
export interface GraphNode {
  id: string; layer: string; node_type: string; label: string;
  metadata: Record<string, any>; x: number; y: number; last_seen: string;
}
export interface GraphEdge {
  source: string; target: string; layer: string; relation: string; strength: number; metadata: Record<string, any>;
}
export interface GraphData {
  nodes: GraphNode[]; edges: GraphEdge[];
}
export interface GraphStats {
  nodes_by_layer: Record<string, number>; edges: number; observations: number; inferences: number;
}

export const fetchNetworkGraph = (layer?: string) => get<GraphData>(`/api/network/graph${layer ? `?layer=${layer}` : ""}`);
export const fetchNetworkSubgraph = (nodeId: string, depth = 1) => get<GraphData>(`/api/network/graph/${encodeURIComponent(nodeId)}?depth=${depth}`);
export const fetchNetworkStats = () => get<GraphStats>("/api/network/stats");
export const fetchNetworkObservations = (nodeId: string, metric?: string, hours = 24) =>
  get<{ observations: any[] }>(`/api/network/observations/${encodeURIComponent(nodeId)}?hours=${hours}${metric ? `&metric=${metric}` : ""}`);
export const fetchNetworkInferences = (nodeId: string, inferenceType?: string, limit = 20) =>
  get<{ inferences: any[] }>(`/api/network/inferences/${encodeURIComponent(nodeId)}?limit=${limit}${inferenceType ? `&inference_type=${inferenceType}` : ""}`);
export async function analyseNetwork(scope: "device" | "health" | "threats", nodeId?: string) {
  const r = await fetch("/api/network/analyse", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ scope, node_id: nodeId }) });
  return r.json();
}

// ── Agents ─────────────────────────────────────────────────────────────────
export interface AgentInfo {
  id: string; name: string; role: string; status: string;
  created_at: string; allowed_tools: string[];
  tasks_completed: number; tasks_total: number;
}
export interface AgentStats {
  agents_alive: number; agents_running: number; total_tasks_completed: number;
}
export interface AgentTaskJob {
  id: string; agent: string; role: string; task: string;
  status: string; result: string | null; error: string | null;
  created: string; latency_ms: number | null;
}
export const fetchAgents = () => get<{ agents: AgentInfo[] }>("/api/agents");
export const fetchAgentStats = () => get<AgentStats>("/api/agents/stats");
export const fetchAgentTasks = () => get<{ tasks: AgentTaskJob[] }>("/api/agents/tasks");
export async function launchAgentTask(role: string, task: string) {
  const r = await fetch("/api/agents/task", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ role, task }) });
  return r.json() as Promise<{ success?: boolean; task_id?: string; agent?: string; error?: string }>;
}
export async function createAgent(name: string, role: string) {
  const r = await fetch("/api/agents", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, role }) });
  return r.json() as Promise<{ success?: boolean; agent?: AgentInfo; error?: string }>;
}
