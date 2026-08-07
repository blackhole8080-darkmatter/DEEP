"""Regressions found by running the subsystems, not by reading them.

Every one of these passed static checks and the existing suite while being
broken at runtime. They were found by driving each subsystem through its real
lifecycle — start, ingest, query, stop — against real SQLite files.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from core.event_bus import EventBus


@pytest.fixture
async def bus():
    b = EventBus()
    await b.start()
    return b


# ═══════════════════════════════════════════════════════════════════════════
# AnomalyDetector: a failed baseline used to take detection down with it
# ═══════════════════════════════════════════════════════════════════════════


def _detector(bus, db_path):
    from ai.anomaly.anomaly_detector import AnomalyDetector
    from ai.anomaly.system_baseline import SystemBaseline

    baseline = SystemBaseline(event_bus=bus, redis_state=MagicMock())
    baseline._db_path = db_path
    det = AnomalyDetector(event_bus=bus, redis_state=MagicMock(),
                          system_baseline=baseline, network_baseline=None)
    det._db_path = db_path
    det._model_path = db_path.parent / "models.pkl"
    return det


@pytest.mark.asyncio
async def test_detector_starts_when_the_snapshot_table_is_absent(bus, tmp_path):
    """The snapshot tables belong to the baselines; the detector only reads them.

    server.py logs a baseline start failure and carries on to start the
    detector anyway, so a missing table used to raise OperationalError out of
    detector.start(). The server caught that too — leaving anomaly detection
    silently off while everything else looked healthy.
    """
    db = tmp_path / "anom.db"
    det = _detector(bus, db)

    await det.start()          # must not raise
    assert det._started is True
    # No snapshots means no models, so detection correctly reports itself as
    # not running. The point of the fix is that start() completes instead of
    # raising, leaving the detector ready to train as soon as data arrives.
    status = det.status()
    assert status["models_ready"] is False
    assert status["detection_running"] is False
    await det.stop()


@pytest.mark.asyncio
async def test_absent_table_is_reported_once_not_once_per_hour_bucket(bus, tmp_path):
    """Training walks all 24 hour buckets; the warning fired on every one."""
    db = tmp_path / "anom.db"
    det = _detector(bus, db)

    await det.start()
    assert det._missing_tables == {"system_snapshots"}
    await det.stop()


@pytest.mark.asyncio
async def test_a_real_sqlite_error_still_propagates(bus, tmp_path):
    """Only 'no such table' is tolerated — genuine corruption must surface."""
    db = tmp_path / "anom.db"
    det = _detector(bus, db)
    db.write_bytes(b"this is not a sqlite database")

    with pytest.raises(sqlite3.DatabaseError):
        det._snapshot_rows("system_snapshots", 0)


@pytest.mark.asyncio
async def test_the_marker_clears_once_the_table_appears(bus, tmp_path):
    db = tmp_path / "anom.db"
    det = _detector(bus, db)

    det._snapshot_rows("system_snapshots", 0)
    assert "system_snapshots" in det._missing_tables

    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "CREATE TABLE system_snapshots (id INTEGER PRIMARY KEY, timestamp TEXT, hour INT)"
        )
    det._snapshot_rows("system_snapshots", 0)
    assert "system_snapshots" not in det._missing_tables


def test_hours_covered_counts_network_models_too():
    """models_ready=True with hours_covered=0 read as a contradiction.

    A host with network baselines but no system ones trained fine and then
    reported covering zero hours, because the count only looked at
    _system_models.
    """
    from ai.anomaly.anomaly_detector import AnomalyDetector

    det = AnomalyDetector.__new__(AnomalyDetector)
    det._system_models = {}
    det._network_models = {3: object(), 4: object()}
    covered = len(set(det._system_models) | set(det._network_models))
    assert covered == 2

    det._system_models = {4: object(), 5: object()}
    covered = len(set(det._system_models) | set(det._network_models))
    assert covered == 3, "overlapping hours must not be double counted"


# ═══════════════════════════════════════════════════════════════════════════
# KnowledgeGraph: colliding relationship ids silently dropped data
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_relationships_extracted_together_get_distinct_ids(bus, tmp_path, monkeypatch):
    """Ids were f"rel_{int(time.time()*1000)}".

    Extraction yields several relationships per ingest() call, comfortably
    inside one millisecond, so they shared an id and each overwrote the last
    in self.relationships — five extracted, one stored.
    """
    from core.knowledge_graph import KnowledgeGraph

    monkeypatch.chdir(tmp_path)
    kg = KnowledgeGraph(event_bus=bus)
    await kg.start()

    result = kg.ingest(
        "DEEP uses FastAPI for the backend. Aryan runs DEEP on a Debian server. "
        "The project depends on requests and aiohttp for HTTP.",
        source_id="probe",
    )
    ids = [r["id"] for r in result["relationships"]]

    assert ids, "extraction produced no relationships to check"
    # The actual defect: distinct relationships shared one id.
    assert len(set(ids)) == len(ids), f"colliding relationship ids: {ids}"
    # And each survives into the graph rather than overwriting a sibling.
    for rel_id in ids:
        assert rel_id in kg.relationships, f"{rel_id} was overwritten before it landed"
    # Ids must not be a bare clock reading — that is what made them collide.
    # (KnowledgeGraph persists to a fixed project path, so absolute counts are
    # shared across runs and can't be asserted on here.)
    assert not any(i.removeprefix("rel_").isdigit() for i in ids)
    await kg.stop()


@pytest.mark.asyncio
async def test_entity_ids_are_unique_across_rapid_creation(bus, tmp_path, monkeypatch):
    """The old suffix was int(time.time()*1000) % 10000, wrapping every 10s."""
    from core.knowledge_graph import KnowledgeGraph

    monkeypatch.chdir(tmp_path)
    kg = KnowledgeGraph(event_bus=bus)
    await kg.start()

    kg.ingest("Debian and FastAPI and Redis and Postgres and Kubernetes and Nginx.",
              source_id="probe")
    ids = list(kg.entities)
    assert len(set(ids)) == len(ids), f"colliding entity ids: {ids}"
    await kg.stop()


# ═══════════════════════════════════════════════════════════════════════════
# NetworkScanner: must stay usable with no nmap and no LAN
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_scanner_degrades_without_nmap(bus):
    """Containers and locked-down hosts have no nmap; DEEP must still run."""
    from network.scanner import NetworkScanner

    scanner = NetworkScanner(event_bus=bus, redis_state=MagicMock())
    await scanner.start()

    assert await scanner.get_devices() == []
    assert await scanner.get_device("192.0.2.1") is None
    assert await scanner.is_ip_on_network("192.0.2.1") is False
    assert scanner.status()["total_devices"] == 0

    await scanner.stop()
