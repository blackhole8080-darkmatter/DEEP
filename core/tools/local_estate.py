"""Tools that let DEEP's reasoning brain read its *own* observations.

DEEP already had good reach into public threat intelligence (see
``core/tools/intel.py``) but none at all into what it had actually seen on the
network it watches. Asking "has anything odd happened here today?" could not be
answered, despite a correlated, severity-scored timeline sitting in memory.

These handlers close that gap. Together with the intel tools they compound:
the model can take a device that started beaconing at 03:00 (``security_events``
/ ``anomalies``), resolve where it was talking to (``threat_lookup``), and check
whether the CVE it is probably exploiting is in CISA's actively-exploited
catalogue (``cve_intel``) — a chain no single tool supports.

**Everything here is read-only.** These report what DEEP already collected
passively; none of them scans, probes or changes state. Acting on a finding
stays with the existing action tools (``trust_device``, ``block_device``,
``network_scan``), which is where that authorisation boundary already lives.

**Subsystems are reached through ``ctx.estate``**, the shared service registry
attached by ``interface/server.py``. Each is optional: DEEP runs with Pi-hole,
Bluetooth and nmap all absent, so every handler reports the subsystem as
unavailable rather than raising. Saying "the DNS sinkhole isn't configured" is
useful to the model; an AttributeError is not.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.domain.models import ToolResult
from core.tools.registry import tool


def _subsystem(ctx: Any, name: str) -> Optional[Any]:
    """Fetch a wired subsystem, or None when it isn't running in this context."""
    estate = getattr(ctx, "estate", None)
    if estate is None:
        return None
    return getattr(estate, name, None)


def _unavailable(name: str, tool_name: str, hint: str = "") -> ToolResult:
    detail = f" {hint}" if hint else ""
    return ToolResult(
        False, f"The {name} subsystem isn't available in this session.{detail}", tool_name
    )


def _lines(header: str, rows: List[str], empty: str) -> str:
    if not rows:
        return empty
    return "\n".join([header, *rows])


# ═══════════════════════════════════════════════════════════════════════════
# What DEEP has seen
# ═══════════════════════════════════════════════════════════════════════════


@tool(
    "security_events",
    "Recent security events DEEP has observed on this network, newest first — "
    "the correlated timeline of device alerts, anomalies and classified threats, "
    "each with severity and any matched MITRE ATT&CK techniques or CVEs. Use this "
    "for ANY question about what has happened here: 'anything odd today?', 'what "
    "triggered that alert?', 'has this device done this before?'. This is DEEP's "
    "own record of the local estate, not public threat intelligence.",
    {"limit": "How many events to return (default 20)",
     "severity": "Optional floor: info, low, medium, high or critical"},
)
async def security_events(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    timeline = _subsystem(ctx, "security_timeline")
    if timeline is None:
        return _unavailable("security timeline", "security_events")

    try:
        limit = max(1, int(args.get("limit", 20)))
    except (TypeError, ValueError):
        limit = 20
    severity = (args.get("severity") or "").strip().lower() or None

    events = timeline.get_timeline(limit=limit, min_severity=severity)
    if not events:
        scope = f" at severity >= {severity}" if severity else ""
        return ToolResult(
            True, f"No security events recorded{scope}. The estate has been quiet.",
            "security_events",
        )

    rows = []
    for e in events:
        bits = [
            f"  [{str(e.get('severity', '?')).upper()}] {e.get('timestamp', '?')}",
            f"{e.get('kind', 'event')}: {e.get('summary', '')}",
        ]
        if e.get("device_ip") or e.get("device_mac"):
            bits.append(f"(device {e.get('device_ip') or e.get('device_mac')})")
        if e.get("techniques"):
            bits.append(f"ATT&CK: {', '.join(str(t) for t in e['techniques'][:4])}")
        if e.get("related_cves"):
            bits.append(f"CVEs: {', '.join(str(c) for c in e['related_cves'][:4])}")
        rows.append(" ".join(bits))

    stats = {}
    try:
        stats = timeline.get_stats() or {}
    except Exception:  # noqa: BLE001 - stats are a nicety, never worth failing on
        pass
    header = f"{len(events)} security event(s), newest first."
    if stats:
        header += f" Totals: {stats}"
    return ToolResult(True, _lines(header, rows, "No events."), "security_events")


@tool(
    "anomalies",
    "Statistical anomalies DEEP's baseline models have flagged — metrics that "
    "deviated from what is normal FOR THIS MACHINE and network, with the observed "
    "value, the expected range and how many standard deviations out it was. Use "
    "when asked whether behaviour is unusual, or to explain why something was "
    "flagged. Note these are deviations from a learned baseline, not proof of "
    "compromise: a legitimate backup job looks anomalous too.",
    {"hours": "Look-back window in hours (default 24)"},
)
async def anomalies(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    detector = _subsystem(ctx, "anomaly_detector")
    if detector is None:
        return _unavailable("anomaly detector", "anomalies")

    try:
        hours = max(1, int(args.get("hours", 24)))
    except (TypeError, ValueError):
        hours = 24

    found = await detector.get_recent_anomalies(hours=hours)
    if not found:
        return ToolResult(
            True,
            f"No anomalies in the last {hours}h — system and network metrics have "
            "stayed within their learned baselines.",
            "anomalies",
        )

    rows = [
        f"  [{a.severity.upper()}] {a.timestamp} {a.anomaly_type}/{a.metric}: "
        f"observed {a.current_value:.2f}, expected ~{a.expected_mean:.2f} "
        f"(±{a.expected_std:.2f}), z={a.z_score:.1f}"
        for a in found
    ]
    stats = await detector.get_anomaly_stats()
    return ToolResult(
        True,
        _lines(f"{len(found)} anomal(ies) in the last {hours}h. Stats: {stats}",
               rows, "None."),
        "anomalies",
    )


@tool(
    "threat_predictions",
    "Recent verdicts from DEEP's trained threat classifier — the neural net that "
    "labels observed network behaviour by attack class with a confidence score. "
    "Use to see what the model currently believes about activity here. Treat "
    "confidence honestly: a low-confidence prediction is a hint to investigate, "
    "not a finding.",
    {"count": "How many recent predictions to return (default 15)"},
)
async def threat_predictions(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    classifier = _subsystem(ctx, "threat_classifier")
    if classifier is None:
        return _unavailable("threat classifier", "threat_predictions")

    try:
        count = max(1, int(args.get("count", 15)))
    except (TypeError, ValueError):
        count = 15

    predictions = await classifier.get_recent_predictions(n=count)
    status = classifier.status()
    if not predictions:
        return ToolResult(
            True,
            "No classifications recorded yet. The model may still be gathering "
            f"training data — classifier status: {status}",
            "threat_predictions",
        )

    rows = [
        "  " + ", ".join(f"{k}={v}" for k, v in p.items() if v not in (None, ""))
        for p in predictions
    ]
    return ToolResult(
        True, _lines(f"{len(predictions)} recent prediction(s). Model: {status}", rows, "None."),
        "threat_predictions",
    )


# ═══════════════════════════════════════════════════════════════════════════
# What is on the network
# ═══════════════════════════════════════════════════════════════════════════


@tool(
    "local_devices",
    "Devices DEEP has discovered on the local network — IP, MAC, resolved vendor, "
    "hostname, open ports, OS guess, and whether the device is on the known/trusted "
    "list. Use for 'what's on my network', 'is there anything I don't recognise', or "
    "to resolve an IP seen in an alert to an actual device. Discovery is passive; "
    "this reports what has already been seen rather than scanning now.",
    {"unknown_only": "Set true to list only devices not marked as known/trusted"},
)
async def local_devices(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    scanner = _subsystem(ctx, "scanner")
    if scanner is None:
        return _unavailable("network scanner", "local_devices")

    devices = await scanner.get_devices()
    unknown_only = str(args.get("unknown_only", "")).strip().lower() in {"1", "true", "yes", "on"}
    if unknown_only:
        devices = [d for d in devices if not getattr(d, "is_known", False)]

    if not devices:
        return ToolResult(
            True,
            "No devices in the registry yet."
            + (" (Filtered to unknown devices only.)" if unknown_only else "")
            + " The scanner may still be warming up, or nmap may not be installed.",
            "local_devices",
        )

    rows = []
    for d in devices:
        bits = [f"  {d.ip:<15} {(d.mac or '--'):<18} {(d.vendor or 'unknown vendor')}"]
        if d.hostname:
            bits.append(f"host={d.hostname}")
        if d.open_ports:
            bits.append(f"ports={','.join(str(p) for p in d.open_ports[:8])}")
        if d.os_guess:
            bits.append(f"os={d.os_guess}")
        bits.append("KNOWN" if d.is_known else "UNKNOWN")
        rows.append(" ".join(bits))

    scope = "unknown device(s)" if unknown_only else "device(s) seen on the local network"
    return ToolResult(True, _lines(f"{len(devices)} {scope}:", rows, "None."), "local_devices")


@tool(
    "wifi_environment",
    "Wireless access points DEEP can see nearby, plus the evil-twin detector's "
    "current state. An evil twin is a rogue AP impersonating a network you trust to "
    "capture traffic; the detector watches for a known SSID appearing on an "
    "unexpected BSSID. Use when asked about nearby WiFi, rogue access points, or "
    "whether it is safe to connect here.",
    {},
)
async def wifi_environment(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    proximity = _subsystem(ctx, "proximity")
    evil_twin = _subsystem(ctx, "evil_twin")
    if proximity is None and evil_twin is None:
        return _unavailable(
            "wireless monitoring", "wifi_environment",
            "It needs a WiFi interface capable of scanning.",
        )

    sections: List[str] = []
    if evil_twin is not None:
        sections.append(f"Evil-twin detector: {evil_twin.status()}")

    if proximity is not None:
        aps = await proximity.get_nearby_aps()
        if aps:
            rows = [
                f"  {(ap.ssid or '<hidden>'):<28} {ap.bssid}  {ap.signal_dbm} dBm  "
                f"ch{ap.channel} {ap.encryption or 'open'}"
                + (f"  [{ap.vendor}]" if ap.vendor else "")
                + ("  YOURS" if ap.is_yours else "")
                for ap in aps
            ]
            sections.append(_lines(f"{len(aps)} nearby access point(s):", rows, ""))
        else:
            sections.append("No nearby access points recorded (no scan yet, or no WiFi adapter).")

    return ToolResult(True, "\n\n".join(sections), "wifi_environment")


@tool(
    "dns_activity",
    "DNS query activity and blocking from the Pi-hole sinkhole: totals, the most "
    "requested domains, and per-client history. DNS is often the earliest visible "
    "sign of a compromise — malware resolves its command-and-control domain before "
    "any payload moves. Use when asked what a device has been contacting, or to "
    "investigate suspicious outbound behaviour.",
    {"client_ip": "Optional: show the query history for one client IP instead of the summary"},
)
async def dns_activity(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    pihole = _subsystem(ctx, "pihole")
    if pihole is None:
        return _unavailable(
            "Pi-hole", "dns_activity", "Set PIHOLE_URL and PIHOLE_API_TOKEN to enable it."
        )

    client_ip = (args.get("client_ip") or "").strip()
    if client_ip:
        queries = await pihole.get_client_activity(client_ip)
        if not queries:
            return ToolResult(True, f"No recorded DNS queries from {client_ip}.", "dns_activity")
        rows = ["  " + ", ".join(f"{k}={v}" for k, v in q.items()) for q in queries[:40]]
        return ToolResult(
            True, _lines(f"{len(queries)} DNS quer(ies) from {client_ip}:", rows, ""), "dns_activity"
        )

    summary = await pihole.get_summary()
    if summary is None:
        return ToolResult(
            False, "Pi-hole is configured but did not respond — check PIHOLE_URL and the token.",
            "dns_activity",
        )
    sections = [f"Pi-hole summary: {summary}"]
    top = await pihole.get_top_domains()
    if top:
        sections.append(f"Top domains: {top}")
    return ToolResult(True, "\n".join(sections), "dns_activity")


# ═══════════════════════════════════════════════════════════════════════════
# Where the two halves meet
# ═══════════════════════════════════════════════════════════════════════════


@tool(
    "stack_exposure",
    "Cross-reference live threat intelligence against the technologies DEEP knows "
    "the user actually works with, from its knowledge graph. Answers 'does any of "
    "this affect ME?' — a newly-exploited CVE only matters if it hits something in "
    "your own stack. Returns matches with the entity that matched and why. An empty "
    "result is meaningful: nothing in the current feeds touches your known stack.",
    {},
)
async def stack_exposure(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    watch = _subsystem(ctx, "global_threat_watch")
    if watch is None:
        return _unavailable("global threat watch", "stack_exposure")

    matches = await watch.run_once()
    if not matches:
        return ToolResult(
            True,
            "No current threat-intel items match the technologies in DEEP's knowledge "
            "graph. Either nothing in the live feeds touches your stack, or the graph "
            "has not learned enough about what you work with yet.",
            "stack_exposure",
        )

    rows = ["  " + ", ".join(f"{k}={v}" for k, v in m.items() if v not in (None, "")) for m in matches]
    return ToolResult(
        True,
        _lines(f"{len(matches)} threat-intel item(s) matching your known stack:", rows, ""),
        "stack_exposure",
    )


@tool(
    "exploit_search",
    "Find published proof-of-concept exploit code for a CVE, via Exploit-DB and "
    "GitHub. Availability of a public exploit sharply raises real-world risk and is "
    "a strong prioritisation signal alongside CVSS and EPSS. Use when asked how "
    "serious or how exploitable a vulnerability is. Returns references and metadata "
    "for assessment — DEEP does not run exploit code.",
    {"cve_id": "e.g. CVE-2021-44228", "keyword": "Alternative to cve_id: free-text search"},
)
async def exploit_search(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    from domains.cybersec.exploit_lookup import ExploitLookup

    cve_id = (args.get("cve_id") or "").strip().upper()
    keyword = (args.get("keyword") or "").strip()
    if not cve_id and not keyword:
        return ToolResult(False, "Provide either cve_id or keyword.", "exploit_search")

    lookup = ExploitLookup()
    entries = await (lookup.search_by_cve(cve_id) if cve_id else lookup.search_by_keyword(keyword))
    target = cve_id or f"'{keyword}'"
    if not entries:
        return ToolResult(
            True,
            f"No public exploit code found for {target}. That is not proof none exists — "
            "it means these sources have nothing indexed.",
            "exploit_search",
        )

    rows = [
        f"  [{e.source}] {e.id} — {e.title} ({e.platform}/{e.language}, {e.date})"
        + ("  VERIFIED" if e.verified else "")
        + f"  {e.url}"
        for e in entries[:15]
    ]
    return ToolResult(
        True, _lines(f"{len(entries)} public exploit reference(s) for {target}:", rows, ""),
        "exploit_search",
    )
