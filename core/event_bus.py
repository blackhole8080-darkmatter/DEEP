"""
core/event_bus.py

Central async pub/sub EventBus for DEEP.

All inter-module communication routes through this bus using asyncio-native
pub/sub. No threading — everything is async/await.

Pattern:
    - Modules subscribe to named events (or "*" for all events).
    - Publishers fire-and-forget; subscribers run concurrently via gather.
    - Event history keeps the last 50 events for introspection/debugging.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List

logger = logging.getLogger(__name__)

# Configurable via config.py if we ever need tuning, but history size is
# small enough to hardcode as a local constant per project standards.
_MAX_HISTORY = 50

# Type alias for async callbacks
EventCallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async-native pub/sub event bus for DEEP.

    Follows the standard DEEP class pattern:
        __init__() -> start() -> ... operations ... -> stop() -> status()
    """

    def __init__(self) -> None:
        """Initialize the event bus (inactive until start() is called)."""
        self._subscribers: Dict[str, List[EventCallback]] = {}
        self._wildcard_subscribers: List[EventCallback] = []
        self._history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)
        self._started = False
        self._start_time: float = 0.0
        self._total_fired: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Activate the event bus and record uptime baseline."""
        self._started = True
        self._start_time = time.monotonic()
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Deactivate the event bus and clear all subscribers."""
        self._started = False
        self._subscribers.clear()
        self._wildcard_subscribers.clear()
        logger.info("EventBus stopped and subscribers cleared")

    def status(self) -> dict[str, Any]:
        """
        Return current operational status.

        Returns:
            dict with keys:
                - active_subscribers (int): total registered callbacks
                - total_events_fired (int): events published since start()
                - uptime_seconds (float): seconds since start()
        """
        uptime = time.monotonic() - self._start_time if self._started else 0.0
        active = sum(len(cbs) for cbs in self._subscribers.values()) + len(self._wildcard_subscribers)
        return {
            "active_subscribers": active,
            "total_events_fired": self._total_fired,
            "uptime_seconds": round(uptime, 2),
        }

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    def subscribe(self, event_name: str, callback: EventCallback) -> None:
        """
        Register an async callback for a named event.

        Supports multiple subscribers per event. The callback signature must be:
            async def handler(event_name: str, payload: dict) -> None

        Use event_name="*" to subscribe to ALL events.

        Args:
            event_name: event name to listen for, or "*" for wildcard.
            callback: async coroutine to invoke on matching events.
        """
        if not self._started:
            logger.warning("EventBus.subscribe called before start()")

        if event_name == "*":
            if callback not in self._wildcard_subscribers:
                self._wildcard_subscribers.append(callback)
        else:
            self._subscribers.setdefault(event_name, [])
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: EventCallback) -> None:
        """
        Remove a previously registered callback.

        Args:
            event_name: event name the callback was registered for, or "*".
            callback: the exact async callback to remove.
        """
        if event_name == "*":
            try:
                self._wildcard_subscribers.remove(callback)
            except ValueError:
                logger.warning("Wildcard unsubscribe: callback not found")
        else:
            cbs = self._subscribers.get(event_name, [])
            try:
                cbs.remove(callback)
            except ValueError:
                logger.warning(f"Unsubscribe: callback not found for event '{event_name}'")
            if not cbs:
                self._subscribers.pop(event_name, None)

    # ------------------------------------------------------------------
    # Publish API
    # ------------------------------------------------------------------

    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        """
        Fire an event to all matching subscribers concurrently.

        Named subscribers and wildcard subscribers both receive the event.
        Each subscriber runs as an independent asyncio task; gather() waits
        for all to complete. Exceptions in individual subscribers are caught
        and logged — they never propagate to the publisher.

        Args:
            event_name: name of the event being fired.
            payload: serializable dict passed to every subscriber.
        """
        if not self._started:
            logger.warning(f"EventBus.publish('{event_name}') called before start()")

        self._total_fired += 1

        # Record in history (timestamp is UTC ISO-8601)
        self._history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_name,
            "payload": payload,
        })

        # Build list of targets
        targets: List[EventCallback] = []
        targets.extend(self._subscribers.get(event_name, []))
        targets.extend(self._wildcard_subscribers)

        if not targets:
            return

        # Fire concurrently; isolate failures so one broken subscriber
        # doesn't break the others.
        results = await asyncio.gather(
            *(cb(event_name, payload) for cb in targets),
            return_exceptions=True,
        )

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                cb_name = getattr(targets[idx], "__name__", repr(targets[idx]))
                logger.error(
                    f"Subscriber '{cb_name}' raised {type(result).__name__} "
                    f"on event '{event_name}': {result}"
                )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, event_name: str | None = None) -> list[dict[str, Any]]:
        """
        Retrieve recent event history.

        Args:
            event_name: optional filter — only return events with this name.

        Returns:
            List of history entries ordered oldest -> newest, each containing
            timestamp (ISO-8601), event name, and payload.
        """
        history_list = list(self._history)
        if event_name:
            history_list = [h for h in history_list if h["event"] == event_name]
        return history_list


# ═══════════════════════════════════════════════════════════════════════
# Usage Example: voice_pipeline -> deep_core via EventBus
# ═══════════════════════════════════════════════════════════════════════
"""
# ---- voice_pipeline.py (publishes) ----
from core.event_bus import EventBus

async def on_transcription_complete(audio_path: str, transcript: str, bus: EventBus):
    # After Whisper finishes, publish the user command
    await bus.publish("user_command", {
        "source": "voice",
        "audio_path": audio_path,
        "text": transcript,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })

# ---- deep_core.py (subscribes) ----
from core.event_bus import EventBus

async def handle_user_command(event_name: str, payload: dict):
    # event_name == "user_command"
    text = payload["text"]
    source = payload["source"]  # "voice" | "chat" | "api"
    print(f"[{source.upper()}] User said: {text}")
    # ... route to brain, tools, etc.

async def setup_core(bus: EventBus):
    bus.subscribe("user_command", handle_user_command)

# ---- startup sequence ----
bus = EventBus()
await bus.start()

# Register all subscribers before any publishes
await setup_core(bus)

# Later, anywhere in the system:
await bus.publish("user_command", {"source": "chat", "text": "What's the weather?"})
"""
