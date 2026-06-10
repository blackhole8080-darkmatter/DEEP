"""
core/redis_state.py

Redis shared state layer for DEEP v2.

Provides cross-device memory: PC, phone, Pi all share one live brain state
via a central Redis instance (typically on the Raspberry Pi, accessed over
Tailscale).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY NAMESPACES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  deep:session:{key}           — per-session context
  deep:device:{device_id}:{key}— per-device state
  deep:global:{key}            — shared across all devices
  deep:mood                    — current mood (global)
  deep:last_command            — last spoken command
  deep:active_device           — which device is primary
  deep:conversation:{id}       — conversation history

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Raspberry Pi setup (run once):
  sudo apt install redis-server
  sudo systemctl enable redis-server
  sudo systemctl start redis-server

Bind to Tailscale IP (edit /etc/redis/redis.conf):
  bind 127.0.0.1 100.x.x.x
  (replace with actual Tailscale IP)

Windows PC — connect to Pi Redis over Tailscale:
  Set REDIS_URL = "redis://100.x.x.x:6379"
  in core/config.py (or via .env)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RedisStateManager:
    """
    Shared state layer backed by Redis with local cache fallback.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        self._client: Any = None
        self._pubsub: Any = None
        self._redis_available = False
        self._started = False
        self._stop_event = asyncio.Event()

        self._local_cache: dict[str, Any] = {}
        self._sync_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None
        self._keys_synced = 0
        self._last_sync: str | None = None
        self._connected_since: str | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_url(self) -> str:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "redis_url", "redis://localhost:6379")
        except Exception:
            return "redis://localhost:6379"

    def _resolve_sync_interval(self) -> int:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "redis_sync_interval_s", 5)
        except Exception:
            return 5

    def _resolve_instance_id(self) -> str:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "deep_instance_id", "deep-main")
        except Exception:
            return "deep-main"

    def _resolve_conversation_max(self) -> int:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "conversation_history_max", 20)
        except Exception:
            return 20

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect to Redis or fall back to local cache."""
        self._stop_event.clear()

        try:
            import redis.asyncio as redis

            url = self._resolve_url()
            self._client = redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await self._client.ping()
            self._redis_available = True
            self._connected_since = self._now()
            logger.info(f"RedisStateManager connected to {url}")

            await self._restore_session_state()
            self._sync_task = asyncio.create_task(self._sync_loop())
            self._listen_task = asyncio.create_task(self._listen_for_changes())

            await self._event_bus.publish(
                "redis_connected",
                {"url": url, "timestamp": self._now()},
            )
        except Exception as exc:
            self._redis_available = False
            logger.warning(
                f"Redis unavailable ({exc}). "
                "DEEP will use local cache only."
            )
            await self._event_bus.publish(
                "redis_unavailable",
                {"error": str(exc), "timestamp": self._now()},
            )

        self._started = True

    async def stop(self) -> None:
        """Disconnect from Redis and stop background tasks."""
        self._started = False
        self._stop_event.set()

        for task in (self._sync_task, self._listen_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None

        self._redis_available = False
        logger.info("RedisStateManager stopped")

    def status(self) -> dict[str, Any]:
        return {
            "available": self._redis_available,
            "url": self._resolve_url(),
            "local_cache_size": len(self._local_cache),
            "keys_synced": self._keys_synced,
            "last_sync": self._last_sync,
            "connected_since": self._connected_since,
        }

    # ------------------------------------------------------------------
    # Core KV API
    # ------------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: Any,
        ttl_s: int | None = None,
        broadcast: bool = False,
    ) -> None:
        """Serialize value to JSON and store in Redis + local cache."""
        serialized = json.dumps(value)
        self._local_cache[key] = value

        if self._redis_available and self._client:
            try:
                await self._client.set(key, serialized, ex=ttl_s)
                self._keys_synced += 1
                if broadcast:
                    await self._client.publish(
                        "deep:state_changes",
                        json.dumps({"key": key, "value": value, "source_device": self._resolve_instance_id()}),
                    )
            except Exception as exc:
                logger.warning(f"Redis set error: {exc}")

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from Redis (prefer) or local cache."""
        if self._redis_available and self._client:
            try:
                raw = await self._client.get(key)
                if raw is not None:
                    value = json.loads(raw)
                    self._local_cache[key] = value
                    return value
            except Exception as exc:
                logger.warning(f"Redis get error: {exc}")
        return self._local_cache.get(key, default)

    async def delete(self, key: str) -> None:
        """Remove key from Redis and local cache."""
        self._local_cache.pop(key, None)
        if self._redis_available and self._client:
            try:
                await self._client.delete(key)
            except Exception as exc:
                logger.warning(f"Redis delete error: {exc}")

    async def get_all(self, prefix: str) -> dict[str, Any]:
        """Return all keys matching prefix + '*'."""
        result: dict[str, Any] = {}
        if self._redis_available and self._client:
            try:
                async for key in self._client.scan_iter(match=f"{prefix}*"):
                    raw = await self._client.get(key)
                    if raw is not None:
                        result[key] = json.loads(raw)
                        self._local_cache[key] = result[key]
            except Exception as exc:
                logger.warning(f"Redis scan error: {exc}")
        # Fallback: scan local cache
        for key, value in self._local_cache.items():
            if key.startswith(prefix):
                result[key] = value
        return result

    # ------------------------------------------------------------------
    # Namespaced convenience methods
    # ------------------------------------------------------------------

    async def set_session(self, key: str, value: Any) -> None:
        await self.set(f"deep:session:{key}", value, ttl_s=86400)

    async def get_session(self, key: str, default: Any = None) -> Any:
        return await self.get(f"deep:session:{key}", default)

    async def set_device(self, device_id: str, key: str, value: Any) -> None:
        await self.set(f"deep:device:{device_id}:{key}", value)

    async def get_device(self, device_id: str, key: str, default: Any = None) -> Any:
        return await self.get(f"deep:device:{device_id}:{key}", default)

    async def set_global(self, key: str, value: Any, broadcast: bool = False) -> None:
        await self.set(f"deep:global:{key}", value, broadcast=broadcast)

    async def get_global(self, key: str, default: Any = None) -> Any:
        return await self.get(f"deep:global:{key}", default)

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    async def save_conversation_turn(
        self,
        command: str,
        response: str,
        device_id: str,
        mood: str,
    ) -> None:
        """Append a user/DEEP turn to the shared conversation log."""
        conv_id = self._resolve_instance_id()
        key = f"deep:conversation:{conv_id}"
        history: list[dict[str, Any]] = await self.get(key, default=[])
        now = self._now()

        history.append({
            "role": "user",
            "content": command,
            "device": device_id,
            "mood": mood,
            "timestamp": now,
        })
        history.append({
            "role": "deep",
            "content": response,
            "timestamp": now,
        })

        max_history = self._resolve_conversation_max()
        history = history[-max_history:]
        await self.set(key, history, ttl_s=86400, broadcast=True)

    async def get_conversation_history(self) -> list[dict[str, Any]]:
        conv_id = self._resolve_instance_id()
        return await self.get(f"deep:conversation:{conv_id}", default=[])

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _restore_session_state(self) -> None:
        """Load deep:global:* keys into local cache on startup."""
        if not self._redis_available or not self._client:
            return
        try:
            global_keys = await self.get_all("deep:global:")
            self._local_cache.update(global_keys)
            logger.info(f"Restored {len(global_keys)} global keys from Redis")
        except Exception as exc:
            logger.warning(f"Session restore error: {exc}")

    async def _sync_loop(self) -> None:
        """Periodically push DEEP state to Redis."""
        interval = self._resolve_sync_interval()
        while not self._stop_event.is_set():
            try:
                await self.set_global(
                    "status",
                    {
                        "version": "v2",
                        "last_sync": self._now(),
                    },
                )
                self._last_sync = self._now()
            except Exception as exc:
                logger.debug(f"Sync loop error: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _listen_for_changes(self) -> None:
        """Subscribe to deep:state_changes and update local cache."""
        if not self._redis_available or not self._client:
            return

        try:
            self._pubsub = self._client.pubsub()
            await self._pubsub.subscribe("deep:state_changes")
            logger.info("Subscribed to deep:state_changes")
        except Exception as exc:
            logger.warning(f"Pub/sub subscribe error: {exc}")
            return

        while not self._stop_event.is_set():
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message is None:
                    continue
                data = json.loads(message["data"])
                key = data.get("key")
                value = data.get("value")
                source_device = data.get("source_device")
                if key:
                    self._local_cache[key] = value
                    await self._event_bus.publish(
                        "state_synced",
                        {
                            "key": key,
                            "value": value,
                            "source_device": source_device,
                        },
                    )
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.debug(f"Pub/sub listen error: {exc}")
