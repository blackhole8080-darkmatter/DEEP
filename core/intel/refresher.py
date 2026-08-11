"""Background pre-warming of the hot intelligence feeds.

The operations console reads five feeds on almost every screen: the CISA KEV
catalog, EPSS top-risk scores, the abuse.ch Feodo C2 blocklist, the Tor exit
list, and the SANS ISC attacker table. Fetched on demand they cost the operator
a multi-second stall on the first load after every restart and after every TTL
expiry — the console is slowest exactly when someone has just opened it because
something happened.

This refresher moves that cost off the request path. It walks the feed list on
a slow tick and re-fetches each one shortly *before* its cache entry expires,
so the on-demand read is always a cache hit.

Points worth knowing:

* **Cadence comes from the catalog.** Each feed names a source id in
  ``public_apis.CATALOG`` and inherits that source's ``ttl_seconds``. There is
  no second set of intervals to drift out of sync with the cache.
* **A refresh is a real fetch.** ``refresh=True`` bypasses both cache tiers,
  otherwise "refreshing" would just re-read what is already there. The warm-up
  pass at boot deliberately does *not* set it, so a console restarted with a
  warm disk cache issues no network traffic at all.
* **Failure backs off, it does not spin.** A feed that errors is retried on an
  exponential delay capped at its normal cadence, so an offline laptop makes a
  handful of attempts an hour rather than one a minute.
* **It is optional.** ``DEEP_INTEL_REFRESH=0`` turns it off; nothing else in
  the intel layer depends on it running.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from core.intel import public_apis
from core.intel.http import IntelHTTP, shared_http
from core.intel.live_stats import (
    EPSS_TOP,
    FEODO_URL,
    ISC_TOP_SOURCES,
    KEV_URL,
    TOR_EXITS,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Feed:
    """One upstream document worth keeping warm."""

    source_id: str
    """Id in ``public_apis.CATALOG`` — this is where the cadence comes from."""

    url: str
    label: str
    as_json: bool = True

    @property
    def ttl_s(self) -> int:
        api = public_apis.get(self.source_id)
        return api.ttl_seconds if api else 3600


#: The feeds the console reads on nearly every screen. URLs are imported from
#: ``live_stats`` rather than repeated, so this can only ever warm what is read.
HOT_FEEDS: tuple[Feed, ...] = (
    Feed("cisa_kev", KEV_URL, "CISA KEV catalog"),
    Feed("epss", EPSS_TOP.format(limit=20), "EPSS top-risk CVEs"),
    Feed("feodo", FEODO_URL, "abuse.ch Feodo C2 blocklist"),
    Feed("sans_isc", ISC_TOP_SOURCES.format(limit=100), "SANS ISC top attackers"),
    Feed("tor_exits", TOR_EXITS, "Tor exit list", as_json=False),
)


def refresh_enabled() -> bool:
    return os.environ.get("DEEP_INTEL_REFRESH", "1").strip().lower() not in {
        "0", "false", "off", "no",
    }


class IntelRefresher:
    """Keeps the hot feeds warm so the console never waits on a cold cache."""

    #: Refresh at this fraction of the TTL, so the entry is replaced before it
    #: expires rather than after somebody has already hit the gap.
    LEAD_FRACTION = 0.85

    #: First retry delay after a failure; doubles per consecutive failure.
    BACKOFF_BASE_S = 60.0

    def __init__(
        self,
        http: Optional[IntelHTTP] = None,
        feeds: Sequence[Feed] = HOT_FEEDS,
        *,
        tick_s: float = 60.0,
        initial_delay_s: float = 10.0,
        stagger_s: float = 2.0,
        prune_every_s: float = 3600.0,
    ) -> None:
        self._http = http or shared_http()
        self._feeds = tuple(feeds)
        self._tick_s = tick_s
        self._initial_delay_s = initial_delay_s
        self._stagger_s = stagger_s
        self._prune_every_s = prune_every_s
        self._task: Optional[asyncio.Task] = None
        self._due: Dict[str, float] = {}          # source_id -> monotonic deadline
        self._failures: Dict[str, int] = {}
        self._last: Dict[str, Dict[str, Any]] = {}
        self._passes = 0
        self._next_prune = 0.0

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Spawn the loop. Returns False when refreshing is switched off."""
        if not refresh_enabled():
            logger.info("intel refresher disabled by DEEP_INTEL_REFRESH")
            return False
        if self._task is not None and not self._task.done():
            return True
        self._task = asyncio.create_task(self._run(), name="intel-refresher")
        return True

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def _run(self) -> None:
        # Boot is already busy; let the rest of DEEP come up first.
        await asyncio.sleep(self._initial_delay_s)
        # Warm-up pass: no `refresh`, so a warm disk cache costs nothing and a
        # cold one is filled before the operator asks for it.
        await self.refresh_once(force=False)
        while True:
            await asyncio.sleep(self._tick_s)
            try:
                await self.refresh_once()
                await self._maybe_prune()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - a bad pass must not kill the loop
                logger.exception("intel refresh pass failed")

    # ── the work ─────────────────────────────────────────────────────────────

    async def refresh_once(self, *, force: bool = True) -> Dict[str, Any]:
        """Refresh every feed that is due. Returns what this pass did.

        ``force=False`` makes the pass a warm-up: feeds are fetched through the
        normal cache, so anything already cached is left alone.
        """
        self._passes += 1
        now = time.monotonic()
        touched: Dict[str, Any] = {}
        first = True
        for feed in self._feeds:
            if force and self._due.get(feed.source_id, 0.0) > now:
                continue
            if not public_apis.get(feed.source_id) or not _configured(feed.source_id):
                continue
            if not first and self._stagger_s > 0:
                # Four multi-megabyte downloads at once is a self-inflicted
                # stall; spread them out.
                await asyncio.sleep(self._stagger_s)
            first = False
            touched[feed.source_id] = await self._refresh(feed, force=force)
        return {"pass": self._passes, "refreshed": touched}

    async def _refresh(self, feed: Feed, *, force: bool) -> Dict[str, Any]:
        ttl = feed.ttl_s
        started = time.monotonic()
        if feed.as_json:
            result = await self._http.get_json(feed.url, ttl=ttl, refresh=force)
        else:
            result = await self._http.get_text(feed.url, ttl=ttl, refresh=force)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        # Only a clean fetch counts. `ok` alone is not enough: the transport
        # answers from cache when a source is unreachable — stale, or still
        # inside its TTL — and carries the error along. Treating that as a
        # success would reset the backoff on a source that is still down.
        succeeded = result.ok and not result.stale and not result.error

        if succeeded:
            self._failures.pop(feed.source_id, None)
            # Come back shortly before this payload expires. On a warm-up pass
            # the answer came from cache with only part of its life left, so
            # scheduling off the full TTL would let it lapse. Jittered so five
            # feeds that started together do not stay in lockstep.
            remaining = result.fresh_for_s if result.fresh_for_s > 0 else float(ttl)
            delay = max(
                self._tick_s, remaining * self.LEAD_FRACTION * random.uniform(0.9, 1.0)
            )
        else:
            fails = self._failures.get(feed.source_id, 0) + 1
            self._failures[feed.source_id] = fails
            delay = min(self.BACKOFF_BASE_S * (2 ** (fails - 1)), float(ttl))

        self._due[feed.source_id] = time.monotonic() + delay
        record = {
            "label": feed.label,
            "ok": succeeded,
            "cached": result.cached,
            "stale": result.stale,
            "stale_age_s": int(result.stale_age_s),
            "error": "" if succeeded else (result.error or "unavailable"),
            "elapsed_ms": elapsed_ms,
            "next_in_s": int(delay),
            "at": time.time(),
        }
        self._last[feed.source_id] = record
        if not succeeded:
            logger.debug(
                "intel refresh: %s unavailable (%s)", feed.label, record["error"]
            )
        return record

    async def _maybe_prune(self) -> None:
        now = time.monotonic()
        if now < self._next_prune:
            return
        self._next_prune = now + self._prune_every_s
        removed = await self._http.prune_cache()
        if removed:
            logger.info("intel cache: pruned %d expired entries", removed)

    # ── introspection ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        now = time.monotonic()
        return {
            "enabled": refresh_enabled(),
            "running": self.running,
            "passes": self._passes,
            "feeds": [
                {
                    "source_id": f.source_id,
                    "label": f.label,
                    "ttl_s": f.ttl_s,
                    "configured": _configured(f.source_id),
                    "due_in_s": max(0, int(self._due.get(f.source_id, now) - now)),
                    "consecutive_failures": self._failures.get(f.source_id, 0),
                    "last": self._last.get(f.source_id),
                }
                for f in self._feeds
            ],
        }


def _configured(source_id: str) -> bool:
    api = public_apis.get(source_id)
    return bool(api and api.configured)


_shared_refresher: Optional[IntelRefresher] = None


def shared_refresher() -> IntelRefresher:
    global _shared_refresher
    if _shared_refresher is None:
        _shared_refresher = IntelRefresher()
    return _shared_refresher
