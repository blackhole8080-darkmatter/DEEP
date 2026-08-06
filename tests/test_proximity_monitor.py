"""
tests/test_proximity_monitor.py

Validation suite for the Passive Proximity Monitor.

Run:
    python tests/test_proximity_monitor.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

from core.event_bus import EventBus
from network.proximity_monitor import (
    ProximityMonitor,
    WiFiProximitySensor,
    BluetoothProximitySensor,
    ProximityAP,
    ProximityBTDevice,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: ProximityMonitor starts gracefully when WiFi interface unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def test_starts_gracefully_no_wifi():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    monitor = ProximityMonitor(event_bus=bus, redis_state=redis)
    await monitor.start()
    status = monitor.status()
    assert status["wifi_scanning"] is True  # started even if no interface
    await monitor.stop()
    await bus.stop()
    print("  ✓ ProximityMonitor starts gracefully when WiFi unavailable")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: ProximityAP dataclass instantiates correctly
# ═══════════════════════════════════════════════════════════════════════════════

async def test_proximity_ap_dataclass():
    ap = ProximityAP(
        ssid="TestNet",
        bssid="AA:BB:CC:DD:EE:FF",
        signal_dbm=-55,
        channel=6,
        encryption="WPA2",
        first_seen="2024-01-01T00:00:00+00:00",
        last_seen="2024-01-01T00:00:00+00:00",
        seen_count=1,
        is_yours=False,
    )
    assert ap.ssid == "TestNet"
    assert ap.signal_dbm == -55
    assert ap.encryption == "WPA2"
    print("  ✓ ProximityAP dataclass instantiates correctly")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: _analyse_wifi fires "open_network_nearby" for OPEN encryption AP above threshold
# ═══════════════════════════════════════════════════════════════════════════════

async def test_analyse_wifi_fires_open_network():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("open_network_nearby", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    sensor = WiFiProximitySensor(event_bus=bus, redis_state=redis)
    sensor._signal_threshold = -80

    aps = [
        ProximityAP(ssid="FreeWiFi", bssid="11:22:33:44:55:66", signal_dbm=-50, encryption="OPEN", is_yours=False),
        ProximityAP(ssid="SecureNet", bssid="AA:BB:CC:DD:EE:FF", signal_dbm=-50, encryption="WPA2", is_yours=False),
    ]
    await sensor.analyse(aps)
    await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["event"] == "open_network_nearby"
    assert captured[0]["payload"]["ssid"] == "FreeWiFi"

    await bus.stop()
    print("  ✓ _analyse_wifi fires open_network_nearby for OPEN AP")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: _analyse_wifi does NOT fire for your own AP (is_yours = True)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_analyse_wifi_skips_own_ap():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("open_network_nearby", capture)
    bus.subscribe("persistent_unknown_ap", capture)
    bus.subscribe("strong_new_ap_detected", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    sensor = WiFiProximitySensor(event_bus=bus, redis_state=redis)
    sensor._signal_threshold = -80
    sensor._home_bssid = "AA:BB:CC:DD:EE:FF"

    aps = [
        ProximityAP(ssid="MyHome", bssid="AA:BB:CC:DD:EE:FF", signal_dbm=-30, encryption="WPA2", is_yours=True),
    ]
    await sensor.analyse(aps)
    await asyncio.sleep(0.05)

    assert len(captured) == 0

    await bus.stop()
    print("  ✓ _analyse_wifi does NOT fire for your own AP")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: _analyse_bluetooth fires "unknown_bt_device_nearby" for close unknown device
# ═══════════════════════════════════════════════════════════════════════════════

async def test_analyse_bt_fires_unknown_device():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("unknown_bt_device_nearby", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    sensor = BluetoothProximitySensor(event_bus=bus, redis_state=redis)
    sensor._close_threshold = -60

    devices = [
        ProximityBTDevice(mac="11:22:33:44:55:66", name="UnknownPhone", rssi=-40, is_yours=False),
        ProximityBTDevice(mac="AA:BB:CC:DD:EE:FF", name="Aryan-Watch", rssi=-40, is_yours=True),
    ]
    await sensor.analyse(devices)
    await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["event"] == "unknown_bt_device_nearby"
    assert captured[0]["payload"]["name"] == "UnknownPhone"

    await bus.stop()
    print("  ✓ _analyse_bluetooth fires unknown_bt_device_nearby for close unknown device")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: _analyse_bluetooth does NOT fire for KNOWN_BT_DEVICES
# ═══════════════════════════════════════════════════════════════════════════════

async def test_analyse_bt_skips_known_device():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("unknown_bt_device_nearby", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    sensor = BluetoothProximitySensor(event_bus=bus, redis_state=redis)
    sensor._close_threshold = -60
    sensor._known_bt = {"AA:BB:CC:DD:EE:FF"}

    devices = [
        ProximityBTDevice(mac="AA:BB:CC:DD:EE:FF", name="Aryan-Watch", rssi=-40, is_yours=True),
    ]
    await sensor.analyse(devices)
    await asyncio.sleep(0.05)

    assert len(captured) == 0

    await bus.stop()
    print("  ✓ _analyse_bluetooth does NOT fire for KNOWN_BT_DEVICES")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: _detect_patterns fires "recurring_unknown_device" after 3+ days
# ═══════════════════════════════════════════════════════════════════════════════

async def test_detect_patterns_recurring():
    bus = EventBus()
    await bus.start()

    captured = []
    async def capture(event_name, payload):
        captured.append({"event": event_name, "payload": payload})
    bus.subscribe("recurring_unknown_device", capture)

    redis = MagicMock()
    redis.set_global = AsyncMock()

    monitor = ProximityMonitor(event_bus=bus, redis_state=redis)
    # Simulate 3 days of sightings
    for day in ["2024-01-01", "2024-01-02", "2024-01-03"]:
        monitor._proximity_log.append({
            "timestamp": f"{day}T12:00:00+00:00",
            "mac_or_bssid": "11:22:33:44:55:66",
            "device_type": "wifi",
            "signal": -60,
            "seen_count": 1,
        })

    await monitor._detect_patterns()
    await asyncio.sleep(0.05)

    assert len(captured) == 1
    assert captured[0]["payload"]["days_seen"] == 3

    await bus.stop()
    print("  ✓ _detect_patterns fires recurring_unknown_device after 3+ days")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: get_proximity_summary() returns valid dict when no scan data available yet
# ═══════════════════════════════════════════════════════════════════════════════

async def test_proximity_summary_empty():
    bus = EventBus()
    await bus.start()

    redis = MagicMock()
    redis.set_global = AsyncMock()

    monitor = ProximityMonitor(event_bus=bus, redis_state=redis)
    # Isolate from the durable store: sensors seed history from persisted state on
    # init (real APs the running system has seen), which would otherwise make this
    # "empty summary" assertion depend on live machine state.
    monitor._wifi_sensor._ap_history.clear()
    monitor._bt_sensor._bt_history.clear()
    summary = await monitor.get_proximity_summary()

    assert "wifi" in summary
    assert "bluetooth" in summary
    assert summary["wifi"]["total_nearby"] == 0
    assert summary["bluetooth"]["total_nearby"] == 0
    assert "alerts_today" in summary

    await bus.stop()
    print("  ✓ get_proximity_summary() returns valid dict when no scan data")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Passive-only enforcement — verify no connect() or send() calls exist
# ═══════════════════════════════════════════════════════════════════════════════

def test_passive_only_no_connect_or_send():
    source_path = DEEP_ROOT / "network" / "proximity_monitor.py"
    source = source_path.read_text(encoding="utf-8")

    # Strip comments to avoid false positives in docstrings
    lines = source.splitlines()
    code_lines = [ln for ln in lines if not ln.strip().startswith("#")]
    code = "\n".join(code_lines)

    forbidden = [".connect(", ".send("]
    found = [f for f in forbidden if f in code]
    assert len(found) == 0, f"Passive-only violation: found {found} in proximity_monitor.py"
    print("  ✓ Passive-only enforcement: no connect() or send() calls in file")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Passive Proximity Monitor validation...\n")

    await test_starts_gracefully_no_wifi()
    await test_proximity_ap_dataclass()
    await test_analyse_wifi_fires_open_network()
    await test_analyse_wifi_skips_own_ap()
    await test_analyse_bt_fires_unknown_device()
    await test_analyse_bt_skips_known_device()
    await test_detect_patterns_recurring()
    await test_proximity_summary_empty()
    test_passive_only_no_connect_or_send()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All Passive Proximity Monitor tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
