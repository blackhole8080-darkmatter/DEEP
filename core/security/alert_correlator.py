"""
core/security/alert_correlator.py

Enriches raw anomaly/threat events with MITRE ATT&CK technique context (and
opportunistic related-CVE signal), and republishes a single `security_alert`
event carrying that context instead of a bare metric name or threat label.

Wiring: construct once with the app's shared EventBus and call `start()`
during startup, after `AnomalyDetector` / `ThreatClassifier` are already
publishing to the bus (order doesn't actually matter — subscription just
needs to happen before the events fire). It only *adds* a new
`security_alert` event; `anomaly_detected` and `threat_classified` keep
firing exactly as before, so nothing else in the app has to change.

Scope note: `anomaly_detected` (ai/anomaly/anomaly_detector.py) and
`threat_classified` (ai/threat/threat_classifier.py) payloads are host-
aggregate — NetworkFlowSnapshot has no per-device IP/MAC field. So the CVE
enrichment here is keyword/class-level ("what's being actively exploited
for this kind of attack right now"), not a hard "device X is running
vulnerable service Y" match. Wiring the network scanner's per-device
open-port/service data (network/scanner.py NetworkDevice.open_ports) into
this correlator is the natural next step for a real device-to-CVE match.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from domains.cybersec.mitre_attack import MITREAttack, Technique

logger = logging.getLogger(__name__)


# threat_classified uses ThreatLabel names (ai/threat/threat_dataset.py);
# anomaly_detected uses free-form NetworkFlowSnapshot/SystemSnapshot metric
# names. Both get mapped to a ATT&CK/CVE search query.
_THREAT_TYPE_QUERIES: Dict[str, str] = {
    "PORT_SCAN": "network service scanning",
    "BRUTE_FORCE": "brute force credential access",
    "ARP_SPOOF": "adversary in the middle",
    "DEAUTH": "denial of wireless service",
    "EXFILTRATION": "data exfiltration",
    "UNKNOWN_THREAT": "impair defenses",
}

_ANOMALY_METRIC_QUERIES: Dict[str, str] = {
    "active_connections": "network service scanning",
    "unique_remote_ips": "command and control",
    "new_connections_ps": "network service scanning",
    "bytes_sent_ps": "data exfiltration",
    "bytes_recv_ps": "data exfiltration",
    "dns_queries_ps": "application layer protocol",
    "connection_duration_avg": "application layer protocol",
}


@dataclass
class SecurityAlert:
    """A correlated, explainable security event ready for the UI/dashboard."""

    id: str
    source_event: str  # "anomaly_detected" | "threat_classified"
    kind: str  # threat_type or anomaly_type/metric
    severity: str
    timestamp: str
    summary: str
    techniques: List[Dict[str, Any]] = field(default_factory=list)
    related_cves: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_event": self.source_event,
            "kind": self.kind,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "techniques": self.techniques,
            "related_cves": self.related_cves,
        }


class AlertCorrelator:
    """
    Subscribes to `anomaly_detected` / `threat_classified`, enriches each
    with MITRE ATT&CK context (+ opportunistic CVE/KEV signal), and
    republishes as `security_alert`.
    """

    def __init__(self, event_bus: Any, cve_intel: Optional[Any] = None) -> None:
        self.event_bus = event_bus
        self._mitre = MITREAttack()
        self._cve_intel = cve_intel  # lazily constructed on first use if not supplied
        self._started = False
        self._counter = 0

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.event_bus.subscribe("anomaly_detected", self._on_anomaly)
        self.event_bus.subscribe("threat_classified", self._on_threat)
        logger.info("AlertCorrelator started")

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self.event_bus.unsubscribe("anomaly_detected", self._on_anomaly)
        self.event_bus.unsubscribe("threat_classified", self._on_threat)

    # ── event handlers ──────────────────────────────────────────────────

    async def _on_anomaly(self, event_name: str, payload: Dict[str, Any]) -> None:
        metric = str(payload.get("metric", "") or "")
        anomaly_type = str(payload.get("anomaly_type", "") or metric or "anomaly")
        query = _ANOMALY_METRIC_QUERIES.get(metric, metric.replace("_", " ") or anomaly_type)

        z_score = payload.get("z_score")
        current = payload.get("current_value")
        expected = payload.get("expected_mean")
        if z_score is not None and current is not None and expected is not None:
            summary = (
                f"Anomalous {metric.replace('_', ' ')}: {current} "
                f"(expected ~{expected}, z={float(z_score):.1f})"
            )
        else:
            summary = f"Anomalous {metric.replace('_', ' ') or anomaly_type}"

        await self._correlate(
            source_event="anomaly_detected",
            kind=anomaly_type,
            severity=str(payload.get("severity", "low") or "low"),
            timestamp=str(payload.get("timestamp", "") or ""),
            query=query,
            summary=summary,
            raw=payload,
        )

    async def _on_threat(self, event_name: str, payload: Dict[str, Any]) -> None:
        threat_type = str(payload.get("threat_type", "UNKNOWN_THREAT") or "UNKNOWN_THREAT")
        query = _THREAT_TYPE_QUERIES.get(threat_type, threat_type.replace("_", " ").lower())
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        severity = "high" if confidence >= 0.85 else "medium" if confidence >= 0.7 else "low"

        await self._correlate(
            source_event="threat_classified",
            kind=threat_type,
            severity=severity,
            timestamp=str(payload.get("timestamp", "") or ""),
            query=query,
            summary=f"{threat_type.replace('_', ' ').title()} classified with {confidence * 100:.0f}% confidence",
            raw=payload,
        )

    # ── correlation core ────────────────────────────────────────────────

    async def _correlate(
        self,
        *,
        source_event: str,
        kind: str,
        severity: str,
        timestamp: str,
        query: str,
        summary: str,
        raw: Dict[str, Any],
    ) -> None:
        techniques = self._match_techniques(query)
        related_cves = await self._match_cves(query)

        self._counter += 1
        alert = SecurityAlert(
            id=f"sa-{int(datetime.now(timezone.utc).timestamp() * 1000)}-{self._counter}",
            source_event=source_event,
            kind=kind,
            severity=severity,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            summary=summary,
            techniques=[
                {
                    "id": t.id,
                    "name": t.name,
                    "tactics": t.tactics,
                    "detection": t.detection,
                    "mitigation": t.mitigation,
                }
                for t in techniques
            ],
            related_cves=related_cves,
            raw=raw,
        )
        logger.info(f"[alert_correlator] {kind} -> {len(techniques)} technique(s), {len(related_cves)} CVE(s)")
        await self.event_bus.publish("security_alert", alert.to_dict())

    def _match_techniques(self, query: str, limit: int = 3) -> List[Technique]:
        try:
            return self._mitre.search_ttp(query)[:limit]
        except Exception as e:
            logger.debug(f"[alert_correlator] mitre search failed: {e}")
            return []

    async def _match_cves(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Opportunistic: recent high-severity CVEs related to this attack class.
        Best-effort only — network failures or a missing NVD response degrade to []."""
        try:
            if self._cve_intel is None:
                from domains.cybersec.cve_intel import CVEIntel

                self._cve_intel = CVEIntel()
            results = await self._cve_intel.search(keyword=query, min_cvss=7.0, days_back=30)
            return [
                {
                    "cve_id": r.cve_id,
                    "severity": r.cvss_v3.severity if r.cvss_v3 else None,
                    "cvss_score": r.cvss_v3.score if r.cvss_v3 else r.cvss_v2_score,
                    "is_kev": r.is_kev,
                    "description": r.description[:200],
                }
                for r in results[:limit]
            ]
        except Exception as e:
            logger.debug(f"[alert_correlator] cve search failed: {e}")
            return []
