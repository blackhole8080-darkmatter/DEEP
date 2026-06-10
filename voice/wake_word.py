"""
voice/wake_word.py

Wake-word detection using openWakeWord.
Runs continuously in a background thread so PyAudio's
blocking read() never stalls the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger("voice.wake_word")

from core.event_bus import EventBus

# ── Optional dependency ──────────────────────────────────────────────────

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not installed — WakeWordDetector disabled")

try:
    from openwakeword.model import Model
    OWW_AVAILABLE = True
except ImportError:
    OWW_AVAILABLE = False
    logger.warning("openwakeword not installed — WakeWordDetector disabled")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# WakeWordDetector
# ═══════════════════════════════════════════════════════════════════════════════

class WakeWordDetector:
    """Continuous wake-word listener that publishes *wake_word_detected* events."""

    def __init__(
        self,
        event_bus: EventBus,
        *,
        model_name: str = "hey_jarvis",
        threshold: float = 0.5,
        verifier_threshold: float = 0.6,
        cooldown_seconds: float = 2.0,
        device_index: Optional[int] = None,
    ) -> None:
        self.event_bus = event_bus
        self.model_name = model_name
        self.threshold = threshold
        self.verifier_threshold = verifier_threshold
        self.cooldown_seconds = cooldown_seconds
        self.device_index = device_index

        self._started = False
        self._running = False
        self._active = False          # True after wake → STT should capture
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cooldown_until = 0.0

        self._total_detections = 0
        self._last_detected: Optional[str] = None

        self._oww_model = None
        self._pa: Optional[Any] = None
        self._stream: Optional[Any] = None

        # ── Custom DEEP model state ─────────────────────────────────────────
        self._use_custom = False
        self._onnx_session = None
        self._verifier = None
        self._feature_dim = 96

        if not PYAUDIO_AVAILABLE:
            logger.warning(
                "WakeWordDetector created but pyaudio missing — "
                "start() will be a no-op"
            )

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started:
            return
        if not PYAUDIO_AVAILABLE:
            logger.warning("WakeWordDetector.start() skipped — pyaudio missing")
            return

        self._loop = asyncio.get_running_loop()

        # ── Custom DEEP model path ──────────────────────────────────────────
        if self.model_name == "deep_custom":
            model_dir = Path("voice/models")
            onnx_path = model_dir / "deep_wake_word.onnx"
            verifier_path = model_dir / "deep_verifier.pkl"

            if onnx_path.exists() and verifier_path.exists():
                if not ONNX_AVAILABLE:
                    logger.error("onnxruntime required for deep_custom model")
                    return
                if not JOBLIB_AVAILABLE:
                    logger.error("joblib required for deep_custom verifier")
                    return
                try:
                    self._onnx_session = ort.InferenceSession(str(onnx_path))
                    self._verifier = joblib.load(verifier_path)
                    self._use_custom = True
                    logger.info(
                        f"Custom wake-word model loaded: deep_custom "
                        f"(threshold={self.threshold}, verifier={self.verifier_threshold})"
                    )
                except Exception as e:
                    logger.error(f"Failed to load custom DEEP model: {e}")
                    self._use_custom = False
            else:
                logger.warning(
                    f"deep_custom model files not found ({onnx_path}, {verifier_path}) — "
                    f"falling back to hey_jarvis"
                )
                self._use_custom = False

        # ── Load openWakeWord model (either primary or fallback) ─────────────
        if not self._use_custom:
            if not OWW_AVAILABLE:
                logger.warning("WakeWordDetector.start() skipped — openwakeword missing")
                return
            try:
                fallback_name = self.model_name if self.model_name != "deep_custom" else "hey_jarvis"
                self._oww_model = Model(wakeword_models=[fallback_name])
                logger.info(
                    f"Wake-word model loaded: '{fallback_name}' "
                    f"(threshold={self.threshold})"
                )
            except Exception as e:
                logger.error(f"Failed to load openWakeWord model '{fallback_name}': {e}")
                return

        # Subscribe to stt_complete to reset _active
        self.event_bus.subscribe("stt_complete", self._on_stt_complete)

        self._running = True
        self._started = True

        # Launch blocking listener in a thread
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("WakeWordDetector started (background thread)")

    async def stop(self) -> None:
        if not self._started:
            return
        self._running = False
        self._started = False

        self.event_bus.unsubscribe("stt_complete", self._on_stt_complete)

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._oww_model = None
        logger.info("WakeWordDetector stopped")

    # ── Listening loop (runs in thread, NOT async) ───────────────────────────

    def _listen_loop(self) -> None:
        """Blocking loop — runs in its own thread."""
        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=1280,  # 80ms @ 16kHz — openWakeWord requirement
            )
        except Exception as e:
            logger.error(f"PyAudio input stream failed: {e}")
            return

        logger.info("Wake-word listener thread active")
        while self._running:
            try:
                audio_chunk = self._stream.read(
                    1280, exception_on_overflow=False,
                )
            except Exception as e:
                logger.warning(f"Stream read error: {e}")
                time.sleep(0.05)
                continue

            pcm = np.frombuffer(audio_chunk, dtype=np.int16)

            if self._use_custom:
                self._process_custom(pcm)
            else:
                prediction = self._oww_model.predict(pcm)
                score = prediction.get(self.model_name, 0.0)
                if score >= self.threshold:
                    now = time.time()
                    if now >= self._cooldown_until:
                        self._cooldown_until = now + self.cooldown_seconds
                        self._on_wake(score)

    # ── Custom two-stage processing ─────────────────────────────────────────

    def _process_custom(self, pcm: np.ndarray) -> None:
        """Two-stage detection: base ONNX → voice verifier."""
        if self._onnx_session is None or not LIBROSA_AVAILABLE:
            return

        # Normalize to float32 [-1, 1]
        audio_f = pcm.astype(np.float32) / 32768.0

        # Pad or trim to 1.5s
        target_len = int(1.5 * 16000)
        if len(audio_f) < target_len:
            audio_f = np.pad(audio_f, (0, target_len - len(audio_f)), mode="constant")
        else:
            audio_f = audio_f[:target_len]

        # Extract features (96-dim mel mean fallback)
        features = self._extract_features(audio_f)
        if features is None:
            return

        # Stage 1: Base ONNX model
        try:
            onnx_out = self._onnx_session.run(None, {"input": features})
            # ONNX logistic regression: output[1] is probabilities [n_samples, 2]
            base_probs = onnx_out[1]
            base_score = float(base_probs[0][1])
        except Exception as exc:
            logger.debug(f"Custom model inference error: {exc}")
            return

        if base_score < self.threshold:
            return

        # Stage 2: Voice verifier (only if stage 1 passes)
        try:
            verifier_probs = self._verifier.predict_proba(features)
            verifier_score = float(verifier_probs[0][1])
        except Exception as exc:
            logger.debug(f"Verifier inference error: {exc}")
            return

        if verifier_score < self.verifier_threshold:
            return

        now = time.time()
        if now >= self._cooldown_until:
            self._cooldown_until = now + self.cooldown_seconds
            self._log_detection(base_score, verifier_score)
            self._on_wake(base_score, verifier_score=verifier_score)

    def _extract_features(self, audio: np.ndarray) -> np.ndarray | None:
        """Extract 96-dim feature vector from audio."""
        if not LIBROSA_AVAILABLE:
            return None
        try:
            mel = librosa.feature.melspectrogram(
                y=audio, sr=16000, n_mels=96, n_fft=512, hop_length=256
            )
            log_mel = librosa.power_to_db(mel, ref=np.max)
            feat = np.mean(log_mel, axis=1).reshape(1, 96).astype(np.float32)
            return feat
        except Exception as exc:
            logger.debug(f"Feature extraction error: {exc}")
            return None

    def _log_detection(self, base_score: float, verifier_score: float) -> None:
        """Log detection scores to pattern_memory for ongoing monitoring."""
        logger.info(
            f"DEEP detected (base={base_score:.3f}, verifier={verifier_score:.3f})"
        )

    # ── Wake handler (called from thread → thread-safe dispatch) ─────────────

    def _on_wake(self, score: float, verifier_score: float | None = None) -> None:
        """Called from the listening thread when wake word is detected."""
        self._total_detections += 1
        self._active = True
        self._last_detected = self._now_iso()
        logger.info(f"Wake word '{self.model_name}' detected (score={score:.3f})")

        if self._loop is None:
            return

        payload: Dict[str, Any] = {
            "timestamp": self._last_detected,
            "score": float(score),
            "model_name": self.model_name,
        }
        if verifier_score is not None:
            payload["verifier_score"] = float(verifier_score)

        asyncio.run_coroutine_threadsafe(
            self.event_bus.publish("wake_word_detected", payload),
            self._loop,
        )

    # ── EventBus subscriber (async, runs on main loop) ────────────────────────

    async def _on_stt_complete(self, event_name: str, payload: dict) -> None:
        """Reset active state once STT has captured the command."""
        if self._active:
            self._active = False
            logger.debug("WakeWordDetector reset after stt_complete")

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "total_detections": self._total_detections,
            "last_detected": self._last_detected,
            "model_name": self.model_name,
            "threshold": self.threshold,
            "started": self._started,
            "model_type": "deep_custom" if self._use_custom else "hey_jarvis",
            "verifier_enabled": self._use_custom,
        }
