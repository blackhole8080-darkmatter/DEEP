"""
tests/test_threat_dataset_builder.py

Regression test for ThreatDatasetBuilder._load_threat_flows(): it used to
select a.threat_type, a column that doesn't exist on audit_log (only
payload_json does — see core/audit_trail.py), so the query always raised and
was swallowed by a broad except, silently returning [] every time. The "real
threat events" half of the training pipeline had never actually produced
data. This builds a real temp SQLite DB matching both tables' actual schemas
and confirms threat flows now load with the correct label.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.threat.threat_dataset import ThreatDatasetBuilder, ThreatLabel, THREAT_TYPE_MAP


def _make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "deep_anomaly.db"
    with closing(sqlite3.connect(str(db_path))) as conn, conn:
        conn.execute("""
            CREATE TABLE network_baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, hour INTEGER NOT NULL, day_of_week INTEGER NOT NULL,
                bytes_sent_ps REAL, bytes_recv_ps REAL, packets_sent_ps REAL, packets_recv_ps REAL,
                active_connections INTEGER, unique_remote_ips INTEGER, dns_queries_ps REAL,
                new_connections_ps REAL, connection_duration_avg REAL
            )
        """)
        conn.execute("""
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                entry_type TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
                payload_json TEXT, device_id TEXT, session_id TEXT,
                prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, verified INTEGER DEFAULT 1
            )
        """)
        conn.execute("CREATE TABLE anomalies (timestamp TEXT, anomaly_type TEXT)")

        ts = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO network_baseline (timestamp, hour, day_of_week, bytes_sent_ps, bytes_recv_ps, "
            "packets_sent_ps, packets_recv_ps, active_connections, unique_remote_ips, dns_queries_ps, "
            "new_connections_ps, connection_duration_avg) VALUES (?, 12, 2, 5.0, 5.0, 3.0, 3.0, 40, 60, 1.0, 20.0, 0.2)",
            (ts,),
        )
        # Mirrors what AuditTrail._on_any_event actually stores for a real
        # threat_classified event: payload_json holds threat_type in
        # ThreatLabel.name form ("PORT_SCAN"), not THREAT_TYPE_MAP's
        # lowercase keys.
        conn.execute(
            "INSERT INTO audit_log (timestamp, entry_type, actor, action, payload_json, prev_hash, entry_hash) "
            "VALUES (?, 'THREAT_DETECTED', 'system', 'threat_classified', ?, 'x', 'y')",
            (ts, json.dumps({"threat_type": "PORT_SCAN", "confidence": 0.9})),
        )
    return db_path


def test_load_threat_flows_reads_real_audit_entries(tmp_path) -> None:
    """Previously always returned [] due to the a.threat_type bug."""
    db_path = _make_db(tmp_path)
    builder = ThreatDatasetBuilder(network_baseline=None, anomaly_db_path=str(db_path))

    import asyncio
    result = asyncio.run(builder._load_threat_flows())

    assert len(result) == 1
    flow, label = result[0]
    assert flow.active_connections == 40
    assert label == ThreatLabel.PORT_SCAN


def test_extract_threat_label_handles_both_casings_and_garbage() -> None:
    # Real classifier output: ThreatLabel.name style, uppercase
    assert ThreatDatasetBuilder._extract_threat_label(
        json.dumps({"threat_type": "BRUTE_FORCE"})
    ) == ThreatLabel.BRUTE_FORCE

    # Hand-labeled / THREAT_TYPE_MAP style, lowercase
    assert ThreatDatasetBuilder._extract_threat_label(
        json.dumps({"threat_type": "arp_spoof"})
    ) == ThreatLabel.ARP_SPOOF

    # alert_correlator.py's security_alert_correlated payload uses "kind"
    assert ThreatDatasetBuilder._extract_threat_label(
        json.dumps({"kind": "EXFILTRATION"})
    ) == ThreatLabel.EXFILTRATION

    # Missing / unparseable / unrecognized -> UNKNOWN_THREAT, not a crash
    assert ThreatDatasetBuilder._extract_threat_label(None) == ThreatLabel.UNKNOWN_THREAT
    assert ThreatDatasetBuilder._extract_threat_label("not json") == ThreatLabel.UNKNOWN_THREAT
    assert ThreatDatasetBuilder._extract_threat_label(json.dumps({"threat_type": "made_up"})) == ThreatLabel.UNKNOWN_THREAT


def test_threat_type_map_keys_are_all_lowercase() -> None:
    """Guards the assumption _extract_threat_label relies on."""
    assert all(k == k.lower() for k in THREAT_TYPE_MAP)
