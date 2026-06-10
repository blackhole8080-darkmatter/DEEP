"""
voice_web.py

Web-ready voice interface for DEEP - generates audio files for browser playback.
Works with Edge TTS (free) or ElevenLabs (requires paid API key).

Usage in web server:
    from DEEP.core.voice_web import VoiceWeb
    
    voice = VoiceWeb(settings)
    await voice.initialize()
    
    # Generate audio file
    audio_path = await voice.generate_audio("Hello, I am DEEP.")
    
    # Serve via HTTP
    return FileResponse(audio_path, media_type="audio/mp3")
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import aiohttp

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from .elevenlabs_tts import ElevenLabsTTSIntegration
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

try:
    from .event_bus import EventBus
except ImportError:
    from event_bus import EventBus

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Result from audio generation"""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    duration_estimate: float = 0.0  # Estimated duration in seconds


class VoiceWeb:
    """
    Web-ready voice interface that generates audio files.
    Suitable for serving audio via HTTP endpoints.
    """
    
    # Audio cache directory
    CACHE_DIR = "data/audio_cache"
    
    def __init__(self, settings: Settings, event_bus: EventBus = None):
        self.settings = settings
        self._initialized = False
        self._elevenlabs: Optional[ElevenLabsTTSIntegration] = None
        self._cache: Dict[str, str] = {}  # text_hash -> file_path
        self.event_bus = event_bus
        
        # Ensure cache directory exists
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    async def start(self) -> None:
        """Activate voice engine."""
        await self.initialize()
        logger.info("[VoiceWeb] Started")

    async def stop(self) -> None:
        """Deactivate voice engine."""
        await self.cleanup()
        logger.info("[VoiceWeb] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "initialized": self._initialized,
            "cache_files": len(self._cache),
        }
    
    async def initialize(self) -> bool:
        """Initialize voice providers"""
        # Try ElevenLabs if API key available
        if ELEVENLABS_AVAILABLE and self.settings.elevenlabs_api_key:
            try:
                self._elevenlabs = ElevenLabsTTSIntegration({
                    "api_key": self.settings.elevenlabs_api_key,
                    "default_voice": self.settings.elevenlabs_voice,
                    "cache_size": 50
                })
                await self._elevenlabs.initialize()
                logger.info("✓ ElevenLabs initialized for web")
            except Exception as e:
                logger.warning(f"⚠ ElevenLabs failed: {e}, using Edge TTS")
                self._elevenlabs = None
        
        self._initialized = True
        return True
    
    async def generate_audio(
        self,
        text: str,
        voice: Optional[str] = None,
        use_cache: bool = True
    ) -> AudioResult:
        """
        Generate audio file for text.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional)
            use_cache: Use cached audio if available
        
        Returns:
            AudioResult with file path
        """
        if not text or not text.strip():
            if self.event_bus:
                try:
                    await self.event_bus.publish("tts_error", {"text": text or "", "error": "Empty text"})
                except Exception:
                    pass
            return AudioResult(success=False, error="Empty text")
        
        text = text.strip()
        
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text, voice)
            if cache_key in self._cache:
                cached_path = self._cache[cache_key]
                if os.path.exists(cached_path):
                    return AudioResult(
                        success=True,
                        file_path=cached_path,
                        duration_estimate=self._estimate_duration(text)
                    )
        
        # Try ElevenLabs first (highest quality)
        if self._elevenlabs:
            try:
                audio_data = await self._elevenlabs.generate_speech(text, voice)
                file_path = self._save_audio(audio_data, cache_key if use_cache else None)
                
                return AudioResult(
                    success=True,
                    file_path=file_path,
                    duration_estimate=self._estimate_duration(text)
                )
            except Exception as e:
                logger.warning(f"ElevenLabs failed: {e}, falling back to Edge TTS")
        
        # Fallback to Edge TTS (free)
        try:
            file_path = await self._generate_edge_tts(text, voice, cache_key if use_cache else None)
            
            duration_ms = int(self._estimate_duration(text) * 1000)
            if self.event_bus:
                try:
                    await self.event_bus.publish("tts_complete", {
                        "text": text,
                        "duration_ms": duration_ms,
                    })
                except Exception:
                    pass
            return AudioResult(
                success=True,
                file_path=file_path,
                duration_estimate=self._estimate_duration(text)
            )
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            if self.event_bus:
                try:
                    await self.event_bus.publish("tts_error", {"text": text, "error": str(e)})
                except Exception:
                    pass
            return AudioResult(success=False, error=str(e))
    
    async def _generate_edge_tts(
        self,
        text: str,
        voice: Optional[str],
        cache_key: Optional[str]
    ) -> str:
        """Generate audio using Edge TTS"""
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts not installed")
        
        voice_id = voice or self.settings.edge_tts_voice
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=self.settings.edge_tts_rate,
            volume="+0%"
        )
        
        # Generate audio
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        return self._save_audio(bytes(audio_data), cache_key)
    
    def _save_audio(self, audio_data: bytes, cache_key: Optional[str]) -> str:
        """Save audio data to file"""
        if cache_key:
            file_path = os.path.join(self.CACHE_DIR, f"{cache_key}.mp3")
        else:
            fd, file_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
        
        with open(file_path, "wb") as f:
            f.write(audio_data)
        
        if cache_key:
            self._cache[cache_key] = file_path
        
        return file_path
    
    def _get_cache_key(self, text: str, voice: Optional[str]) -> str:
        """Generate cache key for text + voice"""
        import hashlib
        voice_id = voice or self.settings.edge_tts_voice
        content = f"{voice_id}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _estimate_duration(self, text: str) -> float:
        """Estimate audio duration based on word count"""
        # Average speaking rate: ~150 words per minute = 2.5 words per second
        word_count = len(text.split())
        return word_count / 2.5
    
    async def generate_greeting(self) -> AudioResult:
        """Generate greeting audio with personality"""
        if self.personality:
            text = self.personality.get_wake_response()
        else:
            text = "Hello, I am DEEP."
        
        return await self.generate_audio(text)
    
    async def generate_confirmation(self) -> AudioResult:
        """Generate confirmation audio"""
        if self.personality:
            text = self.personality.get_confirmation()
        else:
            text = "Done."
        
        return await self.generate_audio(text)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(Path(self.CACHE_DIR).glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cached_files": len(cache_files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_directory": self.CACHE_DIR
        }
    
    def clear_cache(self) -> int:
        """Clear audio cache, return number of files removed"""
        cache_files = list(Path(self.CACHE_DIR).glob("*.mp3"))
        removed = 0
        
        for f in cache_files:
            try:
                f.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove {f}: {e}")
        
        self._cache.clear()
        return removed
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        if self._elevenlabs:
            await self._elevenlabs.cleanup()


# FastAPI endpoint example
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()
voice_web: Optional[VoiceWeb] = None

@app.on_event("startup")
async def startup():
    global voice_web
    from DEEP.core.config import Settings
    settings = Settings()
    voice_web = VoiceWeb(settings)
    await voice_web.initialize()

@app.get("/voice/speak")
async def speak(text: str):
    result = await voice_web.generate_audio(text)
    if result.success:
        return FileResponse(result.file_path, media_type="audio/mp3")
    return {"error": result.error}

@app.get("/voice/greet")
async def greet():
    result = await voice_web.generate_greeting()
    if result.success:
        return FileResponse(result.file_path, media_type="audio/mp3")
    return {"error": result.error}
"""
