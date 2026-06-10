"""
voice/audio_utils.py

Shared audio utilities used by all voice components in DEEP.
Works on Windows (dev) and Raspberry Pi (production).
"""

from __future__ import annotations

import logging
import re
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger("voice.audio_utils")

# ── Optional imports ─────────────────────────────────────────────────────

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not installed — audio output disabled")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not installed — audio capture disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# Device enumeration & selection
# ═══════════════════════════════════════════════════════════════════════════════

def list_audio_devices() -> List[dict]:
    """Return a list of all audio devices with their capabilities."""
    devices = []
    if not PYAUDIO_AVAILABLE:
        logger.warning("list_audio_devices(): PyAudio unavailable")
        return devices

    pa = pyaudio.PyAudio()
    try:
        count = pa.get_device_count()
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            devices.append({
                "index": i,
                "name": info.get("name", ""),
                "max_input_channels": info.get("maxInputChannels", 0),
                "max_output_channels": info.get("maxOutputChannels", 0),
                "default_sample_rate": info.get("defaultSampleRate", 0),
                "is_default_input": info.get("index") == pa.get_default_input_device_info().get("index"),
                "is_default_output": info.get("index") == pa.get_default_output_device_info().get("index"),
            })
    finally:
        pa.terminate()
    return devices


def get_input_device_index(name_fragment: str) -> Optional[int]:
    """Find an input device whose name contains *name_fragment* (case-insensitive)."""
    if not PYAUDIO_AVAILABLE:
        return None

    pa = pyaudio.PyAudio()
    try:
        count = pa.get_device_count()
        fragment_lower = name_fragment.lower()
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                if fragment_lower in info.get("name", "").lower():
                    logger.info(f"Found input device '{info['name']}' at index {i}")
                    return i
        logger.warning(f"No input device matching '{name_fragment}' found")
        return None
    finally:
        pa.terminate()


def get_output_device_index(name_fragment: str) -> Optional[int]:
    """Find an output device whose name contains *name_fragment* (case-insensitive)."""
    if not PYAUDIO_AVAILABLE:
        return None

    pa = pyaudio.PyAudio()
    try:
        count = pa.get_device_count()
        fragment_lower = name_fragment.lower()
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if info.get("maxOutputChannels", 0) > 0:
                if fragment_lower in info.get("name", "").lower():
                    logger.info(f"Found output device '{info['name']}' at index {i}")
                    return i
        logger.warning(f"No output device matching '{name_fragment}' found")
        return None
    finally:
        pa.terminate()


# ═══════════════════════════════════════════════════════════════════════════════
# Microphone health check
# ═══════════════════════════════════════════════════════════════════════════════

def test_microphone(device_index: Optional[int] = None, duration_s: float = 1.0) -> float:
    """Record *duration_s* seconds and return the RMS energy level."""
    if not PYAUDIO_AVAILABLE:
        logger.warning("test_microphone(): PyAudio unavailable")
        return 0.0

    RATE = 16000
    CHUNK = 1024
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK,
        )
        frames = []
        chunks = int(RATE / CHUNK * duration_s)
        for _ in range(chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.int16))
        stream.stop_stream()
        stream.close()

        audio = np.concatenate(frames)
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        logger.info(f"Microphone test: RMS={rms:.1f} over {duration_s}s")
        return float(rms)
    except Exception as e:
        logger.warning(f"Microphone test failed: {e}")
        return 0.0
    finally:
        pa.terminate()


# ═══════════════════════════════════════════════════════════════════════════════
# Startup sound (programmatic)
# ═══════════════════════════════════════════════════════════════════════════════

async def play_startup_sound() -> None:
    """Play a short DEEP boot tone — 440Hz → 660Hz → 880Hz."""
    if not SOUNDDEVICE_AVAILABLE:
        logger.warning("play_startup_sound(): sounddevice unavailable")
        return

    sr = 22050

    def _tone(freq: float, duration: float, volume: float = 0.3) -> np.ndarray:
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        return (np.sin(2 * np.pi * freq * t) * volume).astype(np.float32)

    # 440Hz (0.1s) → 660Hz (0.1s) → 880Hz (0.15s)
    audio = np.concatenate([
        _tone(440.0, 0.10),
        np.zeros(int(sr * 0.02)),  # 20ms gap
        _tone(660.0, 0.10),
        np.zeros(int(sr * 0.02)),
        _tone(880.0, 0.15),
    ])

    sd.play(audio, samplerate=sr)
    sd.wait()
    logger.info("Startup sound played")


# ═══════════════════════════════════════════════════════════════════════════════
# Text sanitisation for speech
# ═══════════════════════════════════════════════════════════════════════════════

_MARKDOWN_RE = re.compile(
    r"\*\*(.*?)\*\*"       # bold
    r"|__(.*?)__"           # underline
    r"|`([^`]+)`"           # inline code
    r"|^\s*[-*]\s+"        # bullet
    r"|\#+\s+"             # heading (escaped # for VERBOSE mode)
    r"|https?://\S+"       # URLs
, re.MULTILINE | re.VERBOSE)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE,
)

_ABBREVIATIONS = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "and so on",
    "et al.": "and colleagues",
    "vs.": "versus",
    "w.r.t.": "with respect to",
    "approx.": "approximately",
    "Dr.": "Doctor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Prof.": "Professor",
}


def strip_for_speech(text: str) -> str:
    """Remove markdown, URLs, emoji, and expand abbreviations for TTS."""
    # Remove markdown / URLs
    text = _MARKDOWN_RE.sub("", text)
    # Remove emoji
    text = _EMOJI_RE.sub("", text)
    # Expand abbreviations
    for abbr, full in _ABBREVIATIONS.items():
        text = re.sub(re.escape(abbr), full, text, flags=re.IGNORECASE)
    # Collapse multiple spaces / newlines
    text = " ".join(text.split())
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# Model download helper
# ═══════════════════════════════════════════════════════════════════════════════

def download_file(url: str, dest: Path, chunk_size: int = 8192) -> bool:
    """Download *url* → *dest*, creating parent dirs as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            if resp.status != 200:
                logger.error(f"Download failed: {url} → status {resp.status}")
                return False
            total = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
        logger.info(f"Downloaded {dest.name} ({total:,} bytes)")
        return True
    except Exception as e:
        logger.error(f"Download failed: {url} → {e}")
        return False
