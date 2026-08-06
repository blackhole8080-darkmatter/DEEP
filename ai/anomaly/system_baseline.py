"""
ai/anomaly/system_baseline.py

Collects and stores normal system behaviour profiles across time-of-day and day-of-week.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import closing
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

MONITORED_METRICS = [
    "cpu_percent", "ram_percent", "ram_used_mb",
    "disk_read_mbs", "disk_write_mbs",
    "net_sent_mbs", "net_recv_mbs",
    "active_processes", "top_process_cpu",
]


@dataclass
class SystemSnapshot:
    timestamp: str = ""
    hour: int = 0
    day_of_week: int = 0
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_mb: float = 0.0
    disk_read_mbs: float = 0.0
    disk_write_mbs: float = 0.0
    net_sent_mbs: float = 0.0
    net_recv_mbs: float = 0.0
    active_processes: int = 0
    top_process_cpu: float = 0.0
    top_process_name: str = ""
    gpu_percent: float | None = None


class SystemBaseline:
    """Collects and stores normal system behaviour profiles."""

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
        self._last_disk = None
        self._last_net = None

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        await self._init_db()
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("[SystemBaseline] Started")

    async def stop(self) -> None:
        self._started = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[SystemBaseline] Stopped")

    async def _init_db(self) -> None:
        """Create the system_snapshots table."""
        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    cpu_percent REAL,
                    ram_percent REAL,
                    ram_used_mb REAL,
                    disk_read_mbs REAL,
                    disk_write_mbs REAL,
                    net_sent_mbs REAL,
                    net_recv_mbs REAL,
                    active_processes INTEGER,
                    top_process_cpu REAL,
                    top_process_name TEXT,
                    gpu_percent REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_system_hour_dow ON system_snapshots(hour, day_of_week)"
            )
            conn.commit()

    async def _collection_loop(self) -> None:
        """Collect snapshots every sample_interval seconds."""
        while self._started:
            try:
                snapshot = await self._take_snapshot()
                await self._store_snapshot(snapshot)

                if self.redis_state:
                    try:
                        await self.redis_state.set_global(
                            "current_system_snapshot", snapshot.__dict__
                        )
                    except Exception as exc:
                        logger.debug(f"Redis snapshot sync error: {exc}")

                await self.event_bus.publish("system_snapshot_collected", snapshot.__dict__)

            except Exception as exc:
                logger.warning(f"[SystemBaseline] Collection error: {exc}")

            await asyncio.sleep(self._sample_interval)

    async def _take_snapshot(self) -> SystemSnapshot:
        """Capture current system state."""
        if not PSUTIL_AVAILABLE:
            return SystemSnapshot()

        now = datetime.now(timezone.utc)

        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()

        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()

        # Compute deltas for disk and network rates
        disk_read_mbs = 0.0
        disk_write_mbs = 0.0
        if self._last_disk and disk:
            disk_read_mbs = (disk.read_bytes - self._last_disk.read_bytes) / (1024**2) / self._sample_interval
            disk_write_mbs = (disk.write_bytes - self._last_disk.write_bytes) / (1024**2) / self._sample_interval
        self._last_disk = disk

        net_sent_mbs = 0.0
        net_recv_mbs = 0.0
        if self._last_net and net:
            net_sent_mbs = (net.bytes_sent - self._last_net.bytes_sent) / (1024**2) / self._sample_interval
            net_recv_mbs = (net.bytes_recv - self._last_net.bytes_recv) / (1024**2) / self._sample_interval
        self._last_net = net

        # Process info
        active_procs = 0
        top_cpu = 0.0
        top_name = ""
        try:
            for p in psutil.process_iter(["name", "cpu_percent"]):
                active_procs += 1
                cpu_pct = p.info.get("cpu_percent") or 0.0
                if cpu_pct > top_cpu:
                    top_cpu = cpu_pct
                    top_name = p.info.get("name", "")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        gpu_pct = None
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_pct = gpus[0].load * 100
        except ImportError:
            pass

        return SystemSnapshot(
            timestamp=now.isoformat(),
            hour=now.hour,
            day_of_week=now.weekday(),
            cpu_percent=cpu,
            ram_percent=ram.percent,
            ram_used_mb=ram.used / (1024**2),
            disk_read_mbs=disk_read_mbs,
            disk_write_mbs=disk_write_mbs,
            net_sent_mbs=net_sent_mbs,
            net_recv_mbs=net_recv_mbs,
            active_processes=active_procs,
            top_process_cpu=top_cpu,
            top_process_name=top_name,
            gpu_percent=gpu_pct,
        )

    async def _store_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Persist snapshot to SQLite."""
        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.execute(
                """
                INSERT INTO system_snapshots
                (timestamp, hour, day_of_week, cpu_percent, ram_percent, ram_used_mb,
                 disk_read_mbs, disk_write_mbs, net_sent_mbs, net_recv_mbs,
                 active_processes, top_process_cpu, top_process_name, gpu_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp, snapshot.hour, snapshot.day_of_week,
                    snapshot.cpu_percent, snapshot.ram_percent, snapshot.ram_used_mb,
                    snapshot.disk_read_mbs, snapshot.disk_write_mbs,
                    snapshot.net_sent_mbs, snapshot.net_recv_mbs,
                    snapshot.active_processes, snapshot.top_process_cpu,
                    snapshot.top_process_name, snapshot.gpu_percent,
                ),
            )
            conn.commit()

    async def get_baseline_stats(
        self, hour: int, day_of_week: int
    ) -> Optional[dict[str, dict[str, float]]]:
        """Return mean/std/p95/p99 for each metric at this hour/day."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self._history_days)).isoformat()

        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT cpu_percent, ram_percent, ram_used_mb,
                       disk_read_mbs, disk_write_mbs, net_sent_mbs, net_recv_mbs,
                       active_processes, top_process_cpu
                FROM system_snapshots
                WHERE timestamp >= ?
                  AND hour = ?
                  AND day_of_week = ?
                """,
                (cutoff, hour, day_of_week),
            ).fetchall()

        if len(rows) < self._min_samples:
            return None

        import numpy as np

        stats: dict[str, dict[str, float]] = {}
        for metric in MONITORED_METRICS:
            values = np.array([r[metric] for r in rows if r[metric] is not None])
            if values.size == 0:
                continue
            stats[metric] = {
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values)), 4),
                "p95": round(float(np.percentile(values, 95)), 4),
                "p99": round(float(np.percentile(values, 99)), 4),
            }

        return stats

    async def get_snapshot_history(
        self, hours_back: int = 24
    ) -> List[SystemSnapshot]:
        """Return recent snapshots."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()

        with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM system_snapshots
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                """,
                (cutoff,),
            ).fetchall()

        # Only map columns that are actual dataclass fields — the DB row also
        # has an 'id' primary key which SystemSnapshot doesn't accept.
        _fields = SystemSnapshot.__dataclass_fields__
        return [SystemSnapshot(**{k: r[k] for k in r.keys() if k in _fields}) for r in rows]

    def status(self) -> dict[str, Any]:
        """Return operational status."""
        total = 0
        oldest = None
        baseline_ready = False
        try:
            with closing(sqlite3.connect(str(self._db_path))) as conn, conn:
                cur = conn.execute("SELECT COUNT(*) FROM system_snapshots")
                total = cur.fetchone()[0]
                cur = conn.execute("SELECT MIN(timestamp) FROM system_snapshots")
                oldest = cur.fetchone()[0]
            baseline_ready = total >= self._min_samples
        except Exception:
            pass

        return {
            "snapshots_collected": total,
            "oldest_snapshot": oldest,
            "baseline_ready": baseline_ready,
            "collection_running": self._started,
        }
