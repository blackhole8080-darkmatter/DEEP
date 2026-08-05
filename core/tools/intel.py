"""Public-API intelligence tools, exposed to DEEP's LLM.

The intel layer (``core/intel/``) already backs the HUD's ops terminal and the
``/api/intel/*`` endpoints. These handlers put the same capability in front of
the reasoning brain, so asking DEEP "is 45.33.32.156 malicious?" or "how bad is
CVE-2021-44228 really?" in chat produces an attributed, sourced answer instead
of a recollection from training data — which for threat intel is always stale
and sometimes wrong.

Two things shape how results are returned:

* **Answers stay attributed.** Each finding is rendered with the source that
  produced it, and any source that failed is named. The model can then say
  "Shodan reports these ports, but the KEV catalog was unreachable" rather
  than flattening everything into unsourced prose.
* **Output is compact.** Tool results are re-fed to the model, so a dossier is
  summarised to its verdict, signals and top findings rather than dumped as
  raw JSON, which would eat the context window for no benefit.
"""

from __future__ import annotations

from typing import Any, Dict

from core.domain.models import ToolResult
from core.intel import public_apis
from core.intel.live_stats import shared_live_intel
from core.intel.osint_investigator import Dossier, OSINTInvestigator
from core.tools.registry import tool

_investigator = OSINTInvestigator()

# Findings worth surfacing to the model, in the order an analyst would read
# them. Anything else stays in the structured payload but off the prompt.
_PRIORITY_LABELS = (
    "actively_exploited", "exploit_probability_30d", "cvss", "known_cves",
    "botnet_c2", "attack_reports", "tor_exit_node", "known_breaches",
    "open_ports", "software", "hostnames", "location", "organisation",
    "announcing_asn", "abuse_contact", "known_vulnerabilities", "advisories",
    "a_records", "subdomains_seen", "missing_spf", "vendor",
)


def _render(d: Dossier) -> str:
    """Compact, attributed rendering of a dossier for the model's context."""
    lines = [d.summary]

    ordered = sorted(
        d.findings,
        key=lambda f: _PRIORITY_LABELS.index(f.label)
        if f.label in _PRIORITY_LABELS else len(_PRIORITY_LABELS),
    )
    for f in ordered[:14]:
        value = f.value
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in list(value)[:8])
        elif isinstance(value, dict):
            value = ", ".join(f"{k}={v}" for k, v in list(value.items())[:5])
        lines.append(f"  - {f.label}: {value}   [source: {f.source}]")

    if d.degraded:
        lines.append(
            "  (unreachable this run: " + ", ".join(sorted(d.degraded)) + ")"
        )
    return "\n".join(lines)


@tool(
    "threat_lookup",
    "Look up any security indicator against live public intelligence sources and "
    "return an attributed dossier with a risk verdict. Auto-detects the type — IP, "
    "domain, CVE id, ASN, file hash, MAC, or ecosystem package (pypi:requests). "
    "Use this for ANY question about whether something is malicious, exposed, "
    "vulnerable or suspicious. Always prefer it over answering from memory: CVE, "
    "exploitation and reputation data change daily and training data is stale.",
    {"target": "IP, domain, CVE-YYYY-NNNNN, ASN (AS15169), file hash, MAC, or "
               "ecosystem:package such as pypi:requests"},
)
async def threat_lookup(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    target = str(args.get("target", "")).strip()
    if not target:
        return ToolResult(False, "Missing target.", "threat_lookup")

    dossier = await _investigator.investigate(target)
    if dossier.indicator == "unknown":
        return ToolResult(False, dossier.summary, "threat_lookup")
    return ToolResult(True, _render(dossier), "threat_lookup")


@tool(
    "cve_intel",
    "Get the current, authoritative picture of one CVE: CVSS severity and vector "
    "from NVD, EPSS 30-day exploitation probability from FIRST, whether CISA lists "
    "it as actively exploited in the wild (with its remediation deadline), and "
    "which packages it affects. Use whenever a CVE id comes up — KEV listing and "
    "EPSS matter far more for prioritisation than severity alone.",
    {"cve_id": "e.g. CVE-2021-44228"},
)
async def cve_intel(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    cve_id = str(args.get("cve_id", "")).strip().upper()
    if not cve_id:
        return ToolResult(False, "Missing cve_id.", "cve_intel")

    dossier = await _investigator.investigate(cve_id)
    if dossier.indicator != "cve":
        return ToolResult(
            False, f"'{cve_id}' is not a CVE id (expected CVE-YYYY-NNNNN).", "cve_intel"
        )
    return ToolResult(True, _render(dossier), "cve_intel")


@tool(
    "dependency_audit",
    "Check whether a software package has known security advisories, via OSV.dev. "
    "Covers PyPI, npm, Go, Maven, crates.io, NuGet and RubyGems. Use when asked "
    "whether a dependency is safe, or what a library's known issues are.",
    {"package": "ecosystem:name, e.g. pypi:requests or npm:lodash"},
)
async def dependency_audit(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    package = str(args.get("package", "")).strip()
    if not package:
        return ToolResult(False, "Missing package.", "dependency_audit")

    dossier = await _investigator.investigate(package)
    if dossier.indicator != "package":
        return ToolResult(
            False,
            "Expected ecosystem:name, e.g. pypi:requests or npm:lodash.",
            "dependency_audit",
        )
    return ToolResult(True, _render(dossier), "dependency_audit")


@tool(
    "threat_landscape",
    "Current global threat statistics: how many actively-exploited vulnerabilities "
    "CISA has added recently, which vendors dominate that list, how many botnet "
    "command-and-control servers are live and which malware families run them, and "
    "which intelligence sources are currently reachable. Use for 'what's happening "
    "in security right now' style questions.",
    {},
)
async def threat_landscape(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    stats = await shared_live_intel().cyber_stats()

    lines: list[str] = []
    kev = stats.get("kev", {})
    if kev.get("available"):
        vendors = ", ".join(
            f"{v['vendor']} ({v['count']})" for v in kev.get("top_vendors", [])[:5]
        )
        lines += [
            f"CISA KEV: {kev['total']} actively-exploited CVEs catalogued; "
            f"{kev['added_7d']} added in the last 7 days, {kev['added_30d']} in 30.",
            f"  {kev['ransomware_linked']} are linked to known ransomware campaigns.",
            f"  Most-listed vendors: {vendors}.",
        ]
        recent = kev.get("latest", [])[:5]
        if recent:
            lines.append("  Newest entries:")
            lines += [
                f"    {v['cve']} — {v['vendor']} {v['product']} (added {v['added']}, "
                f"remediate by {v['due']})"
                for v in recent
            ]
    else:
        lines.append("CISA KEV: unavailable this run.")

    botnet = stats.get("botnet", {})
    if botnet.get("available"):
        families = ", ".join(
            f"{f['family']} ({f['count']})" for f in botnet.get("families", [])[:5]
        )
        lines.append(
            f"Botnet C2 (abuse.ch): {botnet['active_c2_servers']} live servers. "
            f"Top families: {families}."
        )
    else:
        lines.append("Botnet C2: unavailable this run.")

    anon = stats.get("anonymity", {})
    if anon.get("available"):
        lines.append(f"Tor: {anon['tor_exit_nodes']} exit nodes currently published.")

    src = stats.get("sources", {})
    lines.append(
        f"Sources: {src.get('available_now')}/{src.get('total')} reachable "
        f"({src.get('keyless')} need no key; "
        f"{src.get('key_configured')}/{src.get('key_required')} keyed ones configured)."
    )
    if stats.get("degraded"):
        lines.append("Degraded: " + ", ".join(sorted(stats["degraded"])) + ".")

    return ToolResult(True, "\n".join(lines), "threat_landscape")


@tool(
    "intel_sources",
    "List the public intelligence APIs DEEP can query, which work without any key, "
    "and which are waiting on an API key the user hasn't configured. Use when asked "
    "what DEEP can look up, or why a lookup came back empty.",
    {"category": "Optional filter: vulnerability, reputation, exposure, network, "
                 "certificate, breach, geo"},
)
async def intel_sources(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    summary = public_apis.summary()
    rows = summary["sources"]

    category = str(args.get("category", "")).strip().lower()
    if category:
        rows = [r for r in rows if r["category"] == category]
        if not rows:
            valid = sorted({s["category"] for s in summary["sources"]})
            return ToolResult(
                False, f"No such category '{category}'. Valid: {', '.join(valid)}.",
                "intel_sources",
            )

    lines = [
        f"{summary['available_now']}/{summary['total']} sources usable right now "
        f"({summary['keyless']} need no key; "
        f"{summary['key_configured']}/{summary['key_required']} keyed ones configured)."
    ]
    for r in rows:
        state = "live" if r["configured"] else f"needs {r['env_var']}"
        lines.append(f"  {r['name']} [{r['category']}] — {state}: {r['description']}")
    return ToolResult(True, "\n".join(lines), "intel_sources")
