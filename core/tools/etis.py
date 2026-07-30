"""
DEEP ETIS tools — Modern registry integration.
"""

from core.tools.registry import tool
from core.domain.models import ToolResult

@tool(
    "etis_cve_lookup",
    "Full CVE record lookup from NVD + KEV check.",
    {
        "cve_id": "The CVE ID to look up (e.g. 'CVE-2024-3400')"
    }
)
async def etis_cve_lookup(ctx, args) -> ToolResult:
    try:
        from domains.cybersec.cve_intel import CVEIntel
        intel = CVEIntel()
        result = await intel.lookup(args["cve_id"].strip().upper())
        # lookup() always returns a CVERecord; failures come back as a stub with
        # empty published/modified and the message in `description` (no `.error`).
        if not result.published:
            return ToolResult(ok=False, content=f"[CVE] {result.description}", tool_name="etis_cve_lookup")
        cvss = result.cvss_v3
        if cvss:
            sev_line = f"Severity: {cvss.severity} (CVSS {cvss.score:.1f})"
        elif result.cvss_v2_score:
            sev_line = f"Severity: CVSS v2 {result.cvss_v2_score:.1f}"
        else:
            sev_line = "Severity: unknown"
        lines = [
            f"[CVE] {result.cve_id}",
            sev_line,
            f"Published: {result.published}",
            f"KEV: {'YES — actively exploited in the wild!' if result.is_kev else 'No'}",
            f"CWE: {', '.join(result.cwe) if result.cwe else 'n/a'}",
            f"Description: {result.description}",
        ]
        return ToolResult(ok=True, content="\n".join(lines), tool_name="etis_cve_lookup")
    except Exception as e:
        return ToolResult(ok=False, content=f"[CVE] {e}", tool_name="etis_cve_lookup")

@tool(
    "etis_mitre_search",
    "Search MITRE ATT&CK techniques by keyword.",
    {
        "query": "The keyword to search for (e.g. 'credential access')"
    }
)
async def etis_mitre_search(ctx, args) -> ToolResult:
    try:
        from domains.cybersec.mitre_attack import MITREAttack
        mitre = MITREAttack()
        results = mitre.search_ttp(args["query"])  # sync; returns List[Technique]
        if not results:
            return ToolResult(ok=True, content=f"[MITRE] No techniques found for: {args['query']}", tool_name="etis_mitre_search")
        lines = [f"[MITRE ATT&CK] Results for '{args['query']}':"]
        for t in results[:5]:
            lines.append(f"  {t.id} | {t.name} | Tactics: {', '.join(t.tactics)}")
        return ToolResult(ok=True, content="\n".join(lines), tool_name="etis_mitre_search")
    except Exception as e:
        return ToolResult(ok=False, content=f"[MITRE] {e}", tool_name="etis_mitre_search")

@tool(
    "etis_connection_geo",
    "Show where this machine's live network connections are going right now: "
    "geolocated remote peers (city/country/ISP), which local process opened each, "
    "and risk flags (hosting/cloud or proxy/VPN). Use for 'where are my "
    "connections going', 'what is my computer talking to', network situational awareness.",
    {}
)
async def etis_connection_geo(ctx, args) -> ToolResult:
    try:
        import asyncio
        from network.connection_geo import scan_connections
        data = await asyncio.to_thread(scan_connections)
        if data.get("error"):
            return ToolResult(ok=False, content=f"[CONN] {data['error']}", tool_name="etis_connection_geo")
        peers = data.get("peers", [])
        if not peers:
            return ToolResult(ok=True, content="[CONN] No public outbound connections right now.", tool_name="etis_connection_geo")
        o = data.get("origin")
        lines = [
            f"[CONNECTION GEOGRAPHY] {data['count']} peers across "
            f"{len(data.get('countries', []))} countries; {data.get('elevated', 0)} elevated (hosting/proxy)."
            + (f" Egress: {o['city']}, {o['country']} ({o['isp']})." if o else ""),
        ]
        for p in peers[:15]:
            flag = " ⚠PROXY" if p["proxy"] else (" ⚠HOSTING" if p["hosting"] else "")
            procs = ", ".join(p["processes"]) or "?"
            lines.append(f"  {p['city']}, {p['country']} · {p['isp']} · {procs} · {p['connections']}×{flag}")
        if len(peers) > 15:
            lines.append(f"  …and {len(peers) - 15} more.")
        return ToolResult(ok=True, content="\n".join(lines), tool_name="etis_connection_geo")
    except Exception as e:
        return ToolResult(ok=False, content=f"[CONN] {e}", tool_name="etis_connection_geo")


@tool(
    "etis_sandbox_execute",
    "Execute code in the secure Docker sandbox. Useful for quick scripting or exploiting testing.",
    {
        "code": "The code to execute",
        "language": "Programming language ('python', 'bash', 'node')",
        "timeout": "Timeout in seconds (default 30)"
    }
)
async def etis_sandbox_execute(ctx, args) -> ToolResult:
    try:
        from core.sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        timeout = int(args.get("timeout", 30))
        result = await executor.execute(code=args["code"], language=args.get("language", "python"), timeout=timeout)
        if not result.success:
            return ToolResult(ok=False, content=f"[SANDBOX] Error:\n{result.error or result.stderr}", tool_name="etis_sandbox_execute")
        return ToolResult(ok=True, content=f"[SANDBOX] Success:\n{result.stdout}", tool_name="etis_sandbox_execute")
    except Exception as e:
        return ToolResult(ok=False, content=f"[SANDBOX] Exception: {e}", tool_name="etis_sandbox_execute")
