"""
ai/anomaly/anomaly_detector.py

Uses IsolationForest to detect statistical outliers in system and network behaviour.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

from ai.anomaly.system_baseline import SystemBaseline, SystemSnapshot, MONITORED_METRICS
from ai.anomaly.network_baseline import NetworkBaseline, NetworkFlowSnapshot

logger = logging.getLogger(__name__)

SYSTEM_FEATURES = [
    "cpu_percent", "ram_percent",
    "disk_read_mbs", "disk_write_mbs",
    "net_sent_mbs", "net_recv_mbs",
    "active_processes", "top_process_cpu",
]

NETWORK_FEATURES = [
    "bytes_sent_ps", "bytes_recv_ps",
    "packets_sent_ps", "packets_recv_ps",
    "active_connections", "unique_remote_ips",
    "dns_queries_ps", "new_connections_ps",
]


@dataclass
class Anomaly:
    anomaly_type: str  # "system" | "network"
    metric: str
    current_value: float
    expected_mean: float
    expected_std: float
    z_score: float
    severity: str  # "low" | "medium" | "high"
    timestamp: str
    context: dict


class AnomalyDetector:
    """Detects statistical anomalies in system and network behaviour."""

    def __init__(
        self,
        event_bus: Any,
        redis_state: Any,
        system_baseline: SystemBaseline,
        network_baseline: Optional[NetworkBaseline] = None,
    ) -> None:
        self.event_bus = event_bus
        self.redis_state = redis_state
        self.system_baseline = system_baseline
        self.network_baseline = network_baseline
        self.settings = Settings()

        self._db_path = Path(getattr(self.settings, "anomaly_db_path", "logs/anomaly/deep_anomaly.db"))
        # Baseline tables this detector has already reported as absent, so the
        # warning isn't repeated for all 24 hour buckets on every training pass.
        self._missing_tables: set[str] = set()
        self._model_path = Path(getattr(self.settings, "anomaly_model_path", "ai/models/anomaly_models.pkl"))
        self._check_interval = int(getattr(self.settings, "anomaly_check_interval_s", 60))
        self._model_refresh_days = int(getattr(self.settings, "anomaly_model_refresh_days", 7))
        self._contamination = float(getattr(self.settings, "anomaly_contamination", 0.05))
        self._z_threshold = float(getattr(self.settings, "anomaly_z_threshold", 3.0))
        self._min_samples = int(getattr(self.settings, "min_baseline_samples", 10))

        self._started = False
        self._detection_task: Optional[asyncio.Task] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._models_ready = False
        self._system_models: Dict[int, Any] = {}
        self._network_models: Dict[int, Any] = {}
        self._hours_covered = 0
        self._last_anomaly: Optional[str] = None

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        await self._init_db()
        await self._train_models_if_ready()
        self._detection_task = asyncio.create_task(self._detection_loop())
        self._refresh_task = asyncio.create_task(self._model_refresh_loop())
        logger.info("[AnomalyDetector] Started")

    async def stop(self) -> None:
        self._started = False
        for task in (self._detection_task, self._refresh_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("[AnomalyDetector] Stopped")

    async def _init_db(self) -> None:
        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    current_value REAL,
                    expected_mean REAL,
                    expected_std REAL,
                    z_score REAL,
                    severity TEXT,
                    context_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp)"
            )
            conn.commit()

    async def _train_models_if_ready(self) -> None:
        if not SKLEARN_AVAILABLE or not NUMPY_AVAILABLE:
            logger.warning("[AnomalyDetector] sklearn/numpy unavailable — anomaly detection disabled")
            return

        trained_any = False
        for hour in range(24):
            # System model
            system_snapshots = await self._get_system_snapshots_for_hour(hour)
            if len(system_snapshots) >= self._min_samples:
                features = self._extract_system_features(system_snapshots)
                model = IsolationForest(
                    n_estimators=100,
                    contamination=self._contamination,
                    random_state=42,
                )
                model.fit(features)
                self._system_models[hour] = model
                trained_any = True

            # Network model
            if self.network_baseline:
                network_snapshots = await self._get_network_snapshots_for_hour(hour)
                if len(network_snapshots) >= self._min_samples:
                    features = self._extract_network_features(network_snapshots)
                    model = IsolationForest(
                        n_estimators=100,
                        contamination=self._contamination,
                        random_state=42,
                    )
                    model.fit(features)
                    self._network_models[hour] = model
                    trained_any = True

        if trained_any:
            self._models_ready = True
            # Union, not just the system models: a host with network baselines
            # but no system ones (or vice versa) trained fine but reported
            # "0 hours covered" while claiming to be ready, which reads as a
            # contradiction in the status and in the HUD.
            self._hours_covered = len(set(self._system_models) | set(self._network_models))
            if JOBLIB_AVAILABLE:
                joblib.dump(
                    {"system": self._system_models, "network": self._network_models},
                    str(self._model_path),
                )
            await self.event_bus.publish("anomaly_models_trained", {
                "hours_covered": self._hours_covered,
            })
            logger.info(f"[AnomalyDetector] Models trained for {self._hours_covered} hours")

    def _snapshot_rows(self, table: str, hour: int) -> List[sqlite3.Row]:
        """Read one hour of baseline snapshots, tolerating an absent table.

        The snapshot tables are owned by SystemBaseline and NetworkBaseline,
        not by this class — it only reads them. If a baseline failed to start
        (no psutil, unwritable path, DB removed underneath us) its table won't
        exist, and server.py logs that failure and carries on to start this
        detector anyway. Letting the missing table raise here meant a baseline
        problem took anomaly detection down with it, silently: the server
        caught the second failure too, so everything still looked healthy while
        nothing was being detected.

        No snapshots is the honest answer in that case. Detection stays dark
        until data exists, which is what happens on a fresh install regardless.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        try:
            with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE timestamp >= ? AND hour = ?",  # noqa: S608 - fixed literals, never user input
                    (cutoff, hour),
                ).fetchall()
            # Only clear the marker once the read actually succeeded — clearing
            # it first meant every call re-armed the warning and logged again.
            self._missing_tables.discard(table)
            return rows
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            # Training walks all 24 hour buckets, so warn once per table rather
            # than 24 times per pass. Cleared again below once the table shows
            # up, so a later disappearance is still reported.
            if table not in self._missing_tables:
                self._missing_tables.add(table)
                logger.warning(
                    "[AnomalyDetector] '%s' does not exist yet — its baseline has not "
                    "started or has failed. Treating as no snapshots.", table,
                )
            return []

    async def _get_system_snapshots_for_hour(self, hour: int) -> List[SystemSnapshot]:
        rows = self._snapshot_rows("system_snapshots", hour)
        _fields = SystemSnapshot.__dataclass_fields__
        return [SystemSnapshot(**{k: r[k] for k in r.keys() if k in _fields}) for r in rows]

    async def _get_network_snapshots_for_hour(self, hour: int) -> List[NetworkFlowSnapshot]:
        rows = self._snapshot_rows("network_baseline", hour)
        _fields = NetworkFlowSnapshot.__dataclass_fields__
        return [NetworkFlowSnapshot(**{k: r[k] for k in r.keys() if k in _fields}) for r in rows]

    def _extract_system_features(self, snapshots: List[SystemSnapshot]) -> Any:
        if not NUMPY_AVAILABLE:
            return None
        data = []
        for s in snapshots:
            data.append([
                s.cpu_percent, s.ram_percent,
                s.disk_read_mbs, s.disk_write_mbs,
                s.net_sent_mbs, s.net_recv_mbs,
                s.active_processes, s.top_process_cpu,
            ])
        arr = np.array(data, dtype=np.float32)
        # Normalize per-feature
        mins = arr.min(axis=0)
        maxs = arr.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0
        return (arr - mins) / ranges

    def _extract_network_features(self, snapshots: List[NetworkFlowSnapshot]) -> Any:
        if not NUMPY_AVAILABLE:
            return None
        data = []
        for s in snapshots:
            data.append([
                s.bytes_sent_ps, s.bytes_recv_ps,
                s.packets_sent_ps, s.packets_recv_ps,
                s.active_connections, s.unique_remote_ips,
                s.dns_queries_ps, s.new_connections_ps,
            ])
        arr = np.array(data, dtype=np.float32)
        mins = arr.min(axis=0)
        maxs = arr.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0
        return (arr - mins) / ranges

    async def _detection_loop(self) -> None:
        while self._started:
            try:
                if self._models_ready:
                    snapshot = await self.system_baseline._take_snapshot()
                    await self._check_system_anomaly(snapshot)

                    if self.network_baseline:
                        net_snapshot = await self.network_baseline._take_network_snapshot()
                        await self._check_network_anomaly(net_snapshot)
            except Exception as exc:
                logger.warning(f"[AnomalyDetector] Detection error: {exc}")
            await asyncio.sleep(self._check_interval)

    async def _check_system_anomaly(self, snapshot: SystemSnapshot) -> None:
        hour = snapshot.hour
        if hour not in self._system_models:
            return

        features = self._extract_system_features([snapshot])
        if features is None or features.size == 0:
            return

        is_anomaly = self._system_models[hour].predict(features)[0] == -1
        if not is_anomaly:
            return

        stats = await self.system_baseline.get_baseline_stats(hour, snapshot.day_of_week)
        if not stats:
            return

        for metric in MONITORED_METRICS:
            current = getattr(snapshot, metric)
            if metric not in stats:
                continue
            mean = stats[metric]["mean"]
            std = stats[metric]["std"]
            if std > 0:
                z = abs(current - mean) / std
                if z > self._z_threshold:
                    anomaly = Anomaly(
                        anomaly_type="system",
                        metric=metric,
                        current_value=current,
                        expected_mean=mean,
                        expected_std=std,
                        z_score=z,
                        severity=_get_severity(z),
                        timestamp=snapshot.timestamp,
                        context=snapshot.__dict__,
                    )
                    await self._handle_anomaly(anomaly)

    async def _check_network_anomaly(self, snapshot: NetworkFlowSnapshot) -> None:
        hour = snapshot.hour
        if hour not in self._network_models:
            return

        features = self._extract_network_features([snapshot])
        if features is None or features.size == 0:
            return

        is_anomaly = self._network_models[hour].predict(features)[0] == -1
        if not is_anomaly:
            return

        stats = await self.network_baseline.get_baseline_stats(hour, snapshot.day_of_week) if self.network_baseline else None
        if not stats:
            return

        for metric in NETWORK_FEATURES:
            current = getattr(snapshot, metric)
            if metric not in stats:
                continue
            mean = stats[metric]["mean"]
            std = stats[metric]["std"]
            if std > 0:
                z = abs(current - mean) / std
                if z > self._z_threshold:
                    anomaly = Anomaly(
                        anomaly_type="network",
                        metric=metric,
                        current_value=current,
                        expected_mean=mean,
                        expected_std=std,
                        z_score=z,
                        severity=_get_severity(z),
                        timestamp=snapshot.timestamp,
                        context=snapshot.__dict__,
                    )
                    await self._handle_anomaly(anomaly)

    async def _handle_anomaly(self, anomaly: Anomaly) -> None:
        """Log anomaly, publish events, and optionally speak alert."""
        import json

        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.execute(
                """
                INSERT INTO anomalies
                (timestamp, anomaly_type, metric, current_value, expected_mean,
                 expected_std, z_score, severity, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    anomaly.timestamp, anomaly.anomaly_type, anomaly.metric,
                    anomaly.current_value, anomaly.expected_mean,
                    anomaly.expected_std, anomaly.z_score, anomaly.severity,
                    json.dumps(anomaly.context, default=str),
                ),
            )
            conn.commit()

        self._last_anomaly = anomaly.timestamp

        if self.redis_state:
            try:
                await self.redis_state.set_global("latest_anomaly", anomaly.__dict__)
            except Exception as exc:
                logger.debug(f"Redis anomaly sync error: {exc}")

        await self.event_bus.publish("anomaly_detected", anomaly.__dict__)

        # Severity-based response
        if anomaly.severity == "high":
            await self.event_bus.publish("tts_speak", {
                "text": (
                    f"Anomaly detected. {anomaly.metric.replace('_', ' ')} "
                    f"is {anomaly.current_value:.1f}, expected around "
                    f"{anomaly.expected_mean:.1f}. Z-score: {anomaly.z_score:.1f}."
                ),
                "priority": "urgent",
            })
        elif anomaly.severity == "medium":
            await self.event_bus.publish("tts_speak", {
                "text": f"Unusual {anomaly.metric.replace('_', ' ')} detected.",
                "priority": "normal",
            })
        # Low severity: log only, no TTS (avoid alert fatigue)

    async def get_recent_anomalies(self, hours: int = 24) -> List[Anomaly]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM anomalies WHERE timestamp >= ? ORDER BY timestamp DESC",
                (cutoff,),
            ).fetchall()
        import json
        return [
            Anomaly(
                anomaly_type=r["anomaly_type"],
                metric=r["metric"],
                current_value=r["current_value"],
                expected_mean=r["expected_mean"],
                expected_std=r["expected_std"],
                z_score=r["z_score"],
                severity=r["severity"],
                timestamp=r["timestamp"],
                context=json.loads(r["context_json"]) if r["context_json"] else {},
            )
            for r in rows
        ]

    async def get_anomaly_stats(self) -> dict[str, Any]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total_today = 0
        by_severity = {"low": 0, "medium": 0, "high": 0}
        most_metric = None
        max_count = 0

        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM anomalies WHERE timestamp LIKE ?",
                (f"{today}%",),
            )
            total_today = cur.fetchone()[0]

            cur = conn.execute(
                "SELECT severity, COUNT(*) FROM anomalies WHERE timestamp LIKE ? GROUP BY severity",
                (f"{today}%",),
            )
            for sev, count in cur.fetchall():
                by_severity[sev] = count

            cur = conn.execute(
                "SELECT metric, COUNT(*) FROM anomalies WHERE timestamp LIKE ? GROUP BY metric ORDER BY COUNT(*) DESC LIMIT 1",
                (f"{today}%",),
            )
            row = cur.fetchone()
            if row:
                most_metric = row[0]

        baseline_age = 0
        try:
            with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
                cur = conn.execute("SELECT MIN(timestamp) FROM system_snapshots")
                oldest = cur.fetchone()[0]
                if oldest:
                    oldest_dt = datetime.fromisoformat(oldest)
                    baseline_age = (datetime.now(timezone.utc) - oldest_dt).days
        except Exception:
            pass

        return {
            "total_today": total_today,
            "by_severity": by_severity,
            "most_anomalous_metric": most_metric,
            "models_ready": self._models_ready,
            "hours_covered": self._hours_covered,
            "baseline_age_days": baseline_age,
        }

    async def _model_refresh_loop(self) -> None:
        while self._started:
            try:
                await asyncio.sleep(self._model_refresh_days * 86400)
                if self._started:
                    logger.info("[AnomalyDetector] Refreshing models with new baseline data")
                    await self._train_models_if_ready()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"[AnomalyDetector] Refresh loop error: {exc}")

    def status(self) -> dict[str, Any]:
        total_today = 0
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM anomalies WHERE timestamp LIKE ?",
                    (f"{today}%",),
                )
                total_today = cur.fetchone()[0]
        except Exception:
            pass

        return {
            "models_ready": self._models_ready,
            "hours_covered": self._hours_covered,
            "anomalies_today": total_today,
            "last_anomaly": self._last_anomaly,
            "detection_running": self._started and self._models_ready,
            "contamination": self._contamination,
        }


def _get_severity(z_score: float) -> str:
    if z_score > 5.0:
        return "high"
    if z_score > 3.5:
        return "medium"
    return "low"
