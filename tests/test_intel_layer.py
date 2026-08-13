"""Tests for the public-API intelligence layer.

Every upstream is faked at the transport boundary (:class:`FakeHTTP`), so these
run offline and deterministically. What they verify is DEEP's own behaviour:
indicator classification, how upstream payloads map onto findings, that risk
scoring follows the collected signals, that a dead source degrades instead of
failing the dossier, and that the terminal's guardrails hold.
"""
from __future__ import annotations

import pytest

from core.intel import public_apis
from core.intel.http import Fetch
from core.intel.live_stats import LiveIntel
from core.intel.ops_terminal import OpsTerminal
from core.intel.osint_investigator import Indicator, OSINTInvestigator


class FakeHTTP:
    """Stand-in for IntelHTTP: matches a URL substring to a canned payload."""

    def __init__(self, routes: dict[str, object], fail: set[str] | None = None) -> None:
        self.routes = routes
        self.fail = fail or set()
        self.calls: list[str] = []

    def _resolve(self, url: str) -> Fetch:
        self.calls.append(url)
        for fragment in self.fail:
            if fragment in url:
                return Fetch(ok=False, error="simulated upstream failure", status=503)
        for fragment, payload in self.routes.items():
            if fragment in url:
                return Fetch(ok=True, data=payload, status=200)
        return Fetch(ok=False, error="no route", status=404)

    async def get_json(self, url, *, headers=None, ttl=None):
        return self._resolve(url)

    async def get_text(self, url, *, headers=None, ttl=None):
        return self._resolve(url)

    async def post_json(self, url, payload, *, headers=None, ttl=None):
        return self._resolve(url)

    def stats(self):
        return {"requests": len(self.calls)}


# ═══════════════════════════════════════════════════════════════════════════
# Indicator classification
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "target,expected",
    [
        ("8.8.8.8", Indicator.IP),
        ("2606:4700:4700::1111", Indicator.IP),
        ("example.com", Indicator.DOMAIN),
        ("sub.deep.example.co.uk", Indicator.DOMAIN),
        ("CVE-2021-44228", Indicator.CVE),
        ("cve-2021-44228", Indicator.CVE),
        ("AS15169", Indicator.ASN),
        ("pypi:requests", Indicator.PACKAGE),
        ("npm:lodash", Indicator.PACKAGE),
        ("aa:bb:cc:dd:ee:ff", Indicator.MAC),
        ("d41d8cd98f00b204e9800998ecf8427e", Indicator.HASH),
        ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", Indicator.HASH),
    ],
)
def test_classify(target, expected):
    assert OSINTInvestigator.classify(target) is expected


@pytest.mark.parametrize("target", ["", "   ", "not a target", "???", "http://x"])
def test_classify_rejects_garbage(target):
    assert OSINTInvestigator.classify(target) is None


# ═══════════════════════════════════════════════════════════════════════════
# IP investigation
# ═══════════════════════════════════════════════════════════════════════════


def _ip_routes(**overrides):
    routes = {
        "internetdb.shodan.io": {
            "ip": "45.33.32.156",
            "ports": [22, 80, 443, 3389, 8080, 9200],
            "vulns": ["CVE-2021-44228"],
            "hostnames": ["bad.example.net"],
            "cpes": ["cpe:/a:apache:log4j"],
        },
        "ipapi.co": {
            "latitude": 52.37, "longitude": 4.89, "city": "Amsterdam",
            "country_name": "Netherlands", "country_code": "NL",
            "org": "AS64496 Example Hosting", "asn": "AS64496", "region": "NH",
        },
        "stat.ripe.net": {"data": {"asns": ["64496"], "prefix": "45.33.32.0/24"}},
        "rdap.org": {
            "name": "EXAMPLE-NET",
            "entities": [{
                "roles": ["abuse"],
                "vcardArray": ["vcard", [["email", {}, "text", "abuse@example.net"]]],
            }],
        },
        "isc.sans.edu": {"ip": {"number": "45.33.32.156", "attacks": "4200", "count": "310"}},
        "torproject.org": "104.244.42.65\n45.33.32.156\n",
        "feodotracker": [{"ip_address": "45.33.32.156", "malware": "Emotet", "port": 443}],
    }
    routes.update(overrides)
    return routes


@pytest.mark.asyncio
async def test_ip_dossier_collects_every_source():
    http = FakeHTTP(_ip_routes())
    d = await OSINTInvestigator(http=http).investigate("45.33.32.156")

    assert d.indicator == "ip"
    labels = {f.label for f in d.findings}
    assert {"open_ports", "known_cves", "location", "announcing_asn",
            "abuse_contact", "attack_reports", "tor_exit_node", "botnet_c2"} <= labels

    assert d.geo["city"] == "Amsterdam"
    assert d.geo["country"] == "Netherlands"

    # Every finding is attributed to the source that produced it.
    assert all(f.source for f in d.findings)


@pytest.mark.asyncio
async def test_ip_risk_reflects_collected_signals():
    d = await OSINTInvestigator(http=FakeHTTP(_ip_routes())).investigate("45.33.32.156")
    assert d.risk == "critical"
    assert "botnet_c2" in d.signals
    assert "known_vulns" in d.signals
    assert d.risk_score >= 60
    assert "botnet" in d.summary.lower()


@pytest.mark.asyncio
async def test_clean_ip_scores_clean():
    http = FakeHTTP({
        "internetdb.shodan.io": {"ports": [443], "vulns": [], "hostnames": [], "cpes": []},
        "ipapi.co": {"latitude": 1.0, "longitude": 2.0, "city": "Nowhere",
                     "country_name": "Testland", "org": "Test ISP"},
        "stat.ripe.net": {"data": {"asns": ["65000"], "prefix": "93.184.216.0/24"}},
        "rdap.org": {"name": "TEST-NET"},
        "isc.sans.edu": {"ip": {}},
        "torproject.org": "",
        "feodotracker": [],
    })
    d = await OSINTInvestigator(http=http).investigate("93.184.216.34")
    assert d.risk == "clean"
    assert d.risk_score == 0
    assert d.signals == []


@pytest.mark.asyncio
async def test_private_ip_short_circuits_without_calling_anyone():
    http = FakeHTTP({})
    d = await OSINTInvestigator(http=http).investigate("192.168.1.10")
    assert d.risk == "n/a"
    assert http.calls == []
    assert "private or reserved address" in d.summary


@pytest.mark.asyncio
async def test_dead_sources_degrade_without_failing_the_dossier():
    http = FakeHTTP(_ip_routes(), fail={"isc.sans.edu", "feodotracker", "rdap.org"})
    d = await OSINTInvestigator(http=http).investigate("45.33.32.156")

    assert d.geo is not None                      # healthy sources still landed
    assert set(d.degraded) >= {"sans_isc", "feodo", "rdap"}
    assert "sans_isc" not in d.sources_answered
    assert "shodan_internetdb" in d.sources_answered
    assert 0 < d.confidence < 1.0                 # confidence reflects partial coverage
    assert "Degraded" in d.summary


@pytest.mark.asyncio
async def test_total_source_blackout_yields_unknown_not_clean():
    """A silent internet must never read as 'nothing wrong here'."""
    http = FakeHTTP({}, fail={"http"})
    d = await OSINTInvestigator(http=http).investigate("45.33.32.156")
    assert d.risk == "unknown"
    assert d.confidence == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# CVE investigation
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cve_dossier_merges_nvd_epss_and_kev():
    http = FakeHTTP({
        "services.nvd.nist.gov": {
            "vulnerabilities": [{"cve": {
                "descriptions": [{"lang": "en", "value": "Log4j JNDI RCE"}],
                "published": "2021-12-10T10:15:09.143",
                "metrics": {"cvssMetricV31": [{"cvssData": {
                    "baseScore": 10.0, "baseSeverity": "CRITICAL",
                    "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                }}]},
            }}]
        },
        "api.first.org": {"data": [{"cve": "CVE-2021-44228", "epss": "0.97", "percentile": "0.999"}]},
        "cisa.gov": {"vulnerabilities": [{
            "cveID": "CVE-2021-44228", "dateAdded": "2021-12-10", "dueDate": "2021-12-24",
            "vendorProject": "Apache", "product": "Log4j",
        }]},
        "api.osv.dev": {"affected": [{"package": {"ecosystem": "Maven", "name": "org.apache.logging.log4j:log4j-core"}}]},
    })
    d = await OSINTInvestigator(http=http).investigate("CVE-2021-44228")

    assert d.indicator == "cve"
    by_label = {f.label: f.value for f in d.findings}
    assert by_label["cvss"]["severity"] == "CRITICAL"
    assert by_label["exploit_probability_30d"]["score"] == 0.97
    assert by_label["actively_exploited"]["remediate_by"] == "2021-12-24"
    assert "Maven:org.apache.logging.log4j:log4j-core" in by_label["affected_packages"]

    assert {"kev_listed", "high_epss", "critical_severity"} <= set(d.signals)
    assert d.risk == "critical"


@pytest.mark.asyncio
async def test_cve_not_in_kev_is_reported_as_such():
    http = FakeHTTP({
        "services.nvd.nist.gov": {"vulnerabilities": []},
        "api.first.org": {"data": [{"cve": "CVE-2020-0001", "epss": "0.001", "percentile": "0.1"}]},
        "cisa.gov": {"vulnerabilities": []},
        "api.osv.dev": {},
    })
    d = await OSINTInvestigator(http=http).investigate("CVE-2020-0001")
    exploited = next(f for f in d.findings if f.label == "actively_exploited")
    assert exploited.value is False
    assert "kev_listed" not in d.signals


# ═══════════════════════════════════════════════════════════════════════════
# Domain, package, MAC
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_domain_dossier_flags_missing_spf_and_breaches():
    http = FakeHTTP({
        "type=A": {"Answer": [{"name": "example.com", "type": 1, "TTL": 300, "data": "93.184.216.34"}]},
        "type=MX": {"Answer": [{"data": "10 mail.example.com"}]},
        "type=NS": {"Answer": [{"data": "ns1.example.com"}]},
        "type=TXT": {"Answer": [{"data": '"docusign=abc"'}]},
        "crt.sh": [{"name_value": "www.example.com\nvpn.example.com"},
                   {"name_value": "*.example.com"}],
        "rdap.org": {"events": [{"eventAction": "registration", "eventDate": "1995-08-14"}],
                     "status": ["client transfer prohibited"]},
        "haveibeenpwned.com": [{"Name": "ExampleBreach", "PwnCount": 12345}],
    })
    d = await OSINTInvestigator(http=http).investigate("example.com")

    by_label = {f.label: f.value for f in d.findings}
    assert by_label["a_records"] == ["93.184.216.34"]
    assert "vpn.example.com" in by_label["subdomains_seen"]
    assert "*" not in "".join(by_label["subdomains_seen"])  # wildcards filtered out
    assert "missing_spf" in by_label
    assert by_label["known_breaches"]["accounts_exposed"] == 12345
    assert "breached_domain" in d.signals


@pytest.mark.asyncio
async def test_domain_with_spf_is_not_flagged():
    http = FakeHTTP({
        "type=TXT": {"Answer": [{"data": '"v=spf1 include:_spf.example.com -all"'}]},
    })
    d = await OSINTInvestigator(http=http).investigate("example.com")
    assert not any(f.label == "missing_spf" for f in d.findings)


@pytest.mark.asyncio
async def test_package_advisories():
    http = FakeHTTP({"api.osv.dev": {"vulns": [
        {"id": "GHSA-xxxx", "aliases": ["CVE-2023-32681"], "summary": "Proxy-Authorization leak"},
    ]}})
    d = await OSINTInvestigator(http=http).investigate("pypi:requests")
    assert d.indicator == "package"
    advisories = next(f for f in d.findings if f.label == "advisories")
    assert advisories.value[0]["id"] == "CVE-2023-32681"
    assert "known_vulns" in d.signals


@pytest.mark.asyncio
async def test_randomised_mac_is_called_out():
    """Bit 1 of the first octet marks a locally-administered (randomised) MAC."""
    http = FakeHTTP({"macvendors.com": "Apple, Inc."})
    d = await OSINTInvestigator(http=http).investigate("aa:bb:cc:dd:ee:ff")
    labels = {f.label for f in d.findings}
    assert "locally_administered" in labels

    d2 = await OSINTInvestigator(http=http).investigate("a8:bb:cc:dd:ee:ff")
    assert "locally_administered" not in {f.label for f in d2.findings}
    assert any(f.label == "vendor" and f.value == "Apple, Inc." for f in d2.findings)


# ═══════════════════════════════════════════════════════════════════════════
# Live stats
# ═══════════════════════════════════════════════════════════════════════════


def _kev_payload():
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    return {
        "catalogVersion": "2026.08.03",
        "vulnerabilities": [
            {"cveID": "CVE-2026-1", "vendorProject": "Microsoft", "product": "Windows",
             "dateAdded": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
             "dueDate": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
             "knownRansomwareCampaignUse": "Known"},
            {"cveID": "CVE-2026-2", "vendorProject": "Microsoft", "product": "Exchange",
             "dateAdded": (today - timedelta(days=20)).strftime("%Y-%m-%d"),
             "dueDate": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
             "knownRansomwareCampaignUse": "Unknown"},
            {"cveID": "CVE-2025-9", "vendorProject": "Cisco", "product": "IOS",
             "dateAdded": (today - timedelta(days=200)).strftime("%Y-%m-%d"),
             "dueDate": (today - timedelta(days=180)).strftime("%Y-%m-%d")},
        ],
    }


@pytest.mark.asyncio
async def test_cyber_stats_computes_kev_velocity():
    http = FakeHTTP({
        "cisa.gov": _kev_payload(),
        "api.first.org": {"data": [{"cve": "CVE-2026-1", "epss": "0.9", "percentile": "0.99"}]},
        "feodotracker": [{"ip_address": "203.0.113.1", "malware": "Emotet", "country": "NL"},
                         {"ip_address": "203.0.113.2", "malware": "Emotet", "country": "DE"}],
        "torproject.org": "1.1.1.1\n2.2.2.2\n3.3.3.3\n",
    })
    stats = await LiveIntel(http=http).cyber_stats()

    kev = stats["kev"]
    assert kev["available"] is True
    assert kev["total"] == 3
    assert kev["added_7d"] == 1
    assert kev["added_30d"] == 2
    assert kev["remediation_overdue"] == 2
    assert kev["remediation_due_14d"] == 1
    assert kev["ransomware_linked"] == 1
    assert kev["top_vendors"][0] == {"vendor": "Microsoft", "count": 2}

    assert stats["botnet"]["active_c2_servers"] == 2
    assert stats["botnet"]["families"][0]["family"] == "Emotet"
    assert stats["anonymity"]["tor_exit_nodes"] == 3
    assert stats["sources"]["keyless"] > 0


@pytest.mark.asyncio
async def test_cyber_stats_marks_dead_feeds_unavailable_not_zero():
    """A feed that is down must not read as 'zero threats'."""
    http = FakeHTTP({"cisa.gov": _kev_payload()}, fail={"feodotracker", "torproject"})
    stats = await LiveIntel(http=http).cyber_stats()
    assert stats["kev"]["available"] is True
    assert stats["botnet"]["available"] is False
    assert stats["botnet"].get("active_c2_servers") is None
    assert "feodo" in stats["degraded"]


@pytest.mark.asyncio
async def test_threat_map_attributes_every_node_to_its_feed():
    http = FakeHTTP({
        "isc.sans.edu": [{"ip": "203.000.113.010", "attacks": "9000", "targets": "12",
                          "mindate": "2026-07-01", "maxdate": "2026-08-01"}],
        "feodotracker": [{"ip_address": "198.51.100.7", "malware": "QakBot",
                          "port": 443, "status": "online"}],
        "ip-api.com/batch": [
            {"status": "success", "query": "203.0.113.10", "lat": 52.3, "lon": 4.8,
             "country": "Netherlands", "countryCode": "NL", "city": "Amsterdam",
             "org": "Example Hosting", "as": "AS64496"},
            {"status": "success", "query": "198.51.100.7", "lat": 50.1, "lon": 8.6,
             "country": "Germany", "countryCode": "DE", "city": "Frankfurt",
             "org": "Bad Hoster", "as": "AS64497"},
        ],
    })
    result = await LiveIntel(http=http).threat_map(limit=50)

    assert result["count"] == 2
    by_ip = {n["ip"]: n for n in result["nodes"]}

    # ISC zero-pads its octets; DEEP must normalise so geo lines up.
    assert by_ip["203.0.113.10"]["classification"] == "scanner"
    assert by_ip["203.0.113.10"]["source"] == "SANS ISC"
    assert by_ip["203.0.113.10"]["detail"]["attacks"] == 9000

    assert by_ip["198.51.100.7"]["classification"] == "botnet_c2"
    assert by_ip["198.51.100.7"]["severity"] == "critical"
    assert by_ip["198.51.100.7"]["detail"]["malware"] == "QakBot"

    # No node carries an invented field.
    for node in result["nodes"]:
        assert node["source"], "every node must name its feed"
        assert node["classification"] in {"scanner", "botnet_c2"}


@pytest.mark.asyncio
async def test_threat_map_drops_ungeolocatable_nodes():
    http = FakeHTTP({
        "isc.sans.edu": [{"ip": "203.0.113.10", "attacks": "5"},
                         {"ip": "203.0.113.11", "attacks": "5"}],
        "feodotracker": [],
        "ip-api.com/batch": [
            {"status": "success", "query": "203.0.113.10", "lat": 1.0, "lon": 2.0,
             "country": "X", "countryCode": "X", "city": "Y", "org": "Z", "as": "AS1"},
            {"status": "fail", "query": "203.0.113.11"},
        ],
    })
    result = await LiveIntel(http=http).threat_map()
    assert result["count"] == 1
    assert result["nodes"][0]["ip"] == "203.0.113.10"


# ═══════════════════════════════════════════════════════════════════════════
# Ops terminal
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_help_lists_every_registered_command():
    result = await OpsTerminal().execute("help")
    assert result.ok
    from core.intel.ops_terminal import COMMANDS

    for spec in COMMANDS:
        assert spec.name in result.text


@pytest.mark.asyncio
async def test_unknown_command_suggests_the_closest_match():
    result = await OpsTerminal().execute("investgate 1.1.1.1")
    assert not result.ok
    assert "investigate" in result.error


@pytest.mark.asyncio
async def test_terminal_never_shells_out():
    """An unrecognised verb is an error, not something handed to a shell."""
    for hostile in ["rm -rf /", "; cat /etc/passwd", "$(whoami)", "sh -c 'echo x'"]:
        result = await OpsTerminal().execute(hostile)
        assert not result.ok
        assert "unknown command" in result.error


@pytest.mark.asyncio
async def test_scan_refuses_targets_outside_the_local_subnet():
    result = await OpsTerminal().execute("scan 8.8.8.8")
    assert not result.ok
    assert "refusing to scan" in result.error


@pytest.mark.asyncio
async def test_scan_requires_a_scanner_even_for_local_targets():
    """Local target passes the address guard, then fails closed with no scanner."""
    result = await OpsTerminal().execute("scan 192.168.1.5")
    assert not result.ok
    assert "not available" in result.error


@pytest.mark.asyncio
async def test_commands_without_arguments_report_usage():
    for verb in ("investigate", "whois", "dns", "subdomains", "exposure", "cve", "deps", "scan"):
        result = await OpsTerminal().execute(verb)
        assert not result.ok, verb
        assert "usage:" in result.error, verb


@pytest.mark.asyncio
async def test_kev_command_renders_the_catalog():
    http = FakeHTTP({"cisa.gov": _kev_payload(), "api.first.org": {"data": []},
                     "feodotracker": [], "torproject.org": ""})
    term = OpsTerminal(live=LiveIntel(http=http))
    result = await term.execute("kev --vendor Microsoft --limit 5")
    assert result.ok
    assert "CVE-2026-1" in result.text
    assert "CVE-2025-9" not in result.text  # filtered out by --vendor


@pytest.mark.asyncio
async def test_terminal_command_catalog_matches_the_dispatcher():
    """Every declared command must have a handler, and vice versa."""
    from core.intel.ops_terminal import COMMANDS

    term = OpsTerminal()
    for spec in COMMANDS:
        assert hasattr(term, f"_cmd_{spec.name}"), f"{spec.name} declared but not implemented"
    handlers = {n[len("_cmd_"):] for n in dir(term) if n.startswith("_cmd_")}
    declared = {c.name for c in COMMANDS}
    assert handlers == declared


# ═══════════════════════════════════════════════════════════════════════════
# Catalog integrity
# ═══════════════════════════════════════════════════════════════════════════


def test_catalog_entries_are_well_formed():
    for api in public_apis.CATALOG:
        assert api.id and api.name and api.description
        assert api.base_url.startswith("http")
        assert api.docs_url.startswith("http")
        assert api.indicators, f"{api.id} declares no indicator types"
        if api.auth is public_apis.Auth.KEY:
            assert api.env_var, f"{api.id} needs a key but names no env var"


def test_catalog_ids_are_unique():
    ids = [a.id for a in public_apis.CATALOG]
    assert len(ids) == len(set(ids))


def test_keyless_sources_are_always_configured():
    for api in public_apis.CATALOG:
        if api.auth is public_apis.Auth.NONE:
            assert api.configured is True


def test_every_indicator_type_has_a_keyless_source():
    """A fresh clone with no keys must answer for every indicator type.

    Hashes were the one gap until urlscan.io was catalogued. Note what it
    actually provides: urlscan indexes the SHA-256 of every resource it
    fetched, so a hash pivots to the pages observed serving that file. That is
    *provenance*, not a malware verdict — reputation still needs VirusTotal, and
    `_collect_hash` says so rather than letting a keyless answer imply more
    than it covers.
    """
    for kind in public_apis.Indicator:
        keyless = public_apis.for_indicator(kind, keyless_only=True)
        assert keyless, f"no keyless source covers {kind.value}"


@pytest.mark.asyncio
async def test_shared_http_session_closes_cleanly():
    """The pooled session must be closable, or every shutdown leaks a connector."""
    from core.intel.http import IntelHTTP

    http = IntelHTTP()
    await http.close()   # never opened — must not raise
    await http.close()   # idempotent
    assert http.stats()["cache_entries"] == 0


def test_server_shutdown_closes_pooled_http_sessions():
    """Regression: neither pooled aiohttp session had a shutdown hook.

    The intel layer's public-API session, and the LLM client's — which
    /api/status opens on every poll via brain.health_check().
    """
    import inspect

    from interface import server

    source = inspect.getsource(server.shutdown_event)
    assert "shared_http" in source and "close()" in source
    assert "ollama_client.close()" in source


# ═══════════════════════════════════════════════════════════════════════════
# Local-estate commands — pinned to the real NetworkScanner contract
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_devices_reads_the_real_scanner_contract():
    """get_devices() is async and yields NetworkDevice dataclasses, not dicts.

    Regression: this was called synchronously and its results treated as
    dicts, so the command returned a coroutine and would have raised on
    .get(). Built here from the real class so the test breaks if it changes.
    """
    from types import SimpleNamespace

    from network.scanner import NetworkDevice, NetworkScanner

    devices = [
        NetworkDevice(ip="192.168.1.5", mac="aa:bb:cc:dd:ee:01", hostname="nas",
                      vendor="Synology", is_known=True, open_ports=[22, 5000],
                      last_seen="2026-08-05T10:00:00Z"),
        NetworkDevice(ip="192.168.1.99", mac="aa:bb:cc:dd:ee:02", hostname=None,
                      vendor=None, is_known=False, last_seen="2026-08-05T10:01:00Z"),
    ]

    class FakeScanner:
        async def get_devices(self):
            return devices

    assert callable(NetworkScanner.get_devices)

    term = OpsTerminal(services=SimpleNamespace(scanner=FakeScanner()))

    result = await term.execute("devices")
    assert result.ok, result.error
    assert len(result.rows) == 2
    assert result.rows[0]["ip"] == "192.168.1.5"
    assert result.rows[0]["known"] is True
    assert "192.168.1.99" in result.text

    only_unknown = await term.execute("devices --unknown")
    assert [r["ip"] for r in only_unknown.rows] == ["192.168.1.99"]


@pytest.mark.asyncio
async def test_scan_uses_scan_target_not_a_method_that_never_existed():
    """Regression: guarded on `deep_scan_device`, which NetworkScanner has no.

    The guard was therefore always False and `scan` could never run, even with
    a healthy scanner attached.
    """
    from types import SimpleNamespace

    from network.scanner import NetworkDevice, NetworkScanner

    assert not hasattr(NetworkScanner, "deep_scan_device")
    assert callable(NetworkScanner.scan_target)

    scanned = []

    class FakeScanner:
        async def scan_target(self, ip):
            scanned.append(ip)
            return NetworkDevice(ip=ip, mac="aa:bb:cc:dd:ee:03", hostname="printer",
                                 vendor="HP", open_ports=[80, 631], os_guess="Linux 5.x")

    term = OpsTerminal(services=SimpleNamespace(scanner=FakeScanner()))
    result = await term.execute("scan 192.168.1.42")

    assert result.ok, result.error
    assert scanned == ["192.168.1.42"]
    assert result.data["open_ports"] == [80, 631]
    assert "printer" in result.text


@pytest.mark.asyncio
async def test_scan_reports_a_silent_host_rather_than_crashing():
    from types import SimpleNamespace

    class FakeScanner:
        async def scan_target(self, ip):
            return None

    term = OpsTerminal(services=SimpleNamespace(scanner=FakeScanner()))
    result = await term.execute("scan 192.168.1.250")
    assert result.ok
    assert "did not respond" in result.text


@pytest.mark.asyncio
async def test_timeline_reads_the_real_security_timeline_contract():
    from types import SimpleNamespace

    from core.security.security_timeline import SecurityTimeline

    assert callable(SecurityTimeline.get_timeline)

    class FakeTimeline:
        def get_timeline(self, limit=50, min_severity=None):
            return [
                {"timestamp": "2026-08-05T10:00:00Z", "severity": "high",
                 "kind": "port_scan", "summary": "Port scan from 192.168.1.99"},
            ]

    term = OpsTerminal(services=SimpleNamespace(security_timeline=FakeTimeline()))
    result = await term.execute("timeline --severity high")
    assert result.ok, result.error
    assert result.rows[0]["severity"] == "high"
    assert "port_scan" in result.text
