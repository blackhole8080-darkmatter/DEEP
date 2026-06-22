"""
core/audit_trail.py

Immutable audit trail with SHA-256 hash chaining.
Every action DEEP takes is permanently logged with
tamper-evident hash chaining — any modification breaks
the chain and is detectable.
"""

from __future__ import annotations

import asyncio
from contextlib import closing
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    logger.warning("aiosqlite not installed — AuditTrail will use sync sqlite3 fallback")

# ── Data models ─────────────────────────────────────────────────────────


class EntryType:
    COMMAND = "COMMAND"
    RESPONSE = "RESPONSE"
    SKILL_INVOKED = "SKILL_INVOKED"
    APP_LAUNCHED = "APP_LAUNCHED"
    APP_KILLED = "APP_KILLED"
    FILE_ACCESSED = "FILE_ACCESSED"
    NETWORK_SCAN = "NETWORK_SCAN"
    THREAT_DETECTED = "THREAT_DETECTED"
    IP_BLOCKED = "IP_BLOCKED"
    DEVICE_JOINED = "DEVICE_JOINED"
    DEVICE_LEFT = "DEVICE_LEFT"
    BT_CONNECTED = "BT_CONNECTED"
    VOICE_COMMAND = "VOICE_COMMAND"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    AGENT_MISSION = "AGENT_MISSION"
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    AUTH_ATTEMPT = "AUTH_ATTEMPT"
    INTEGRITY_FAIL = "INTEGRITY_FAIL"


@dataclass
class AuditEntry:
    """Single immutable audit record."""

    id: int | None = None
    timestamp: str = ""
    entry_type: str = ""
    actor: str = ""
    action: str = ""
    payload: dict = None  # type: ignore[assignment]
    device_id: str = ""
    session_id: str = ""
    prev_hash: str = ""
    entry_hash: str = ""
    verified: bool = True

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


@dataclass
class IntegrityReport:
    total_entries: int = 0
    verified: int = 0
    failures: list[int] = None  # type: ignore[assignment]
    first_failure_id: int | None = None
    intact: bool = True

    def __post_init__(self):
        if self.failures is None:
            self.failures = []


# ── AuditTrail ──────────────────────────────────────────────────────────


class AuditTrail:
    """
    SQLite append-only log with SHA-256 hash chaining.
    Every record contains the hash of the previous record.
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._db_path: str = self._resolve_db_path()
        self._integrity_interval: int = self._resolve_int("audit_integrity_check_interval_s", 3600)
        self._export_dir: str = self._resolve_str("audit_export_dir", "logs/sessions")
        self._session_id: str = str(uuid.uuid4())
        self._last_hash: str = "0" * 64  # genesis hash
        # Cached verdict from the most recent integrity verification. status()
        # returns this instead of a hardcoded True so a cheap call can't lie.
        self._last_integrity_ok: bool = True
        self._started = False
        self._check_task: asyncio.Task | None = None
        # Serializes log() so concurrent events can't share a prev_hash and
        # break the by-id chain linkage (the cause of spurious integrity fails).
        self._log_lock = asyncio.Lock()

    def _resolve_db_path(self) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), "audit_db_path", "logs/audit/deep_audit.db")
        except Exception:
            return "logs/audit/deep_audit.db"

    def _resolve_int(self, name: str, default: int) -> int:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    def _resolve_str(self, name: str, default: str) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._started = True
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self._export_dir).mkdir(parents=True, exist_ok=True)

        await self._init_db()
        last = await self._get_last_hash_from_db()
        if last:
            self._last_hash = last

        await self.log(EntryType.SYSTEM_START, "system", "DEEP started", payload={"version": "v2", "session_id": self._session_id})

        # Subscribe to ALL events via wildcard
        self._event_bus.subscribe("*", self._on_any_event)

        self._check_task = asyncio.create_task(self._integrity_check_loop())
        logger.info("AuditTrail started")

    async def stop(self) -> None:
        self._started = False

        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        try:
            self._event_bus.unsubscribe("*", self._on_any_event)
        except Exception:
            pass

        await self.log(EntryType.SYSTEM_STOP, "system", "DEEP stopped", payload={"session_id": self._session_id})
        logger.info("AuditTrail stopped")

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _init_db(self) -> None:
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        entry_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        payload_json TEXT,
                        device_id TEXT,
                        session_id TEXT,
                        prev_hash TEXT NOT NULL,
                        entry_hash TEXT NOT NULL,
                        verified INTEGER DEFAULT 1
                    )
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(entry_type)"
                )
                await db.commit()
        else:
            import sqlite3
            with closing(sqlite3.connect(self._db_path)) as db, db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        entry_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        payload_json TEXT,
                        device_id TEXT,
                        session_id TEXT,
                        prev_hash TEXT NOT NULL,
                        entry_hash TEXT NOT NULL,
                        verified INTEGER DEFAULT 1
                    )
                    """
                )
                db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
                db.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(entry_type)")
                db.commit()

    async def _get_last_hash_from_db(self) -> str | None:
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1") as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        else:
            import sqlite3
            with closing(sqlite3.connect(self._db_path)) as db, db:
                row = db.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
                return row[0] if row else None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    async def log(
        self,
        entry_type: str,
        actor: str,
        action: str,
        payload: dict | None = None,
        device_id: str | None = None,
    ) -> AuditEntry:
        payload = payload or {}
        device_id = device_id or self._resolve_device_id()
        timestamp = self._now()
        payload_json = json.dumps(payload, sort_keys=True)

        # The hash chain links each entry to the previous one, so reading
        # self._last_hash → inserting → updating it must be atomic. Without this
        # lock, concurrent events share a prev_hash and break the by-id chain.
        async with self._log_lock:
            prev_hash = self._last_hash
            # Build hash input: timestamp|type|actor|action|payload_json|prev_hash
            hash_input = (
                f"{timestamp}|{entry_type}|{actor}|{action}|"
                f"{payload_json}|{prev_hash}"
            )
            entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            entry = AuditEntry(
                id=None,
                timestamp=timestamp,
                entry_type=entry_type,
                actor=actor,
                action=action,
                payload=payload,
                device_id=device_id,
                session_id=self._session_id,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                verified=True,
            )

            if AIOSQLITE_AVAILABLE:
                async with aiosqlite.connect(self._db_path) as db:
                    cursor = await db.execute(
                        """
                        INSERT INTO audit_log
                        (timestamp, entry_type, actor, action, payload_json, device_id, session_id, prev_hash, entry_hash, verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp, entry_type, actor, action,
                            payload_json, device_id, self._session_id,
                            prev_hash, entry_hash, 1,
                        ),
                    )
                    await db.commit()
                    entry.id = cursor.lastrowid
            else:
                import sqlite3
                with closing(sqlite3.connect(self._db_path)) as db, db:
                    cur = db.execute(
                        """
                        INSERT INTO audit_log
                        (timestamp, entry_type, actor, action, payload_json, device_id, session_id, prev_hash, entry_hash, verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp, entry_type, actor, action,
                            payload_json, device_id, self._session_id,
                            prev_hash, entry_hash, 1,
                        ),
                    )
                    db.commit()
                    entry.id = cur.lastrowid

            self._last_hash = entry_hash
        return entry

    def _resolve_device_id(self) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), "deep_device_id", "unknown")
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------
    # Event mapping
    # ------------------------------------------------------------------

    _EVENT_MAP: dict[str, tuple[str, str]] = {
        "user_command": (EntryType.COMMAND, "aryan"),
        "deep_response": (EntryType.RESPONSE, "deep"),
        "skill_invoked": (EntryType.SKILL_INVOKED, "deep"),
        "app_launched": (EntryType.APP_LAUNCHED, "deep"),
        "app_killed": (EntryType.APP_KILLED, "deep"),
        "threat_detected": (EntryType.THREAT_DETECTED, "system"),
        "ip_blocked": (EntryType.IP_BLOCKED, "deep"),
        "unknown_device_detected": (EntryType.DEVICE_JOINED, "system"),
        "device_left_network": (EntryType.DEVICE_LEFT, "system"),
        "bt_audio_activated": (EntryType.BT_CONNECTED, "system"),
        "wake_word_detected": (EntryType.VOICE_COMMAND, "aryan"),
        "knowledge_query": (EntryType.KNOWLEDGE_QUERY, "aryan"),
        "agent_mission_started": (EntryType.AGENT_MISSION, "deep"),
        "breakthrough_detected": (EntryType.KNOWLEDGE_QUERY, "deep"),
    }

    async def _on_any_event(self, event_name: str, payload: dict) -> None:
        if not self._started:
            return
        try:
            # Auto-map known events
            if event_name in self._EVENT_MAP:
                entry_type, actor = self._EVENT_MAP[event_name]
                action = self._summarise_payload(event_name, payload)
                await self.log(entry_type, actor, action, payload)

            # Always log security events
            if any(word in event_name for word in ("threat", "attack", "blocked", "evil_twin", "intrusion", "security")):
                if event_name not in self._EVENT_MAP:
                    await self.log(EntryType.THREAT_DETECTED, "system", event_name, payload)
        except Exception as exc:
            logger.debug(f"Audit auto-log error: {exc}")

    @staticmethod
    def _summarise_payload(event: str, payload: dict) -> str:
        if event == "user_command":
            return f"Command: {payload.get('text', '?')[:100]}"
        if event == "deep_response":
            return f"Response to: {payload.get('command', '?')[:50]}"
        if event == "app_launched":
            return f"Launched: {payload.get('name', '?')}"
        if event == "app_killed":
            return f"Killed: {payload.get('name', '?')}"
        if event == "threat_detected":
            return f"Threat: {payload.get('threat_type', '?')} from {payload.get('source_ip', '?')}"
        if event == "ip_blocked":
            return f"Blocked IP: {payload.get('ip', '?')}"
        if event == "unknown_device_detected":
            return f"Unknown device: {payload.get('ip', '?')} ({payload.get('vendor', '?')})"
        if event == "device_left_network":
            return f"Device left: {payload.get('ip', '?')}"
        if event == "wake_word_detected":
            return f"Wake word + transcript: {payload.get('text', '?')[:80]}"
        return event

    # ------------------------------------------------------------------
    # Integrity verification
    # ------------------------------------------------------------------

    async def verify_integrity(self, start_id: int = 1, end_id: int | None = None, record: bool = True) -> IntegrityReport:
        rows = await self._fetch_range(start_id, end_id)
        report = IntegrityReport(total_entries=len(rows))
        prev_hash = "0" * 64

        for row in rows:
            rid = row["id"]
            # Recompute expected hash
            hash_input = (
                f"{row['timestamp']}|{row['entry_type']}|{row['actor']}|"
                f"{row['action']}|{row['payload_json']}|{prev_hash}"
            )
            expected = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            if expected != row["entry_hash"]:
                report.failures.append(rid)
                if report.first_failure_id is None:
                    report.first_failure_id = rid
            else:
                report.verified += 1

            prev_hash = row["entry_hash"]

        report.intact = len(report.failures) == 0
        self._last_integrity_ok = report.intact

        # Log integrity failure if found (itself gets chained). Skipped for
        # read-only checks (e.g. get_stats) so polling the UI never appends a
        # failure entry or fires a tampering alert.
        if not report.intact and record:
            await self.log(
                EntryType.INTEGRITY_FAIL,
                "system",
                f"Hash chain broken at IDs: {report.failures}",
                payload={"failures": report.failures, "first": report.first_failure_id},
            )
            await self._event_bus.publish("audit_integrity_failed", {
                "failures": report.failures,
                "first_failure_id": report.first_failure_id,
            })
            await self._event_bus.publish("tts_speak", {
                "text": "Warning. Audit log integrity check failed. Possible tampering detected.",
                "priority": "urgent",
            })

        return report

    async def _fetch_range(self, start_id: int, end_id: int | None) -> list[dict]:
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                if end_id:
                    async with db.execute(
                        "SELECT * FROM audit_log WHERE id >= ? AND id <= ? ORDER BY id",
                        (start_id, end_id),
                    ) as cursor:
                        return [dict(r) for r in await cursor.fetchall()]
                else:
                    async with db.execute(
                        "SELECT * FROM audit_log WHERE id >= ? ORDER BY id", (start_id,)
                    ) as cursor:
                        return [dict(r) for r in await cursor.fetchall()]
        else:
            import sqlite3
            with closing(sqlite3.connect(self._db_path)) as db, db:
                db.row_factory = sqlite3.Row
                if end_id:
                    rows = db.execute(
                        "SELECT * FROM audit_log WHERE id >= ? AND id <= ? ORDER BY id",
                        (start_id, end_id),
                    ).fetchall()
                else:
                    rows = db.execute(
                        "SELECT * FROM audit_log WHERE id >= ? ORDER BY id", (start_id,)
                    ).fetchall()
                return [dict(r) for r in rows]

    async def _integrity_check_loop(self) -> None:
        while self._started:
            try:
                await asyncio.wait_for(asyncio.sleep(self._integrity_interval), timeout=self._integrity_interval + 1)
            except asyncio.TimeoutError:
                pass
            if not self._started:
                break
            try:
                await self.verify_integrity()
            except Exception as exc:
                logger.debug(f"Scheduled integrity check error: {exc}")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def query(
        self,
        entry_type: str | None = None,
        actor: str | None = None,
        device_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        clauses: list[str] = []
        params: list[Any] = []

        if entry_type:
            clauses.append("entry_type = ?")
            params.append(entry_type)
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if device_id:
            clauses.append("device_id = ?")
            params.append(device_id)
        if start_time:
            clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            clauses.append("timestamp <= ?")
            params.append(end_time)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM audit_log{where} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = await self._execute_fetch(sql, tuple(params))
        return [self._row_to_entry(r) for r in rows]

    async def get_session_log(self, session_id: str | None = None) -> list[AuditEntry]:
        sid = session_id or self._session_id
        rows = await self._execute_fetch(
            "SELECT * FROM audit_log WHERE session_id = ? ORDER BY id",
            (sid,),
        )
        return [self._row_to_entry(r) for r in rows]

    async def get_threat_log(self, hours: int = 24) -> list[AuditEntry]:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = await self._execute_fetch(
            """
            SELECT * FROM audit_log
            WHERE entry_type IN ('THREAT_DETECTED', 'IP_BLOCKED', 'INTEGRITY_FAIL')
              AND timestamp >= ?
            ORDER BY id DESC
            """,
            (cutoff,),
        )
        return [self._row_to_entry(r) for r in rows]

    async def get_stats(self) -> dict[str, Any]:
        total = 0
        today = 0
        by_type: dict[str, int] = {}
        threat_count = 0        # threats today (date-filtered)
        threat_count_all = 0    # threats over the whole ledger
        last_time = None
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        rows = await self._execute_fetch("SELECT * FROM audit_log ORDER BY id", ())
        for r in rows:
            total += 1
            is_today = r["timestamp"].startswith(today_str)
            if is_today:
                today += 1
            by_type[r["entry_type"]] = by_type.get(r["entry_type"], 0) + 1
            if r["entry_type"] in ("THREAT_DETECTED", "IP_BLOCKED", "INTEGRITY_FAIL"):
                threat_count_all += 1
                if is_today:
                    threat_count += 1
            last_time = r["timestamp"]

        # Most active hour
        hours: dict[int, int] = {}
        for r in rows:
            try:
                h = datetime.fromisoformat(r["timestamp"]).hour
                hours[h] = hours.get(h, 0) + 1
            except Exception:
                pass
        most_active = max(hours, key=hours.get) if hours else None

        chain_intact = True
        try:
            report = await self.verify_integrity(record=False)   # read-only: no side effects
            chain_intact = report.intact
        except Exception:
            pass

        db_size = 0.0
        try:
            db_size = os.path.getsize(self._db_path) / (1024 * 1024)
        except Exception:
            pass

        return {
            "total_entries": total,
            "entries_today": today,
            "entries_by_type": by_type,
            "most_active_hour": most_active,
            "threat_count_today": threat_count,
            "threat_count_total": threat_count_all,
            "last_integrity_check": self._now(),
            "chain_intact": chain_intact,
            "db_size_mb": round(db_size, 2),
        }

    async def export_session(self, session_id: str, format: str = "json") -> str:
        entries = await self.get_session_log(session_id)
        ext = "json" if format == "json" else "txt"
        path = Path(self._export_dir) / f"{session_id}.{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            data = [{
                "id": e.id,
                "timestamp": e.timestamp,
                "type": e.entry_type,
                "actor": e.actor,
                "action": e.action,
                "payload": e.payload,
                "device_id": e.device_id,
                "prev_hash": e.prev_hash,
                "entry_hash": e.entry_hash,
            } for e in entries]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            lines = []
            for e in entries:
                ts = e.timestamp.replace("T", " ").split("+")[0]
                lines.append(f"[{ts}] {e.entry_type:<16} {e.actor:<8} {e.action}")
            path.write_text("\n".join(lines), encoding="utf-8")

        return str(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_fetch(self, sql: str, params: tuple) -> list[dict]:
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(sql, params) as cursor:
                    return [dict(r) for r in await cursor.fetchall()]
        else:
            import sqlite3
            with closing(sqlite3.connect(self._db_path)) as db, db:
                db.row_factory = sqlite3.Row
                return [dict(r) for r in db.execute(sql, params).fetchall()]

    def _row_to_entry(self, row: dict) -> AuditEntry:
        return AuditEntry(
            id=row.get("id"),
            timestamp=row.get("timestamp", ""),
            entry_type=row.get("entry_type", ""),
            actor=row.get("actor", ""),
            action=row.get("action", ""),
            payload=json.loads(row.get("payload_json", "{}")),
            device_id=row.get("device_id", ""),
            session_id=row.get("session_id", ""),
            prev_hash=row.get("prev_hash", ""),
            entry_hash=row.get("entry_hash", ""),
            verified=bool(row.get("verified", 1)),
        )

    def status(self) -> dict[str, Any]:
        db_size = 0.0
        try:
            db_size = os.path.getsize(self._db_path) / (1024 * 1024)
        except Exception:
            pass
        return {
            "db_path": self._db_path,
            "total_entries": self._get_approximate_count(),
            "session_id": self._session_id,
            # Reflects the last integrity-check result rather than asserting True.
            # Full verification runs in the background loop / get_stats(); this is
            # the cached verdict so a cheap status() call never lies.
            "chain_intact": self._last_integrity_ok,
            "last_entry_time": self._now(),
            "db_size_mb": round(db_size, 2),
        }

    def _get_approximate_count(self) -> int:
        try:
            import sqlite3
            with closing(sqlite3.connect(self._db_path)) as db, db:
                row = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()
                return row[0] if row else 0
        except Exception:
            return 0
