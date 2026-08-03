"""Unified OSINT pivot engine.

Give it an indicator — an IP, a domain, a CVE, an ASN, a package, a MAC — and
it works out what the indicator is, fans out across every catalogued source
that can say something about it, and returns one normalised dossier with a
verdict.

The design goal is that an operator types one thing and gets the answer they
would otherwise assemble by hand from six browser tabs. Concretely:

* **Type inference, not type selection.** ``8.8.8.8``, ``CVE-2021-44228``,
  ``AS15169`` and ``pypi:requests`` all go into the same box.
* **Parallel fan-out, partial results.** Sources are queried concurrently and
  independently. One timing out never blocks or fails the dossier; it lands in
  ``degraded`` and the rest of the report still renders.
* **Findings carry their source.** Every fact is attributed to the API that
  said it, so a verdict can be audited rather than trusted.
* **The verdict is derived, not invented.** Risk is computed from the signals
  actually collected, and ``confidence`` reflects how many sources answered.
  When nothing answers, the verdict is ``unknown`` — never a fabricated score.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.intel import public_apis
from core.intel.http import Fetch, IntelHTTP, shared_http
from core.intel.public_apis import Indicator

logger = logging.getLogger(__name__)

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)
_ASN_RE = re.compile(r"^AS(\d{1,10})$", re.I)
_MAC_RE = re.compile(r"^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$", re.I)
_HASH_LENGTHS = {32: "md5", 40: "sha1", 64: "sha256"}
_HASH_RE = re.compile(r"^[0-9a-f]+$", re.I)
_PACKAGE_RE = re.compile(r"^(pypi|npm|go|maven|crates\.io|nuget|rubygems):(.+)$", re.I)
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$", re.I
)

# Risk weights. Kept as one visible table rather than scattered through the
# collectors so the scoring is auditable in a single place.
_RISK_SIGNALS: Dict[str, int] = {
    "kev_listed": 45,
    "botnet_c2": 45,
    "high_epss": 30,
    "attack_reports": 25,
    "known_vulns": 25,
    "tor_exit": 15,
    "critical_severity": 20,
    "high_severity": 12,
    "many_open_ports": 10,
    "breached_domain": 15,
}


@dataclass(slots=True)
class Finding:
    """One attributed fact about the target."""

    source: str
    label: str
    value: Any
    severity: str = "info"  # info | low | medium | high | critical

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Dossier:
    """The full result of an investigation."""

    target: str
    indicator: str
    risk: str = "unknown"
    risk_score: int = 0
    confidence: float = 0.0
    summary: str = ""
    findings: List[Finding] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    sources_queried: List[str] = field(default_factory=list)
    sources_answered: List[str] = field(default_factory=list)
    degraded: Dict[str, str] = field(default_factory=dict)
    geo: Optional[Dict[str, Any]] = None
    elapsed_ms: int = 0
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d


class OSINTInvestigator:
    """Fans one indicator out across the public-API catalog."""

    def __init__(self, http: Optional[IntelHTTP] = None) -> None:
        self._http = http or shared_http()

    # ── entry point ──────────────────────────────────────────────────────────

    @staticmethod
    def classify(target: str) -> Optional[Indicator]:
        """Infer what kind of indicator ``target`` is, or None if unrecognised."""
        t = (target or "").strip()
        if not t:
            return None
        if _CVE_RE.match(t):
            return Indicator.CVE
        if _ASN_RE.match(t):
            return Indicator.ASN
        if _MAC_RE.match(t):
            return Indicator.MAC
        if _PACKAGE_RE.match(t):
            return Indicator.PACKAGE
        try:
            ipaddress.ip_address(t)
            return Indicator.IP
        except ValueError:
            pass
        if len(t) in _HASH_LENGTHS and _HASH_RE.match(t):
            return Indicator.HASH
        if _DOMAIN_RE.match(t):
            return Indicator.DOMAIN
        return None

    async def investigate(self, target: str) -> Dossier:
        """Build a dossier for ``target``, whatever kind of indicator it is."""
        started = asyncio.get_event_loop().time()
        target = (target or "").strip()
        kind = self.classify(target)

        if kind is None:
            return Dossier(
                target=target,
                indicator="unknown",
                summary=(
                    "Unrecognised indicator. Expected an IP, domain, CVE id "
                    "(CVE-2021-44228), ASN (AS15169), file hash, MAC address, or "
                    "ecosystem package (pypi:requests)."
                ),
                generated_at=_now(),
            )

        dossier = Dossier(target=target, indicator=kind.value, generated_at=_now())

        collectors = {
            Indicator.IP: self._collect_ip,
            Indicator.DOMAIN: self._collect_domain,
            Indicator.CVE: self._collect_cve,
            Indicator.ASN: self._collect_asn,
            Indicator.PACKAGE: self._collect_package,
            Indicator.MAC: self._collect_mac,
            Indicator.HASH: self._collect_hash,
        }
        await collectors[kind](target, dossier)

        self._score(dossier)
        dossier.elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000)
        return dossier

    # ── collectors ───────────────────────────────────────────────────────────

    async def _collect_ip(self, ip: str, d: Dossier) -> None:
        addr = ipaddress.ip_address(ip)
        # Covers RFC1918, loopback, link-local and the IANA special-purpose
        # ranges (documentation, benchmarking, …) — none of them are routable,
        # so no public source has anything to say about them.
        if not addr.is_global:
            d.findings.append(
                Finding("local", "scope", "Not globally routable (private, loopback or reserved)")
            )
            d.summary = (
                f"{ip} is a private or reserved address. Public intelligence sources have "
                "nothing to say about it; use the local network view instead."
            )
            d.risk = "n/a"
            return

        tasks = {
            "shodan_internetdb": self._fetch("shodan_internetdb", f"https://internetdb.shodan.io/{ip}"),
            "ipapi_co": self._fetch("ipapi_co", f"https://ipapi.co/{ip}/json/"),
            "ripestat": self._fetch(
                "ripestat", f"https://stat.ripe.net/data/network-info/data.json?resource={ip}"
            ),
            "rdap": self._fetch("rdap", f"https://rdap.org/ip/{ip}"),
            "sans_isc": self._fetch("sans_isc", f"https://isc.sans.edu/api/ip/{ip}?json"),
            "tor_exits": self._fetch_text("tor_exits", "https://check.torproject.org/torbulkexitlist"),
            "feodo": self._fetch("feodo", "https://feodotracker.abuse.ch/downloads/ipblocklist.json"),
        }
        results = await self._gather(tasks, d)

        exposure = results.get("shodan_internetdb")
        if isinstance(exposure, dict):
            ports = exposure.get("ports") or []
            vulns = exposure.get("vulns") or []
            hostnames = exposure.get("hostnames") or []
            cpes = exposure.get("cpes") or []
            if ports:
                d.findings.append(
                    Finding("shodan_internetdb", "open_ports", ports,
                            "medium" if len(ports) > 5 else "info")
                )
                if len(ports) > 5:
                    d.signals.append("many_open_ports")
            if hostnames:
                d.findings.append(Finding("shodan_internetdb", "hostnames", hostnames))
            if cpes:
                d.findings.append(Finding("shodan_internetdb", "software", cpes))
            if vulns:
                d.findings.append(Finding("shodan_internetdb", "known_cves", vulns, "high"))
                d.signals.append("known_vulns")

        geo = results.get("ipapi_co")
        if isinstance(geo, dict) and not geo.get("error"):
            d.geo = {
                "lat": geo.get("latitude"),
                "lon": geo.get("longitude"),
                "city": geo.get("city"),
                "region": geo.get("region"),
                "country": geo.get("country_name"),
                "country_code": geo.get("country_code"),
                "org": geo.get("org"),
                "asn": geo.get("asn"),
            }
            d.findings.append(
                Finding("ipapi_co", "location",
                        f"{geo.get('city') or '?'}, {geo.get('country_name') or '?'}")
            )
            if geo.get("org"):
                d.findings.append(Finding("ipapi_co", "organisation", geo["org"]))

        routing = results.get("ripestat")
        if isinstance(routing, dict):
            data = routing.get("data") or {}
            asns = data.get("asns") or []
            prefix = data.get("prefix")
            if asns:
                d.findings.append(Finding("ripestat", "announcing_asn", [f"AS{a}" for a in asns]))
            if prefix:
                d.findings.append(Finding("ripestat", "bgp_prefix", prefix))

        rdap = results.get("rdap")
        if isinstance(rdap, dict):
            if rdap.get("name"):
                d.findings.append(Finding("rdap", "netname", rdap["name"]))
            abuse = _rdap_abuse_contacts(rdap)
            if abuse:
                d.findings.append(Finding("rdap", "abuse_contact", abuse))

        isc = results.get("sans_isc")
        attacks = _isc_attack_count(isc)
        if attacks:
            d.findings.append(
                Finding("sans_isc", "attack_reports", attacks,
                        "high" if attacks > 100 else "medium")
            )
            d.signals.append("attack_reports")

        tor_list = results.get("tor_exits")
        if isinstance(tor_list, str) and ip in tor_list.split():
            d.findings.append(Finding("tor_exits", "tor_exit_node", True, "medium"))
            d.signals.append("tor_exit")

        feodo = results.get("feodo")
        if isinstance(feodo, list):
            match = next((e for e in feodo if isinstance(e, dict) and e.get("ip_address") == ip), None)
            if match:
                d.findings.append(
                    Finding("feodo", "botnet_c2", match.get("malware", "unknown family"), "critical")
                )
                d.signals.append("botnet_c2")

    async def _collect_domain(self, domain: str, d: Dossier) -> None:
        tasks = {
            "dns_doh_a": self._dns(domain, "A"),
            "dns_doh_mx": self._dns(domain, "MX"),
            "dns_doh_ns": self._dns(domain, "NS"),
            "dns_doh_txt": self._dns(domain, "TXT"),
            "crtsh": self._fetch("crtsh", f"https://crt.sh/?q=%25.{domain}&output=json"),
            "rdap": self._fetch("rdap", f"https://rdap.org/domain/{domain}"),
            "hibp_breaches": self._fetch(
                "hibp_breaches", f"https://haveibeenpwned.com/api/v3/breaches?Domain={domain}"
            ),
        }
        results = await self._gather(tasks, d)

        a_records = _doh_answers(results.get("dns_doh_a"))
        if a_records:
            d.findings.append(Finding("dns_doh", "a_records", a_records))
        for label, key in (("mx_records", "dns_doh_mx"), ("nameservers", "dns_doh_ns")):
            vals = _doh_answers(results.get(key))
            if vals:
                d.findings.append(Finding("dns_doh", label, vals))
        txt = _doh_answers(results.get("dns_doh_txt"))
        if txt:
            d.findings.append(Finding("dns_doh", "txt_records", txt[:10]))
            if not any("v=spf1" in t for t in txt):
                d.findings.append(
                    Finding("dns_doh", "missing_spf",
                            "No SPF record — domain is spoofable in email", "medium")
                )

        certs = results.get("crtsh")
        if isinstance(certs, list) and certs:
            names = sorted({
                n.strip().lower()
                for c in certs if isinstance(c, dict)
                for n in (c.get("name_value") or "").split("\n")
                if n.strip() and "*" not in n
            })
            d.findings.append(Finding("crtsh", "subdomains_seen", names[:50]))
            d.findings.append(Finding("crtsh", "certificates_issued", len(certs)))

        rdap = results.get("rdap")
        if isinstance(rdap, dict):
            events = {e.get("eventAction"): e.get("eventDate") for e in rdap.get("events", [])
                      if isinstance(e, dict)}
            if events.get("registration"):
                d.findings.append(Finding("rdap", "registered", events["registration"]))
            if events.get("expiration"):
                d.findings.append(Finding("rdap", "expires", events["expiration"]))
            if rdap.get("status"):
                d.findings.append(Finding("rdap", "status", rdap["status"]))

        breaches = results.get("hibp_breaches")
        if isinstance(breaches, list) and breaches:
            named = [b.get("Name") for b in breaches if isinstance(b, dict)]
            total = sum(b.get("PwnCount", 0) for b in breaches if isinstance(b, dict))
            d.findings.append(
                Finding("hibp_breaches", "known_breaches",
                        {"breaches": named, "accounts_exposed": total}, "high")
            )
            d.signals.append("breached_domain")

    async def _collect_cve(self, cve: str, d: Dossier) -> None:
        cve = cve.upper()
        tasks = {
            "epss": self._fetch("epss", f"https://api.first.org/data/v1/epss?cve={cve}"),
            "nvd": self._fetch(
                "nvd", f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve}"
            ),
            "osv": self._post("osv", "https://api.osv.dev/v1/vulns/" + cve, None),
            "cisa_kev": self._fetch(
                "cisa_kev",
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            ),
        }
        results = await self._gather(tasks, d)

        nvd = results.get("nvd")
        severity = None
        if isinstance(nvd, dict):
            vulns = nvd.get("vulnerabilities") or []
            if vulns and isinstance(vulns[0], dict):
                item = vulns[0].get("cve", {})
                descs = item.get("descriptions") or []
                english = next((x.get("value") for x in descs if x.get("lang") == "en"), None)
                if english:
                    d.findings.append(Finding("nvd", "description", english))
                metrics = (item.get("metrics") or {})
                for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                    entries = metrics.get(key) or []
                    if entries:
                        data = entries[0].get("cvssData", {})
                        severity = (data.get("baseSeverity") or "").upper()
                        d.findings.append(
                            Finding("nvd", "cvss",
                                    {"score": data.get("baseScore"),
                                     "severity": severity,
                                     "vector": data.get("vectorString")},
                                    _sev_bucket(severity))
                        )
                        break
                if item.get("published"):
                    d.findings.append(Finding("nvd", "published", item["published"]))

        if severity == "CRITICAL":
            d.signals.append("critical_severity")
        elif severity == "HIGH":
            d.signals.append("high_severity")

        epss = results.get("epss")
        if isinstance(epss, dict):
            rows = epss.get("data") or []
            if rows and isinstance(rows[0], dict):
                score = _to_float(rows[0].get("epss"))
                percentile = _to_float(rows[0].get("percentile"))
                d.findings.append(
                    Finding("epss", "exploit_probability_30d",
                            {"score": score, "percentile": percentile},
                            "high" if score >= 0.5 else "info")
                )
                if score >= 0.5:
                    d.signals.append("high_epss")

        kev = results.get("cisa_kev")
        if isinstance(kev, dict):
            entry = next(
                (v for v in kev.get("vulnerabilities", [])
                 if isinstance(v, dict) and v.get("cveID") == cve),
                None,
            )
            if entry:
                d.findings.append(
                    Finding("cisa_kev", "actively_exploited",
                            {"added": entry.get("dateAdded"),
                             "remediate_by": entry.get("dueDate"),
                             "product": f"{entry.get('vendorProject','')} {entry.get('product','')}".strip()},
                            "critical")
                )
                d.signals.append("kev_listed")
            else:
                d.findings.append(Finding("cisa_kev", "actively_exploited", False))

        osv = results.get("osv")
        if isinstance(osv, dict) and osv.get("affected"):
            packages = sorted({
                f"{a.get('package',{}).get('ecosystem','?')}:{a.get('package',{}).get('name','?')}"
                for a in osv["affected"] if isinstance(a, dict)
            })
            if packages:
                d.findings.append(Finding("osv", "affected_packages", packages[:25]))

    async def _collect_asn(self, asn: str, d: Dossier) -> None:
        number = _ASN_RE.match(asn).group(1)
        tasks = {
            "rdap": self._fetch("rdap", f"https://rdap.org/autnum/{number}"),
            "ripestat": self._fetch(
                "ripestat", f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{number}"
            ),
            "ripestat_prefixes": self._fetch(
                "ripestat",
                f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{number}",
            ),
        }
        results = await self._gather(tasks, d)

        overview = results.get("ripestat")
        if isinstance(overview, dict):
            data = overview.get("data") or {}
            if data.get("holder"):
                d.findings.append(Finding("ripestat", "holder", data["holder"]))
            if data.get("announced") is not None:
                d.findings.append(Finding("ripestat", "announced", data["announced"]))

        prefixes = results.get("ripestat_prefixes")
        if isinstance(prefixes, dict):
            entries = (prefixes.get("data") or {}).get("prefixes") or []
            if entries:
                d.findings.append(Finding("ripestat", "announced_prefix_count", len(entries)))
                d.findings.append(
                    Finding("ripestat", "sample_prefixes",
                            [p.get("prefix") for p in entries[:15] if isinstance(p, dict)])
                )

        rdap = results.get("rdap")
        if isinstance(rdap, dict) and rdap.get("name"):
            d.findings.append(Finding("rdap", "asn_name", rdap["name"]))

    async def _collect_package(self, target: str, d: Dossier) -> None:
        match = _PACKAGE_RE.match(target)
        ecosystem_raw, name = match.group(1).lower(), match.group(2)
        ecosystem = {
            "pypi": "PyPI", "npm": "npm", "go": "Go",
            "maven": "Maven", "crates.io": "crates.io",
            "nuget": "NuGet", "rubygems": "RubyGems",
        }[ecosystem_raw]

        tasks = {
            "osv": self._post(
                "osv", "https://api.osv.dev/v1/query",
                {"package": {"name": name, "ecosystem": ecosystem}},
            ),
        }
        results = await self._gather(tasks, d)

        osv = results.get("osv")
        if isinstance(osv, dict):
            vulns = osv.get("vulns") or []
            if not vulns:
                d.findings.append(Finding("osv", "known_vulnerabilities", 0))
                return
            d.findings.append(Finding("osv", "known_vulnerabilities", len(vulns), "high"))
            d.signals.append("known_vulns")
            listed = []
            for v in vulns[:20]:
                if not isinstance(v, dict):
                    continue
                aliases = v.get("aliases") or []
                cve = next((a for a in aliases if a.startswith("CVE-")), v.get("id"))
                listed.append({"id": cve, "summary": (v.get("summary") or "")[:160]})
                sev = _osv_severity(v)
                if sev == "CRITICAL":
                    d.signals.append("critical_severity")
            d.findings.append(Finding("osv", "advisories", listed))

    async def _collect_mac(self, mac: str, d: Dossier) -> None:
        tasks = {"macvendors": self._fetch_text("macvendors", f"https://api.macvendors.com/{mac}")}
        results = await self._gather(tasks, d)
        vendor = results.get("macvendors")
        if isinstance(vendor, str) and vendor.strip():
            d.findings.append(Finding("macvendors", "vendor", vendor.strip()))
        oui = mac.upper().replace("-", ":")[:8]
        d.findings.append(Finding("local", "oui", oui))
        # Locally-administered bit set in the first octet => randomised/spoofed MAC.
        first_octet = int(mac.replace("-", ":").split(":")[0], 16)
        if first_octet & 0b10:
            d.findings.append(
                Finding("local", "locally_administered",
                        "Randomised or manually-set MAC — vendor lookup is not identity", "medium")
            )

    async def _collect_hash(self, digest: str, d: Dossier) -> None:
        algo = _HASH_LENGTHS[len(digest)]
        d.findings.append(Finding("local", "algorithm", algo))
        vt = public_apis.get("virustotal")
        if vt and vt.configured:
            key = public_apis.get("virustotal").env_var or ""
            import os

            fetch = await self._http.get_json(
                f"https://www.virustotal.com/api/v3/files/{digest}",
                headers={"x-apikey": os.environ.get(key, "")},
            )
            d.sources_queried.append("virustotal")
            if fetch.ok and isinstance(fetch.data, dict):
                d.sources_answered.append("virustotal")
                stats = (
                    fetch.data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                )
                malicious = stats.get("malicious", 0)
                d.findings.append(
                    Finding("virustotal", "detections", stats,
                            "critical" if malicious > 5 else "medium" if malicious else "info")
                )
                if malicious:
                    d.signals.append("known_vulns")
            else:
                d.degraded["virustotal"] = fetch.error or "no result"
        else:
            d.findings.append(
                Finding("local", "note",
                        "File-hash reputation needs VIRUSTOTAL_API_KEY; no keyless source "
                        "covers hashes.")
            )

    # ── fetch plumbing ───────────────────────────────────────────────────────

    async def _fetch(self, source_id: str, url: str) -> Tuple[str, Fetch]:
        api = public_apis.get(source_id)
        ttl = api.ttl_seconds if api else 900
        return source_id, await self._http.get_json(url, ttl=ttl)

    async def _fetch_text(self, source_id: str, url: str) -> Tuple[str, Fetch]:
        api = public_apis.get(source_id)
        ttl = api.ttl_seconds if api else 900
        return source_id, await self._http.get_text(url, ttl=ttl)

    async def _post(self, source_id: str, url: str, payload: Any) -> Tuple[str, Fetch]:
        api = public_apis.get(source_id)
        ttl = api.ttl_seconds if api else 900
        if payload is None:
            return source_id, await self._http.get_json(url, ttl=ttl)
        return source_id, await self._http.post_json(url, payload, ttl=ttl)

    async def _dns(self, domain: str, rtype: str) -> Tuple[str, Fetch]:
        url = f"https://cloudflare-dns.com/dns-query?name={domain}&type={rtype}"
        return "dns_doh", await self._http.get_json(
            url, headers={"Accept": "application/dns-json"}, ttl=600
        )

    async def _gather(self, tasks: Dict[str, Any], d: Dossier) -> Dict[str, Any]:
        """Run every collector concurrently; record who answered and who didn't."""
        keys = list(tasks.keys())
        outcomes = await asyncio.gather(*tasks.values(), return_exceptions=True)

        payloads: Dict[str, Any] = {}
        for key, outcome in zip(keys, outcomes):
            if isinstance(outcome, BaseException):
                d.degraded[key] = f"{type(outcome).__name__}: {outcome}"
                continue
            source_id, fetch = outcome
            if source_id not in d.sources_queried:
                d.sources_queried.append(source_id)
            if fetch.ok:
                if source_id not in d.sources_answered:
                    d.sources_answered.append(source_id)
                payloads[key] = fetch.data
            else:
                d.degraded[key] = fetch.error
        return payloads

    # ── scoring ──────────────────────────────────────────────────────────────

    def _score(self, d: Dossier) -> None:
        if d.risk == "n/a":
            d.confidence = 1.0
            return

        d.signals = sorted(set(d.signals))
        d.risk_score = min(100, sum(_RISK_SIGNALS.get(s, 0) for s in d.signals))

        if not d.sources_answered:
            d.risk = "unknown"
            d.confidence = 0.0
            d.summary = (
                f"No public source answered for {d.target}. "
                f"Attempted {len(d.sources_queried)}; all degraded or unreachable."
            )
            return

        if d.risk_score >= 60:
            d.risk = "critical"
        elif d.risk_score >= 35:
            d.risk = "high"
        elif d.risk_score >= 15:
            d.risk = "elevated"
        elif d.risk_score > 0:
            d.risk = "low"
        else:
            d.risk = "clean"

        d.confidence = round(len(d.sources_answered) / max(1, len(d.sources_queried)), 2)
        d.summary = self._summarise(d)

    @staticmethod
    def _summarise(d: Dossier) -> str:
        parts = [
            f"{d.target} ({d.indicator}) — {d.risk.upper()} "
            f"[score {d.risk_score}/100, {len(d.sources_answered)}/{len(d.sources_queried)} sources]"
        ]
        readable = {
            "kev_listed": "listed in CISA KEV (exploited in the wild)",
            "botnet_c2": "active botnet command-and-control",
            "high_epss": "high 30-day exploitation probability",
            "attack_reports": "reported attacking ISC sensors",
            "known_vulns": "known vulnerabilities present",
            "tor_exit": "Tor exit node",
            "critical_severity": "critical severity",
            "high_severity": "high severity",
            "many_open_ports": "broad open-port surface",
            "breached_domain": "appears in known breach corpora",
        }
        flagged = [readable[s] for s in d.signals if s in readable]
        if flagged:
            parts.append("Signals: " + "; ".join(flagged) + ".")
        else:
            parts.append("No adverse signals from the sources that answered.")
        if d.degraded:
            parts.append(f"Degraded: {', '.join(sorted(d.degraded))}.")
        return " ".join(parts)


# ── small helpers ────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sev_bucket(severity: Optional[str]) -> str:
    return {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(
        (severity or "").upper(), "info"
    )


def _doh_answers(payload: Any) -> List[str]:
    """Pull the record values out of a Cloudflare DNS-JSON response."""
    if not isinstance(payload, dict):
        return []
    return [
        str(a.get("data", "")).strip('"')
        for a in payload.get("Answer", [])
        if isinstance(a, dict) and a.get("data")
    ]


def _isc_attack_count(payload: Any) -> int:
    """ISC wraps its answer as {"ip": {"count": ..., "attacks": ...}}."""
    if not isinstance(payload, dict):
        return 0
    record = payload.get("ip")
    if not isinstance(record, dict):
        return 0
    for key in ("attacks", "count"):
        value = record.get(key)
        if value not in (None, "", "null"):
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


def _rdap_abuse_contacts(rdap: Dict[str, Any]) -> List[str]:
    """Extract abuse-role email addresses from an RDAP vCard array."""
    contacts: List[str] = []
    for entity in rdap.get("entities", []) or []:
        if not isinstance(entity, dict):
            continue
        roles = entity.get("roles") or []
        if "abuse" not in [str(r).lower() for r in roles]:
            continue
        vcard = entity.get("vcardArray")
        if not (isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list)):
            continue
        for item in vcard[1]:
            if isinstance(item, list) and len(item) >= 4 and item[0] == "email":
                contacts.append(str(item[3]))
    return contacts


def _osv_severity(vuln: Dict[str, Any]) -> str:
    """Best-effort severity from an OSV record's database_specific block."""
    specific = vuln.get("database_specific")
    if isinstance(specific, dict):
        sev = specific.get("severity")
        if isinstance(sev, str):
            return sev.upper()
    return ""
