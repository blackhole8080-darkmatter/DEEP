# DEEP

**A local-first, voice-and-chat AI assistant with a real cybersecurity brain.**

DEEP watches your local network, correlates what it sees against live threat
intelligence (CVEs, MITRE ATT&CK, CISA KEV, OSINT feeds), remembers what you're
working on, and talks to you about it — through a JARVIS-style web HUD or by
voice. It runs entirely on your own machine; a local LLM via
[Ollama](https://ollama.com) is enough to use it fully offline, with optional
cloud models (Claude, Gemini, Groq) as a fallback for harder reasoning.

This is a personal, actively-evolving project, not a finished product. The
README below describes what's actually wired up and working today — not a
wishlist.

---

## What it actually does

**Network & cybersecurity intelligence**
- Passive, 100%-local network monitoring — device discovery, fingerprinting,
  ARP/connection tracking, evil-twin AP detection
- Anomaly detection (baseline-deviation models for system + network behavior)
  feeding a trainable threat classifier
- Every anomaly/threat gets enriched automatically with matching
  [MITRE ATT&CK](https://attack.mitre.org/) techniques and related CVEs, then
  surfaced on one live, severity-scored security timeline
- **A unified OSINT investigator.** Give it any indicator — IP, domain, CVE,
  ASN, file hash, MAC, or `pypi:requests` — and it infers the type, fans out
  across every applicable public source concurrently, and returns one dossier
  with a derived risk verdict. Every finding names the API that produced it,
  so a verdict can be audited rather than trusted. A source that times out
  lands in `degraded` and the rest of the report still renders; if *nothing*
  answers, the verdict is `unknown`, never a fabricated all-clear.
- **20 catalogued public APIs, 16 of which need no key at all** — CISA KEV,
  FIRST EPSS, NVD, OSV.dev, GitHub Advisories, Shodan InternetDB, SANS ISC,
  abuse.ch Feodo Tracker, the Tor exit list, RDAP, RIPEstat, Cloudflare DoH,
  crt.sh, Have I Been Pwned's breach catalog and more. `GET /api/intel/sources`
  shows exactly which are live and which are waiting on a key you haven't set.
  Shodan/VirusTotal/AbuseIPDB/OTX slot in on top when you supply keys.
- Live threat intel ingestion: CISA KEV, major security blogs (Krebs,
  The Hacker News, BleepingComputer, SANS ISC, Cisco Talos, Google Project
  Zero, Microsoft MSRC), r/netsec + r/cybersecurity, and — with a free API
  key — AlienVault OTX pulses and abuse.ch URLhaus/ThreatFox
- Global threat signal gets cross-referenced against what DEEP already knows
  you work with, so a fresh CVE disclosure for a tool in your own stack
  surfaces proactively instead of getting lost in a feed

**The assistant can use all of it**
- DEEP can read its own observations, not just the internet: `security_events`
  (the correlated local timeline, with matched ATT&CK techniques and CVEs),
  `anomalies`, `threat_predictions`, `local_devices`, `wifi_environment`
  (including evil-twin state), `dns_activity`, `stack_exposure` (live CVEs
  matched against *your* stack) and `exploit_search`. Combined with the OSINT
  tools this chains: a device that started beaconing at 03:00 → who it was
  talking to → whether the CVE it's likely exploiting is in CISA KEV.
- 61 tools reach the reasoning brain, every one of which actually runs — the
  surface was audited by executing all of them, not by reading the list.
  Off-mission groups (phone control, personal finance, email, XR) and tools
  that referenced integrations the registry never built are gone.
- Shell execution (`run_command`) is opt-in behind `DEEP_ENABLE_SHELL_TOOL`.
  The other file tools are path-sandboxed to a workspace root; that command
  is not — it sandboxes the working directory, not the command — so it isn't
  handed to an LLM by default.
- The OSINT layer is exposed to DEEP's reasoning brain as tools, so asking
  "is 45.33.32.156 malicious?" or "how urgent is CVE-2021-44228 really?" in
  chat produces a sourced answer from live feeds rather than a recollection
  from training data. Every finding it repeats carries the API that produced
  it, and unreachable sources are named.

**Memory & reasoning**
- A persistent knowledge graph plus a "world model" — a live, LLM-synthesized
  summary of your projects, priorities, and recent activity, injected into
  every conversation so responses are actually personalized
- Tamper-evident audit trail (hash-chained log) for every action DEEP takes
- Multi-provider LLM routing: Ollama locally, Claude/Gemini/Groq as optional
  cloud fallback for harder queries

**Operations center**
- **A read-only ops terminal** in the HUD: `investigate`, `whois`, `dns`,
  `subdomains`, `exposure`, `cve`, `kev`, `epss`, `deps`, `threatmap`,
  `stats`, `sources`, `devices`, `timeline`, `scan`. History, tab completion
  and structured output. Nothing shells out — an unrecognised verb is an
  error, not something handed to a shell — and `scan`, the only command that
  emits a packet, refuses any target outside your own subnet.
- **Live statistics board**: KEV velocity (added in 7/30/90 days, overdue
  remediations, ransomware-linked), active botnet C2 population by family and
  country, Tor exit count, and per-source health. A feed that is down renders
  as "unavailable", never as zero.
- **Intelligence map**: geolocated attacker and C2 nodes, each carrying the
  classification the feed that listed it actually assigned. Click a node for a
  full dossier.

**Interface**
- A FastAPI + WebSocket backend driving a Vite/Lit/TypeScript web HUD
- Live, real-time visualizations (a global threat globe, a Matrix-style
  waterfall) driven by actual WebSocket telemetry — not decoration
- Four selectable visual skins (calm / neon / etis / hacker)
- Chat renders sanitized markdown and code blocks

> **Voice is currently removed.** The `voice/` package was deleted and the
> endpoints that fronted it (`/api/tts`, `/api/transcribe`) now return 503
> rather than pretending to work.

---

## Quickstart

**Requirements:** Python 3.11+, a recent Node.js (only if you're building the
frontend yourself), and [Ollama](https://ollama.com) for local/offline LLM use.

```bash
git clone https://github.com/blackhole8080-darkmatter/DEEP.git
cd DEEP

# Backend
make install              # pip install -e .[dev]
cp .env.example .env      # fill in whatever optional keys you want (see below)

# Local LLM (skip if you're only using a cloud provider)
ollama pull llama3.2

# Start
make start                 # python interface/server.py
```

Then open **http://127.0.0.1:5174**.

No `make`? The equivalent manual steps:
```bash
pip install -r requirements.txt
python interface/server.py
```

To rebuild the frontend after editing anything under `interface/web/`:
```bash
cd interface/web
npm install
npm run build   # emits to interface/static/app-dist, which the backend serves
```

Run the test suite with `make test` (or `pytest`). The frontend typechecks as
part of `npm run build`; `npm run typecheck` runs it alone.

Once DEEP is up, open the **Terminal** tool in the HUD and try:

```
help                      # every command, grouped
sources                   # which public APIs are live right now
stats                     # global KEV velocity, botnet C2 count, feed health
investigate 1.1.1.1       # full dossier — auto-detects the indicator type
cve CVE-2021-44228        # CVSS + EPSS + KEV status + affected packages
kev --vendor Microsoft    # actively-exploited vulns, filtered
deps pypi:requests        # advisories for a package you depend on
```

---

## Configuration

Everything in `.env` is optional — DEEP degrades gracefully and tells you in
the startup logs which pieces are inactive without a given key.

DEEP's OSINT layer works fully on a fresh clone: 16 of its 20 catalogued
sources need no signup. Keys below only add the four gated ones.

**Remote access:** DEEP trusts loopback unconditionally. Any other client —
LAN, Tailnet — needs a key. Leave `DEEP_API_KEY` unset and DEEP mints a random
one on first boot, stores it in `data/.deep_api_key`, and prints it in the
startup log.

| Variable | Unlocks | Get one at |
|---|---|---|
| `DEEP_API_KEY` | remote (non-loopback) access; auto-generated if unset | — |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | local LLM (default: `llama3.2`) | [ollama.com](https://ollama.com) |
| `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` | cloud LLM fallback | respective provider consoles |
| `SHODAN_API_KEY` | internet-exposure lookups | [shodan.io](https://account.shodan.io/register) |
| `VIRUSTOTAL_API_KEY` | file/URL/IP reputation | [virustotal.com](https://www.virustotal.com/gui/join-us) |
| `ABUSEIPDB_API_KEY` | IP abuse reputation | [abuseipdb.com](https://www.abuseipdb.com/register) |
| `OTX_API_KEY` | AlienVault threat-intel pulses | [otx.alienvault.com](https://otx.alienvault.com/api) |
| `ABUSECH_AUTH_KEY` | URLhaus + ThreatFox malware/IOC feeds | [auth.abuse.ch](https://auth.abuse.ch/) |
| `NEWSAPI_KEY` | broader news briefings | [newsapi.org](https://newsapi.org) |

See `.env.example` for the full list with inline notes.

---

## Architecture

```
DEEP/
├── core/            # brain: LLM routing, memory, knowledge graph, event bus,
│   │                 #   world model, audit trail, global threat watch
│   └── intel/       # public-API layer: source catalog, shared HTTP transport,
│                     #   OSINT investigator, live stats/map, ops terminal
├── ai/               # anomaly detection + threat classifier (PyTorch/sklearn)
├── domains/          # cybersecurity, RF signals, protocol analysis
├── network/          # scanner, evil-twin detection, proximity, remote access
├── engine/           # JARVIS assistant orchestration (voice, tools, tech skills)
├── knowledge/        # ingestion, briefings, breakthrough detection
├── interface/
│   ├── server.py     # FastAPI app + WebSocket entrypoint
│   ├── routers/       # REST endpoints, one module per subsystem
│   └── web/            # Vite + Lit + TypeScript frontend source
│       └── (builds to interface/static/app-dist, served by the backend)
├── mcp_server/       # MCP server exposing DEEP as tools to other agents
├── archive/          # retired subsystems, kept for history — not loaded
│   └── web/          #   34 frontend modules that reached no entry point
└── tests/            # pytest suite
```

Everything runs as one process locally — no required external services
beyond an optional Ollama instance. SQLite handles local storage; nothing is
sent off-device unless you configure a cloud LLM or one of the optional
threat-intel API keys above.

---

## Project status

DEEP started broad (it briefly included physics/chemistry/genomics engines
and a full science-computation suite) and has been deliberately narrowed to
focus on **network + cybersecurity + memory**. Retired subsystems live in
`archive/` rather than being deleted, in case they're useful reference later.

Expect rough edges — this is a solo, actively-developed project. Issues and
PRs are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
