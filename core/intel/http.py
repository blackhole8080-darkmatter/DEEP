"""Shared async HTTP transport for DEEP's public-API intelligence layer.

Every public source DEEP queries goes through :class:`IntelHTTP` so that
timeouts, per-host politeness, caching and failure isolation are decided in
one place rather than re-improvised per source. Sources stay declarative;
this module owns the network behaviour.

Design notes:

* **Nothing raises.** Intelligence gathering fans out across a dozen
  third-party services, any of which can be down, rate-limiting, or slow.
  A fetch returns :class:`Fetch`, which carries either a payload or an error
  string. Callers merge whatever came back and report the rest as degraded.
* **Per-host rate limiting.** Free tiers are generous but finite (ip-api and
  macvendors both ban on burst). A minimum interval per host is enforced with
  one lock per host, so concurrent pivots on the same source serialise
  instead of tripping the limit.
* **TTL cache.** Threat data changes on the order of minutes-to-hours, not
  milliseconds. Repeated pivots on the same indicator (which the terminal and
  the map both do) hit the cache.
* **The cache has a disk.** Behind the in-memory tier sits
  :class:`~core.intel.cache_store.IntelCacheStore`, so a restart does not throw
  away the KEV catalog it downloaded a minute ago. The disk tier also keeps
  entries for a grace period past expiry, which lets a fetch fall back to stale
  data when a source is unreachable — reported as ``Fetch.stale_age_s`` so a
  caller can say *how* old rather than passing it off as current.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from core.intel.cache_store import (
    IntelCacheStore,
    cache_key,
    redact,
    shared_cache_store,
)

try:
    import aiohttp

    _AIOHTTP_OK = True
except ImportError:  # pragma: no cover - exercised only on minimal installs
    _AIOHTTP_OK = False

logger = logging.getLogger(__name__)

USER_AGENT = "DEEP-OSINT/1.0 (+https://github.com/blackhole8080-darkmatter/DEEP)"

# Politeness floor per host, in seconds. Sources not listed get DEFAULT_INTERVAL.
_HOST_MIN_INTERVAL: Dict[str, float] = {
    "api.macvendors.com": 1.0,
    "ip-api.com": 1.5,
    "crt.sh": 2.0,
    "isc.sans.edu": 1.0,
}
DEFAULT_INTERVAL = 0.25


@dataclass(slots=True)
class Fetch:
    """Outcome of a single upstream call. Never raises; inspect ``ok``."""

    ok: bool
    data: Any = None
    status: int = 0
    error: str = ""
    cached: bool = False
    elapsed_ms: int = 0
    #: True when this payload is being served *past its TTL* because the source
    #: could not be reached, with ``stale_age_s`` giving its age. Callers that
    #: display the data must display this too: stale intelligence is useful,
    #: stale intelligence passed off as current is a lie.
    stale: bool = False
    stale_age_s: float = 0.0
    #: How many more seconds this payload stays valid. Lets the refresher come
    #: back just before a cached entry expires instead of guessing from the TTL.
    fresh_for_s: float = 0.0

    @property
    def json(self) -> Any:
        """The payload, or None when the call failed."""
        return self.data if self.ok else None


@dataclass(slots=True)
class _CacheEntry:
    value: Fetch
    expires_at: float


class IntelHTTP:
    """Async JSON/text client with caching, timeouts and per-host throttling."""

    #: Responses shorter-lived than this are not worth a disk write.
    PERSIST_MIN_TTL = 60

    def __init__(
        self,
        timeout_s: float = 12.0,
        default_ttl: int = 300,
        *,
        store: Optional[IntelCacheStore] = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._default_ttl = default_ttl
        self._cache: Dict[str, _CacheEntry] = {}
        self._store = store
        self._host_locks: Dict[str, asyncio.Lock] = {}
        self._host_last_call: Dict[str, float] = {}
        self._session: Optional["aiohttp.ClientSession"] = None
        self._stats: Dict[str, int] = {
            "requests": 0, "cache_hits": 0, "disk_hits": 0,
            "stale_served": 0, "errors": 0,
        }

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self) -> "aiohttp.ClientSession":
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout_s),
                headers={"User-Agent": USER_AGENT},
                # Honour HTTP(S)_PROXY / NO_PROXY / .netrc from the environment.
                # aiohttp ignores them unless asked, so on any machine behind a
                # proxy every catalogued source failed with a bare connection
                # error — a whole intelligence layer reporting "degraded" with
                # no hint that the network, not the sources, was the problem.
                # A no-op where no proxy is configured.
                trust_env=True,
            )
        return self._session

    # ── throttling ───────────────────────────────────────────────────────────

    async def _throttle(self, host: str) -> None:
        interval = _HOST_MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            last = self._host_last_call.get(host, 0.0)
            wait = interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._host_last_call[host] = time.monotonic()

    # ── fetching ─────────────────────────────────────────────────────────────

    async def get_json(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        ttl: Optional[int] = None,
        refresh: bool = False,
    ) -> Fetch:
        return await self._request(
            "GET", url, headers=headers, ttl=ttl, as_json=True, refresh=refresh
        )

    async def post_json(
        self,
        url: str,
        payload: Any,
        *,
        headers: Optional[Dict[str, str]] = None,
        ttl: Optional[int] = None,
        refresh: bool = False,
    ) -> Fetch:
        return await self._request(
            "POST", url, headers=headers, ttl=ttl,
            as_json=True, body=payload, refresh=refresh,
        )

    async def get_text(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        ttl: Optional[int] = None,
        refresh: bool = False,
    ) -> Fetch:
        return await self._request(
            "GET", url, headers=headers, ttl=ttl, as_json=False, refresh=refresh
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]],
        ttl: Optional[int],
        as_json: bool,
        body: Any = None,
        refresh: bool = False,
    ) -> Fetch:
        mem_key = f"{method}:{url}:{json.dumps(body, sort_keys=True) if body else ''}"
        now = time.monotonic()
        if not refresh:
            hit = self._cache.get(mem_key)
            if hit is not None and hit.expires_at > now:
                self._stats["cache_hits"] += 1
                return Fetch(
                    ok=hit.value.ok,
                    data=hit.value.data,
                    status=hit.value.status,
                    error=hit.value.error,
                    cached=True,
                    elapsed_ms=hit.value.elapsed_ms,
                    stale=hit.value.stale,
                    stale_age_s=hit.value.stale_age_s,
                    fresh_for_s=hit.expires_at - now,
                )

        # Disk tier. Read even when refreshing, because the row doubles as the
        # fallback if this fetch fails.
        stored = None
        if self._store is not None:
            stored = await self._store.get(cache_key(method, url, body))
            if stored is not None and stored.fresh and not refresh:
                return self._serve_stored(mem_key, stored)

        if not _AIOHTTP_OK:
            return self._fallback(mem_key, stored, "aiohttp not installed")

        host = urlsplit(url).hostname or "?"
        await self._throttle(host)

        self._stats["requests"] += 1
        started = time.monotonic()
        try:
            session = await self._get_session()
            req_headers = dict(headers or {})
            async with session.request(method, url, headers=req_headers, json=body) as resp:
                elapsed = int((time.monotonic() - started) * 1000)
                if resp.status >= 400:
                    result = Fetch(
                        ok=False,
                        status=resp.status,
                        error=f"HTTP {resp.status}",
                        elapsed_ms=elapsed,
                    )
                else:
                    if as_json:
                        payload = await resp.json(content_type=None)
                    else:
                        payload = await resp.text()
                    result = Fetch(ok=True, data=payload, status=resp.status, elapsed_ms=elapsed)
        except asyncio.TimeoutError:
            result = Fetch(
                ok=False,
                error=f"timeout after {self._timeout_s:.0f}s",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all, see module docstring
            result = Fetch(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )

        if not result.ok:
            self._stats["errors"] += 1
            if stored is not None:
                # A forced refresh that failed onto a copy which has not yet
                # expired is not stale — the data is still current, and calling
                # it stale would raise a false alarm on the console. The error
                # still rides along so the refresher knows the source is down.
                if stored.fresh:
                    return self._serve_stored(mem_key, stored, error=result.error)
                return self._fallback(mem_key, stored, result.error)

        # Failures are cached too, but briefly — enough to stop a fan-out from
        # hammering a source that is currently down, not long enough to hide a
        # recovery.
        base_ttl = ttl if ttl is not None else self._default_ttl
        effective_ttl = base_ttl if result.ok else 30
        if result.ok:
            result.fresh_for_s = float(effective_ttl)
        self._cache[mem_key] = _CacheEntry(
            value=result, expires_at=time.monotonic() + effective_ttl
        )

        persistable = result.ok and effective_ttl >= self.PERSIST_MIN_TTL
        if persistable and self._store is not None:
            await self._store.put(
                cache_key(method, url, body),
                label=redact(method, url),
                payload=result.data,
                status=result.status,
                ttl_s=effective_ttl,
            )
        return result

    def _serve_stored(self, mem_key: str, stored, *, error: str = "") -> Fetch:
        """Return an unexpired durable-cache row and promote it into memory."""
        self._stats["disk_hits"] += 1
        remaining = max(1.0, stored.expires_at - time.time())
        result = Fetch(
            ok=True, data=stored.payload, status=stored.status,
            error=error, cached=True, fresh_for_s=remaining,
        )
        self._cache[mem_key] = _CacheEntry(
            value=result, expires_at=time.monotonic() + remaining
        )
        return result

    def _fallback(self, mem_key: str, stored, error: str) -> Fetch:
        """Serve an expired-but-recent payload when the source is unreachable.

        Better than a blank panel, and only defensible because ``stale_age_s``
        travels with it. Held in memory only briefly so that a source coming
        back is noticed within half a minute rather than after its full TTL.
        """
        if stored is None:
            return Fetch(ok=False, error=error)
        self._stats["stale_served"] += 1
        result = Fetch(
            ok=True,
            data=stored.payload,
            status=stored.status,
            error=error,
            cached=True,
            stale=True,
            stale_age_s=stored.age_s,
        )
        self._cache[mem_key] = _CacheEntry(
            value=result, expires_at=time.monotonic() + 30
        )
        return result

    # ── introspection ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "cache_entries": len(self._cache),
            "persistent": self._store is not None,
            "transport": "aiohttp" if _AIOHTTP_OK else "unavailable",
        }

    async def cache_stats(self) -> Dict[str, Any]:
        """Memory tier plus, when persistence is on, the disk tier."""
        out: Dict[str, Any] = {"memory": self.stats()}
        out["disk"] = (
            await self._store.stats() if self._store is not None else {"enabled": False}
        )
        return out

    def clear_cache(self) -> None:
        """Drop the memory tier. The disk tier is cleared explicitly."""
        self._cache.clear()

    async def clear_persistent_cache(self) -> None:
        self._cache.clear()
        if self._store is not None:
            await self._store.clear()

    async def prune_cache(self) -> int:
        return await self._store.prune() if self._store is not None else 0


# Process-wide client. The intel layer is read-only and stateless per call, so
# one shared session keeps connection reuse and the throttle state coherent.
_shared: Optional[IntelHTTP] = None


def shared_http() -> IntelHTTP:
    global _shared
    if _shared is None:
        _shared = IntelHTTP(store=shared_cache_store())
    return _shared
