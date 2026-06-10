"""
tests/test_bluetooth_audio.py

Validation suite for Bluetooth private ear, WhisperEar, and SpatialAudio.

Run:
    python tests/test_bluetooth_audio.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

from core.event_bus import EventBus
from voice.bluetooth_audio import BluetoothAudioManager, BTAudioDevice
from voice.whisper_ear import WhisperEar
from voice.spatial_audio import SpatialAudio


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: BluetoothAudioManager starts without BT hardware (graceful degradation)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_bt_audio_starts_without_bleak():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    mgr = BluetoothAudioManager(event_bus=bus, redis_state=redis)
    with patch("voice.bluetooth_audio.BLEAK_AVAILABLE", False):
        await mgr.start()

    status = mgr.status()
    assert status["bt_active"] is False
    assert status["preferred_configured"] is False

    await mgr.stop()
    await bus.stop()
    print("  ✓ BluetoothAudioManager starts gracefully without bleak")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: _activate_bt_routing publishes "bt_audio_activated" event
# ═══════════════════════════════════════════════════════════════════════════════

async def test_activate_bt_routing_publishes_event():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("bt_audio_activated", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    mgr = BluetoothAudioManager(event_bus=bus, redis_state=redis)
    mgr._bt_active = False
    device = BTAudioDevice(mac="AA:BB:CC:DD:EE:FF", name="TestBuds")

    with patch("voice.bluetooth_audio.sys.platform", "linux"):
        with patch("voice.bluetooth_audio.subprocess.run"):
            await mgr._activate_bt_routing(device)

    await asyncio.sleep(0.05)
    assert len(captured) == 1
    assert captured[0]["event"] == "bt_audio_activated"
    assert captured[0]["payload"]["device_name"] == "TestBuds"

    await mgr.stop()
    await bus.stop()
    print("  ✓ _activate_bt_routing publishes bt_audio_activated event")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: _deactivate_bt_routing publishes "bt_audio_deactivated" event
# ═══════════════════════════════════════════════════════════════════════════════

async def test_deactivate_bt_routing_publishes_event():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("bt_audio_deactivated", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    mgr = BluetoothAudioManager(event_bus=bus, redis_state=redis)
    mgr._bt_active = True

    with patch("voice.bluetooth_audio.sys.platform", "linux"):
        with patch("voice.bluetooth_audio.subprocess.run"):
            await mgr._deactivate_bt_routing()

    await asyncio.sleep(0.05)
    assert len(captured) == 1
    assert captured[0]["event"] == "bt_audio_deactivated"
    assert mgr._bt_active is False

    await bus.stop()
    print("  ✓ _deactivate_bt_routing publishes bt_audio_deactivated event")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: set_volume clamps to 0-100 range
# ═══════════════════════════════════════════════════════════════════════════════

async def test_set_volume_clamps():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    mgr = BluetoothAudioManager(event_bus=bus, redis_state=redis)
    mgr._bt_active = True
    mgr._active_device = BTAudioDevice(mac="AA:BB:CC:DD:EE:FF", name="Test")

    await mgr.set_volume(150)
    assert mgr._volume == 100

    await mgr.set_volume(-20)
    assert mgr._volume == 0

    await mgr.set_volume(42)
    assert mgr._volume == 42

    await bus.stop()
    print("  ✓ set_volume clamps to 0-100 range")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: WhisperEar activates on "bt_audio_activated" and publishes "whisper_ear_active"
# ═══════════════════════════════════════════════════════════════════════════════

async def test_whisper_ear_activates():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("whisper_ear_active", capture)

    bt_audio = MagicMock()
    ear = WhisperEar(event_bus=bus, bt_audio=bt_audio)
    await ear.start()

    with patch("voice.whisper_ear.PYAUDIO_AVAILABLE", True):
        with patch("voice.whisper_ear.pyaudio.PyAudio") as mock_pa:
            mock_inst = MagicMock()
            mock_inst.get_device_count.return_value = 1
            mock_inst.get_device_info_by_index.return_value = {
                "name": "TestBuds Hands-Free AG Audio",
                "maxInputChannels": 2,
            }
            mock_pa.return_value = mock_inst
            await ear._on_bt_activated("", {"device_name": "TestBuds"})

    await asyncio.sleep(0.05)
    assert len(captured) == 1
    assert captured[0]["event"] == "whisper_ear_active"
    assert captured[0]["payload"]["device"] == "TestBuds"

    await ear.stop()
    await bus.stop()
    print("  ✓ WhisperEar activates on bt_audio_activated")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: WhisperEar deactivates on "bt_audio_deactivated" and publishes "whisper_ear_inactive"
# ═══════════════════════════════════════════════════════════════════════════════

async def test_whisper_ear_deactivates():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("whisper_ear_inactive", capture)

    bt_audio = MagicMock()
    ear = WhisperEar(event_bus=bus, bt_audio=bt_audio)
    await ear.start()
    ear._active = True
    ear._bt_mic_device = "TestBuds"

    await ear._on_bt_deactivated("", {})
    await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["event"] == "whisper_ear_inactive"
    assert ear._active is False

    await ear.stop()
    await bus.stop()
    print("  ✓ WhisperEar deactivates on bt_audio_deactivated")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: SpatialAudio.pan_audio returns stereo array (shape: [n, 2]) from mono input
# ═══════════════════════════════════════════════════════════════════════════════

def test_spatial_pan_stereo():
    spatial = SpatialAudio(event_bus=MagicMock())
    spatial._enabled = True
    mono = np.ones(1000, dtype=np.float32)
    stereo = spatial.pan_audio(mono, 0.0)
    assert stereo.shape == (1000, 2)
    print("  ✓ SpatialAudio.pan_audio returns stereo array from mono input")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Pan position CENTER returns equal L/R gain
# ═══════════════════════════════════════════════════════════════════════════════

def test_spatial_pan_center():
    spatial = SpatialAudio(event_bus=MagicMock())
    spatial._enabled = True
    mono = np.ones(1000, dtype=np.float32)
    stereo = spatial.pan_audio(mono, 0.0)
    np.testing.assert_array_almost_equal(stereo[:, 0], stereo[:, 1])
    print("  ✓ Pan CENTER returns equal L/R gain")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Pan position LEFT returns higher L than R gain
# ═══════════════════════════════════════════════════════════════════════════════

def test_spatial_pan_left():
    spatial = SpatialAudio(event_bus=MagicMock())
    spatial._enabled = True
    mono = np.ones(1000, dtype=np.float32)
    stereo = spatial.pan_audio(mono, -1.0)
    assert np.mean(stereo[:, 0]) > np.mean(stereo[:, 1])
    print("  ✓ Pan LEFT returns higher L than R gain")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: status() returns valid dict when no BT active
# ═══════════════════════════════════════════════════════════════════════════════

async def test_bt_audio_status_empty():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    mgr = BluetoothAudioManager(event_bus=bus, redis_state=redis)
    status = mgr.status()
    assert status["bt_active"] is False
    assert status["active_device"] is None
    assert "volume_percent" in status

    await bus.stop()
    print("  ✓ status() returns valid dict when no BT active")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Bluetooth Private Ear & Spatial Audio validation...\n")

    await test_bt_audio_starts_without_bleak()
    await test_activate_bt_routing_publishes_event()
    await test_deactivate_bt_routing_publishes_event()
    await test_set_volume_clamps()
    await test_whisper_ear_activates()
    await test_whisper_ear_deactivates()
    test_spatial_pan_stereo()
    test_spatial_pan_center()
    test_spatial_pan_left()
    await test_bt_audio_status_empty()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All Bluetooth Private Ear & Spatial Audio tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
