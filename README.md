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
- OSINT recon (DNS, cert transparency, geolocation) plus optional
  Shodan / VirusTotal / AbuseIPDB / Mozilla HTTP Observatory lookups
- Live threat intel ingestion: CISA KEV, major security blogs (Krebs,
  The Hacker News, BleepingComputer, SANS ISC, Cisco Talos, Google Project
  Zero, Microsoft MSRC), r/netsec + r/cybersecurity, and — with a free API
  key — AlienVault OTX pulses and abuse.ch URLhaus/ThreatFox
- Global threat signal gets cross-referenced against what DEEP already knows
  you work with, so a fresh CVE disclosure for a tool in your own stack
  surfaces proactively instead of getting lost in a feed

**Memory & reasoning**
- A persistent knowledge graph plus a "world model" — a live, LLM-synthesized
  summary of your projects, priorities, and recent activity, injected into
  every conversation so responses are actually personalized
- Tamper-evident audit trail (hash-chained log) for every action DEEP takes
- Multi-provider LLM routing: Ollama locally, Claude/Gemini/Groq as optional
  cloud fallback for harder queries

**Interface**
- A FastAPI + WebSocket backend driving a Vite/Lit/TypeScript web HUD
- Live, real-time visualizations (a global threat globe, a Matrix-style
  waterfall) driven by actual WebSocket telemetry — not decoration
- Four selectable visual skins (calm / neon / etis / hacker)
- Voice in and out (offline Whisper STT, Edge/Piper/ElevenLabs TTS)

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

Run the test suite with `make test` (or `pytest`).

---

## Configuration

Everything in `.env` is optional — DEEP degrades gracefully and tells you in
the startup logs which pieces are inactive without a given key.

| Variable | Unlocks | Get one at |
|---|---|---|
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
│                     #   world model, audit trail, global threat watch
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
