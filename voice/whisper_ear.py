"""
voice/whisper_ear.py

Private microphone input mode.
When BT earbuds with a mic are connected, DEEP receives voice commands
through the earbud mic instead of the room microphone.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not installed — WhisperEar disabled")


class WhisperEar:
    """
    Switches STT input to Bluetooth earbud mic when connected.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, bt_audio: Any) -> None:
        self._event_bus = event_bus
        self._bt_audio = bt_audio
        self._started = False
        self._active = False
        self._bt_mic_device: str | None = None
        self._device_index: int | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._started = True
        self._event_bus.subscribe("bt_audio_activated", self._on_bt_activated)
        self._event_bus.subscribe("bt_audio_deactivated", self._on_bt_deactivated)
        logger.info("WhisperEar started")

    async def stop(self) -> None:
        self._started = False
        try:
            self._event_bus.unsubscribe("bt_audio_activated", self._on_bt_activated)
            self._event_bus.unsubscribe("bt_audio_deactivated", self._on_bt_deactivated)
        except Exception:
            pass
        if self._active:
            await self._on_bt_deactivated("", {})
        logger.info("WhisperEar stopped")

    def status(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "bt_mic_device": self._bt_mic_device,
            "device_index": self._device_index,
        }

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_bt_activated(self, event_name: str, payload: dict) -> None:
        device_name = payload.get("device_name", "")
        if not device_name:
            return
        mic_index = await self._find_bt_mic(device_name)
        if mic_index is not None:
            await self._switch_input_to_bt(mic_index)
            self._bt_mic_device = device_name
            self._active = True
            await self._event_bus.publish(
                "whisper_ear_active",
                {"device": device_name, "device_index": mic_index},
            )
            logger.info(f"WhisperEar active — input switched to BT mic: {device_name}")

    async def _on_bt_deactivated(self, event_name: str, payload: dict) -> None:
        if not self._active:
            return
        await self._event_bus.publish(
            "stt_restart_input",
            {"device_index": None},
        )
        await self._event_bus.publish("whisper_ear_inactive", {})
        self._active = False
        self._bt_mic_device = None
        self._device_index = None
        logger.info("WhisperEar inactive — input restored to default")

    # ------------------------------------------------------------------
    # Mic discovery
    # ------------------------------------------------------------------

    async def _find_bt_mic(self, device_name: str) -> int | None:
        if not PYAUDIO_AVAILABLE:
            return None
        try:
            pa = pyaudio.PyAudio()
            fragments = device_name.lower().split()
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                name = info.get("name", "").lower()
                if info.get("maxInputChannels", 0) > 0:
                    # Match if any fragment of the BT device name appears
                    if any(f in name for f in fragments if len(f) > 2):
                        pa.terminate()
                        return i
            pa.terminate()
        except Exception as exc:
            logger.warning(f"BT mic discovery error: {exc}")
        return None

    async def _switch_input_to_bt(self, device_index: int) -> None:
        self._device_index = device_index
        await self._event_bus.publish(
            "stt_restart_input",
            {"device_index": device_index},
        )
