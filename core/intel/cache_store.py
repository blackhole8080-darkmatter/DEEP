"""Durable backing store for the public-API intelligence cache.

:class:`~core.intel.http.IntelHTTP` caches upstream responses in memory, which
means every restart is cold. The first HUD load after a boot blocks on four
multi-megabyte feeds (the CISA KEV catalog alone is several MB), and a console
restarted twice in a minute downloads the same catalog twice — burning free-tier
goodwill for data that had not changed. This module gives that cache a disk
that outlives the process.

Three properties here are load-bearing:

* **Wall-clock expiry.** The in-memory cache expires against
  ``time.monotonic()``, which restarts with the process and is meaningless once
  written down. Rows here carry absolute Unix timestamps, so a cache written
  yesterday knows it is a day old.
* **No URLs on disk.** Several catalogued sources take their credential in the
  query string. The row key is therefore a SHA-256 digest of the request, and
  the only human-readable column is the method, scheme, host and path with the
  query stripped. The database cannot leak a key the environment holds, and it
  is created 0600 regardless.
* **Nothing blocks the loop.** SQLite is synchronous, so every call here runs
  in a worker thread. Failures are logged once and swallowed: a cache that
  breaks should make the console slow, not broken.

Entries are kept for a grace period *past* their expiry so that
``IntelHTTP`` can fall back to stale data when a source is unreachable. That
fallback is only honest because the age travels with it — see
``Fetch.stale_age_s``.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/intel_cache.db"

#: Largest single response we are willing to write. The KEV catalog is ~5 MB
#: and the Tor exit list ~1 MB; anything an order of magnitude past that is
#: more likely a source misbehaving than intelligence worth keeping.
MAX_ENTRY_BYTES = 16 * 1024 * 1024

#: Budget for the whole cache. Exceeding it prunes least-recently-written rows.
MAX_TOTAL_BYTES = 192 * 1024 * 1024

#: How long an expired row stays available as a stale fallback.
STALE_GRACE_S = 24 * 3600

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intel_cache (
    key        TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    payload    TEXT NOT NULL,
    status     INTEGER NOT NULL DEFAULT 0,
    stored_at  REAL NOT NULL,
    expires_at REAL NOT NULL,
    bytes      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_intel_cache_expires ON intel_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_intel_cache_stored ON intel_cache(stored_at);
"""


def cache_key(method: str, url: str, body: Any = None) -> str:
    """Stable digest of a request. Hashed so no URL — or key in one — is stored."""
    raw = f"{method.upper()}:{url}:{json.dumps(body, sort_keys=True) if body else ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def redact(method: str, url: str) -> str:
    """A label safe to write down: no query string, so no credential."""
    parts = urlsplit(url)
    host = parts.hostname or "?"
    return f"{method.upper()} {parts.scheme}://{host}{parts.path}"


@dataclass(slots=True)
class StoredResponse:
    """A row read back out of the cache. May be fresh or within the stale grace."""

    payload: Any
    status: int
    stored_at: float
    expires_at: float

    @property
    def age_s(self) -> float:
        return max(0.0, time.time() - self.stored_at)

    @property
    def fresh(self) -> bool:
        return self.expires_at > time.time()


def cache_enabled() -> bool:
    """Persistence is on unless explicitly switched off."""
    return os.environ.get("DEEP_INTEL_CACHE", "1").strip().lower() not in {
        "0", "false", "off", "no",
    }


class IntelCacheStore:
    """SQLite-backed persistence for upstream intelligence responses."""

    def __init__(
        self,
        path: Optional[str | Path] = None,
        *,
        max_entry_bytes: int = MAX_ENTRY_BYTES,
        max_total_bytes: int = MAX_TOTAL_BYTES,
        stale_grace_s: float = STALE_GRACE_S,
    ) -> None:
        self._path = Path(
            path or os.environ.get("DEEP_INTEL_CACHE_DB") or DEFAULT_DB_PATH
        )
        self._max_entry_bytes = max_entry_bytes
        self._max_total_bytes = max_total_bytes
        self._stale_grace_s = stale_grace_s
        self._ready = False
        self._disabled = False
        self._init_lock = asyncio.Lock()
        self._stats: Dict[str, int] = {
            "hits": 0, "stale_hits": 0, "misses": 0, "writes": 0,
            "skipped": 0, "errors": 0, "pruned": 0,
        }

    @property
    def path(self) -> Path:
        return self._path

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def _ensure(self) -> bool:
        """Create the database on first use. Never raises; disables on failure."""
        if self._ready:
            return True
        if self._disabled:
            return False
        async with self._init_lock:
            if self._ready or self._disabled:
                return self._ready
            try:
                await asyncio.to_thread(self._init_sync)
                self._ready = True
            except Exception as exc:  # noqa: BLE001 - a bad disk must not stop DEEP
                logger.warning("intel cache disabled (%s): %s", self._path, exc)
                self._disabled = True
        return self._ready

    def _init_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(_SCHEMA)
            db.commit()
        # Responses from key-gated sources land here, so keep it owner-only.
        try:
            os.chmod(self._path, 0o600)
        except OSError:  # pragma: no cover - platform dependent
            pass

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path), timeout=10)

    # ── reads ────────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[StoredResponse]:
        """Return a row if one survives, fresh *or* within the stale grace.

        The caller decides what to do with a stale entry; this layer only
        refuses to hand back something older than the grace window.
        """
        if not await self._ensure():
            return None
        try:
            row = await asyncio.to_thread(self._get_sync, key)
        except Exception as exc:  # noqa: BLE001
            self._stats["errors"] += 1
            logger.debug("intel cache read failed: %s", exc)
            return None

        if row is None:
            self._stats["misses"] += 1
            return None

        payload_json, status, stored_at, expires_at = row
        try:
            payload = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError):
            self._stats["errors"] += 1
            return None

        entry = StoredResponse(
            payload, int(status), float(stored_at), float(expires_at)
        )
        self._stats["hits" if entry.fresh else "stale_hits"] += 1
        return entry

    def _get_sync(self, key: str):
        horizon = time.time() - self._stale_grace_s
        with closing(self._connect()) as db:
            cur = db.execute(
                "SELECT payload, status, stored_at, expires_at FROM intel_cache "
                "WHERE key = ? AND expires_at > ?",
                (key, horizon),
            )
            return cur.fetchone()

    # ── writes ───────────────────────────────────────────────────────────────

    async def put(
        self,
        key: str,
        *,
        label: str,
        payload: Any,
        status: int,
        ttl_s: float,
    ) -> bool:
        """Persist one successful response. Returns False when it was skipped."""
        if not await self._ensure():
            return False
        try:
            blob = json.dumps(payload)
        except (TypeError, ValueError):
            # Not everything upstream returns is JSON-serialisable; the memory
            # cache still has it, this tier just skips it.
            self._stats["skipped"] += 1
            return False
        if len(blob) > self._max_entry_bytes:
            self._stats["skipped"] += 1
            logger.debug(
                "intel cache: %s payload is %d bytes, over cap", label, len(blob)
            )
            return False

        now = time.time()
        try:
            await asyncio.to_thread(
                self._put_sync, key, label, blob, int(status), now, now + ttl_s
            )
        except Exception as exc:  # noqa: BLE001
            self._stats["errors"] += 1
            logger.debug("intel cache write failed: %s", exc)
            return False
        self._stats["writes"] += 1
        return True

    def _put_sync(
        self,
        key: str,
        label: str,
        blob: str,
        status: int,
        stored_at: float,
        expires_at: float,
    ) -> None:
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO intel_cache"
                " (key, label, payload, status, stored_at, expires_at, bytes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET"
                "   label=excluded.label, payload=excluded.payload,"
                "   status=excluded.status,"
                "   stored_at=excluded.stored_at, expires_at=excluded.expires_at,"
                "   bytes=excluded.bytes",
                (key, label, blob, status, stored_at, expires_at, len(blob)),
            )

    # ── maintenance ──────────────────────────────────────────────────────────

    async def prune(self) -> int:
        """Drop rows past the stale grace, then enforce the size budget."""
        if not await self._ensure():
            return 0
        try:
            removed = await asyncio.to_thread(self._prune_sync)
        except Exception as exc:  # noqa: BLE001
            self._stats["errors"] += 1
            logger.debug("intel cache prune failed: %s", exc)
            return 0
        self._stats["pruned"] += removed
        return removed

    def _prune_sync(self) -> int:
        horizon = time.time() - self._stale_grace_s
        with closing(self._connect()) as db, db:
            removed = db.execute(
                "DELETE FROM intel_cache WHERE expires_at <= ?", (horizon,)
            ).rowcount or 0
            total = db.execute(
                "SELECT COALESCE(SUM(bytes), 0) FROM intel_cache"
            ).fetchone()[0]
            if total > self._max_total_bytes:
                # Oldest writes go first — the hot feeds are rewritten constantly,
                # so this evicts one-off pivots rather than the console's staples.
                rows = db.execute(
                    "SELECT key, bytes FROM intel_cache ORDER BY stored_at ASC"
                ).fetchall()
                for row_key, nbytes in rows:
                    if total <= self._max_total_bytes:
                        break
                    db.execute("DELETE FROM intel_cache WHERE key = ?", (row_key,))
                    total -= nbytes
                    removed += 1
        return removed

    async def clear(self) -> None:
        if not await self._ensure():
            return
        try:
            await asyncio.to_thread(self._clear_sync)
        except Exception as exc:  # noqa: BLE001
            self._stats["errors"] += 1
            logger.debug("intel cache clear failed: %s", exc)

    def _clear_sync(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM intel_cache")

    # ── introspection ────────────────────────────────────────────────────────

    async def stats(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            **self._stats,
            "path": str(self._path),
            "enabled": not self._disabled,
        }
        if not self._ready:
            base.update(entries=0, bytes=0, fresh=0, oldest_age_s=0)
            return base
        try:
            entries, nbytes, fresh, oldest = await asyncio.to_thread(self._stats_sync)
        except Exception:  # noqa: BLE001
            base.update(entries=0, bytes=0, fresh=0, oldest_age_s=0)
            return base
        base.update(
            entries=entries,
            bytes=nbytes,
            fresh=fresh,
            oldest_age_s=int(time.time() - oldest) if oldest else 0,
        )
        return base

    def _stats_sync(self):
        now = time.time()
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(bytes), 0), "
                "COALESCE(SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END), 0), "
                "MIN(stored_at) FROM intel_cache",
                (now,),
            ).fetchone()
        return int(row[0]), int(row[1]), int(row[2]), row[3]


# Process-wide store, paired with the process-wide IntelHTTP.
_shared_store: Optional[IntelCacheStore] = None


def shared_cache_store() -> Optional[IntelCacheStore]:
    """The default store, or None when persistence is switched off."""
    global _shared_store
    if not cache_enabled():
        return None
    if _shared_store is None:
        _shared_store = IntelCacheStore()
    return _shared_store
