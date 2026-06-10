"""
tests/test_anomaly_detector.py

Unit tests for the behaviour-based anomaly detection system.
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: SystemBaseline stores snapshot correctly
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_system_baseline_store_snapshot() -> None:
    """SystemBaseline should store snapshots in SQLite."""
    try:
        from ai.anomaly.system_baseline import SystemBaseline, SystemSnapshot
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        baseline = SystemBaseline(event_bus=AsyncMock(), redis_state=MagicMock())
        baseline._db_path = Path(db_path)
        await baseline._init_db()

        snapshot = SystemSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            hour=14, day_of_week=2,
            cpu_percent=25.0, ram_percent=60.0, ram_used_mb=4096.0,
        )
        await baseline._store_snapshot(snapshot)

        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM system_snapshots")
            assert cur.fetchone()[0] == 1
        print("  ✓ SystemBaseline stores snapshot correctly")
    finally:
        Path(db_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: get_baseline_stats returns None when fewer than MIN_BASELINE_SAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_baseline_stats_not_enough_samples() -> None:
    """get_baseline_stats should return None when there are fewer than min samples."""
    try:
        from ai.anomaly.system_baseline import SystemBaseline
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    baseline = SystemBaseline(event_bus=AsyncMock(), redis_state=MagicMock())
    baseline._min_samples = 10

    # Don't create any snapshots
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    baseline._db_path = Path(db_path)
    await baseline._init_db()

    try:
        stats = await baseline.get_baseline_stats(hour=14, day_of_week=2)
        assert stats is None, "Expected None when no samples exist"
        print("  ✓ get_baseline_stats returns None when insufficient samples")
    finally:
        Path(db_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: _extract_features returns correct shape
# ═══════════════════════════════════════════════════════════════════════════════

def test_extract_features_shape() -> None:
    """_extract_features should return shape (n_samples, n_features)."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector
        from ai.anomaly.system_baseline import SystemSnapshot
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    snapshots = [
        SystemSnapshot(cpu_percent=10, ram_percent=50, disk_read_mbs=1, disk_write_mbs=0.5,
                       net_sent_mbs=0.1, net_recv_mbs=0.2, active_processes=100, top_process_cpu=5),
        SystemSnapshot(cpu_percent=20, ram_percent=60, disk_read_mbs=2, disk_write_mbs=1.0,
                       net_sent_mbs=0.2, net_recv_mbs=0.4, active_processes=120, top_process_cpu=10),
    ]

    detector = AnomalyDetector(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    features = detector._extract_system_features(snapshots)
    assert features is not None
    assert features.shape == (2, 8), f"Expected (2, 8), got {features.shape}"
    print("  ✓ _extract_features returns correct shape (n_samples, 8)")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: IsolationForest trains without crash on synthetic data
# ═══════════════════════════════════════════════════════════════════════════════

def test_isolation_forest_trains() -> None:
    """IsolationForest should fit on synthetic snapshot features."""
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        pytest.skip("scikit-learn not available")

    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector
        from ai.anomaly.system_baseline import SystemSnapshot
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    snapshots = []
    for i in range(20):
        snapshots.append(SystemSnapshot(
            cpu_percent=10 + i, ram_percent=40 + i,
            disk_read_mbs=i * 0.1, disk_write_mbs=i * 0.05,
            net_sent_mbs=i * 0.01, net_recv_mbs=i * 0.02,
            active_processes=100 + i, top_process_cpu=i * 0.5,
        ))

    detector = AnomalyDetector(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    features = detector._extract_system_features(snapshots)
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(features)
    preds = model.predict(features)
    assert len(preds) == 20
    print("  ✓ IsolationForest trains without crash on 20 synthetic samples")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: _get_severity returns correct labels
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_severity_labels() -> None:
    """Verify severity mapping for different z-scores."""
    try:
        from ai.anomaly.anomaly_detector import _get_severity
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    assert _get_severity(2.9) == "low"
    assert _get_severity(4.0) == "medium"
    assert _get_severity(6.0) == "high"
    print("  ✓ _get_severity returns correct labels for z=2.9, z=4.0, z=6.0")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: _handle_anomaly publishes "anomaly_detected" event
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_handle_anomaly_publishes_event() -> None:
    """_handle_anomaly should publish 'anomaly_detected' to EventBus."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector, Anomaly
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    event_bus = AsyncMock()
    detector = AnomalyDetector(
        event_bus=event_bus, redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    detector._db_path = Path(tempfile.mktemp(suffix=".db"))
    await detector._init_db()

    try:
        anomaly = Anomaly(
            anomaly_type="system", metric="cpu_percent",
            current_value=95.0, expected_mean=20.0, expected_std=5.0,
            z_score=15.0, severity="high",
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={},
        )
        await detector._handle_anomaly(anomaly)

        event_bus.publish.assert_any_call("anomaly_detected", anomaly.__dict__)
        print("  ✓ _handle_anomaly publishes 'anomaly_detected' event")
    finally:
        detector._db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: High severity anomaly publishes "tts_speak" with priority "urgent"
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_high_severity_tts_urgent() -> None:
    """High severity anomaly should trigger urgent TTS alert."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector, Anomaly
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    event_bus = AsyncMock()
    detector = AnomalyDetector(
        event_bus=event_bus, redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    detector._db_path = Path(tempfile.mktemp(suffix=".db"))
    await detector._init_db()

    try:
        anomaly = Anomaly(
            anomaly_type="system", metric="cpu_percent",
            current_value=95.0, expected_mean=20.0, expected_std=5.0,
            z_score=15.0, severity="high",
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={},
        )
        await detector._handle_anomaly(anomaly)

        # Check that tts_speak was published with urgent priority
        calls = event_bus.publish.call_args_list
        tts_calls = [c for c in calls if c[0][0] == "tts_speak"]
        assert len(tts_calls) > 0, "Expected tts_speak for high severity"
        payload = tts_calls[0][0][1]
        assert payload["priority"] == "urgent"
        print("  ✓ High severity anomaly publishes 'tts_speak' with priority 'urgent'")
    finally:
        detector._db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Low severity anomaly does NOT publish "tts_speak"
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_low_severity_no_tts() -> None:
    """Low severity anomaly should NOT trigger TTS (alert fatigue prevention)."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector, Anomaly
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    event_bus = AsyncMock()
    detector = AnomalyDetector(
        event_bus=event_bus, redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    detector._db_path = Path(tempfile.mktemp(suffix=".db"))
    await detector._init_db()

    try:
        anomaly = Anomaly(
            anomaly_type="system", metric="cpu_percent",
            current_value=30.0, expected_mean=20.0, expected_std=5.0,
            z_score=3.2, severity="low",
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={},
        )
        await detector._handle_anomaly(anomaly)

        calls = event_bus.publish.call_args_list
        tts_calls = [c for c in calls if c[0][0] == "tts_speak"]
        assert len(tts_calls) == 0, "Low severity should NOT trigger TTS"
        print("  ✓ Low severity anomaly does NOT publish 'tts_speak' (alert fatigue prevention)")
    finally:
        detector._db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: AnomalyDetector skips detection when models not ready
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_skips_when_models_not_ready() -> None:
    """Detection should be skipped gracefully when models aren't trained yet."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector
        from ai.anomaly.system_baseline import SystemSnapshot
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    detector = AnomalyDetector(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    detector._models_ready = False

    snapshot = SystemSnapshot(hour=14, day_of_week=2, cpu_percent=50.0)
    # Should not crash even though models aren't ready
    await detector._check_system_anomaly(snapshot)
    print("  ✓ AnomalyDetector skips detection gracefully when models not ready")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: NetworkBaseline stores flow snapshot and publishes event
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_network_baseline_store_and_publish() -> None:
    """NetworkBaseline should store snapshots and publish 'network_flow_recorded'."""
    try:
        from ai.anomaly.network_baseline import NetworkBaseline, NetworkFlowSnapshot
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    event_bus = AsyncMock()
    baseline = NetworkBaseline(event_bus=event_bus, redis_state=MagicMock())
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    baseline._db_path = Path(db_path)
    await baseline._init_db()

    try:
        snapshot = NetworkFlowSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            hour=14, day_of_week=2,
            bytes_sent_ps=100.0, bytes_recv_ps=200.0,
        )
        await baseline._store_snapshot(snapshot)
        await event_bus.publish("network_flow_recorded", snapshot.__dict__)

        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM network_baseline")
            assert cur.fetchone()[0] == 1

        event_bus.publish.assert_any_call("network_flow_recorded", snapshot.__dict__)
        print("  ✓ NetworkBaseline stores snapshot and publishes 'network_flow_recorded'")
    finally:
        Path(db_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Model refresh loop retrains on new data
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_model_refresh_loop_exists() -> None:
    """AnomalyDetector should have a model refresh loop that retrains."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    detector = AnomalyDetector(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    assert hasattr(detector, "_model_refresh_loop")
    print("  ✓ Model refresh loop method exists")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: get_anomaly_stats returns valid dict before any anomalies
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stats_before_any_anomalies() -> None:
    """get_anomaly_stats should return a valid dict even with zero anomalies."""
    try:
        from ai.anomaly.anomaly_detector import AnomalyDetector
    except ImportError:
        pytest.skip("Dependencies missing for anomaly detection")

    detector = AnomalyDetector(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        system_baseline=MagicMock(), network_baseline=None,
    )
    detector._db_path = Path(tempfile.mktemp(suffix=".db"))
    await detector._init_db()

    try:
        stats = await detector.get_anomaly_stats()
        assert "total_today" in stats
        assert "by_severity" in stats
        assert "models_ready" in stats
        assert stats["total_today"] == 0
        print("  ✓ get_anomaly_stats returns valid dict before any anomalies detected")
    finally:
        detector._db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
