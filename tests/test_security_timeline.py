"""
tests/test_security_timeline.py

Unit tests for SecurityTimeline: merges raw `security_alert` (device-level)
and `security_alert_correlated` (enriched anomaly/threat) events into one
severity-scored, time-ordered feed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_bus import EventBus
from core.security.security_timeline import SecurityTimeline


@pytest.mark.asyncio
async def test_merges_raw_and_correlated_events() -> None:
    bus = EventBus()
    await bus.start()
    timeline = SecurityTimeline(bus)
    await timeline.start()

    # Raw device-level event (network_monitor.py schema)
    await bus.publish("security_alert", {
        "id": "raw-1",
        "timestamp": "2026-07-30T10:00:00+00:00",
        "event_type": "new_device",
        "severity": "medium",
        "title": "New device joined the network",
        "device_mac": "AA:BB:CC:DD:EE:FF",
        "device_ip": "192.168.1.50",
    })

    # Enriched event (alert_correlator.py schema)
    await bus.publish("security_alert_correlated", {
        "id": "sa-2",
        "source_event": "threat_classified",
        "kind": "PORT_SCAN",
        "severity": "high",
        "timestamp": "2026-07-30T10:05:00+00:00",
        "summary": "Port Scan classified with 92% confidence",
        "techniques": [{"id": "T1046", "name": "Network Service Scanning"}],
        "related_cves": [],
    })

    timeline_items = timeline.get_timeline(limit=10)
    assert len(timeline_items) == 2
    # Sorted newest-first
    assert timeline_items[0]["id"] == "sa-2"
    assert timeline_items[1]["id"] == "raw-1"
    assert timeline_items[0]["techniques"][0]["id"] == "T1046"
    assert timeline_items[1]["device_mac"] == "AA:BB:CC:DD:EE:FF"

    await timeline.stop()


@pytest.mark.asyncio
async def test_min_severity_filter() -> None:
    bus = EventBus()
    await bus.start()
    timeline = SecurityTimeline(bus)
    await timeline.start()

    await bus.publish("security_alert_correlated", {
        "id": "low-1", "kind": "port_scan", "severity": "low",
        "timestamp": "2026-07-30T10:00:00+00:00", "summary": "low sev",
    })
    await bus.publish("security_alert_correlated", {
        "id": "high-1", "kind": "brute_force", "severity": "high",
        "timestamp": "2026-07-30T10:01:00+00:00", "summary": "high sev",
    })

    all_items = timeline.get_timeline(limit=10)
    assert len(all_items) == 2

    high_only = timeline.get_timeline(limit=10, min_severity="high")
    assert len(high_only) == 1
    assert high_only[0]["id"] == "high-1"

    await timeline.stop()


@pytest.mark.asyncio
async def test_stats_counts_by_severity_and_kind() -> None:
    bus = EventBus()
    await bus.start()
    timeline = SecurityTimeline(bus)
    await timeline.start()

    await bus.publish("security_alert_correlated", {
        "id": "a", "kind": "PORT_SCAN", "severity": "high",
        "timestamp": "2026-07-30T10:00:00+00:00", "summary": "x",
    })
    await bus.publish("security_alert_correlated", {
        "id": "b", "kind": "PORT_SCAN", "severity": "high",
        "timestamp": "2026-07-30T10:01:00+00:00", "summary": "y",
    })
    await bus.publish("security_alert_correlated", {
        "id": "c", "kind": "BRUTE_FORCE", "severity": "medium",
        "timestamp": "2026-07-30T10:02:00+00:00", "summary": "z",
    })

    stats = timeline.get_stats()
    assert stats["total"] == 3
    assert stats["by_severity"]["high"] == 2
    assert stats["by_severity"]["medium"] == 1
    assert stats["by_kind"]["PORT_SCAN"] == 2

    await timeline.stop()
