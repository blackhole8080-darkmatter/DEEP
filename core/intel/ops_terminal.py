"""The DEEP operations terminal — a command engine for the security console.

This is the keyboard-driven surface of the operations center. An analyst types
``whois 8.8.8.8`` or ``cve CVE-2021-44228`` or ``kev --vendor Microsoft`` and
gets structured output, without leaving the HUD and without a dozen browser
tabs.

Deliberate design choices:

**Every command is read-only.** Nothing here scans, probes, exploits, or sends
a single packet at a third party. The terminal queries public intelligence
sources and DEEP's own already-collected local state. The one command that
touches a host — ``scan`` — is restricted to the operator's own local subnet
and delegates to the existing NetworkScanner, which is the component that
already owns that authorisation boundary. There is no shell escape and no
arbitrary-command path: an unrecognised verb is an error, never something
handed to a shell.

**Structured results, not screen-scraped text.** Each command returns a
:class:`CommandResult` carrying typed rows plus a rendered text block, so the
same output can drive a table, a chart, or a plain terminal line.

**Commands are declared, not hardcoded into a parser.** ``COMMANDS`` is the
single registry; ``help`` reads it, the frontend's autocomplete reads it, and
adding a verb means adding one entry.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.intel import public_apis
from core.intel.live_stats import LiveIntel, shared_live_intel
from core.intel.osint_investigator import Dossier, OSINTInvestigator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CommandResult:
    """Structured output from one terminal command."""

    ok: bool
    command: str
    text: str = ""
    rows: List[Dict[str, Any]] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "command": self.command,
            "text": self.text,
            "rows": self.rows,
            "data": self.data,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Declaration of one terminal verb."""

    name: str
    summary: str
    usage: str
    group: str
    examples: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "usage": self.usage,
            "group": self.group,
            "examples": list(self.examples),
        }


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "help", "List commands, or explain one.", "help [command]", "core",
        ("help", "help investigate"),
    ),
    CommandSpec(
        "investigate",
        "Full OSINT dossier on any indicator — auto-detects type.",
        "investigate <ip|domain|cve|asn|hash|mac|pypi:pkg>",
        "osint",
        ("investigate 1.1.1.1", "investigate example.com", "investigate CVE-2021-44228"),
    ),
    CommandSpec(
        "whois", "Registry and routing ownership for an IP, domain or ASN.",
        "whois <ip|domain|asn>", "osint",
        ("whois 8.8.8.8", "whois AS15169"),
    ),
    CommandSpec(
        "dns", "Resolve DNS records over an encrypted resolver.",
        "dns <domain> [--type A|AAAA|MX|NS|TXT]", "osint",
        ("dns example.com", "dns example.com --type MX"),
    ),
    CommandSpec(
        "subdomains", "Enumerate subdomains from certificate transparency logs.",
        "subdomains <domain>", "osint",
        ("subdomains example.com",),
    ),
    CommandSpec(
        "exposure", "Internet-facing ports, software and known CVEs for an IP.",
        "exposure <ip>", "osint",
        ("exposure 1.1.1.1",),
    ),
    CommandSpec(
        "cve", "Full vulnerability record: CVSS, EPSS, KEV status, affected packages.",
        "cve <CVE-ID>", "vuln",
        ("cve CVE-2021-44228",),
    ),
    CommandSpec(
        "kev", "CISA Known Exploited Vulnerabilities, newest first.",
        "kev [--vendor <name>] [--days <n>] [--limit <n>]", "vuln",
        ("kev", "kev --vendor Microsoft --limit 20", "kev --days 7"),
    ),
    CommandSpec(
        "epss", "Exploit-probability ranking for the next 30 days.",
        "epss [cve] [--limit <n>]", "vuln",
        ("epss", "epss CVE-2021-44228"),
    ),
    CommandSpec(
        "deps", "Check an ecosystem package for known advisories.",
        "deps <ecosystem>:<package>", "vuln",
        ("deps pypi:requests", "deps npm:lodash"),
    ),
    CommandSpec(
        "threatmap", "Live geolocated attacker and C2 nodes.",
        "threatmap [--limit <n>]", "intel",
        ("threatmap", "threatmap --limit 50"),
    ),
    CommandSpec(
        "stats", "Global cyber statistics: KEV velocity, botnets, source health.",
        "stats", "intel",
        ("stats",),
    ),
    CommandSpec(
        "sources", "Show the public-API catalog and which sources are live.",
        "sources [--category <name>]", "intel",
        ("sources", "sources --category vulnerability"),
    ),
    CommandSpec(
        "devices", "Devices DEEP has discovered on the local network.",
        "devices [--unknown]", "local",
        ("devices", "devices --unknown"),
    ),
    CommandSpec(
        "timeline", "Recent local security events, newest first.",
        "timeline [--limit <n>] [--severity <level>]", "local",
        ("timeline", "timeline --severity high"),
    ),
    CommandSpec(
        "scan", "Port/OS scan of one host on your own local subnet.",
        "scan <local-ip>", "local",
        ("scan 192.168.1.42",),
    ),
    CommandSpec(
        "clear", "Clear the terminal buffer.", "clear", "core",
    ),
)

_BY_NAME: Dict[str, CommandSpec] = {c.name: c for c in COMMANDS}


class OpsTerminal:
    """Parses and executes operations-center commands."""

    def __init__(
        self,
        investigator: Optional[OSINTInvestigator] = None,
        live: Optional[LiveIntel] = None,
        services: Any = None,
    ) -> None:
        self._osint = investigator or OSINTInvestigator()
        self._live = live or shared_live_intel()
        # The shared service registry, for commands that read DEEP's own state.
        # Optional so the terminal is usable (and testable) standalone.
        self._services = services

    # ── entry point ──────────────────────────────────────────────────────────

    async def execute(self, line: str) -> CommandResult:
        started = datetime.now(timezone.utc)
        raw = (line or "").strip()
        if not raw:
            return CommandResult(ok=True, command="", text="")

        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            return CommandResult(ok=False, command=raw, error=f"parse error: {exc}")

        verb, args = tokens[0].lower(), tokens[1:]
        spec = _BY_NAME.get(verb)
        if spec is None:
            suggestion = _closest(verb)
            hint = f" Did you mean '{suggestion}'?" if suggestion else ""
            return CommandResult(
                ok=False,
                command=raw,
                error=f"unknown command: {verb}.{hint} Type 'help' for the full list.",
            )

        handler: Callable[[List[str]], Awaitable[CommandResult]] = getattr(self, f"_cmd_{verb}")
        try:
            result = await handler(args)
        except Exception as exc:  # noqa: BLE001 - a bad command must not kill the console
            logger.exception("[ops_terminal] %s failed", verb)
            result = CommandResult(ok=False, command=raw, error=f"{type(exc).__name__}: {exc}")

        result.command = raw
        result.elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return result

    # ── core ─────────────────────────────────────────────────────────────────

    async def _cmd_help(self, args: List[str]) -> CommandResult:
        if args:
            spec = _BY_NAME.get(args[0].lower())
            if spec is None:
                return CommandResult(ok=False, command="help", error=f"no such command: {args[0]}")
            lines = [f"{spec.name} — {spec.summary}", f"  usage: {spec.usage}"]
            if spec.examples:
                lines.append("  examples:")
                lines += [f"    {e}" for e in spec.examples]
            return CommandResult(ok=True, command="help", text="\n".join(lines),
                                 rows=[spec.to_dict()])

        groups: Dict[str, List[CommandSpec]] = {}
        for spec in COMMANDS:
            groups.setdefault(spec.group, []).append(spec)
        order = ["core", "osint", "vuln", "intel", "local"]
        titles = {
            "core": "CORE", "osint": "OSINT & RECON", "vuln": "VULNERABILITY INTELLIGENCE",
            "intel": "GLOBAL INTELLIGENCE", "local": "LOCAL ESTATE",
        }
        lines: List[str] = ["DEEP operations terminal — all commands are read-only.", ""]
        for group in order:
            if group not in groups:
                continue
            lines.append(titles.get(group, group.upper()))
            width = max(len(s.name) for s in groups[group])
            for spec in groups[group]:
                lines.append(f"  {spec.name.ljust(width)}  {spec.summary}")
            lines.append("")
        lines.append("Type 'help <command>' for usage and examples.")
        return CommandResult(ok=True, command="help", text="\n".join(lines),
                             rows=[s.to_dict() for s in COMMANDS])

    async def _cmd_clear(self, args: List[str]) -> CommandResult:
        return CommandResult(ok=True, command="clear", data={"action": "clear"})

    # ── OSINT ────────────────────────────────────────────────────────────────

    async def _cmd_investigate(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("investigate")
        dossier = await self._osint.investigate(args[0])
        return CommandResult(
            ok=dossier.indicator != "unknown",
            command="investigate",
            text=_render_dossier(dossier),
            rows=[f.to_dict() for f in dossier.findings],
            data=dossier.to_dict(),
            error="" if dossier.indicator != "unknown" else dossier.summary,
        )

    async def _cmd_whois(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("whois")
        dossier = await self._osint.investigate(args[0])
        keep = {"netname", "asn_name", "holder", "announcing_asn", "bgp_prefix",
                "abuse_contact", "organisation", "registered", "expires", "status",
                "announced_prefix_count", "location"}
        rows = [f.to_dict() for f in dossier.findings if f.label in keep]
        if not rows:
            return CommandResult(ok=False, command="whois",
                                 error=f"no registry data returned for {args[0]}",
                                 data=dossier.to_dict())
        return CommandResult(ok=True, command="whois", text=_render_rows(rows), rows=rows,
                             data=dossier.to_dict())

    async def _cmd_dns(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("dns")
        domain = args[0]
        flags = _flags(args[1:])
        rtype = (flags.get("type") or "A").upper()
        _, fetch = await self._osint._dns(domain, rtype)  # noqa: SLF001 - same package
        if not fetch.ok:
            return CommandResult(ok=False, command="dns", error=fetch.error)
        answers = [
            {"name": a.get("name"), "type": a.get("type"), "ttl": a.get("TTL"),
             "data": str(a.get("data", "")).strip('"')}
            for a in (fetch.data or {}).get("Answer", []) if isinstance(a, dict)
        ]
        if not answers:
            return CommandResult(ok=True, command="dns",
                                 text=f"No {rtype} records for {domain}.")
        return CommandResult(ok=True, command="dns", rows=answers,
                             text=_render_rows(answers),
                             data={"domain": domain, "type": rtype})

    async def _cmd_subdomains(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("subdomains")
        dossier = await self._osint.investigate(args[0])
        found = next((f for f in dossier.findings if f.label == "subdomains_seen"), None)
        if found is None:
            return CommandResult(ok=False, command="subdomains",
                                 error=f"certificate transparency returned nothing for {args[0]}")
        names = list(found.value)
        return CommandResult(
            ok=True, command="subdomains",
            text=f"{len(names)} distinct names in CT logs for {args[0]}:\n" + "\n".join(
                f"  {n}" for n in names),
            rows=[{"subdomain": n} for n in names],
            data={"domain": args[0], "count": len(names)},
        )

    async def _cmd_exposure(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("exposure")
        target = args[0]
        try:
            ipaddress.ip_address(target)
        except ValueError:
            return CommandResult(ok=False, command="exposure",
                                 error="exposure takes an IP address")
        dossier = await self._osint.investigate(target)
        keep = {"open_ports", "hostnames", "software", "known_cves"}
        rows = [f.to_dict() for f in dossier.findings if f.label in keep]
        if not rows:
            return CommandResult(ok=True, command="exposure",
                                 text=f"No internet-facing exposure recorded for {target}.",
                                 data=dossier.to_dict())
        return CommandResult(ok=True, command="exposure", rows=rows,
                             text=_render_rows(rows), data=dossier.to_dict())

    # ── vulnerability ────────────────────────────────────────────────────────

    async def _cmd_cve(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("cve")
        dossier = await self._osint.investigate(args[0].upper())
        if dossier.indicator != "cve":
            return CommandResult(ok=False, command="cve",
                                 error=f"'{args[0]}' is not a CVE id (expected CVE-YYYY-NNNNN)")
        return CommandResult(ok=True, command="cve", text=_render_dossier(dossier),
                             rows=[f.to_dict() for f in dossier.findings],
                             data=dossier.to_dict())

    async def _cmd_kev(self, args: List[str]) -> CommandResult:
        flags = _flags(args)
        stats = await self._live.cyber_stats()
        kev = stats.get("kev", {})
        if not kev.get("available"):
            return CommandResult(ok=False, command="kev",
                                 error=stats.get("degraded", {}).get("cisa_kev", "KEV unavailable"))
        rows = kev.get("latest", [])
        vendor = flags.get("vendor")
        if vendor:
            rows = [r for r in rows if vendor.lower() in str(r.get("vendor", "")).lower()]
        limit = _int_flag(flags, "limit", 15)
        rows = rows[:limit]
        header = (
            f"CISA KEV — {kev['total']} total, "
            f"{kev['added_7d']} added in 7d, {kev['added_30d']} in 30d, "
            f"{kev['ransomware_linked']} ransomware-linked."
        )
        return CommandResult(ok=True, command="kev",
                             text=header + "\n" + _render_rows(rows), rows=rows,
                             data={"summary": {k: v for k, v in kev.items() if k != "latest"}})

    async def _cmd_epss(self, args: List[str]) -> CommandResult:
        positional = [a for a in args if not a.startswith("--")]
        if positional:
            dossier = await self._osint.investigate(positional[0].upper())
            found = next((f for f in dossier.findings
                          if f.label == "exploit_probability_30d"), None)
            if found is None:
                return CommandResult(ok=False, command="epss",
                                     error=f"no EPSS score published for {positional[0]}")
            value = found.value
            return CommandResult(
                ok=True, command="epss",
                text=(f"{positional[0].upper()} — {value['score'] * 100:.2f}% chance of "
                      f"exploitation in 30 days (percentile {value['percentile'] * 100:.1f})"),
                rows=[{"cve": positional[0].upper(), **value}],
            )

        stats = await self._live.cyber_stats()
        epss = stats.get("epss", {})
        if not epss.get("available"):
            return CommandResult(ok=False, command="epss",
                                 error=stats.get("degraded", {}).get("epss", "EPSS unavailable"))
        limit = _int_flag(_flags(args), "limit", 20)
        rows = [
            {"cve": r["cve"], "probability_pct": round(r["probability"] * 100, 2),
             "percentile": round(r["percentile"] * 100, 1)}
            for r in epss.get("highest_risk", [])[:limit]
        ]
        return CommandResult(ok=True, command="epss",
                             text="Highest 30-day exploitation probability:\n" + _render_rows(rows),
                             rows=rows)

    async def _cmd_deps(self, args: List[str]) -> CommandResult:
        if not args:
            return _usage("deps")
        dossier = await self._osint.investigate(args[0])
        if dossier.indicator != "package":
            return CommandResult(
                ok=False, command="deps",
                error="expected <ecosystem>:<package>, e.g. pypi:requests or npm:lodash",
            )
        advisories = next((f for f in dossier.findings if f.label == "advisories"), None)
        count = next((f for f in dossier.findings if f.label == "known_vulnerabilities"), None)
        if advisories is None:
            return CommandResult(ok=True, command="deps",
                                 text=f"{args[0]}: no known advisories.",
                                 data=dossier.to_dict())
        rows = list(advisories.value)
        return CommandResult(
            ok=True, command="deps",
            text=f"{args[0]}: {count.value if count else len(rows)} advisories\n" + _render_rows(rows),
            rows=rows, data=dossier.to_dict(),
        )

    # ── global intelligence ──────────────────────────────────────────────────

    async def _cmd_threatmap(self, args: List[str]) -> CommandResult:
        limit = _int_flag(_flags(args), "limit", 120)
        result = await self._live.threat_map(limit=limit)
        rows = [
            {"ip": n["ip"], "classification": n["classification"], "country": n["country"],
             "org": n["org"], "source": n["source"]}
            for n in result["nodes"][:40]
        ]
        text = (
            f"{result['count']} geolocated nodes across "
            f"{len(result['by_country'])} countries.\n" + _render_rows(rows)
        )
        return CommandResult(ok=True, command="threatmap", text=text, rows=rows, data=result)

    async def _cmd_stats(self, args: List[str]) -> CommandResult:
        stats = await self._live.cyber_stats()
        lines: List[str] = []
        kev = stats.get("kev", {})
        if kev.get("available"):
            lines += [
                "CISA KEV",
                f"  catalog            {kev['total']} entries (v{kev['catalog_version']})",
                f"  added 7d / 30d     {kev['added_7d']} / {kev['added_30d']}",
                f"  remediation overdue {kev['remediation_overdue']}",
                f"  ransomware-linked  {kev['ransomware_linked']}",
            ]
        botnet = stats.get("botnet", {})
        if botnet.get("available"):
            families = ", ".join(f"{f['family']}({f['count']})" for f in botnet["families"][:5])
            lines += ["", "BOTNET C2 (abuse.ch)",
                      f"  active servers     {botnet['active_c2_servers']}",
                      f"  top families       {families}"]
        anon = stats.get("anonymity", {})
        if anon.get("available"):
            lines += ["", "ANONYMITY", f"  tor exit nodes     {anon['tor_exit_nodes']}"]
        src = stats.get("sources", {})
        lines += ["", "SOURCES",
                  f"  available now      {src.get('available_now')}/{src.get('total')}",
                  f"  keyless            {src.get('keyless')}",
                  f"  key configured     {src.get('key_configured')}/{src.get('key_required')}"]
        if stats.get("degraded"):
            lines += ["", "DEGRADED"]
            lines += [f"  {k:<18} {v}" for k, v in sorted(stats["degraded"].items())]
        return CommandResult(ok=True, command="stats", text="\n".join(lines), data=stats)

    async def _cmd_sources(self, args: List[str]) -> CommandResult:
        flags = _flags(args)
        summary = public_apis.summary()
        rows = summary["sources"]
        category = flags.get("category")
        if category:
            rows = [r for r in rows if r["category"] == category.lower()]
        display = [
            {"id": r["id"], "name": r["name"], "category": r["category"],
             "auth": r["auth"], "status": "live" if r["configured"] else f"needs {r['env_var']}"}
            for r in rows
        ]
        header = (
            f"{summary['available_now']}/{summary['total']} sources available "
            f"({summary['keyless']} keyless, "
            f"{summary['key_configured']}/{summary['key_required']} keyed sources configured)"
        )
        return CommandResult(ok=True, command="sources",
                             text=header + "\n" + _render_rows(display),
                             rows=display, data=summary)

    # ── local estate ─────────────────────────────────────────────────────────

    async def _cmd_devices(self, args: List[str]) -> CommandResult:
        scanner = getattr(self._services, "scanner", None) if self._services else None
        if scanner is None or not hasattr(scanner, "get_devices"):
            return CommandResult(ok=False, command="devices",
                                 error="network scanner not available in this context")
        # NetworkScanner.get_devices is async and yields NetworkDevice dataclasses,
        # not dicts — calling it synchronously returned a coroutine, and .get()
        # on a dataclass would have raised.
        devices = await scanner.get_devices()
        if "--unknown" in args:
            devices = [d for d in devices if not getattr(d, "is_known", False)]
        rows = [
            {"ip": d.ip, "mac": d.mac, "vendor": d.vendor, "hostname": d.hostname,
             "known": d.is_known, "ports": d.open_ports, "os": d.os_guess,
             "last_seen": d.last_seen}
            for d in devices
        ]
        if not rows:
            return CommandResult(
                ok=True, command="devices",
                text="No devices in the registry yet — the scanner may still be warming up.")
        return CommandResult(ok=True, command="devices",
                             text=f"{len(rows)} devices\n" + _render_rows(rows), rows=rows)

    async def _cmd_timeline(self, args: List[str]) -> CommandResult:
        timeline = getattr(self._services, "security_timeline", None) if self._services else None
        if timeline is None:
            return CommandResult(ok=False, command="timeline",
                                 error="security timeline not available in this context")
        flags = _flags(args)
        events = timeline.get_timeline(
            limit=_int_flag(flags, "limit", 25),
            min_severity=flags.get("severity"),
        )
        if not events:
            return CommandResult(ok=True, command="timeline", text="No security events recorded.")
        rows = [
            {"time": e.get("timestamp"), "severity": e.get("severity"),
             "kind": e.get("kind") or e.get("type"), "summary": e.get("summary") or e.get("message")}
            for e in events
        ]
        return CommandResult(ok=True, command="timeline",
                             text=_render_rows(rows), rows=rows)

    async def _cmd_scan(self, args: List[str]) -> CommandResult:
        """Active scan — the only command that emits packets, and only locally."""
        if not args:
            return _usage("scan")
        target = args[0]
        try:
            addr = ipaddress.ip_address(target)
        except ValueError:
            return CommandResult(ok=False, command="scan", error="scan takes an IP address")
        if not (addr.is_private or addr.is_loopback):
            return CommandResult(
                ok=False, command="scan",
                error=(
                    f"refusing to scan {target}: active scanning is restricted to your own "
                    "local subnet. Use 'exposure' for passive internet-exposure data on a "
                    "public address."
                ),
            )
        scanner = getattr(self._services, "scanner", None) if self._services else None
        # The real method is scan_target(); there is no deep_scan_device, so the
        # old hasattr guard was always False and scan could never run.
        if scanner is None or not hasattr(scanner, "scan_target"):
            return CommandResult(ok=False, command="scan",
                                 error="network scanner not available in this context")
        device = await scanner.scan_target(target)
        if device is None:
            return CommandResult(ok=True, command="scan",
                                 text=f"{target} did not respond to the scan.")
        row = {
            "ip": device.ip, "mac": device.mac, "hostname": device.hostname,
            "vendor": device.vendor, "os": device.os_guess,
            "open_ports": device.open_ports, "known": device.is_known,
            "last_seen": device.last_seen,
        }
        return CommandResult(ok=True, command="scan", rows=[row],
                             text=_render_rows([row]), data=row)


# ── rendering helpers ────────────────────────────────────────────────────────


def _closest(verb: str) -> Optional[str]:
    """Nearest known command name, for 'did you mean' on a typo."""
    import difflib

    matches = difflib.get_close_matches(verb, list(_BY_NAME), n=1, cutoff=0.6)
    return matches[0] if matches else None


def _usage(name: str) -> CommandResult:
    spec = _BY_NAME[name]
    return CommandResult(ok=False, command=name, error=f"usage: {spec.usage}")


def _flags(args: List[str]) -> Dict[str, str]:
    """Parse ``--key value`` and bare ``--flag`` pairs."""
    out: Dict[str, str] = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token.startswith("--"):
            key = token[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                out[key] = args[i + 1]
                i += 2
                continue
            out[key] = "true"
        i += 1
    return out


def _int_flag(flags: Dict[str, str], key: str, default: int) -> int:
    try:
        return max(1, int(flags[key]))
    except (KeyError, TypeError, ValueError):
        return default


def _render_rows(rows: List[Dict[str, Any]]) -> str:
    """Fixed-width table, so terminal output lines up without a UI table."""
    if not rows:
        return "(no results)"
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    widths = {
        c: min(48, max(len(c), max((len(_cell(r.get(c))) for r in rows), default=0)))
        for c in columns
    }
    header = "  ".join(c.upper().ljust(widths[c]) for c in columns)
    sep = "  ".join("─" * widths[c] for c in columns)
    body = [
        "  ".join(_cell(r.get(c))[: widths[c]].ljust(widths[c]) for c in columns)
        for r in rows
    ]
    return "\n".join([header, sep, *body])


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value[:6]) + ("…" if len(value) > 6 else "")
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in list(value.items())[:4])
    return str(value)


def _render_dossier(d: Dossier) -> str:
    lines = [d.summary, ""]
    if d.geo:
        lines.append(
            f"  location   {d.geo.get('city') or '?'}, {d.geo.get('country') or '?'} "
            f"({d.geo.get('org') or 'unknown org'})"
        )
    if d.findings:
        width = max(len(f.label) for f in d.findings)
        for f in d.findings:
            marker = {"critical": "!!", "high": " !", "medium": " ·"}.get(f.severity, "  ")
            lines.append(f"{marker} {f.label.ljust(width)}  {_cell(f.value)}   [{f.source}]")
    if d.degraded:
        lines += ["", "  unreachable: " + ", ".join(f"{k} ({v})" for k, v in d.degraded.items())]
    return "\n".join(lines)


def command_catalog() -> List[Dict[str, Any]]:
    """The command list, for `/api/intel/terminal/commands` and UI autocomplete."""
    return [c.to_dict() for c in COMMANDS]
