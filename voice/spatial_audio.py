"""
voice/spatial_audio.py

Stereo panning for DEEP voice output.
Different event types come from different spatial directions
to create an intuitive spatial effect on headphones/earbuds.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SpatialAudio:
    """
    Applies stereo panning to TTS audio based on event type.

    Lifecycle: __init__ -> start() -> status()
    """

    # Pan position constants
    LEFT = -1.0
    CENTER = 0.0
    RIGHT = 1.0
    FRONT_LEFT = -0.7
    FRONT_RIGHT = 0.7

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        self._enabled = self._resolve_enabled()
        self._event_pan_map = self._resolve_pan_map()
        self._current_pan = 0.0
        self._started = False

    def _resolve_enabled(self) -> bool:
        try:
            from core.config import Settings
            return getattr(Settings(), "spatial_audio_enabled", True)
        except Exception:
            return True

    def _resolve_pan_map(self) -> dict[str, float]:
        try:
            from core.config import Settings
            return dict(getattr(Settings(), "spatial_event_pan_map", self._default_pan_map()))
        except Exception:
            return self._default_pan_map()

    @staticmethod
    def _default_pan_map() -> dict[str, float]:
        return {
            "security_alert": SpatialAudio.RIGHT,
            "unknown_device_detected": SpatialAudio.RIGHT,
            "threat_detected": SpatialAudio.RIGHT,
            "breakthrough_detected": SpatialAudio.LEFT,
            "briefing_ready": SpatialAudio.CENTER,
            "system_stats": SpatialAudio.LEFT,
            "tts_speak": SpatialAudio.CENTER,
            "deep_response": SpatialAudio.CENTER,
        }

    async def start(self) -> None:
        self._started = True
        logger.info(f"SpatialAudio started (enabled={self._enabled})")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "current_pan": self._current_pan,
            "stereo_output": True,
        }

    # ------------------------------------------------------------------
    # Panning
    # ------------------------------------------------------------------

    def pan_audio(self, audio_array: np.ndarray, position: float) -> np.ndarray:
        """
        Convert mono audio to stereo with panning.

        Args:
            audio_array: mono float32 array, shape (n,)
            position: -1.0 = full left, 0.0 = center, 1.0 = full right

        Returns:
            stereo float32 array, shape (n, 2)
        """
        if not self._enabled:
            # Return dual-mono (no panning)
            if audio_array.ndim == 1:
                return np.column_stack([audio_array, audio_array])
            return audio_array

        if audio_array.ndim == 2 and audio_array.shape[1] == 2:
            # Already stereo — just apply gain
            left_gain = 1.0 - max(0, position)
            right_gain = 1.0 + min(0, position)
            audio_array[:, 0] *= left_gain
            audio_array[:, 1] *= right_gain
            return audio_array

        if audio_array.ndim != 1:
            audio_array = audio_array.flatten()

        left_gain = 1.0 - max(0, position)
        right_gain = 1.0 + min(0, position)
        self._current_pan = position

        stereo = np.column_stack([
            audio_array * left_gain,
            audio_array * right_gain,
        ])
        return stereo.astype(np.float32)

    def get_pan_for_event(self, event_type: str) -> float:
        return self._event_pan_map.get(event_type, 0.0)
