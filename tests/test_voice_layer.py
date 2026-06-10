"""
tests/test_voice_layer.py

Validation suite for the Voice Hardware Layer.

Run:
    python tests/test_voice_layer.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

from core.event_bus import EventBus
from voice.audio_utils import list_audio_devices, strip_for_speech, test_microphone
from voice.wake_word import WakeWordDetector
from voice.stt_engine import STTEngine
import numpy as np
from voice.tts_engine import TTSEngine, _QueueItem


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: strip_for_speech removes markdown, URLs, emoji, expands abbreviations
# ═══════════════════════════════════════════════════════════════════════════════

def test_strip_for_speech():
    text = (
        "**Hello** world! Check out https://example.com "
        "and `code`. e.g. this is an example. "
        "Also 😀 emoji here. vs. others."
    )
    cleaned = strip_for_speech(text)
    assert "**" not in cleaned
    assert "https" not in cleaned
    assert "`" not in cleaned
    assert "😀" not in cleaned
    assert "for example" in cleaned.lower()  # e.g. expanded
    assert "versus" in cleaned.lower()        # vs. expanded
    print("  ✓ strip_for_speech removes markdown, URLs, emoji, expands abbreviations")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: list_audio_devices returns a list (may be empty if PyAudio missing)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_audio_devices():
    devices = list_audio_devices()
    assert isinstance(devices, list), "list_audio_devices() should return a list"
    for dev in devices:
        assert "index" in dev
        assert "name" in dev
        assert "max_input_channels" in dev
        assert "max_output_channels" in dev
    print(f"  ✓ list_audio_devices returned {len(devices)} device(s)")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: test_microphone returns a float (may be 0.0 if PyAudio missing)
# ═══════════════════════════════════════════════════════════════════════════════

def test_microphone_health_check():
    rms = test_microphone(duration_s=0.3)
    assert isinstance(rms, float), "test_microphone should return a float"
    assert rms >= 0.0, "RMS should be non-negative"
    print(f"  ✓ test_microphone returned RMS={rms:.1f}")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: WakeWordDetector initialises and publishes correct event on mock wake
# ═══════════════════════════════════════════════════════════════════════════════

async def test_wake_word_detector_publishes_event():
    bus = EventBus()
    await bus.start()

    detector = WakeWordDetector(
        event_bus=bus,
        model_name="hey_jarvis",
        threshold=0.5,
    )

    # _on_wake is normally called from thread — call directly for test
    detector._loop = asyncio.get_running_loop()
    detector._on_wake(score=0.85)

    # Allow event to propagate
    await asyncio.sleep(0.1)

    history = bus.get_history()
    wake_events = [e for e in history if e["event"] == "wake_word_detected"]
    assert len(wake_events) == 1, f"Expected 1 wake_word_detected event, got {len(wake_events)}"
    payload = wake_events[0]["payload"]
    assert payload["score"] == 0.85
    assert payload["model_name"] == "hey_jarvis"
    assert "timestamp" in payload

    await bus.stop()
    print("  ✓ WakeWordDetector publishes wake_word_detected with correct payload")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: STTEngine initialises and subscribes to wake_word_detected
# ═══════════════════════════════════════════════════════════════════════════════

async def test_stt_engine_subscribes_and_responds():
    bus = EventBus()
    await bus.start()

    stt = STTEngine(
        event_bus=bus,
        model_name="tiny",  # smallest model for fast test
        silence_threshold=300,
        silence_duration_ms=500,
        max_command_duration_s=3.0,
    )

    # Mock the model so we don't actually load Whisper
    stt._model = MagicMock()
    stt._model.transcribe = MagicMock(return_value={
        "text": "hello world",
        "segments": [{"no_speech_prob": 0.02}],
    })
    stt._started = True  # mark as started manually

    # Subscribe manually (bypassing actual start() which loads the model)
    bus.subscribe("wake_word_detected", stt._on_wake)

    # Simulate wake word event → triggers _capture_and_transcribe
    # But _capture_and_transcribe calls _record_command which needs PyAudio
    # So we mock _record_command directly
    stt._record_command = AsyncMock(return_value=None)  # simulate no audio

    await bus.publish("wake_word_detected", {"score": 0.9})
    await asyncio.sleep(0.2)

    # With no audio, should publish stt_failed
    history = bus.get_history()
    failed_events = [e for e in history if e["event"] == "stt_failed"]
    assert len(failed_events) >= 1, f"Expected at least 1 stt_failed, got {len(failed_events)}"

    # Now test with mock audio returning data
    stt._record_command = AsyncMock(
        return_value=__import__("numpy").zeros(16000, dtype=__import__("numpy").float32)
    )
    await bus.publish("wake_word_detected", {"score": 0.9})
    await asyncio.sleep(0.3)

    history2 = bus.get_history()
    user_commands = [e for e in history2 if e["event"] == "user_command"]
    assert len(user_commands) >= 1, f"Expected at least 1 user_command, got {len(user_commands)}"
    assert user_commands[-1]["payload"]["text"] == "hello world"

    await bus.stop()
    print("  ✓ STTEngine transcribes and publishes user_command on wake word")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: TTSEngine.speak() on empty string does not crash
# ═══════════════════════════════════════════════════════════════════════════════

async def test_tts_empty_string():
    bus = EventBus()
    await bus.start()

    tts = TTSEngine(event_bus=bus, model_path="/tmp/fake_model.onnx")
    tts._started = True
    tts._voice = None  # force no voice — should skip gracefully

    # Should not raise
    await tts.speak("", priority="normal")
    await tts.speak("   ", priority="urgent")
    await tts.speak("**bold** only markdown", priority="normal")

    # Process queue manually
    item = await asyncio.wait_for(tts._queue.get(), timeout=0.5)
    # Should not crash when processing
    await tts._speak_one(item)

    await bus.stop()
    print("  ✓ TTSEngine handles empty / markdown-only text gracefully")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Priority queue — urgent item processes before normal items
# ═══════════════════════════════════════════════════════════════════════════════

async def test_tts_priority_queue():
    bus = EventBus()
    await bus.start()

    tts = TTSEngine(event_bus=bus, model_path="/tmp/fake_model.onnx")
    tts._started = True
    tts._voice = None  # no real voice

    # Queue 3 items: normal, normal, urgent (inserted after)
    await tts.speak("first normal", priority="normal")
    await tts.speak("second normal", priority="normal")
    await tts.speak("urgent alert", priority="urgent")

    # Pull from queue and verify order
    items = []
    for _ in range(3):
        item = await asyncio.wait_for(tts._queue.get(), timeout=0.5)
        items.append(item)

    # PriorityQueue orders by (priority_val, seq) — urgent=0, normal=1
    assert items[0].text == "urgent alert", f"First should be urgent, got: {items[0].text}"
    assert items[0].priority_val == 0
    assert items[1].text == "first normal", f"Second should be first normal, got: {items[1].text}"
    assert items[2].text == "second normal", f"Third should be second normal, got: {items[2].text}"

    await bus.stop()
    print("  ✓ Priority queue: urgent item processed before normal items")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: WakeWordDetector status reflects detections
# ═══════════════════════════════════════════════════════════════════════════════

async def test_wake_word_status():
    detector = WakeWordDetector(
        event_bus=MagicMock(),
        model_name="hey_jarvis",
        threshold=0.5,
    )

    status = detector.status()
    assert status["active"] is False
    assert status["total_detections"] == 0
    assert status["model_name"] == "hey_jarvis"
    assert status["threshold"] == 0.5

    detector._active = True
    detector._total_detections = 3
    detector._last_detected = "2024-01-01T00:00:00+00:00"

    status = detector.status()
    assert status["active"] is True
    assert status["total_detections"] == 3
    assert status["last_detected"] == "2024-01-01T00:00:00+00:00"
    print("  ✓ WakeWordDetector status() reflects state correctly")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Overlapped synthesis — 2 sentences produce 2 synthesis + 2 playback calls
# ═══════════════════════════════════════════════════════════════════════════════

async def test_tts_overlapped_synthesis():
    bus = EventBus()
    await bus.start()

    tts = TTSEngine(event_bus=bus, model_path="/tmp/fake_model.onnx")
    tts._started = True
    tts._voice = MagicMock()  # pretend Piper is loaded

    synthesised: list[str] = []
    played: list[int] = []

    async def mock_synthesise(text: str):
        synthesised.append(text)
        return np.zeros(1000, dtype=np.float32)

    async def mock_play(audio):
        played.append(len(audio))

    tts._synthesise = mock_synthesise
    tts._play = mock_play

    item = _QueueItem(priority_val=1, seq=1, text="Hello world. This is a test.")
    await tts._speak_one(item)

    assert len(synthesised) == 2, f"Expected 2 synthesis calls, got {len(synthesised)}"
    assert "Hello world" in synthesised[0]
    assert "This is a test" in synthesised[1]

    assert len(played) == 2, f"Expected 2 playback calls, got {len(played)}"

    await bus.stop()
    print("  ✓ TTSEngine overlaps synthesis and playback for multi-sentence text")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Voice Layer validation...\n")
    test_strip_for_speech()
    test_list_audio_devices()
    test_microphone_health_check()
    await test_wake_word_detector_publishes_event()
    await test_stt_engine_subscribes_and_responds()
    await test_tts_empty_string()
    await test_tts_priority_queue()
    await test_wake_word_status()
    await test_tts_overlapped_synthesis()
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All voice layer tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
