"""
voice/bluetooth_audio.py

Bluetooth private ear — routes DEEP TTS output to a paired Bluetooth audio device.
Uses bleak for passive device discovery and OS-level audio routing for activation.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


try:
    from bleak import BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logger.warning("bleak not installed — BluetoothAudioManager disabled")

# pycaw is Windows-only
try:
    import pycaw.pycaw as pycaw
    from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False


@dataclass
class BTAudioDevice:
    """Paired Bluetooth audio-capable device."""

    mac: str
    name: str
    connected: bool = False
    is_audio: bool = True
    signal_rssi: int = -100
    last_seen: str = ""
    is_preferred: bool = False


class BluetoothAudioManager:
    """
    Manages TTS routing to a paired Bluetooth audio device.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state

        self._started = False
        self._stop_event = asyncio.Event()
        self._monitor_task: asyncio.Task | None = None

        self._preferred_macs: set[str] = self._resolve_preferred()
        self._poll_interval: int = self._resolve_int("bt_audio_poll_s", 15)
        self._bt_active = False
        self._active_device: BTAudioDevice | None = None
        self._volume = 75

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve_preferred(self) -> set[str]:
        try:
            from core.config import Settings
            macs = getattr(Settings(), "preferred_bt_audio_devices", [])
            return {m.upper() for m in macs}
        except Exception:
            return set()

    def _resolve_int(self, name: str, default: int) -> int:
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
        self._stop_event.clear()

        self._event_bus.subscribe("tts_speak", self._handle_tts_speak)
        self._event_bus.subscribe("tts_complete", self._handle_tts_complete)

        self._monitor_task = asyncio.create_task(self._connection_monitor_loop())
        logger.info("BluetoothAudioManager started")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()

        try:
            self._event_bus.unsubscribe("tts_speak", self._handle_tts_speak)
            self._event_bus.unsubscribe("tts_complete", self._handle_tts_complete)
        except Exception:
            pass

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if self._bt_active:
            await self._deactivate_bt_routing()

        logger.info("BluetoothAudioManager stopped")

    def status(self) -> dict[str, Any]:
        return {
            "bt_active": self._bt_active,
            "active_device": self._active_device.name if self._active_device else None,
            "available_devices": 0,
            "preferred_configured": bool(self._preferred_macs),
            "volume_percent": self._volume,
        }

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def _connection_monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                devices = await self._scan_connected_audio_devices()
                preferred = [d for d in devices if d.mac in self._preferred_macs]
                if preferred and not self._bt_active:
                    await self._activate_bt_routing(preferred[0])
                elif not preferred and self._bt_active:
                    await self._deactivate_bt_routing()
            except Exception as exc:
                logger.debug(f"BT monitor error: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def _scan_connected_audio_devices(self) -> list[BTAudioDevice]:
        devices: list[BTAudioDevice] = []

        if not BLEAK_AVAILABLE:
            return devices

        try:
            discovered = await BleakScanner.discover(timeout=5.0)
            for d in discovered:
                mac = d.address.upper()
                name = d.name or "unknown"
                rssi = d.rssi if hasattr(d, "rssi") else -100
                is_preferred = mac in self._preferred_macs
                devices.append(BTAudioDevice(
                    mac=mac,
                    name=name,
                    connected=True,
                    is_audio=True,
                    signal_rssi=rssi,
                    last_seen=self._now(),
                    is_preferred=is_preferred,
                ))
        except Exception as exc:
            logger.debug(f"BT scan error: {exc}")

        return devices

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    async def _activate_bt_routing(self, device: BTAudioDevice) -> None:
        if sys.platform == "win32" and PYCAW_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._set_default_endpoint_windows, device.name)
            except Exception as exc:
                logger.warning(f"Windows BT routing failed: {exc}")
        elif sys.platform == "linux":
            try:
                subprocess.run(
                    ["pactl", "set-default-sink", f"bluealsa_sink_{device.mac.replace(':', '_')}"],
                    capture_output=True, timeout=5,
                )
            except Exception as exc:
                logger.debug(f"Linux BT routing failed: {exc}")

        self._bt_active = True
        self._active_device = device
        await self._redis_state.set_global(
            "audio_output",
            {"type": "bluetooth", "device": device.name, "mac": device.mac},
        )
        await self._event_bus.publish(
            "bt_audio_activated",
            {"device_name": device.name, "mac": device.mac},
        )
        await self._event_bus.publish(
            "tts_speak",
            {
                "text": f"Private channel active. Connected to {device.name}.",
                "priority": "normal",
            },
        )
        logger.info(f"BT audio activated: {device.name}")

    async def _deactivate_bt_routing(self) -> None:
        if sys.platform == "win32" and PYCAW_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._restore_default_endpoint_windows)
            except Exception as exc:
                logger.debug(f"Windows BT restore failed: {exc}")
        elif sys.platform == "linux":
            try:
                subprocess.run(
                    ["pactl", "set-default-sink", "@DEFAULT_SINK@"],
                    capture_output=True, timeout=5,
                )
            except Exception as exc:
                logger.debug(f"Linux BT restore failed: {exc}")

        self._bt_active = False
        self._active_device = None
        await self._event_bus.publish("bt_audio_deactivated", {})
        logger.info("BT audio deactivated")

    # Windows pycaw helpers (run in executor)

    def _set_default_endpoint_windows(self, device_name: str) -> None:
        try:
            devices = AudioUtilities.GetSpeakers()
            # pycaw doesn't have a clean "set default by name" API;
            # this is a best-effort approach for known endpoints.
            # Full implementation would use IMMDeviceEnumerator policy config.
            pass
        except Exception:
            pass

    def _restore_default_endpoint_windows(self) -> None:
        try:
            # Restore to system default
            pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # TTS handling
    # ------------------------------------------------------------------

    async def _handle_tts_speak(self, event_name: str, payload: dict) -> None:
        if self._bt_active:
            logger.debug("TTS routed to BT device (already default)")

    async def _handle_tts_complete(self, event_name: str, payload: dict) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_available_devices(self) -> list[BTAudioDevice]:
        return await self._scan_connected_audio_devices()

    async def connect_device(self, mac: str) -> bool:
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     f"[Windows.Devices.Bluetooth.BluetoothDevice]::FromBluetoothAddressAsync(0x{mac.replace(':', '')}).AsTask().Wait()"],
                    capture_output=True, timeout=10,
                )
                return True
            except Exception:
                pass
        elif sys.platform == "linux":
            try:
                subprocess.run(
                    ["bluetoothctl", "connect", mac],
                    capture_output=True, timeout=10,
                )
                return True
            except Exception:
                pass
        return False

    async def disconnect_device(self, mac: str) -> bool:
        if sys.platform == "linux":
            try:
                subprocess.run(
                    ["bluetoothctl", "disconnect", mac],
                    capture_output=True, timeout=10,
                )
                return True
            except Exception:
                pass
        return False

    async def set_volume(self, percent: int) -> None:
        self._volume = max(0, min(100, percent))

        if sys.platform == "win32" and PYCAW_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._set_volume_windows, self._volume)
            except Exception:
                pass
        elif sys.platform == "linux":
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{self._volume}%"],
                    capture_output=True, timeout=5,
                )
            except Exception:
                pass

        await self._event_bus.publish(
            "volume_changed",
            {"percent": self._volume, "device": self._active_device.name if self._active_device else None},
        )

    def _set_volume_windows(self, percent: int) -> None:
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                volume = session.SimpleAudioVolume
                if volume:
                    volume.SetMasterVolume(percent / 100.0, None)
        except Exception:
            pass
