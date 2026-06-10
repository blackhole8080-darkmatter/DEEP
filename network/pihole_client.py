"""
network/pihole_client.py

Reads Pi-hole DNS data so DEEP can see every domain every device
on your network visits.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not installed — PiholeClient will be non-functional")


class PiholeClient:
    """
    Queries a Pi-hole instance for DNS statistics and recent queries.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._started = False
        self._stop_event = asyncio.Event()

        self._url: str = self._resolve("pihole_url", "http://pi.hole")
        self._token: str = self._resolve("pihole_api_token", "")
        self._poll_interval: int = self._resolve("pihole_poll_interval_s", 30)
        self._suspicious_patterns: tuple[str, ...] = self._resolve_suspicious()

        self._reachable = False
        self._queries_today = 0
        self._block_rate = "0%"
        self._poll_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve(self, name: str, default: Any) -> Any:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    def _resolve_suspicious(self) -> tuple[str, ...]:
        try:
            from core.config import Settings
            return tuple(getattr(Settings(), "suspicious_domain_patterns", []))
        except Exception:
            return ()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._started = True
        self._stop_event.clear()

        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp unavailable — PiholeClient disabled")
            return

        # Verify reachability
        try:
            summary = await self.get_summary()
            self._reachable = bool(summary)
        except Exception:
            self._reachable = False

        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(f"PiholeClient started (reachable={self._reachable})")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("PiholeClient stopped")

    def status(self) -> dict[str, Any]:
        return {
            "reachable": self._reachable,
            "url": self._url,
            "queries_today": self._queries_today,
            "block_rate": self._block_rate,
        }

    # ------------------------------------------------------------------
    # Pi-hole API
    # ------------------------------------------------------------------

    async def get_summary(self) -> dict[str, Any] | None:
        if not AIOHTTP_AVAILABLE:
            return None
        url = f"{self._url}/admin/api.php"
        params = {"summary": ""}
        if self._token:
            params["auth"] = self._token
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data
        except Exception as exc:
            logger.debug(f"Pi-hole summary error: {exc}")
        return None

    async def get_recent_queries(self, count: int = 50) -> list[dict[str, Any]]:
        if not AIOHTTP_AVAILABLE:
            return []
        url = f"{self._url}/admin/api.php"
        params = {"getAllQueries": "", "count": str(count)}
        if self._token:
            params["auth"] = self._token
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
        except Exception as exc:
            logger.debug(f"Pi-hole queries error: {exc}")
        return []

    async def get_top_domains(self) -> dict[str, Any]:
        if not AIOHTTP_AVAILABLE:
            return {}
        url = f"{self._url}/admin/api.php"
        params = {"topItems": ""}
        if self._token:
            params["auth"] = self._token
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as exc:
            logger.debug(f"Pi-hole top domains error: {exc}")
        return {}

    async def block_domain(self, domain: str) -> bool:
        if not AIOHTTP_AVAILABLE:
            return False
        url = f"{self._url}/admin/api.php"
        params = {"list": "black", "add": domain, "auth": self._token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception as exc:
            logger.warning(f"Pi-hole block error: {exc}")
            return False

    async def get_client_activity(self, client_ip: str) -> list[dict[str, Any]]:
        queries = await self.get_recent_queries(count=1000)
        return [q for q in queries if len(q) >= 4 and q[3] == client_ip]

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                summary = await self.get_summary()
                if summary:
                    self._reachable = True
                    self._queries_today = summary.get("dns_queries_today", 0)
                    ads_pct = summary.get("ads_percentage_today", 0)
                    self._block_rate = f"{ads_pct:.1f}%"
                    await self._redis_state.set_global("pihole_summary", summary)

                    # Check for suspicious domains
                    queries = await self.get_recent_queries(count=50)
                    for q in queries:
                        if len(q) < 5:
                            continue
                        domain = q[2] if isinstance(q, (list, tuple)) else q.get("domain", "")
                        if any(pattern in domain for pattern in self._suspicious_patterns):
                            client = q[3] if isinstance(q, (list, tuple)) else q.get("client", "")
                            await self._event_bus.publish(
                                "suspicious_dns_detected",
                                {
                                    "domain": domain,
                                    "client_ip": client,
                                    "timestamp": self._now(),
                                },
                            )
                else:
                    self._reachable = False
            except Exception as exc:
                logger.debug(f"Pi-hole poll error: {exc}")
                self._reachable = False

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
            except asyncio.TimeoutError:
                pass
