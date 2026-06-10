"""
ai/anomaly/network_baseline.py

Records normal network traffic patterns for anomaly detection.
Feeds the threat classifier neural net in Component 4.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class NetworkFlowSnapshot:
    timestamp: str = ""
    hour: int = 0
    day_of_week: int = 0
    bytes_sent_ps: float = 0.0
    bytes_recv_ps: float = 0.0
    packets_sent_ps: float = 0.0
    packets_recv_ps: float = 0.0
    active_connections: int = 0
    unique_remote_ips: int = 0
    dns_queries_ps: float = 0.0
    new_connections_ps: float = 0.0
    connection_duration_avg: float = 0.0


class NetworkBaseline:
    """Records normal network traffic patterns."""

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self.event_bus = event_bus
        self.redis_state = redis_state
        self.settings = Settings()

        self._db_path = Path(getattr(self.settings, "anomaly_db_path", "logs/anomaly/deep_anomaly.db"))
        self._sample_interval = int(getattr(self.settings, "baseline_sample_interval_s", 30))
        self._history_days = int(getattr(self.settings, "baseline_history_days", 30))
        self._min_samples = int(getattr(self.settings, "min_baseline_samples", 10))

        self._started = False
        self._task: Optional[asyncio.Task] = None
        self._last_net = None
        self._last_conn_count = 0

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        await self._init_db()
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("[NetworkBaseline] Started")

    async def stop(self) -> None:
        self._started = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[NetworkBaseline] Stopped")

    async def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS network_baseline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    bytes_sent_ps REAL,
                    bytes_recv_ps REAL,
                    packets_sent_ps REAL,
                    packets_recv_ps REAL,
                    active_connections INTEGER,
                    unique_remote_ips INTEGER,
                    dns_queries_ps REAL,
                    new_connections_ps REAL,
                    connection_duration_avg REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_network_hour_dow ON network_baseline(hour, day_of_week)"
            )
            conn.commit()

    async def _collection_loop(self) -> None:
        while self._started:
            try:
                snapshot = await self._take_network_snapshot()
                await self._store_snapshot(snapshot)
                await self.event_bus.publish("network_flow_recorded", snapshot.__dict__)
            except Exception as exc:
                logger.warning(f"[NetworkBaseline] Collection error: {exc}")
            await asyncio.sleep(self._sample_interval)

    async def _take_network_snapshot(self) -> NetworkFlowSnapshot:
        if not PSUTIL_AVAILABLE:
            return NetworkFlowSnapshot()

        now = datetime.now(timezone.utc)
        net = psutil.net_io_counters()

        bytes_sent_ps = 0.0
        bytes_recv_ps = 0.0
        packets_sent_ps = 0.0
        packets_recv_ps = 0.0
        if self._last_net and net:
            bytes_sent_ps = (net.bytes_sent - self._last_net.bytes_sent) / self._sample_interval
            bytes_recv_ps = (net.bytes_recv - self._last_net.bytes_recv) / self._sample_interval
            packets_sent_ps = (net.packets_sent - self._last_net.packets_sent) / self._sample_interval
            packets_recv_ps = (net.packets_recv - self._last_net.packets_recv) / self._sample_interval
        self._last_net = net

        conns = psutil.net_connections()
        active_connections = len(conns)
        unique_ips = len({c.raddr.ip for c in conns if c.raddr})
        new_conns = max(0, active_connections - self._last_conn_count)
        self._last_conn_count = active_connections

        dns_queries_ps = 0.0

        return NetworkFlowSnapshot(
            timestamp=now.isoformat(),
            hour=now.hour,
            day_of_week=now.weekday(),
            bytes_sent_ps=bytes_sent_ps,
            bytes_recv_ps=bytes_recv_ps,
            packets_sent_ps=packets_sent_ps,
            packets_recv_ps=packets_recv_ps,
            active_connections=active_connections,
            unique_remote_ips=unique_ips,
            dns_queries_ps=dns_queries_ps,
            new_connections_ps=new_conns / self._sample_interval,
            connection_duration_avg=0.0,  # Would need tracking per conn
        )

    async def _store_snapshot(self, snapshot: NetworkFlowSnapshot) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT INTO network_baseline
                (timestamp, hour, day_of_week, bytes_sent_ps, bytes_recv_ps,
                 packets_sent_ps, packets_recv_ps, active_connections,
                 unique_remote_ips, dns_queries_ps, new_connections_ps, connection_duration_avg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp, snapshot.hour, snapshot.day_of_week,
                    snapshot.bytes_sent_ps, snapshot.bytes_recv_ps,
                    snapshot.packets_sent_ps, snapshot.packets_recv_ps,
                    snapshot.active_connections, snapshot.unique_remote_ips,
                    snapshot.dns_queries_ps, snapshot.new_connections_ps,
                    snapshot.connection_duration_avg,
                ),
            )
            conn.commit()

    async def get_baseline_stats(
        self, hour: int, day_of_week: int
    ) -> Optional[dict[str, dict[str, float]]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self._history_days)).isoformat()

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT bytes_sent_ps, bytes_recv_ps, packets_sent_ps, packets_recv_ps,
                       active_connections, unique_remote_ips, dns_queries_ps,
                       new_connections_ps
                FROM network_baseline
                WHERE timestamp >= ?
                  AND hour = ?
                  AND day_of_week = ?
                """,
                (cutoff, hour, day_of_week),
            ).fetchall()

        if len(rows) < self._min_samples:
            return None

        import numpy as np

        metrics = [
            "bytes_sent_ps", "bytes_recv_ps", "packets_sent_ps", "packets_recv_ps",
            "active_connections", "unique_remote_ips", "dns_queries_ps", "new_connections_ps",
        ]
        stats: dict[str, dict[str, float]] = {}
        for metric in metrics:
            values = np.array([r[metric] for r in rows if r[metric] is not None])
            if values.size == 0:
                continue
            stats[metric] = {
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values)), 4),
                "p95": round(float(np.percentile(values, 95)), 4),
            }
        return stats

    async def get_flow_history(self, hours_back: int = 24) -> List[NetworkFlowSnapshot]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM network_baseline WHERE timestamp >= ? ORDER BY timestamp DESC",
                (cutoff,),
            ).fetchall()
        return [NetworkFlowSnapshot(**{k: r[k] for k in r.keys() if k in NetworkFlowSnapshot.__dataclass_fields__}) for r in rows]

    def status(self) -> dict[str, Any]:
        total = 0
        oldest = None
        baseline_ready = False
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                cur = conn.execute("SELECT COUNT(*) FROM network_baseline")
                total = cur.fetchone()[0]
                cur = conn.execute("SELECT MIN(timestamp) FROM network_baseline")
                oldest = cur.fetchone()[0]
            baseline_ready = total >= self._min_samples
        except Exception:
            pass
        return {
            "snapshots_collected": total,
            "baseline_ready": baseline_ready,
            "oldest_snapshot": oldest,
        }
