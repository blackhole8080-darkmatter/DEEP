"""Tests for the tools that expose DEEP's own observations to the LLM.

Fakes here are built from the *real* dataclasses (NetworkDevice, Anomaly,
ProximityAP, ExploitEntry) and mirror the real method signatures, so a rename
or a sync/async change in a subsystem breaks a test rather than the feature.
That is the lesson from `devices` calling an async get_devices() synchronously
and `scan` guarding on a method that never existed — both shipped green.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.tools  # noqa: F401  — registers the tool decorators
from core.tools.registry import TOOL_SPECS

ESTATE_TOOLS = [
    "security_events", "anomalies", "threat_predictions", "local_devices",
    "wifi_environment", "dns_activity", "stack_exposure", "exploit_search",
]


# ── fakes, pinned to the real contracts ──────────────────────────────────────


class FakeTimeline:
    """Mirrors core/security/security_timeline.py."""

    def __init__(self, events=None):
        self.events = events if events is not None else [{
            "id": "corr-1", "source": "correlated", "kind": "port_scan",
            "severity": "high", "timestamp": "2026-08-06T03:14:00Z",
            "summary": "Port scan from 192.168.1.99",
            "techniques": ["T1046"], "related_cves": ["CVE-2021-44228"],
            "device_mac": None, "device_ip": "192.168.1.99",
        }]
        self.calls = []

    def get_timeline(self, limit=50, min_severity=None):
        self.calls.append({"limit": limit, "min_severity": min_severity})
        return self.events

    def get_stats(self):
        return {"total": len(self.events)}


class FakeDetector:
    """Mirrors ai/anomaly/anomaly_detector.py."""

    def __init__(self, found=None):
        from ai.anomaly.anomaly_detector import Anomaly

        self.found = found if found is not None else [
            Anomaly("network", "outbound_bytes", 9_400_000.0, 1_200_000.0,
                    410_000.0, 19.9, "high", "2026-08-06T03:12:00Z", {})
        ]
        self.calls = []

    async def get_recent_anomalies(self, hours=24):
        self.calls.append(hours)
        return self.found

    async def get_anomaly_stats(self):
        return {"last_24h": len(self.found)}


class FakeScanner:
    """Mirrors network/scanner.py — get_devices is async, yields dataclasses."""

    def __init__(self):
        from network.scanner import NetworkDevice

        self.devices = [
            NetworkDevice(ip="192.168.1.5", mac="aa:bb:cc:dd:ee:01", hostname="nas",
                          vendor="Synology", is_known=True, open_ports=[22, 5000]),
            NetworkDevice(ip="192.168.1.99", mac="aa:bb:cc:dd:ee:99", vendor="Espressif",
                          is_known=False, open_ports=[22, 8080], os_guess="Linux"),
        ]

    async def get_devices(self):
        return self.devices


def estate(**kwargs):
    return SimpleNamespace(**kwargs)


@pytest.fixture(scope="module")
def registry():
    from core.tools.deep_registry import DeepToolRegistry

    return DeepToolRegistry()


def _with_estate(registry, **subsystems):
    registry.estate = estate(**subsystems)
    return registry


# ── registration ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ESTATE_TOOLS)
def test_registered(name):
    assert name in TOOL_SPECS


def test_descriptions_tell_the_model_these_are_local_not_public():
    """The whole point is the distinction from the intel tools."""
    joined = " ".join(TOOL_SPECS[n].description.lower() for n in ESTATE_TOOLS)
    assert "local" in joined
    assert "deep" in joined


# ── degradation ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ESTATE_TOOLS)
@pytest.mark.asyncio
async def test_missing_subsystem_explains_itself(registry, name):
    """DEEP runs without Pi-hole, Bluetooth or nmap. A tool whose subsystem is
    absent must say so usefully, never raise."""
    registry.estate = estate()
    result = await registry.execute_tool(name, {})
    assert "Traceback" not in result.content
    if not result.ok:
        assert "isn't available" in result.content or "Provide either" in result.content


@pytest.mark.asyncio
async def test_no_estate_at_all_is_survivable(registry):
    """A bare registry (tests, CLI) has no estate attribute."""
    if hasattr(registry, "estate"):
        del registry.estate
    result = await registry.execute_tool("security_events", {})
    assert not result.ok
    assert "isn't available" in result.content


# ── security_events ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_security_events_renders_attack_context(registry):
    timeline = FakeTimeline()
    _with_estate(registry, security_timeline=timeline)

    result = await registry.execute_tool("security_events", {"limit": 5, "severity": "high"})
    assert result.ok
    assert "port_scan" in result.content
    assert "192.168.1.99" in result.content
    assert "T1046" in result.content            # ATT&CK technique surfaced
    assert "CVE-2021-44228" in result.content   # correlated CVE surfaced
    assert timeline.calls == [{"limit": 5, "min_severity": "high"}]


@pytest.mark.asyncio
async def test_security_events_quiet_estate_reads_as_quiet_not_broken(registry):
    _with_estate(registry, security_timeline=FakeTimeline(events=[]))
    result = await registry.execute_tool("security_events", {})
    assert result.ok
    assert "quiet" in result.content.lower()


@pytest.mark.asyncio
async def test_security_events_survives_stats_failure(registry):
    """Stats are a nicety; losing them must not lose the events."""
    class Broken(FakeTimeline):
        def get_stats(self):
            raise RuntimeError("stats backend down")

    _with_estate(registry, security_timeline=Broken())
    result = await registry.execute_tool("security_events", {})
    assert result.ok
    assert "port_scan" in result.content


@pytest.mark.asyncio
async def test_security_events_tolerates_a_bad_limit(registry):
    _with_estate(registry, security_timeline=(t := FakeTimeline()))
    result = await registry.execute_tool("security_events", {"limit": "lots"})
    assert result.ok
    assert t.calls[-1]["limit"] == 20


# ── anomalies ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anomalies_report_observed_against_expected(registry):
    """A z-score without the baseline it deviated from isn't actionable."""
    _with_estate(registry, anomaly_detector=(d := FakeDetector()))
    result = await registry.execute_tool("anomalies", {"hours": 6})
    assert result.ok
    assert "outbound_bytes" in result.content
    assert "observed" in result.content and "expected" in result.content
    assert "z=19.9" in result.content
    assert d.calls == [6]


@pytest.mark.asyncio
async def test_quiet_baselines_read_as_normal(registry):
    _with_estate(registry, anomaly_detector=FakeDetector(found=[]))
    result = await registry.execute_tool("anomalies", {})
    assert result.ok
    assert "baseline" in result.content.lower()


# ── local_devices ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_local_devices_lists_everything_by_default(registry):
    _with_estate(registry, scanner=FakeScanner())
    result = await registry.execute_tool("local_devices", {})
    assert result.ok
    assert "192.168.1.5" in result.content and "192.168.1.99" in result.content
    assert "KNOWN" in result.content and "UNKNOWN" in result.content


@pytest.mark.asyncio
async def test_local_devices_can_filter_to_unknown(registry):
    _with_estate(registry, scanner=FakeScanner())
    result = await registry.execute_tool("local_devices", {"unknown_only": "true"})
    assert result.ok
    assert "192.168.1.99" in result.content
    assert "192.168.1.5" not in result.content


@pytest.mark.asyncio
async def test_local_devices_matches_the_real_scanner_contract():
    """get_devices() is async on the real class; a sync call returns a coroutine."""
    import inspect

    from network.scanner import NetworkScanner

    assert inspect.iscoroutinefunction(NetworkScanner.get_devices)


# ── wifi / dns / stack ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wifi_environment_reports_aps_and_detector_state(registry):
    from network.proximity_monitor import ProximityAP

    class FakeProximity:
        async def get_nearby_aps(self):
            return [ProximityAP(ssid="HomeNet", bssid="aa:bb:cc:00:11:22", signal_dbm=-42,
                                channel=6, encryption="WPA2", is_yours=True, vendor="Ubiquiti"),
                    ProximityAP(ssid="HomeNet", bssid="de:ad:be:ef:00:01", signal_dbm=-71,
                                channel=11, encryption="open")]

    class FakeEvilTwin:
        def status(self):
            return {"active": True, "suspects": 1}

    _with_estate(registry, proximity=FakeProximity(), evil_twin=FakeEvilTwin())
    result = await registry.execute_tool("wifi_environment", {})
    assert result.ok
    assert "HomeNet" in result.content
    assert "de:ad:be:ef:00:01" in result.content   # the impostor BSSID is visible
    assert "Evil-twin detector" in result.content


@pytest.mark.asyncio
async def test_dns_activity_can_scope_to_one_client(registry):
    class FakePihole:
        async def get_summary(self):
            return {"queries_today": 12000, "blocked_today": 850}

        async def get_top_domains(self):
            return {"top_queries": {"example.com": 400}}

        async def get_client_activity(self, client_ip):
            return [{"domain": "c2.badhost.example", "status": "blocked", "time": "03:13"}]

    _with_estate(registry, pihole=FakePihole())

    summary = await registry.execute_tool("dns_activity", {})
    assert summary.ok and "queries_today" in summary.content

    scoped = await registry.execute_tool("dns_activity", {"client_ip": "192.168.1.99"})
    assert scoped.ok
    assert "c2.badhost.example" in scoped.content


@pytest.mark.asyncio
async def test_dns_activity_reports_an_unreachable_pihole_as_failure(registry):
    class DeadPihole:
        async def get_summary(self):
            return None

    _with_estate(registry, pihole=DeadPihole())
    result = await registry.execute_tool("dns_activity", {})
    assert not result.ok
    assert "did not respond" in result.content


@pytest.mark.asyncio
async def test_stack_exposure_empty_result_is_stated_as_meaningful(registry):
    """'Nothing affects you' is an answer, and must not read as a failure."""
    class NoMatches:
        async def run_once(self):
            return []

    _with_estate(registry, global_threat_watch=NoMatches())
    result = await registry.execute_tool("stack_exposure", {})
    assert result.ok
    assert "no current threat-intel items match" in result.content.lower()


@pytest.mark.asyncio
async def test_stack_exposure_surfaces_matches(registry):
    class Matched:
        async def run_once(self):
            return [{"cve": "CVE-2021-44228", "entity": "log4j", "source": "CISA KEV"}]

    _with_estate(registry, global_threat_watch=Matched())
    result = await registry.execute_tool("stack_exposure", {})
    assert result.ok
    assert "CVE-2021-44228" in result.content and "log4j" in result.content


# ── exploit_search ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exploit_search_needs_an_argument(registry):
    registry.estate = estate()
    result = await registry.execute_tool("exploit_search", {})
    assert not result.ok
    assert "cve_id or keyword" in result.content


@pytest.mark.asyncio
async def test_exploit_search_renders_entries(registry, monkeypatch):
    from domains.cybersec.exploit_lookup import ExploitEntry

    async def fake_by_cve(self, cve_id):
        return [ExploitEntry(id="EDB-50592", title="Log4Shell RCE PoC", cve_id=cve_id,
                             platform="java", language="Python", author="researcher",
                             date="2021-12-14", url="https://example.test/50592",
                             verified=True, source="exploit-db")]

    monkeypatch.setattr(
        "domains.cybersec.exploit_lookup.ExploitLookup.search_by_cve", fake_by_cve
    )
    result = await registry.execute_tool("exploit_search", {"cve_id": "CVE-2021-44228"})
    assert result.ok
    assert "EDB-50592" in result.content
    assert "VERIFIED" in result.content


@pytest.mark.asyncio
async def test_exploit_search_absence_is_not_stated_as_proof(registry, monkeypatch):
    """No indexed PoC is not the same as no PoC existing; say so."""
    async def none_found(self, cve_id):
        return []

    monkeypatch.setattr(
        "domains.cybersec.exploit_lookup.ExploitLookup.search_by_cve", none_found
    )
    result = await registry.execute_tool("exploit_search", {"cve_id": "CVE-2000-0001"})
    assert result.ok
    assert "not proof" in result.content.lower()


# ── wiring ───────────────────────────────────────────────────────────────────


def test_server_hands_the_tool_layer_its_subsystems():
    """Regression guard: without this the assistant can query the public
    internet but nothing DEEP has actually observed."""
    import inspect

    from interface import server

    source = inspect.getsource(server)
    assert "deep_tools.estate = services" in source
