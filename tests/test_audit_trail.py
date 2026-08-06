"""
tests/test_audit_trail.py

Validation suite for the Immutable Audit Trail and Session Manager.

Run:
    python tests/test_audit_trail.py
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import EventBus
from core.audit_trail import AuditTrail, EntryType
from core.session_manager import SessionManager


# ── Helpers ──────────────────────────────────────────────────────────────

async def _cleanup_db(db_path: str):
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: AuditTrail creates DB and SYSTEM_START entry on start()
# ═══════════════════════════════════════════════════════════════════════════════

async def test_audit_trail_creates_db_and_system_start():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-001"
    await audit.start()

    # Check DB exists
    assert os.path.exists(db_path)

    # Check SYSTEM_START entry
    entries = await audit.query(entry_type="SYSTEM_START")
    assert len(entries) >= 1
    assert entries[0].entry_type == "SYSTEM_START"
    assert entries[0].actor == "system"

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ AuditTrail creates DB and SYSTEM_START entry on start()")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: log() inserts entry with valid hash
# ═══════════════════════════════════════════════════════════════════════════════

async def test_log_inserts_valid_hash():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit2.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-002"
    await audit.start()

    entry = await audit.log(EntryType.COMMAND, "aryan", "Command: lights on")
    assert entry.entry_hash is not None
    assert len(entry.entry_hash) == 64  # SHA-256 hex

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ log() inserts entry with valid SHA-256 hash")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Hash chain — second entry's prev_hash equals first entry's entry_hash
# ═══════════════════════════════════════════════════════════════════════════════

async def test_hash_chain_links():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit3.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-003"
    await audit.start()

    e1 = await audit.log(EntryType.COMMAND, "aryan", "cmd1")
    e2 = await audit.log(EntryType.RESPONSE, "deep", "resp1")

    assert e2.prev_hash == e1.entry_hash

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ Hash chain: second entry's prev_hash equals first entry's entry_hash")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: verify_integrity() returns intact=True for unmodified log
# ═══════════════════════════════════════════════════════════════════════════════

async def test_verify_intact_log():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit4.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-004"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd1")
    await audit.log(EntryType.COMMAND, "aryan", "cmd2")

    report = await audit.verify_integrity()
    assert report.intact is True
    assert len(report.failures) == 0

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ verify_integrity() returns intact=True for unmodified log")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: verify_integrity() returns intact=False after manual corruption
# ═══════════════════════════════════════════════════════════════════════════════

async def test_verify_detects_tampering():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit5.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-005"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd1")
    await audit.log(EntryType.COMMAND, "aryan", "cmd2")
    await audit.stop()

    # Tamper with the DB directly — change an action field
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE audit_log SET action = 'HACKED' WHERE id = 2")
    conn.commit()
    conn.close()

    # Reopen audit (last_hash will be stale but verify reads from DB)
    audit2 = AuditTrail(event_bus=bus, redis_state=redis)
    audit2._db_path = db_path
    audit2._session_id = "test-session-005"
    report = await audit2.verify_integrity()

    assert report.intact is False
    assert 2 in report.failures

    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ verify_integrity() detects tampering and identifies correct failure ID")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: INTEGRITY_FAIL entry is logged when tampering detected
# ═══════════════════════════════════════════════════════════════════════════════

async def test_integrity_fail_entry_logged():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit6.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-006"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd1")
    await audit.stop()

    # Tamper
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE audit_log SET action = 'HACKED' WHERE id = 2")
    conn.commit()
    conn.close()

    audit2 = AuditTrail(event_bus=bus, redis_state=redis)
    audit2._db_path = db_path
    audit2._session_id = "test-session-006"
    await audit2.verify_integrity()

    # Check that INTEGRITY_FAIL was itself logged
    entries = await audit2.query(entry_type="INTEGRITY_FAIL")
    assert len(entries) >= 1
    assert "tampering" in entries[0].action.lower() or "broken" in entries[0].action.lower()

    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ INTEGRITY_FAIL entry is logged when tampering detected")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: query() filters correctly by entry_type
# ═══════════════════════════════════════════════════════════════════════════════

async def test_query_filters_by_type():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit7.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-007"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd")
    await audit.log(EntryType.THREAT_DETECTED, "system", "threat")
    await audit.log(EntryType.COMMAND, "aryan", "cmd2")

    commands = await audit.query(entry_type="COMMAND")
    assert len(commands) == 2
    for e in commands:
        assert e.entry_type == "COMMAND"

    threats = await audit.query(entry_type="THREAT_DETECTED")
    assert len(threats) == 1

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ query() filters correctly by entry_type")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: query() pagination works (limit/offset)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_query_pagination():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit8.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-008"
    await audit.start()

    for i in range(5):
        await audit.log(EntryType.COMMAND, "aryan", f"cmd{i}")

    page1 = await audit.query(entry_type="COMMAND", limit=2, offset=0)
    assert len(page1) == 2

    page2 = await audit.query(entry_type="COMMAND", limit=2, offset=2)
    assert len(page2) == 2

    page3 = await audit.query(entry_type="COMMAND", limit=2, offset=4)
    assert len(page3) == 1

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ query() pagination works (limit/offset)")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: get_threat_log() returns only security entries
# ═══════════════════════════════════════════════════════════════════════════════

async def test_get_threat_log():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit9.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-009"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd")
    await audit.log(EntryType.THREAT_DETECTED, "system", "scan")
    await audit.log(EntryType.IP_BLOCKED, "deep", "blocked")

    threats = await audit.get_threat_log(hours=24)
    assert len(threats) == 2
    for e in threats:
        assert e.entry_type in ("THREAT_DETECTED", "IP_BLOCKED", "INTEGRITY_FAIL")

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ get_threat_log() returns only security entries")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: export_session() writes valid text file
# ═══════════════════════════════════════════════════════════════════════════════

async def test_export_session():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit10.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-010"
    audit._export_dir = "logs/sessions_test"
    await audit.start()

    await audit.log(EntryType.COMMAND, "aryan", "cmd1")
    await audit.stop()

    path = await audit.export_session("test-session-010", format="text")
    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    assert "COMMAND" in content
    assert "cmd1" in content

    await bus.stop()
    await _cleanup_db(db_path)
    # cleanup export
    try:
        os.remove(path)
        os.rmdir("logs/sessions_test")
    except Exception:
        pass
    print("  ✓ export_session() writes valid text file")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Wildcard subscription auto-logs user_command and threat_detected
# ═══════════════════════════════════════════════════════════════════════════════

async def test_wildcard_auto_log():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit11.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-011"
    await audit.start()

    # Wait for SYSTEM_START to settle
    await asyncio.sleep(0.05)

    # Publish events that should be auto-logged
    await bus.publish("user_command", {"text": "turn on lights"})
    await asyncio.sleep(0.05)
    await bus.publish("threat_detected", {"threat_type": "port_scan", "source_ip": "10.0.0.1"})
    await asyncio.sleep(0.05)

    commands = await audit.query(entry_type="COMMAND")
    threats = await audit.query(entry_type="THREAT_DETECTED")

    assert any("turn on lights" in e.action for e in commands)
    assert any("port_scan" in e.action for e in threats)

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ Wildcard subscription auto-logs user_command and threat_detected")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: SessionManager counter increments on events
# ═══════════════════════════════════════════════════════════════════════════════

async def test_session_manager_counters():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit12.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-012"
    await audit.start()

    mgr = SessionManager(event_bus=bus, audit_trail=audit, redis_state=redis)
    await mgr.start()

    await bus.publish("user_command", {"text": "cmd1"})
    await bus.publish("user_command", {"text": "cmd2"})
    await bus.publish("threat_detected", {"threat_type": "scan"})
    await asyncio.sleep(0.05)

    assert mgr._current is not None
    assert mgr._current.command_count == 2
    assert mgr._current.threat_count == 1

    await mgr.end_session()
    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    print("  ✓ SessionManager counter increments on events")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: end_session() sets ended_at and exports log
# ═══════════════════════════════════════════════════════════════════════════════

async def test_end_session():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    db_path = "logs/audit/test_audit13.db"
    await _cleanup_db(db_path)

    audit = AuditTrail(event_bus=bus, redis_state=redis)
    audit._db_path = db_path
    audit._session_id = "test-session-013"
    audit._export_dir = "logs/sessions_test"
    await audit.start()

    mgr = SessionManager(event_bus=bus, audit_trail=audit, redis_state=redis)
    await mgr.start()

    await bus.publish("user_command", {"text": "cmd1"})
    await asyncio.sleep(0.05)

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("session_ended", capture)

    await mgr.end_session()
    await asyncio.sleep(0.05)

    assert mgr._current.ended_at is not None
    assert len(captured) == 1
    assert captured[0]["payload"]["command_count"] == 1
    assert captured[0]["payload"]["summary_path"] is not None

    await audit.stop()
    await bus.stop()
    await _cleanup_db(db_path)
    try:
        os.rmdir("logs/sessions_test")
    except Exception:
        pass
    print("  ✓ end_session() sets ended_at and exports log")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Immutable Audit Trail & Session Manager validation...\n")

    await test_audit_trail_creates_db_and_system_start()
    await test_log_inserts_valid_hash()
    await test_hash_chain_links()
    await test_verify_intact_log()
    await test_verify_detects_tampering()
    await test_integrity_fail_entry_logged()
    await test_query_filters_by_type()
    await test_query_pagination()
    await test_get_threat_log()
    await test_export_session()
    await test_wildcard_auto_log()
    await test_session_manager_counters()
    await test_end_session()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All Audit Trail & Session Manager tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
