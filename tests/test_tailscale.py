"""
tests/test_tailscale.py

Validation suite for the Tailscale VPN and Remote Access components.

Run:
    python tests/test_tailscale.py
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
from network.tailscale import TailscaleManager, TailscaleStatus
from network.remote_access import RemoteAccessManager


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: TailscaleManager initialises without binary present (no crash)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_tailscale_manager_init_without_binary():
    bus = EventBus()
    await bus.start()

    # Patch binary existence to False
    with patch.object(Path, "exists", return_value=False):
        mgr = TailscaleManager(event_bus=bus)
        await mgr.start()

    # Should not crash; status should reflect not installed
    status = mgr.status()
    assert status["state"] == "Unknown"
    assert status["ip"] is None
    assert status["peers_count"] == 0

    await mgr.stop()
    await bus.stop()
    print("  ✓ TailscaleManager initialises gracefully without binary")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: _get_status() returns TailscaleStatus with state="Unknown" when binary missing
# ═══════════════════════════════════════════════════════════════════════════════

async def test_get_status_unknown_when_binary_missing():
    bus = EventBus()
    await bus.start()

    mgr = TailscaleManager(event_bus=bus)
    with patch.object(Path, "exists", return_value=False):
        status = await mgr._get_status()

    assert isinstance(status, TailscaleStatus)
    assert status.state == "Unknown"
    assert status.ip == ""
    assert status.peers == []

    await bus.stop()
    print("  ✓ _get_status() returns Unknown when binary missing")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: get_access_info() returns not_connected dict when json file absent
# ═══════════════════════════════════════════════════════════════════════════════

async def test_get_access_info_not_connected_when_file_absent():
    bus = EventBus()
    await bus.start()

    tailscale = MagicMock()
    remote = RemoteAccessManager(event_bus=bus, tailscale=tailscale)

    # Ensure the file does not exist by using a temp path
    with patch.object(remote, "_info_path", Path("/nonexistent/remote_access_info.json")):
        info = await remote.get_access_info()

    assert info["status"] == "not_connected"

    await bus.stop()
    print("  ✓ get_access_info() returns not_connected when json file absent")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: RemoteAccessManager status() returns accessible_remotely: False when not connected
# ═══════════════════════════════════════════════════════════════════════════════

async def test_remote_access_status_not_connected():
    bus = EventBus()
    await bus.start()

    tailscale = MagicMock()
    remote = RemoteAccessManager(event_bus=bus, tailscale=tailscale)

    with patch.object(remote, "_info_path", Path("/nonexistent/remote_access_info.json")):
        status = remote.status()

    assert status["accessible_remotely"] is False
    assert status["url"] is None
    assert status["qr_generated"] is False

    await bus.stop()
    print("  ✓ RemoteAccessManager status() returns accessible_remotely: False")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: "tailscale_not_installed" event published when binary missing on start()
# ═══════════════════════════════════════════════════════════════════════════════

async def test_tailscale_not_installed_event_published():
    bus = EventBus()
    await bus.start()

    captured: list[dict] = []

    async def _capture(event_name: str, payload: dict):
        captured.append({"event": event_name, "payload": payload})

    bus.subscribe("tailscale_not_installed", _capture)

    mgr = TailscaleManager(event_bus=bus)
    with patch.object(Path, "exists", return_value=False):
        await mgr.start()

    # Allow event to propagate
    await asyncio.sleep(0.05)

    assert len(captured) == 1, f"Expected 1 tailscale_not_installed event, got {len(captured)}"
    assert captured[0]["event"] == "tailscale_not_installed"
    assert "path" in captured[0]["payload"]
    assert "timestamp" in captured[0]["payload"]

    await mgr.stop()
    await bus.stop()
    print("  ✓ tailscale_not_installed event published when binary missing")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Tailscale & Remote Access validation...\n")

    await test_tailscale_manager_init_without_binary()
    await test_get_status_unknown_when_binary_missing()
    await test_get_access_info_not_connected_when_file_absent()
    await test_remote_access_status_not_connected()
    await test_tailscale_not_installed_event_published()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All Tailscale & Remote Access tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
