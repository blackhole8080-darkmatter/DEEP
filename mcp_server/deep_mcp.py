#!/usr/bin/env python3
"""
DEEP — MCP server.

Exposes DEEP's local intelligence (network/Bluetooth sensing, device/IP
investigation, persistent memory + knowledge graph, research, security) as
Model Context Protocol tools, so Claude Desktop / Cursor / any MCP client can
use DEEP as an intelligence *backend* — not just an app.

It is a thin, decoupled proxy over DEEP's running HTTP API (default
http://localhost:5174 — the port interface/server.py actually binds), so DEEP
must be running. Set DEEP_BASE_URL to override.

Run (stdio):  python mcp_server/deep_mcp.py
"""
from __future__ import annotations

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

# 5174 is what interface/server.py binds. This defaulted to 7768 — a port
# nothing has listened on since the HUD server moved — so every tool here
# failed with a connection error until DEEP_BASE_URL was set by hand.
BASE = os.environ.get("DEEP_BASE_URL", "http://localhost:5174").rstrip("/")
mcp = FastMCP("DEEP")


async def _get(path: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BASE}{path}", params=params or {})
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE}{path}", json=body)
        r.raise_for_status()
        return r.json()


def _fmt(obj) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


@mcp.tool()
async def deep_status() -> str:
    """Live status of the DEEP system (online state, active model, time)."""
    try:
        return _fmt(await _get("/api/status"))
    except Exception as e:
        return f"DEEP appears offline ({e}). Start DEEP on {BASE}."


@mcp.tool()
async def deep_investigate(target: str) -> str:
    """Build an intelligence dossier on an IP, MAC, hostname or domain:
    vendor, reverse-DNS, geolocation, ISP/ASN, private-vs-public, and risk flags.
    Use to identify an unknown network/Bluetooth device or a remote host."""
    try:
        return _fmt(await _get("/api/investigate", {"target": target}))
    except Exception as e:
        return f"Investigation failed: {e}"


@mcp.tool()
async def deep_investigate_url(url: str) -> str:
    """Investigate a full URL — a link from an email, a message, a report.

    Returns what a browser actually saw when urlscan.io loaded the page:
    redirect chain, final destination, scan history, whether any scan was
    flagged malicious, apex-domain age and submitter tags — plus DNS,
    certificate and registration detail for the host underneath.

    The host's reputation is not the page's: shared hosting serves phishing
    kits from decade-old domains daily. No verdict data means no data, never
    'clean'."""
    try:
        return _fmt(await _get("/api/intel/investigate", {"target": url}))
    except Exception as e:
        return f"URL investigation failed: {e}"


@mcp.tool()
async def deep_scan_surroundings() -> str:
    """What's physically near you right now — nearby Wi-Fi access points and
    Bluetooth devices DEEP senses (counts, plus the strongest named ones with
    vendor/signal). Useful for situational awareness and tracker detection."""
    try:
        summary = await _get("/network/proximity")
        wifi = (await _get("/network/proximity/wifi")).get("aps", [])
        bt = (await _get("/network/proximity/bt")).get("devices", [])
        top_wifi = sorted(wifi, key=lambda a: a.get("signal_dbm", -120), reverse=True)[:8]
        trackers = [d for d in bt if d.get("is_tracker")]
        return _fmt({
            "summary": summary,
            "top_wifi": [{"ssid": a.get("ssid") or "(hidden)", "vendor": a.get("vendor"),
                          "band": a.get("band"), "signal_dbm": a.get("signal_dbm"),
                          "encryption": a.get("encryption")} for a in top_wifi],
            "bluetooth_count": len(bt),
            "trackers_detected": [{"mac": d.get("mac"), "kind": d.get("tracker_kind"),
                                   "vendor": d.get("vendor")} for d in trackers],
        })
    except Exception as e:
        return f"Scan failed: {e}"


@mcp.tool()
async def deep_search_memory(query: str) -> str:
    """Search DEEP's persistent knowledge graph / long-term memory about Aryan
    (people, projects, technologies, preferences, facts it has retained)."""
    try:
        return _fmt(await _get("/api/knowledge/search", {"q": query, "limit": 10}))
    except Exception as e:
        return f"Memory search failed: {e}"


@mcp.tool()
async def deep_remember(fact: str) -> str:
    """Teach DEEP a new fact — ingest free text into its persistent knowledge
    graph so it remembers across sessions."""
    try:
        return _fmt(await _post("/api/knowledge/ingest", {"text": fact}))
    except Exception as e:
        return f"Could not store fact: {e}"


@mcp.tool()
async def deep_research(unread_only: bool = False) -> str:
    """Recent research findings DEEP has ingested (papers, articles, feeds),
    with titles and sources. Set unread_only to focus on what's new."""
    try:
        data = await _get("/api/research/findings")
        finds = data.get("findings", [])
        if unread_only:
            finds = [f for f in finds if f.get("read") in (False, None)]
        out = [{"title": f.get("title"), "source": f.get("source"),
                "type": f.get("source_type")} for f in finds[:15]]
        return _fmt({"count": len(out), "findings": out})
    except Exception as e:
        return f"Research fetch failed: {e}"


@mcp.tool()
async def deep_security_status() -> str:
    """DEEP's current security posture — device counts on the network, anything
    suspicious, and the integrity state of the tamper-evident audit ledger."""
    try:
        sec = await _get("/api/security/status")
        audit = await _get("/audit/stats")
        return _fmt({
            "network": sec.get("summary", sec),
            "audit": {"total_entries": audit.get("total_entries"),
                      "chain_intact": audit.get("chain_intact"),
                      "threats_today": audit.get("threat_count_today")},
        })
    except Exception as e:
        return f"Security status failed: {e}"


if __name__ == "__main__":
    mcp.run()
