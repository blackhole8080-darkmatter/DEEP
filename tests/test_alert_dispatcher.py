"""Alert delivery — mostly tests of what does *not* get sent.

DEEP detected well and delivered nothing: the correlator and the threat watch
published to the bus, the HUD rendered them, and if the HUD wasn't open the
alert existed only in a log nobody reads. These tests pin the gates that make
the delivery path trustworthy — a console that notifies on everything trains
you to ignore it, and one that drops alerts silently can't be relied on either.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List

import pytest

from core.alert_dispatcher import (
    Alert,
    AlertDispatcher,
    Channel,
    DesktopChannel,
    LogChannel,
    WebhookChannel,
    rank,
)
from core.event_bus import EventBus


class RecordingChannel(Channel):
    """Captures deliveries so a test can assert on them."""

    name = "recording"

    def __init__(self, fail: bool = False):
        self.sent: List[Alert] = []
        self._fail = fail

    async def send(self, alert: Alert) -> bool:
        if self._fail:
            raise RuntimeError("channel exploded")
        self.sent.append(alert)
        return True


class ExplodingChannel(Channel):
    name = "exploding"

    async def send(self, alert: Alert) -> bool:
        raise RuntimeError("boom")


@pytest.fixture
def channel():
    return RecordingChannel()


@pytest.fixture
def dispatcher(channel, tmp_path):
    return AlertDispatcher(channels=[channel], min_severity="high", data_dir=tmp_path)


def _alert(severity: str = "high", key: str = "k", title: str = "t") -> Alert:
    return Alert(
        id=f"a_{key}", kind="threat", severity=severity, title=title,
        body="something happened", source="test", dedupe_key=key,
    )


def _open_the_gates(dispatcher: AlertDispatcher) -> None:
    """Neutralise wall-clock-dependent gates so a test asserts one thing.

    Rolling the day here matters: a dispatcher with no saved state has
    ``_today = None``, so its first ``consider()`` correctly zeroes the daily
    counter — which would silently undo a count a test set up beforehand.
    """
    dispatcher._in_quiet_hours = lambda: False  # type: ignore[method-assign]
    dispatcher._roll_day()


# ═══════════════════════════════════════════════════════════════════════════
# The gates
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_an_alert_above_the_floor_is_delivered(dispatcher, channel):
    _open_the_gates(dispatcher)
    assert await dispatcher.consider(_alert("high")) is True
    assert len(channel.sent) == 1
    assert channel.sent[0].title == "t"


@pytest.mark.asyncio
async def test_below_the_floor_is_dropped(dispatcher, channel):
    """Notifying on `info` is how an operator learns to ignore notifications."""
    _open_the_gates(dispatcher)
    for severity in ("info", "low", "medium"):
        assert await dispatcher.consider(_alert(severity, key=severity)) is False
    assert channel.sent == []
    assert dispatcher.status()["counts"]["below_floor"] == 3


@pytest.mark.asyncio
async def test_the_same_alert_twice_is_delivered_once(dispatcher, channel):
    _open_the_gates(dispatcher)
    await dispatcher.consider(_alert(key="same"))
    assert await dispatcher.consider(_alert(key="same")) is False
    assert len(channel.sent) == 1
    assert dispatcher.status()["counts"]["duplicate"] == 1


@pytest.mark.asyncio
async def test_a_burst_is_rate_limited_to_one(dispatcher, channel):
    """One incident emits many alerts; a person should get one notification."""
    _open_the_gates(dispatcher)
    for i in range(5):
        await dispatcher.consider(_alert(key=f"distinct-{i}"))
    assert len(channel.sent) == 1
    assert dispatcher.status()["counts"]["rate_limited"] == 4


@pytest.mark.asyncio
async def test_suppression_is_reported_on_the_next_delivery(dispatcher, channel):
    """Silent drops are what make an alerting system untrustworthy."""
    _open_the_gates(dispatcher)
    for i in range(4):
        await dispatcher.consider(_alert(key=f"burst-{i}"))
    assert dispatcher.status()["suppressed_since_last"] == 3

    dispatcher._last_delivery = 0.0        # rate-limit window elapses
    await dispatcher.consider(_alert(key="after"))

    delivered = channel.sent[-1]
    assert delivered.suppressed == 3
    assert "+3 more suppressed" in delivered.render()
    assert dispatcher.status()["suppressed_since_last"] == 0


@pytest.mark.asyncio
async def test_quiet_hours_hold_a_high_alert(dispatcher, channel):
    dispatcher._in_quiet_hours = lambda: True  # type: ignore[method-assign]
    assert await dispatcher.consider(_alert("high")) is False
    assert channel.sent == []
    assert dispatcher.status()["counts"]["quiet_hours"] == 1


@pytest.mark.asyncio
async def test_critical_overrides_quiet_hours_and_the_rate_limit(dispatcher, channel):
    """Waking you is what `critical` is for; if it shouldn't, it isn't critical."""
    dispatcher._in_quiet_hours = lambda: True  # type: ignore[method-assign]
    dispatcher._last_delivery = time.time()
    dispatcher._delivered_today = dispatcher.MAX_PER_DAY

    assert await dispatcher.consider(_alert("critical", key="c")) is True
    assert len(channel.sent) == 1


@pytest.mark.asyncio
async def test_critical_is_still_deduplicated(dispatcher, channel):
    """Overriding the gates does not license notifying about one thing forever."""
    dispatcher._in_quiet_hours = lambda: True  # type: ignore[method-assign]
    await dispatcher.consider(_alert("critical", key="same"))
    assert await dispatcher.consider(_alert("critical", key="same")) is False
    assert len(channel.sent) == 1


@pytest.mark.asyncio
async def test_the_daily_cap_holds(dispatcher, channel):
    _open_the_gates(dispatcher)
    dispatcher._delivered_today = dispatcher.MAX_PER_DAY
    assert await dispatcher.consider(_alert(key="over")) is False
    assert dispatcher.status()["counts"]["rate_limited"] == 1


def test_the_quiet_window_wraps_around_midnight(dispatcher, monkeypatch):
    """23:00-07:00 crosses midnight; a naive range check is False all night."""
    import core.alert_dispatcher as mod

    class _Clock(datetime):
        hour_value = 0

        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 1, 1, cls.hour_value)

    monkeypatch.setattr(mod, "datetime", _Clock)
    cases = [(23, True), (2, True), (6, True), (7, False), (12, False), (22, False)]
    for hour, quiet in cases:
        _Clock.hour_value = hour
        assert dispatcher._in_quiet_hours() is quiet, f"hour {hour}"


def test_severity_ranking_is_total_and_ordered():
    assert rank("critical") > rank("high") > rank("medium") > rank("low") > rank("info")
    assert rank("CRITICAL") == rank("critical")
    assert rank(None) == rank("info"), "an absent severity must not outrank anything"
    assert rank("nonsense") == rank("info")


# ═══════════════════════════════════════════════════════════════════════════
# Reading the bus events
# ═══════════════════════════════════════════════════════════════════════════


def test_a_kev_match_on_your_own_stack_is_high_by_construction():
    """The feed publishes no severity — but KEV means actively exploited."""
    alert = AlertDispatcher.normalise("world_threat_match", {
        "source": "CISA KEV",
        "cve_id": "CVE-2021-44228",
        "title": "Apache Log4j2 RCE",
        "url": "https://example.test/kev",
        "matched_entity": "log4j",
    })
    assert alert is not None
    assert alert.severity == "high"
    assert "CVE-2021-44228" in alert.title
    assert "log4j" in alert.title
    assert alert.url == "https://example.test/kev"
    assert alert.dedupe_key == "kev:CVE-2021-44228:log4j"


def test_a_correlated_alert_carries_its_attack_and_cve_context():
    """The context is the reason the alert is actionable rather than noise."""
    alert = AlertDispatcher.normalise("security_alert_correlated", {
        "id": "corr-1",
        "kind": "anomaly",
        "severity": "critical",
        "summary": "Beaconing to a known C2 from 192.168.1.42",
        "techniques": ["T1071.001", "T1041"],
        "related_cves": ["CVE-2023-1234"],
        "source_event": "anomaly_detected",
    })
    assert alert is not None
    assert alert.severity == "critical"
    assert "T1071.001" in alert.body
    assert "CVE-2023-1234" in alert.body
    assert alert.context["techniques"] == ["T1071.001", "T1041"]


def test_a_raw_device_alert_keys_on_the_device():
    """Two devices doing the same bad thing are two alerts, not a duplicate."""
    first = AlertDispatcher.normalise("security_alert", {
        "event_type": "new_device", "severity": "high",
        "title": "Unknown device joined", "device_ip": "192.168.1.50",
    })
    second = AlertDispatcher.normalise("security_alert", {
        "event_type": "new_device", "severity": "high",
        "title": "Unknown device joined", "device_ip": "192.168.1.51",
    })
    assert first.dedupe_key != second.dedupe_key


def test_an_empty_payload_produces_nothing_rather_than_a_blank_alert():
    assert AlertDispatcher.normalise("security_alert", {}) is None
    assert AlertDispatcher.normalise("security_alert_correlated", {}) is None
    assert AlertDispatcher.normalise("world_threat_match", {}) is None


@pytest.mark.asyncio
async def test_it_delivers_from_a_real_event_bus(tmp_path):
    """End to end: publish what the correlator publishes, get a notification."""
    bus = EventBus()
    await bus.start()
    channel = RecordingChannel()
    dispatcher = AlertDispatcher(
        event_bus=bus, channels=[channel], min_severity="high", data_dir=tmp_path
    )
    _open_the_gates(dispatcher)
    await dispatcher.start()

    delivered: List[Dict[str, Any]] = []

    async def _capture(_name, payload):
        delivered.append(payload)

    bus.subscribe("alert_delivered", _capture)

    await bus.publish("security_alert_correlated", {
        "id": "corr-9", "kind": "threat", "severity": "critical",
        "summary": "Evil twin AP impersonating your SSID",
        "techniques": ["T1557"], "related_cves": [],
    })

    assert len(channel.sent) == 1
    assert "Evil twin" in channel.sent[0].title
    assert len(delivered) == 1, "the HUD must be able to see what went out"
    assert delivered[0]["channels"] == ["recording"]
    await dispatcher.stop()


@pytest.mark.asyncio
async def test_stopping_unsubscribes(tmp_path):
    bus = EventBus()
    await bus.start()
    channel = RecordingChannel()
    dispatcher = AlertDispatcher(
        event_bus=bus, channels=[channel], min_severity="high", data_dir=tmp_path
    )
    _open_the_gates(dispatcher)
    await dispatcher.start()
    await dispatcher.stop()

    await bus.publish("security_alert_correlated", {
        "severity": "critical", "summary": "after stop",
    })
    assert channel.sent == []


# ═══════════════════════════════════════════════════════════════════════════
# Channels
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_one_failing_channel_does_not_block_the_others(tmp_path):
    good = RecordingChannel()
    dispatcher = AlertDispatcher(
        channels=[ExplodingChannel(), good], min_severity="high", data_dir=tmp_path
    )
    _open_the_gates(dispatcher)

    assert await dispatcher.consider(_alert("high")) is True
    assert len(good.sent) == 1
    assert dispatcher.recent()[0]["channels"] == ["recording"]


@pytest.mark.asyncio
async def test_the_log_channel_always_works(caplog):
    """With nothing configured there must still be a record of the alert."""
    import logging

    with caplog.at_level(logging.WARNING, logger="core.alert_dispatcher"):
        assert await LogChannel().send(_alert("critical", title="disk on fire")) is True
    assert "disk on fire" in caplog.text
    assert "CRITICAL" in caplog.text


@pytest.mark.asyncio
async def test_a_headless_host_reports_desktop_as_unavailable_not_broken():
    channel = DesktopChannel()
    status = channel.status()
    assert status["name"] == "desktop"
    if not channel.available:
        assert await channel.send(_alert()) is False
        assert status["detail"], "an unavailable channel must say why"


@pytest.mark.asyncio
async def test_the_webhook_never_echoes_its_url():
    """For Slack, Discord and ntfy the URL *is* the credential."""
    secret = "https://hooks.example.test/services/T000/B000/SUPERSECRETTOKEN"
    channel = WebhookChannel(secret)
    assert "SUPERSECRETTOKEN" not in repr(channel.status())
    assert channel.status()["configured"] is True


@pytest.mark.asyncio
async def test_an_unreachable_webhook_fails_without_raising():
    channel = WebhookChannel("https://nothing-here.invalid/hook", timeout_s=2)
    assert await channel.send(_alert()) is False
    assert channel.status()["detail"], "the failure reason must be inspectable"


def test_the_webhook_is_off_unless_a_url_is_configured(monkeypatch):
    """It is the only channel that sends DEEP's observations off the machine."""
    from core.alert_dispatcher import _default_channels

    monkeypatch.delenv("DEEP_ALERT_WEBHOOK", raising=False)
    assert not any(c.name == "webhook" for c in _default_channels())

    monkeypatch.setenv("DEEP_ALERT_WEBHOOK", "https://hooks.example.test/x")
    assert any(c.name == "webhook" for c in _default_channels())


def test_the_log_channel_is_always_present(monkeypatch):
    from core.alert_dispatcher import _default_channels

    monkeypatch.setenv("DEEP_ALERT_DESKTOP", "0")
    monkeypatch.delenv("DEEP_ALERT_WEBHOOK", raising=False)
    assert [c.name for c in _default_channels()] == ["log"]


# ═══════════════════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dedupe_survives_a_restart(tmp_path):
    """Otherwise a crash loop re-notifies about the same thing every boot."""
    first = AlertDispatcher(channels=[RecordingChannel()], min_severity="high",
                            data_dir=tmp_path)
    _open_the_gates(first)
    await first.consider(_alert(key="persistent"))

    channel = RecordingChannel()
    reborn = AlertDispatcher(channels=[channel], min_severity="high", data_dir=tmp_path)
    _open_the_gates(reborn)
    assert await reborn.consider(_alert(key="persistent")) is False
    assert channel.sent == []


@pytest.mark.asyncio
async def test_unreadable_state_does_not_stop_alerting(tmp_path):
    (tmp_path / "dispatcher_state.json").write_text("{ this is not json")
    channel = RecordingChannel()
    dispatcher = AlertDispatcher(channels=[channel], min_severity="high",
                                 data_dir=tmp_path)
    _open_the_gates(dispatcher)
    assert await dispatcher.consider(_alert("high")) is True


def test_the_floor_is_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEP_ALERT_MIN_SEVERITY", "critical")
    assert AlertDispatcher(channels=[], data_dir=tmp_path).min_severity == "critical"
    monkeypatch.delenv("DEEP_ALERT_MIN_SEVERITY")
    assert AlertDispatcher(channels=[], data_dir=tmp_path).min_severity == "high"


# ═══════════════════════════════════════════════════════════════════════════
# API surface
# ═══════════════════════════════════════════════════════════════════════════


def test_status_endpoint_exposes_the_gates(client):
    r = client.get("/api/alerts/status")
    assert r.status_code == 200
    body = r.json()
    assert body["min_severity"] in ("info", "low", "medium", "high", "critical")
    assert "quiet_hours" in body
    assert any(c["name"] == "log" for c in body["channels"])


def test_recent_endpoint_returns_a_list(client):
    r = client.get("/api/alerts/recent?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json()["alerts"], list)


def test_the_test_endpoint_rejects_a_bad_severity(client):
    r = client.post("/api/alerts/test", json={"severity": "catastrophic"})
    assert r.status_code == 422
    assert "critical" in r.json()["detail"]


def test_the_test_endpoint_reports_per_channel_results(client):
    r = client.post("/api/alerts/test", json={"severity": "high", "title": "probe"})
    assert r.status_code == 200
    body = r.json()
    assert body["sent"]["title"] == "probe"
    assert body["channels"]["log"] is True
