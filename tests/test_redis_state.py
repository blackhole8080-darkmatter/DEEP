"""
tests/test_redis_state.py

Validation suite for the Redis shared-state and DeviceRegistry components.

Run:
    python tests/test_redis_state.py
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
from core.redis_state import RedisStateManager
from core.device_registry import DeviceRegistry, Device


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: RedisStateManager starts without Redis running (graceful degradation)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_redis_starts_without_redis_running():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    # Patch redis.asyncio.from_url globally since it's imported locally in start()
    try:
        import redis.asyncio
        with patch("redis.asyncio.from_url", side_effect=ConnectionRefusedError("no redis")):
            await mgr.start()
    except ImportError:
        # redis not installed at all — should still start gracefully
        await mgr.start()

    assert mgr.status()["available"] is False
    assert mgr.status()["local_cache_size"] == 0

    await mgr.stop()
    await bus.stop()
    print("  ✓ RedisStateManager starts gracefully without Redis running")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: set()/get() round-trip works via local cache when Redis unavailable
# ═══════════════════════════════════════════════════════════════════════════════

async def test_local_cache_round_trip():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    # Simulate Redis unavailable
    mgr._redis_available = False
    mgr._started = True

    await mgr.set("test_key", {"foo": "bar"})
    result = await mgr.get("test_key")
    assert result == {"foo": "bar"}

    await mgr.stop()
    await bus.stop()
    print("  ✓ set()/get() round-trip via local cache when Redis unavailable")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: get() returns default when key missing
# ═══════════════════════════════════════════════════════════════════════════════

async def test_get_returns_default_when_missing():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    mgr._redis_available = False
    mgr._started = True

    result = await mgr.get("nonexistent_key", default="fallback")
    assert result == "fallback"

    await mgr.stop()
    await bus.stop()
    print("  ✓ get() returns default when key missing")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: save_conversation_turn() appends correctly and respects max
# ═══════════════════════════════════════════════════════════════════════════════

async def test_save_conversation_turn_respects_max():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    mgr._redis_available = False
    mgr._started = True
    mgr._local_cache = {}

    # Populate with more than max items to test truncation
    for i in range(15):
        await mgr.save_conversation_turn(
            command=f"cmd_{i}",
            response=f"resp_{i}",
            device_id="test-device",
            mood="neutral",
        )

    history = await mgr.get_conversation_history()
    # Each turn adds 2 items (user + deep). Max 20 = 10 turns = 20 items.
    # We added 15 turns = 30 items, truncated to 20 items.
    assert len(history) == 20, f"Expected 20 items, got {len(history)}"
    # Verify latest turn survived
    assert history[-1]["content"] == "resp_14"
    assert history[-2]["content"] == "cmd_14"

    await mgr.stop()
    await bus.stop()
    print("  ✓ save_conversation_turn() respects CONVERSATION_HISTORY_MAX")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: get_conversation_history() returns [] when no history exists
# ═══════════════════════════════════════════════════════════════════════════════

async def test_get_conversation_history_empty():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    mgr._redis_available = False
    mgr._started = True
    mgr._local_cache = {}

    history = await mgr.get_conversation_history()
    assert history == [], f"Expected [], got {history}"

    await mgr.stop()
    await bus.stop()
    print("  ✓ get_conversation_history() returns [] when no history")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: DeviceRegistry registers this device on start()
# ═══════════════════════════════════════════════════════════════════════════════

async def test_device_registry_registers_on_start():
    bus = EventBus()
    await bus.start()

    redis = RedisStateManager(event_bus=bus)
    redis._redis_available = False
    redis._started = True
    redis._local_cache = {}

    registry = DeviceRegistry(event_bus=bus, redis_state=redis)
    with patch.object(registry, "_device_id", "test-pc"):
        with patch.object(registry, "_device_name", "Test-PC"):
            await registry.start()

    # Verify device info was written to local cache
    info = redis._local_cache.get("deep:device:test-pc:info", {})
    assert info.get("name") == "Test-PC"
    assert info.get("active") is True

    await registry.stop()
    await redis.stop()
    await bus.stop()
    print("  ✓ DeviceRegistry registers this device on start()")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: DeviceRegistry status() returns available: False gracefully
# ═══════════════════════════════════════════════════════════════════════════════

async def test_device_registry_status_graceful():
    bus = EventBus()
    await bus.start()

    redis = RedisStateManager(event_bus=bus)
    redis._redis_available = False

    registry = DeviceRegistry(event_bus=bus, redis_state=redis)
    status = registry.status()
    assert status["this_device"] is not None
    assert status["active_devices"] == 0
    assert status["primary_device"] is None

    await bus.stop()
    print("  ✓ DeviceRegistry status() returns graceful defaults")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Namespaced set_session / get_session work
# ═══════════════════════════════════════════════════════════════════════════════

async def test_namespaced_session_methods():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    mgr._redis_available = False
    mgr._started = True
    mgr._local_cache = {}

    await mgr.set_session("theme", "dark")
    result = await mgr.get_session("theme")
    assert result == "dark"

    missing = await mgr.get_session("nonexistent", default="light")
    assert missing == "light"

    await mgr.stop()
    await bus.stop()
    print("  ✓ Namespaced set_session / get_session work")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Namespaced set_global / get_global work with broadcast flag
# ═══════════════════════════════════════════════════════════════════════════════

async def test_namespaced_global_methods():
    bus = EventBus()
    await bus.start()

    mgr = RedisStateManager(event_bus=bus)
    mgr._redis_available = False
    mgr._started = True
    mgr._local_cache = {}

    await mgr.set_global("active_device", "phone", broadcast=True)
    result = await mgr.get_global("active_device")
    assert result == "phone"

    await mgr.stop()
    await bus.stop()
    print("  ✓ Namespaced set_global / get_global work")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Redis State & Device Registry validation...\n")

    await test_redis_starts_without_redis_running()
    await test_local_cache_round_trip()
    await test_get_returns_default_when_missing()
    await test_save_conversation_turn_respects_max()
    await test_get_conversation_history_empty()
    await test_device_registry_registers_on_start()
    await test_device_registry_status_graceful()
    await test_namespaced_session_methods()
    await test_namespaced_global_methods()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All Redis State & Device Registry tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
