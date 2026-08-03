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
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

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

    def __init__(self, timeout_s: float = 12.0, default_ttl: int = 300) -> None:
        self._timeout_s = timeout_s
        self._default_ttl = default_ttl
        self._cache: Dict[str, _CacheEntry] = {}
        self._host_locks: Dict[str, asyncio.Lock] = {}
        self._host_last_call: Dict[str, float] = {}
        self._session: Optional["aiohttp.ClientSession"] = None
        self._stats: Dict[str, int] = {"requests": 0, "cache_hits": 0, "errors": 0}

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
    ) -> Fetch:
        return await self._request("GET", url, headers=headers, ttl=ttl, as_json=True)

    async def post_json(
        self,
        url: str,
        payload: Any,
        *,
        headers: Optional[Dict[str, str]] = None,
        ttl: Optional[int] = None,
    ) -> Fetch:
        return await self._request(
            "POST", url, headers=headers, ttl=ttl, as_json=True, body=payload
        )

    async def get_text(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        ttl: Optional[int] = None,
    ) -> Fetch:
        return await self._request("GET", url, headers=headers, ttl=ttl, as_json=False)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]],
        ttl: Optional[int],
        as_json: bool,
        body: Any = None,
    ) -> Fetch:
        cache_key = f"{method}:{url}:{json.dumps(body, sort_keys=True) if body else ''}"
        hit = self._cache.get(cache_key)
        now = time.monotonic()
        if hit is not None and hit.expires_at > now:
            self._stats["cache_hits"] += 1
            cached = Fetch(
                ok=hit.value.ok,
                data=hit.value.data,
                status=hit.value.status,
                error=hit.value.error,
                cached=True,
                elapsed_ms=hit.value.elapsed_ms,
            )
            return cached

        if not _AIOHTTP_OK:
            return Fetch(ok=False, error="aiohttp not installed")

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

        # Failures are cached too, but briefly — enough to stop a fan-out from
        # hammering a source that is currently down, not long enough to hide a
        # recovery.
        effective_ttl = (ttl if ttl is not None else self._default_ttl) if result.ok else 30
        self._cache[cache_key] = _CacheEntry(value=result, expires_at=now + effective_ttl)
        return result

    # ── introspection ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "cache_entries": len(self._cache),
            "transport": "aiohttp" if _AIOHTTP_OK else "unavailable",
        }

    def clear_cache(self) -> None:
        self._cache.clear()


# Process-wide client. The intel layer is read-only and stateless per call, so
# one shared session keeps connection reuse and the throttle state coherent.
_shared: Optional[IntelHTTP] = None


def shared_http() -> IntelHTTP:
    global _shared
    if _shared is None:
        _shared = IntelHTTP()
    return _shared
