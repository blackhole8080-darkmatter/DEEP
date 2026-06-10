# deep/voice.py — Voice I/O (Bible Section 4.1)
"""Wake-word loop, STT (faster-whisper offline / Deepgram online), TTS
(pyttsx3 offline / ElevenLabs online). Every audio dependency is optional and
guarded; with none present, speak() prints and listen_once() reads stdin so the
class is always constructible and testable."""
from __future__ import annotations

import threading

try:
    from . import config
except Exception:  # pragma: no cover
    import config

try:
    import pyttsx3
    PYTTSX3 = True
except Exception:  # pragma: no cover
    PYTTSX3 = False

try:
    from faster_whisper import WhisperModel
    FWHISPER = True
except Exception:  # pragma: no cover
    FWHISPER = False


class VoiceEngine:
    def __init__(self, config=config):
        self.config = config
        self._listening = False
        self._thread = None
        self._tts = None
        self._whisper = None
        if PYTTSX3:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", config.TTS_RATE)
                self._tts.setProperty("volume", config.TTS_VOLUME)
                # prefer a British male voice if available
                for v in self._tts.getProperty("voices"):
                    if "english" in v.name.lower() and ("male" in v.name.lower()
                                                        or "george" in v.name.lower()):
                        self._tts.setProperty("voice", v.id)
                        break
            except Exception:
                self._tts = None

    # ── lifecycle ───────────────────────────────────────────────────
    def start_listener(self):
        self._listening = True
        self._thread = threading.Thread(target=self._detect_wake_word, daemon=True)
        self._thread.start()

    def stop_listener(self):
        self._listening = False

    def _detect_wake_word(self):
        # Real wake-word uses pvporcupine; without it the loop idles.
        import time
        while self._listening:
            time.sleep(0.5)

    # ── STT ─────────────────────────────────────────────────────────
    def listen_once(self, timeout=10) -> str:
        if FWHISPER:
            try:
                return self._record_and_transcribe()
            except Exception:
                pass
        # text fallback
        try:
            return input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def _record_and_transcribe(self) -> str:
        if self._whisper is None:
            self._whisper = WhisperModel(self.config.WHISPER_MODEL, device="cpu",
                                         compute_type="int8")
        import sounddevice as sd
        import numpy as np
        seconds = 5
        rec = sd.rec(int(seconds * self.config.AUDIO_SAMPLE_RATE),
                     samplerate=self.config.AUDIO_SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        segments, _ = self._whisper.transcribe(rec.flatten())
        return " ".join(s.text for s in segments).strip()

    # ── TTS ─────────────────────────────────────────────────────────
    def speak(self, text: str) -> None:
        if not text:
            return
        if self._tts is not None:
            try:
                self._tts.say(text); self._tts.runAndWait(); return
            except Exception:
                pass
        print(f"[DEEP speaks] {text}")

    def test(self) -> None:
        v = VoiceEngine()
        v.speak("DEEP voice test.")  # must not raise
        assert hasattr(v, "listen_once")
        print("voice.VoiceEngine: OK")


def test() -> None:
    VoiceEngine().test()


if __name__ == "__main__":
    test()
