"""
voice/stt_engine.py

Speech-to-text using OpenAI Whisper (local, no cloud).
Triggered by the *wake_word_detected* event, records until
silence is detected, then transcribes and publishes
*user_command* on the EventBus.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("voice.stt")

from core.event_bus import EventBus

# ── Optional dependencies ──────────────────────────────────────────────────

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not installed — STTEngine disabled")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("openai-whisper not installed — STTEngine disabled")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# Config dataclass (mirrors config.py keys)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class STTConfig:
    model_name: str = "base"                    # tiny | base | small
    silence_threshold: int = 300                # RMS units
    silence_duration_ms: int = 1000             # ms of silence to stop recording
    max_command_duration_s: float = 10.0        # hard cap
    device_index: Optional[int] = None          # None = system default
    sample_rate: int = 16000


# ═══════════════════════════════════════════════════════════════════════════════
# STTEngine
# ═══════════════════════════════════════════════════════════════════════════════

class STTEngine:
    """Records audio after wake-word, transcribes with Whisper, publishes command."""

    def __init__(
        self,
        event_bus: EventBus,
        *,
        model_name: str = "base",
        silence_threshold: int = 300,
        silence_duration_ms: int = 1000,
        max_command_duration_s: float = 10.0,
        device_index: Optional[int] = None,
    ) -> None:
        self.event_bus = event_bus
        self.cfg = STTConfig(
            model_name=model_name,
            silence_threshold=silence_threshold,
            silence_duration_ms=silence_duration_ms,
            max_command_duration_s=max_command_duration_s,
            device_index=device_index,
        )

        self._started = False
        self._model = None
        self._device = "cpu"
        self._total_transcriptions = 0
        self._total_ms = 0.0
        self._last_command: Optional[str] = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started:
            return
        if not WHISPER_AVAILABLE:
            logger.warning("STTEngine.start() skipped — openai-whisper missing")
            return
        if not PYAUDIO_AVAILABLE:
            logger.warning("STTEngine.start() skipped — pyaudio missing")
            return

        # Determine device
        if TORCH_AVAILABLE and torch.cuda.is_available():
            self._device = "cuda"
        else:
            self._device = "cpu"

        # Load model in executor thread (blocks for a few seconds)
        logger.info(f"Loading Whisper '{self.cfg.model_name}' on {self._device}...")
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(
            None, lambda: whisper.load_model(self.cfg.model_name).to(self._device),
        )
        logger.info(f"Whisper '{self.cfg.model_name}' loaded ({self._device})")

        # Subscribe to wake word
        self.event_bus.subscribe("wake_word_detected", self._on_wake)
        # Subscribe to BT mic switching (v2)
        self.event_bus.subscribe("stt_restart_input", self._on_restart_input)
        self._started = True
        logger.info("STTEngine started (listening for wake_word_detected)")

    async def stop(self) -> None:
        if not self._started:
            return
        self.event_bus.unsubscribe("wake_word_detected", self._on_wake)
        self._model = None
        self._started = False
        logger.info("STTEngine stopped")

    # ── Wake handler ─────────────────────────────────────────────────────────

    async def _on_wake(self, event_name: str, payload: dict) -> None:
        """Triggered by EventBus 'wake_word_detected'."""
        logger.info("Wake word detected — starting command capture")
        await self._capture_and_transcribe()

    async def _on_restart_input(self, event_name: str, payload: dict) -> None:
        """Switch input device (e.g. to BT earbud mic)."""
        idx = payload.get("device_index")
        self.cfg.device_index = idx
        logger.info(f"STT input device switched to index: {idx}")

    async def _capture_and_transcribe(self) -> None:
        """Full flow: record → transcribe → publish."""
        await self.event_bus.publish("stt_listening", {"timestamp": self._now_iso()})

        try:
            audio = await self._record_command()
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            await self.event_bus.publish("stt_failed", {"reason": "recording_error", "error": str(e)})
            return

        if audio is None or len(audio) == 0:
            await self.event_bus.publish("stt_failed", {"reason": "no_audio"})
            return

        await self.event_bus.publish("stt_processing", {
            "timestamp": self._now_iso(),
            "audio_samples": len(audio),
        })

        try:
            text, confidence = await self._transcribe(audio)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            await self.event_bus.publish("stt_failed", {"reason": "transcription_error", "error": str(e)})
            return

        if text and len(text) > 2:
            self._last_command = text
            self._total_transcriptions += 1

            await self.event_bus.publish("user_command", {
                "text": text,
                "source": "microphone",
                "timestamp": self._now_iso(),
                "confidence": confidence,
            })
            await self.event_bus.publish("stt_complete", {"text": text})
            logger.info(f"STT result: '{text[:80]}...' (conf={confidence:.3f})")
        else:
            await self.event_bus.publish("stt_failed", {"reason": "empty", "raw": text})
            logger.info("STT result empty — nothing recognised")

    # ── Recording ────────────────────────────────────────────────────────────

    async def _record_command(self) -> Optional[np.ndarray]:
        """Record audio from mic until silence is detected."""
        if not PYAUDIO_AVAILABLE:
            return None

        CHUNK_MS = 100
        CHUNK = int(self.cfg.sample_rate * CHUNK_MS / 1000)  # ~1600 samples
        SILENCE_CHUNKS = int(self.cfg.silence_duration_ms / CHUNK_MS)
        MAX_CHUNKS = int(self.cfg.max_command_duration_s * 1000 / CHUNK_MS)

        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.cfg.sample_rate,
                input=True,
                input_device_index=self.cfg.device_index,
                frames_per_buffer=CHUNK,
            )
        except Exception as e:
            logger.error(f"PyAudio input stream failed: {e}")
            return None

        frames: List[np.ndarray] = []
        silent_count = 0
        started = False

        logger.debug("Recording started...")
        try:
            for i in range(MAX_CHUNKS):
                data = stream.read(CHUNK, exception_on_overflow=False)
                pcm = np.frombuffer(data, dtype=np.int16)
                frames.append(pcm)

                rms = np.sqrt(np.mean(pcm.astype(np.float64) ** 2))
                is_silent = rms < self.cfg.silence_threshold

                if not started:
                    # Wait for first non-silent chunk (user started speaking)
                    if not is_silent:
                        started = True
                        silent_count = 0
                else:
                    if is_silent:
                        silent_count += 1
                        if silent_count >= SILENCE_CHUNKS:
                            break  # silence detected → stop
                    else:
                        silent_count = 0
        except Exception as e:
            logger.warning(f"Recording interrupted: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not frames:
            return None

        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        logger.debug(f"Recorded {len(audio)} samples ({len(audio)/self.cfg.sample_rate:.2f}s)")
        return audio

    # ── Transcription ────────────────────────────────────────────────────────

    async def _transcribe(self, audio: np.ndarray) -> Tuple[str, float]:
        """Run Whisper on audio in executor thread, return (text, confidence)."""
        if self._model is None:
            return "", 0.0

        loop = asyncio.get_running_loop()
        start = time.monotonic()

        result = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                audio,
                language="en",
                fp16=False,
                condition_on_previous_text=False,
            ),
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        self._total_ms += elapsed_ms

        text = result.get("text", "").strip()
        segments = result.get("segments", [])
        if segments and "no_speech_prob" in segments[0]:
            confidence = max(0.0, 1.0 - segments[0]["no_speech_prob"])
        else:
            confidence = 0.9

        return text, confidence

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> Dict[str, Any]:
        avg_ms = (
            self._total_ms / self._total_transcriptions
            if self._total_transcriptions else 0.0
        )
        return {
            "model_name": self.cfg.model_name,
            "device": self._device,
            "total_transcriptions": self._total_transcriptions,
            "avg_transcription_ms": round(avg_ms, 1),
            "last_command": self._last_command,
            "started": self._started,
        }
