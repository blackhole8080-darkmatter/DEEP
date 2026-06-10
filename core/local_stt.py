"""
Local STT Module - Offline Whisper Transcription
"""
import whisper
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus


class LocalSTT:
    def __init__(self, model_name="base", event_bus: EventBus = None):
        self.model_name = model_name
        self.model = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.event_bus = event_bus

    def _load_model(self):
        if self.model is None:
            print(f"\n[STT] Loading Whisper offline model '{self.model_name}' (this may take a moment on first run)...")
            self.model = whisper.load_model(self.model_name)
            print("[STT] Offline Whisper model loaded successfully.")

    def _transcribe(self, audio_path: str) -> str:
        self._load_model()
        result = self.model.transcribe(audio_path)
        return result["text"]

    async def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe an audio file to text asynchronously using local Whisper model."""
        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(self.executor, self._transcribe, audio_path)

        if self.event_bus:
            try:
                await self.event_bus.publish("user_command", {
                    "text": transcript.strip(),
                    "source": "microphone",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.85,  # Whisper 'base' approximate
                })
            except Exception as e:
                print(f"[STT] EventBus publish error: {e}")

        return transcript