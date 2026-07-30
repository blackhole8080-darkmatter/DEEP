"""
core/security/security_timeline.py

In-memory rolling timeline that merges the two live security event streams —
raw device-level `security_alert` (core/security/network_monitor.py,
network/evil_twin_detector.py) and enriched `security_alert_correlated`
(core/security/alert_correlator.py) — into one severity-scored, time-ordered
feed for the dashboard.

Purely a read-side aggregator: it doesn't change what either upstream module
publishes, it just also listens and keeps a bounded history so the HUD has
one place to poll (`GET /api/security/timeline`) instead of stitching
together security.py + threat.py + anomaly.py separately.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


class SecurityTimeline:
    def __init__(self, event_bus: Any, max_history: int = 300) -> None:
        self.event_bus = event_bus
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max_history)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.event_bus.subscribe("security_alert", self._on_raw_alert)
        self.event_bus.subscribe("security_alert_correlated", self._on_correlated_alert)
        logger.info("SecurityTimeline started")

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self.event_bus.unsubscribe("security_alert", self._on_raw_alert)
        self.event_bus.unsubscribe("security_alert_correlated", self._on_correlated_alert)

    # ── ingest ──────────────────────────────────────────────────────────

    async def _on_raw_alert(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Device-level events from network_monitor.py / evil_twin_detector.py
        (SecurityEvent.to_dict(): id, timestamp, event_type, severity, title,
        description, device_mac, device_ip, ...)."""
        self._history.append({
            "id": payload.get("id") or f"raw-{len(self._history)}",
            "source": "network_monitor",
            "kind": payload.get("event_type") or payload.get("type") or "security_event",
            "severity": str(payload.get("severity", "info") or "info").lower(),
            "timestamp": payload.get("timestamp", "") or "",
            "summary": payload.get("title") or payload.get("description") or "Security event",
            "techniques": [],
            "related_cves": [],
            "device_mac": payload.get("device_mac"),
            "device_ip": payload.get("device_ip"),
        })

    async def _on_correlated_alert(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Enriched events from alert_correlator.py (SecurityAlert.to_dict())."""
        self._history.append({
            "id": payload.get("id") or f"corr-{len(self._history)}",
            "source": payload.get("source_event", "correlated"),
            "kind": payload.get("kind", "threat"),
            "severity": str(payload.get("severity", "low") or "low").lower(),
            "timestamp": payload.get("timestamp", "") or "",
            "summary": payload.get("summary", ""),
            "techniques": payload.get("techniques", []),
            "related_cves": payload.get("related_cves", []),
            "device_mac": None,
            "device_ip": None,
        })

    # ── read side ───────────────────────────────────────────────────────

    def get_timeline(self, limit: int = 50, min_severity: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self._history)
        if min_severity and min_severity.lower() in _SEVERITY_RANK:
            threshold = _SEVERITY_RANK[min_severity.lower()]
            items = [i for i in items if _SEVERITY_RANK.get(i["severity"], 0) >= threshold]
        items.sort(key=lambda i: i.get("timestamp") or "", reverse=True)
        return items[:limit]

    def get_stats(self) -> Dict[str, Any]:
        items = list(self._history)
        by_severity: Dict[str, int] = {}
        by_kind: Dict[str, int] = {}
        for i in items:
            by_severity[i["severity"]] = by_severity.get(i["severity"], 0) + 1
            by_kind[i["kind"]] = by_kind.get(i["kind"], 0) + 1
        return {"total": len(items), "by_severity": by_severity, "by_kind": by_kind}

    def status(self) -> Dict[str, Any]:
        return {"started": self._started, "history_size": len(self._history)}
