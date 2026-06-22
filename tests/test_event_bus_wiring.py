"""
tests/test_event_bus_wiring.py

Validation suite for the EventBus migration across all DEEP modules.

Run:
    python tests/test_event_bus_wiring.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

# ── Mock heavy imports before loading modules ──────────────────────────────
sys.modules["whisper"] = MagicMock()

from core.event_bus import EventBus
from core.security.network_monitor import NetworkMonitor, SecuritySeverity

# (Test 1 — local_stt user_command — removed with the voice subsystem.)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: network_monitor publishes alert events on the bus
# ═══════════════════════════════════════════════════════════════════════════════

async def test_network_monitor_publishes_security_alert():
    """network_monitor must publish 'security_alert' events on the bus."""
    bus = EventBus()
    await bus.start()

    captured: list[dict] = []

    async def _capture(event_name: str, payload: dict):
        captured.append(payload)

    bus.subscribe("security_alert", _capture)

    netmon = NetworkMonitor(event_bus=bus)
    netmon._emit_event(
        event_type="new_device",
        severity=SecuritySeverity.MEDIUM,
        title="Test device detected",
        description="A test device for wiring validation.",
        device_mac="aa:bb:cc:dd:ee:ff",
        device_ip="192.168.1.100",
    )

    # _emit_event schedules publish as a background task; yield control
    await asyncio.sleep(0.05)

    assert len(captured) == 1, f"Expected 1 security_alert event, got {len(captured)}"
    assert captured[0]["event_type"] == "new_device"
    assert captured[0]["title"] == "Test device detected"

    await bus.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: wildcard subscriber receives events from >=3 different modules
# ═══════════════════════════════════════════════════════════════════════════════

async def test_wildcard_receives_multi_module_events():
    """A wildcard subscriber on '*' must receive events from at least 3 modules."""
    bus = EventBus()
    await bus.start()

    captured: list[str] = []

    async def _wildcard(event_name: str, payload: dict):
        captured.append(event_name)

    bus.subscribe("*", _wildcard)

    # Simulate events from different module namespaces
    await bus.publish("security_alert", {"module": "network_monitor"})
    await bus.publish("agent_created", {"module": "agent_factory"})
    await bus.publish("knowledge_added", {"module": "knowledge_graph"})
    await bus.publish("topic_added", {"module": "research_engine"})

    assert len(captured) >= 3, f"Expected >=3 events, got {len(captured)}"
    assert "security_alert" in captured
    assert "agent_created" in captured
    assert "knowledge_added" in captured

    await bus.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: server startup sequence contains zero .on_event() calls
# ═══════════════════════════════════════════════════════════════════════════════

def test_server_startup_has_no_on_event_calls():
    """
    Grep the server startup sequence for the literal string '.on_event('.
    After migration, every module self-registers in its own start()
    and server.py must contain zero hardcoded .on_event() registrations.
    """
    server_path = DEEP_ROOT / "interface" / "server.py"
    source = server_path.read_text(encoding="utf-8")

    offending = [
        ln.strip()
        for ln in source.splitlines()
        if ".on_event(" in ln
        and not ln.strip().startswith("@")   # exclude FastAPI decorators
        and "def " not in ln                # exclude function definitions
        and not ln.strip().startswith("#")  # exclude comments
    ]

    assert len(offending) == 0, (
        f"Found .on_event() calls in interface/server.py — "
        f"migration incomplete. Lines: {offending}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Run all validation tests."""
    print("Running EventBus wiring validation...\n")

    await test_network_monitor_publishes_security_alert()
    print("✓ network_monitor publishes 'security_alert' on the bus")

    await test_wildcard_receives_multi_module_events()
    print("✓ wildcard subscriber receives events from 4 different modules")

    test_server_startup_has_no_on_event_calls()
    print("✓ server startup sequence has zero .on_event() calls")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All EventBus wiring tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
