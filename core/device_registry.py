"""
core/device_registry.py

Tracks which DEEP client devices are currently active and what they
last did. Works with RedisStateManager for cross-device coordination.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Device:
    """Snapshot of a known DEEP client device."""

    device_id: str
    name: str
    platform: str
    tailscale_ip: str | None
    last_seen: str
    last_command: str | None
    active: bool


class DeviceRegistry:
    """
    Tracks active DEEP devices and enables handoff between them.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._started = False
        self._stop_event = asyncio.Event()
        self._heartbeat_task: asyncio.Task | None = None

        # Resolved from config
        self._device_id = self._resolve_device_id()
        self._device_name = self._resolve_device_name()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve_device_id(self) -> str:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "deep_device_id", sys.platform)
        except Exception:
            return sys.platform

    def _resolve_device_name(self) -> str:
        try:
            from core.config import Settings

            settings = Settings()
            return getattr(settings, "deep_device_name", sys.platform)
        except Exception:
            return sys.platform

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Register this device and start heartbeat."""
        self._started = True
        self._stop_event.clear()

        # Register this device
        await self._redis_state.set_device(
            self._device_id,
            "info",
            {
                "name": self._device_name,
                "platform": sys.platform,
                "last_seen": self._now(),
                "active": True,
            },
        )

        # Subscribe to state_synced for cross-device awareness
        self._event_bus.subscribe("state_synced", self._on_state_synced)

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"DeviceRegistry started — this device: {self._device_id}")

    async def stop(self) -> None:
        """Stop heartbeat and mark device inactive."""
        self._started = False
        self._stop_event.set()

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        try:
            self._event_bus.unsubscribe("state_synced", self._on_state_synced)
        except Exception:
            pass

        # Mark inactive
        try:
            await self._redis_state.set_device(
                self._device_id,
                "info",
                {
                    "name": self._device_name,
                    "platform": sys.platform,
                    "last_seen": self._now(),
                    "active": False,
                },
            )
        except Exception:
            pass

        logger.info("DeviceRegistry stopped")

    def status(self) -> dict[str, Any]:
        """Return operational status."""
        return {
            "this_device": self._device_id,
            "active_devices": 0,  # populated lazily
            "primary_device": None,
        }

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_state_synced(self, event_name: str, payload: dict) -> None:
        """React to state changes from other devices (optional logging)."""
        source = payload.get("source_device")
        if source and source != self._device_id:
            logger.debug(f"State synced from {source}: {payload.get('key')}")

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Update this device's last_seen every 15 seconds."""
        while not self._stop_event.is_set():
            try:
                await self._redis_state.set_device(
                    self._device_id,
                    "heartbeat",
                    self._now(),
                )
            except Exception as exc:
                logger.debug(f"Heartbeat error: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_active_devices(self) -> list[Device]:
        """Return devices with a heartbeat within the last 60 seconds."""
        now = datetime.now(timezone.utc)
        devices: list[Device] = []

        all_device_data = await self._redis_state.get_all("deep:device:")
        for key, value in all_device_data.items():
            # key format: deep:device:{device_id}:{subkey}
            parts = key.split(":")
            if len(parts) < 4:
                continue
            device_id = parts[2]

            info = value if isinstance(value, dict) else {}
            heartbeat = await self._redis_state.get_device(
                device_id, "heartbeat", ""
            )
            last_seen = info.get("last_seen", heartbeat or "")

            # Parse timestamp
            active = False
            if last_seen:
                try:
                    seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    delta = (now - seen).total_seconds()
                    active = delta < 60
                except Exception:
                    pass

            if active:
                devices.append(
                    Device(
                        device_id=device_id,
                        name=info.get("name", device_id),
                        platform=info.get("platform", "unknown"),
                        tailscale_ip=info.get("tailscale_ip"),
                        last_seen=last_seen,
                        last_command=info.get("last_command"),
                        active=True,
                    )
                )

        return devices

    async def get_primary_device(self) -> Device | None:
        """Return the device that most recently spoke a command."""
        active = await self.get_active_devices()
        primary_id = await self._redis_state.get_global("active_device")
        if not primary_id:
            return active[0] if active else None
        for d in active:
            if d.device_id == primary_id:
                return d
        return None

    async def handoff_to(self, device_id: str) -> None:
        """Transfer primary control to another device."""
        await self._redis_state.set_global(
            "active_device", device_id, broadcast=True
        )
        await self._event_bus.publish(
            "device_handoff",
            {"to": device_id, "from": self._device_id},
        )
        logger.info(f"Handoff to {device_id}")

    async def mark_command(self, command: str) -> None:
        """Record that this device just issued a command."""
        now = self._now()
        await self._redis_state.set_global(
            "last_command",
            {
                "command": command,
                "device": self._device_id,
                "timestamp": now,
            },
            broadcast=True,
        )
        await self._redis_state.set_global(
            "active_device", self._device_id, broadcast=True
        )
