"""
network/proximity_store.py — durable memory for DEEP's senses.

Persists every Wi-Fi AP and Bluetooth device DEEP has observed to SQLite, so its
situational awareness survives restarts (no more "1 AP after reboot"). Also keeps
a 24-bucket hour-of-day presence histogram per device, enabling behavioural
baselines: an established device appearing at an unusual hour is flagged.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "proximity.db")

# A device must have this many prior observations before "unusual time" applies.
_MIN_OBS = 20
# If <= this fraction of its sightings fell in the current hour, it's atypical.
_RARE_FRAC = 0.03


class ProximityStore:
    def __init__(self, path: str = _DB) -> None:
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._init()

    def _conn(self):
        return sqlite3.connect(self._path, timeout=5)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS proximity (
                    id TEXT PRIMARY KEY,
                    kind TEXT, name TEXT, vendor TEXT,
                    first_seen TEXT, last_seen TEXT,
                    seen_count INTEGER DEFAULT 0,
                    hours TEXT DEFAULT '[]',
                    extra TEXT DEFAULT '{}'
                )"""
            )
            c.commit()

    def load_all(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        try:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                for r in c.execute("SELECT * FROM proximity"):
                    out[r["id"]] = {
                        "id": r["id"], "kind": r["kind"], "name": r["name"], "vendor": r["vendor"],
                        "first_seen": r["first_seen"], "last_seen": r["last_seen"],
                        "seen_count": r["seen_count"],
                        "hours": json.loads(r["hours"] or "[]") or [0] * 24,
                        "extra": json.loads(r["extra"] or "{}"),
                    }
        except Exception:
            pass
        return out

    def observe(self, dev_id: str, kind: str, name: str | None, vendor: str | None,
                extra: dict | None = None) -> dict[str, Any]:
        """Record one sighting. Returns {'record':..., 'unusual_time':bool, 'is_new':bool}."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        iso = now.isoformat()
        unusual = False
        is_new = False
        try:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT * FROM proximity WHERE id=?", (dev_id,)).fetchone()
                if row:
                    hours = json.loads(row["hours"] or "[]") or [0] * 24
                    if len(hours) != 24:
                        hours = [0] * 24
                    total = sum(hours)
                    # behavioural baseline — judged on PRIOR distribution
                    if total >= _MIN_OBS and hours[hour] <= max(0, total * _RARE_FRAC):
                        unusual = True
                    hours[hour] += 1
                    seen = (row["seen_count"] or 0) + 1
                    nm = name or row["name"]
                    vd = vendor or row["vendor"]
                    ex = json.loads(row["extra"] or "{}"); ex.update(extra or {})
                    c.execute(
                        "UPDATE proximity SET name=?,vendor=?,last_seen=?,seen_count=?,hours=?,extra=? WHERE id=?",
                        (nm, vd, iso, seen, json.dumps(hours), json.dumps(ex), dev_id),
                    )
                    rec = {"id": dev_id, "kind": kind, "name": nm, "vendor": vd,
                           "first_seen": row["first_seen"], "last_seen": iso,
                           "seen_count": seen, "hours": hours, "extra": ex}
                else:
                    is_new = True
                    hours = [0] * 24; hours[hour] = 1
                    ex = extra or {}
                    c.execute(
                        "INSERT INTO proximity (id,kind,name,vendor,first_seen,last_seen,seen_count,hours,extra) VALUES (?,?,?,?,?,?,?,?,?)",
                        (dev_id, kind, name, vendor, iso, iso, 1, json.dumps(hours), json.dumps(ex)),
                    )
                    rec = {"id": dev_id, "kind": kind, "name": name, "vendor": vendor,
                           "first_seen": iso, "last_seen": iso, "seen_count": 1, "hours": hours, "extra": ex}
                c.commit()
        except Exception:
            rec = {"id": dev_id, "kind": kind, "name": name, "vendor": vendor, "seen_count": 1}
        return {"record": rec, "unusual_time": unusual, "is_new": is_new}

    def stats(self) -> dict[str, Any]:
        try:
            with self._conn() as c:
                total = c.execute("SELECT COUNT(*) FROM proximity").fetchone()[0]
                wifi = c.execute("SELECT COUNT(*) FROM proximity WHERE kind='wifi'").fetchone()[0]
                bt = c.execute("SELECT COUNT(*) FROM proximity WHERE kind='bt'").fetchone()[0]
                size = os.path.getsize(self._path) / (1024 * 1024)
            return {"total_known": total, "wifi_known": wifi, "bt_known": bt, "db_size_mb": round(size, 2)}
        except Exception:
            return {"total_known": 0}


# module-level singleton
_store: ProximityStore | None = None
def get_store() -> ProximityStore:
    global _store
    if _store is None:
        _store = ProximityStore()
    return _store
