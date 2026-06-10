"""
voice — Voice Hardware Layer for DEEP.

Components:
    WakeWordDetector   — Continuous wake-word listener (openWakeWord)
    STTEngine          — Speech-to-text (OpenAI Whisper, local)
    TTSEngine          — Neural text-to-speech (Piper, offline)
    audio_utils        — Shared audio utilities

Usage:
    from voice import WakeWordDetector, STTEngine, TTSEngine
    from voice import audio_utils
"""

from __future__ import annotations

from voice.audio_utils import (
    download_file,
    get_input_device_index,
    get_output_device_index,
    list_audio_devices,
    play_startup_sound,
    strip_for_speech,
    test_microphone,
)
from voice.stt_engine import STTEngine
from voice.tts_engine import TTSEngine
from voice.wake_word import WakeWordDetector
from voice.bluetooth_audio import BluetoothAudioManager
from voice.whisper_ear import WhisperEar
from voice.spatial_audio import SpatialAudio

__all__ = [
    "WakeWordDetector",
    "STTEngine",
    "TTSEngine",
    "audio_utils",
    "BluetoothAudioManager",
    "WhisperEar",
    "SpatialAudio",
    "list_audio_devices",
    "get_input_device_index",
    "get_output_device_index",
    "test_microphone",
    "play_startup_sound",
    "strip_for_speech",
    "download_file",
]
