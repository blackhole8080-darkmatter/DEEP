"""
tests/test_alert_correlator.py

Unit tests for AlertCorrelator: anomaly_detected / threat_classified events
get enriched with MITRE ATT&CK context and republished as security_alert.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_bus import EventBus
from core.security.alert_correlator import AlertCorrelator


@pytest.mark.asyncio
async def test_threat_classified_gets_correlated_with_attack_technique() -> None:
    """A PORT_SCAN threat_classified event should map to an ATT&CK technique
    (T1046 - Network Service Scanning is in the built-in technique index)."""
    bus = EventBus()
    await bus.start()

    correlator = AlertCorrelator(bus)
    # Avoid a real network call to NVD in tests.
    correlator._match_cves = AsyncMock(return_value=[])
    await correlator.start()

    received = []

    async def _capture(event_name: str, payload: dict) -> None:
        received.append(payload)

    bus.subscribe("security_alert", _capture)

    await bus.publish("threat_classified", {
        "threat_type": "PORT_SCAN",
        "confidence": 0.92,
        "probabilities": {"PORT_SCAN": 0.92},
        "source": "neural_classifier",
        "timestamp": "2026-07-30T00:00:00+00:00",
    })

    assert len(received) == 1
    alert = received[0]
    assert alert["source_event"] == "threat_classified"
    assert alert["kind"] == "PORT_SCAN"
    assert alert["severity"] == "high"  # confidence 0.92 >= 0.85
    technique_ids = [t["id"] for t in alert["techniques"]]
    assert "T1046" in technique_ids

    await correlator.stop()


@pytest.mark.asyncio
async def test_anomaly_detected_gets_correlated() -> None:
    """A network anomaly on active_connections should also produce a
    security_alert with technique context, even without a CVE hit."""
    bus = EventBus()
    await bus.start()

    correlator = AlertCorrelator(bus)
    correlator._match_cves = AsyncMock(return_value=[])
    await correlator.start()

    received = []

    async def _capture(event_name: str, payload: dict) -> None:
        received.append(payload)

    bus.subscribe("security_alert", _capture)

    await bus.publish("anomaly_detected", {
        "anomaly_type": "network",
        "metric": "active_connections",
        "current_value": 400,
        "expected_mean": 40,
        "expected_std": 10,
        "z_score": 36.0,
        "severity": "high",
        "timestamp": "2026-07-30T00:00:00+00:00",
    })

    assert len(received) == 1
    alert = received[0]
    assert alert["source_event"] == "anomaly_detected"
    assert alert["severity"] == "high"
    assert "active connections" in alert["summary"].lower()
    assert len(alert["techniques"]) > 0

    await correlator.stop()


@pytest.mark.asyncio
async def test_cve_lookup_failure_degrades_gracefully() -> None:
    """If the CVE search blows up (no network, bad NVD response, etc.) the
    alert should still publish with an empty related_cves list, not crash."""
    bus = EventBus()
    await bus.start()

    correlator = AlertCorrelator(bus)
    await correlator.start()

    received = []

    async def _capture(event_name: str, payload: dict) -> None:
        received.append(payload)

    bus.subscribe("security_alert", _capture)

    with patch("domains.cybersec.cve_intel.CVEIntel.search", side_effect=RuntimeError("no network")):
        await bus.publish("threat_classified", {
            "threat_type": "BRUTE_FORCE",
            "confidence": 0.9,
            "timestamp": "2026-07-30T00:00:00+00:00",
        })

    assert len(received) == 1
    assert received[0]["related_cves"] == []

    await correlator.stop()
