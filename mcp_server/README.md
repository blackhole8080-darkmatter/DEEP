# DEEP — MCP Server

Exposes DEEP's local intelligence to any **Model Context Protocol** client
(Claude Desktop, Cursor, etc.) as tools. This turns DEEP from an app into an
**intelligence backend** other AIs can call.

## Tools exposed
| Tool | What it does |
|---|---|
| `deep_status` | Live system status (online state, active model, time) |
| `deep_investigate(target)` | Dossier on an IP / MAC / host / domain (vendor, geo, ISP/ASN, reverse-DNS, risk) |
| `deep_scan_surroundings` | Nearby Wi-Fi APs + Bluetooth devices DEEP senses (incl. tracker detection) |
| `deep_search_memory(query)` | Search DEEP's persistent knowledge graph |
| `deep_remember(fact)` | Teach DEEP a new fact (persists across sessions) |
| `deep_research(unread_only)` | Recent research findings DEEP has ingested |
| `deep_security_status` | Network device counts, suspicious activity, audit-chain integrity |

## How it works
A thin, decoupled proxy over DEEP's HTTP API (default `http://localhost:7768`).
**DEEP must be running** (it auto-starts at login). Override the target with the
`DEEP_BASE_URL` env var.

## Setup (Claude Desktop)
Already wired in `%APPDATA%\Claude\claude_desktop_config.json`:

```json
"mcpServers": {
  "deep": {
    "command": "C:\\Users\\Aryan\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\\python.exe",
    "args": ["C:\\Users\\Aryan\\Aryan_Private\\DEEP\\mcp_server\\deep_mcp.py"]
  }
}
```

**Restart Claude Desktop** to load it. Then ask things like:
- "Use DEEP to investigate 8.8.8.8"
- "What devices are near me right now?" (deep_scan_surroundings)
- "What does DEEP remember about my projects?"
- "Check DEEP's security status"

## Run manually (stdio)
```
python mcp_server/deep_mcp.py
```

## Requires
`pip install "mcp[cli]" httpx` (already installed).
