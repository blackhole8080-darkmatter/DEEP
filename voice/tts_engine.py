"""
voice/tts_engine.py

Neural text-to-speech using Piper (local, offline).
Subscribes to *deep_response* and *tts_speak* events,
queues utterances, and plays audio via sounddevice.
Supports interruption when wake word fires mid-speech.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("voice.tts")

from core.event_bus import EventBus

# ── Optional dependencies ──────────────────────────────────────────────────

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not installed — TTSEngine audio output disabled")

try:
    from piper.voice import PiperVoice
    PIPER_AVAILABLE = True
    try:
        # Newer piper (>=1.0) routes synthesis params through SynthesisConfig
        # and exposes synthesize_wav(); older builds took kwargs on synthesize().
        from piper import SynthesisConfig as _PiperSynthesisConfig
    except Exception:
        _PiperSynthesisConfig = None
except ImportError:
    PIPER_AVAILABLE = False
    _PiperSynthesisConfig = None
    logger.warning("piper-tts not installed — TTSEngine synthesis disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# Internal queue item
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(order=True)
class _QueueItem:
    """PriorityQueue item — lower *priority_val* = higher priority."""
    priority_val: int                                # 0=urgent, 1=normal
    seq: int = field(compare=True)                   # tie-breaker for FIFO
    text: str = field(compare=False, default="")
    timestamp: float = field(compare=False, default=0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TTSEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    """Neural TTS with priority queue and wake-word interruption."""

    def __init__(
        self,
        event_bus: EventBus,
        *,
        model_path: str = "voice/models/en_US-lessac-medium.onnx",
        speaking_rate: float = 1.0,  # length_scale inverse
        max_sentence_length: int = 500,
        spatial_audio=None,
    ) -> None:
        self.event_bus = event_bus
        self.model_path = Path(model_path)
        self.speaking_rate = speaking_rate
        self.max_sentence_length = max_sentence_length
        self._spatial_audio = spatial_audio

        self._started = False
        self._voice: Optional[Any] = None
        self._queue: asyncio.PriorityQueue[_QueueItem] = asyncio.PriorityQueue()
        self._queue_seq = 0
        self._speaking = False
        self._interrupted = False
        self._processor_task: Optional[asyncio.Task] = None

        self._total_spoken = 0
        self._total_synthesis_ms = 0.0
        self._last_text: Optional[str] = None

        # Sentence silence (Piper inter-sentence pause, seconds)
        try:
            from core.config import Settings
            settings = Settings()
            self.sentence_silence = float(getattr(settings, "tts_sentence_silence", 0.05))
        except Exception:
            self.sentence_silence = 0.05

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started:
            return

        # Load Piper voice (can be slow — run in executor)
        if PIPER_AVAILABLE and self.model_path.exists():
            loop = asyncio.get_running_loop()
            self._voice = await loop.run_in_executor(
                None,
                lambda: PiperVoice.load(
                    str(self.model_path),
                    config_path=str(self.model_path) + ".json",
                ),
            )
            logger.info(f"Piper voice loaded: {self.model_path.name}")
        else:
            if not PIPER_AVAILABLE:
                logger.warning("TTSEngine: piper-tts not installed")
            elif not self.model_path.exists():
                logger.warning(f"TTSEngine: model not found at {self.model_path}")

        # Subscribe
        self.event_bus.subscribe("deep_response", self._on_deep_response)
        self.event_bus.subscribe("tts_speak", self._on_tts_speak)
        self.event_bus.subscribe("wake_word_detected", self._on_wake_interrupt)

        self._processor_task = asyncio.create_task(self._process_queue())
        self._started = True
        logger.info("TTSEngine started")

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False

        # Signal processor to exit
        await self._queue.put(_QueueItem(priority_val=0, seq=-1, text="__shutdown__"))

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        self.event_bus.unsubscribe("deep_response", self._on_deep_response)
        self.event_bus.unsubscribe("tts_speak", self._on_tts_speak)
        self.event_bus.unsubscribe("wake_word_detected", self._on_wake_interrupt)

        self._voice = None
        logger.info("TTSEngine stopped")

    # ── Model download helper ──────────────────────────────────────────────

    async def ensure_model(self) -> bool:
        """Download Piper voice model from HuggingFace if not present."""
        if self.model_path.exists() and (self.model_path.with_suffix(".onnx.json")).exists():
            return True

        base_url = (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/"
            "en_US/lessac/medium/"
        )
        onnx_name = "en_US-lessac-medium.onnx"
        json_name = "en_US-lessac-medium.onnx.json"

        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        from voice.audio_utils import download_file

        ok1 = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download_file(
                base_url + onnx_name,
                self.model_path,
            ),
        )
        ok2 = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download_file(
                base_url + json_name,
                self.model_path.with_suffix(".onnx.json"),
            ),
        )
        return ok1 and ok2

    # ── EventBus handlers ──────────────────────────────────────────────────

    async def _on_deep_response(self, event_name: str, payload: dict) -> None:
        """Triggered by GraphOrchestrator or AgentSwarm response."""
        text = payload.get("response", "")
        if text:
            await self.speak(text, priority="normal")

    async def _on_tts_speak(self, event_name: str, payload: dict) -> None:
        """Direct speech request (e.g. from BreakthroughDetector)."""
        text = payload.get("text", "")
        priority = payload.get("priority", "normal")
        if text:
            await self.speak(text, priority=priority)

    async def _on_wake_interrupt(self, event_name: str, payload: dict) -> None:
        """Stop speaking immediately if wake word fires mid-speech."""
        if self._speaking:
            self._interrupted = True
            if SOUNDDEVICE_AVAILABLE:
                sd.stop()
            logger.info("TTS interrupted by wake word")
            await self.event_bus.publish("tts_interrupted", {
                "timestamp": self._now_iso(),
                "reason": "wake_word",
            })

    # ── Public API ─────────────────────────────────────────────────────────

    async def speak(self, text: str, priority: str = "normal") -> None:
        """Queue text for synthesis and playback."""
        if not self._started:
            logger.warning("speak() called before start() — queuing anyway")

        priority_val = 0 if priority == "urgent" else 1
        self._queue_seq += 1
        item = _QueueItem(
            priority_val=priority_val,
            seq=self._queue_seq,
            text=text,
            timestamp=time.time(),
        )
        await self._queue.put(item)
        logger.debug(f"Queued TTS ({priority}): {text[:60]}...")

    # ── Queue processor (background task) ────────────────────────────────────

    async def _process_queue(self) -> None:
        """Consume queue items one at a time."""
        while self._started:
            try:
                item: _QueueItem = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            if item.text == "__shutdown__":
                break

            await self._speak_one(item)

    async def _speak_one(self, item: _QueueItem) -> None:
        """Synthesise and play a single queue item with overlapped synthesis."""
        if not self._voice:
            logger.warning("Piper voice not loaded — skipping speech")
            await self.event_bus.publish("tts_error", {
                "text": item.text[:200],
                "error": "Piper voice not loaded",
            })
            return

        raw_text = item.text
        clean_text = self._strip_for_speech(raw_text)
        if not clean_text:
            logger.debug("Empty text after stripping — skipping")
            return

        sentences = self._split_sentences(clean_text)
        if not sentences:
            return

        self._speaking = True
        self._interrupted = False
        start_all = time.monotonic()
        spoken_sentences: List[str] = []

        try:
            # Producer/consumer queue: synthesis runs ahead of playback.
            # maxsize=1 means only one sentence is buffered ahead,
            # preventing memory from ballooning on long texts.
            audio_queue: asyncio.Queue[Tuple[Optional[np.ndarray], str]] = asyncio.Queue(maxsize=1)

            async def synthesis_worker() -> None:
                for sentence in sentences:
                    if self._interrupted:
                        break
                    if not sentence.strip():
                        continue
                    audio = await self._synthesise(sentence)
                    if audio is not None and not self._interrupted:
                        await audio_queue.put((audio, sentence))
                await audio_queue.put((None, ""))  # sentinel

            async def playback_worker() -> None:
                while True:
                    if self._interrupted:
                        break
                    audio, sentence_text = await audio_queue.get()
                    if audio is None:
                        break
                    await self._play(audio)
                    spoken_sentences.append(sentence_text)
                    await self.event_bus.publish("tts_sentence_spoken", {
                        "sentence": sentence_text,
                        "timestamp": self._now_iso(),
                    })

            await asyncio.gather(synthesis_worker(), playback_worker())
        except Exception as e:
            logger.error(f"TTS playback error: {e}")
            await self.event_bus.publish("tts_error", {
                "text": raw_text[:200],
                "error": str(e),
            })
        finally:
            self._speaking = False
            duration_ms = int((time.monotonic() - start_all) * 1000)
            self._total_spoken += len(spoken_sentences)
            self._last_text = raw_text

            if not self._interrupted:
                await self.event_bus.publish("tts_complete", {
                    "text": raw_text[:500],
                    "duration_ms": duration_ms,
                    "sentence_count": len(spoken_sentences),
                })

    # ── Synthesis ────────────────────────────────────────────────────────────

    async def _synthesise(self, text: str) -> Optional[np.ndarray]:
        """Synthesise one sentence to a numpy float32 array."""
        if not self._voice:
            return None

        loop = asyncio.get_running_loop()
        start = time.monotonic()

        def _do_synth():
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)          # 16-bit
                wav.setframerate(22050)
                # length_scale inverse = speaking_rate
                length_scale = max(0.5, min(2.0, 1.0 / max(0.5, self.speaking_rate)))
                if _PiperSynthesisConfig is not None and hasattr(self._voice, "synthesize_wav"):
                    # Newer piper API (>=1.0): params via SynthesisConfig.
                    syn_config = _PiperSynthesisConfig(length_scale=length_scale)
                    self._voice.synthesize_wav(text, wav, syn_config=syn_config)
                else:
                    # Legacy piper API: kwargs on synthesize().
                    self._voice.synthesize(
                        text, wav,
                        length_scale=length_scale,
                        sentence_silence=self.sentence_silence,
                    )
            buf.seek(0)
            with wave.open(buf, "rb") as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio

        try:
            audio = await loop.run_in_executor(None, _do_synth)
        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return None

        self._total_synthesis_ms += (time.monotonic() - start) * 1000
        return audio

    # ── Playback ───────────────────────────────────────────────────────────

    async def _play(self, audio: np.ndarray) -> None:
        """Play audio via sounddevice (non-blocking, wait in executor)."""
        if not SOUNDDEVICE_AVAILABLE:
            logger.warning("sounddevice unavailable — cannot play audio")
            return

        # Spatial audio panning (v2)
        if self._spatial_audio and self._spatial_audio._enabled:
            audio = self._spatial_audio.pan_audio(audio, self._spatial_audio.get_pan_for_event("tts_speak"))

        loop = asyncio.get_running_loop()

        def _do_play():
            if audio.ndim == 2:
                sd.play(audio, samplerate=22050)
            else:
                sd.play(audio, samplerate=22050)
            sd.wait()

        await loop.run_in_executor(None, _do_play)

    # ── Text helpers ─────────────────────────────────────────────────────────

    def _strip_for_speech(self, text: str) -> str:
        """Sanitise text for TTS (remove markdown, URLs, emoji)."""
        # Same logic as audio_utils.strip_for_speech — inline for speed
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # bold
        text = re.sub(r"__(.*?)__", r"\1", text)       # underline
        text = re.sub(r"`([^`]+)`", r"\1", text)       # inline code
        text = re.sub(r"#+\s+", "", text)              # headings
        text = re.sub(r"https?://\S+", "", text)       # URLs
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)  # bullets
        text = re.sub(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF\U0001F700-\U0001F77F"
            r"\U00002702-\U000027B0\U000024C2-\U0001F251]+",
            "", text, flags=re.UNICODE,
        )
        text = " ".join(text.split())
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences respecting max length."""
        raw = re.split(r"(?<=[.!?])\s+", text)
        sentences = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            # If sentence too long, chunk on commas
            while len(s) > self.max_sentence_length:
                idx = s.rfind(",", 0, self.max_sentence_length)
                if idx <= 0:
                    idx = self.max_sentence_length
                sentences.append(s[:idx].strip())
                s = s[idx + 1:].strip()
            if s:
                sentences.append(s)
        return sentences

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> Dict[str, Any]:
        avg_synth = (
            self._total_synthesis_ms / self._total_spoken
            if self._total_spoken else 0.0
        )
        return {
            "model_name": self.model_path.name if self.model_path else "none",
            "speaking": self._speaking,
            "queue_length": self._queue.qsize(),
            "total_spoken": self._total_spoken,
            "avg_synthesis_ms": round(avg_synth, 1),
            "started": self._started,
        }
