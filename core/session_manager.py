"""
core/session_manager.py

Tracks DEEP sessions — each boot is a session, enabling
per-session replay and analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Single DEEP session snapshot."""

    session_id: str = ""
    started_at: str = ""
    ended_at: str | None = None
    device_id: str = ""
    command_count: int = 0
    threat_count: int = 0
    knowledge_queries: int = 0
    dominant_mood: str | None = None


class SessionManager:
    """
    Tracks per-session statistics and exports session logs.

    Lifecycle: __init__ -> start() -> ... -> end_session()
    """

    def __init__(self, event_bus: Any, audit_trail: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._audit_trail = audit_trail
        self._redis_state = redis_state
        self._current: Session | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._current = Session(
            session_id=self._audit_trail._session_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            device_id=self._resolve_device_id(),
            ended_at=None,
            command_count=0,
            threat_count=0,
            knowledge_queries=0,
            dominant_mood=None,
        )

        await self._redis_state.set_global("current_session", self._current.__dict__)

        # Subscribe to counter events
        self._event_bus.subscribe("user_command", self._on_command)
        self._event_bus.subscribe("threat_detected", self._on_threat)
        self._event_bus.subscribe("knowledge_query", self._on_knowledge)

        logger.info(f"SessionManager started — session {self._current.session_id[:8]}")

    async def end_session(self) -> None:
        if not self._current:
            return

        self._current.ended_at = datetime.now(timezone.utc).isoformat()
        self._current.dominant_mood = await self._get_dominant_mood()

        try:
            path = await self._audit_trail.export_session(
                self._current.session_id, format="text"
            )
        except Exception as exc:
            logger.warning(f"Session export failed: {exc}")
            path = None

        await self._redis_state.set_global("last_session", self._current.__dict__)

        try:
            started = datetime.fromisoformat(self._current.started_at.replace("Z", "+00:00"))
            ended = datetime.fromisoformat(self._current.ended_at.replace("Z", "+00:00"))
            duration = (ended - started).total_seconds()
        except Exception:
            duration = 0

        await self._event_bus.publish("session_ended", {
            "session_id": self._current.session_id,
            "duration_s": int(duration),
            "command_count": self._current.command_count,
            "threat_count": self._current.threat_count,
            "summary_path": path,
        })

        try:
            self._event_bus.unsubscribe("user_command", self._on_command)
            self._event_bus.unsubscribe("threat_detected", self._on_threat)
            self._event_bus.unsubscribe("knowledge_query", self._on_knowledge)
        except Exception:
            pass

        logger.info(f"SessionManager ended — session {self._current.session_id[:8]}")

    # ------------------------------------------------------------------
    # Event counters
    # ------------------------------------------------------------------

    async def _on_command(self, event_name: str, payload: dict) -> None:
        if self._current:
            self._current.command_count += 1

    async def _on_threat(self, event_name: str, payload: dict) -> None:
        if self._current:
            self._current.threat_count += 1

    async def _on_knowledge(self, event_name: str, payload: dict) -> None:
        if self._current:
            self._current.knowledge_queries += 1

    # ------------------------------------------------------------------
    # Mood analysis
    # ------------------------------------------------------------------

    async def _get_dominant_mood(self) -> str | None:
        try:
            entries = await self._audit_trail.query(
                entry_type="COMMAND",
                session_id=self._current.session_id if self._current else None,
                limit=500,
            )
            moods: dict[str, int] = {}
            for e in entries:
                mood = e.payload.get("mood") if e.payload else None
                if mood:
                    moods[mood] = moods.get(mood, 0) + 1
            return max(moods, key=moods.get) if moods else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current(self) -> Session | None:
        return self._current

    def status(self) -> dict[str, Any]:
        if not self._current:
            return {"active": False}
        try:
            started = datetime.fromisoformat(self._current.started_at.replace("Z", "+00:00"))
            duration = (datetime.now(timezone.utc) - started).total_seconds()
        except Exception:
            duration = 0
        return {
            "session_id": self._current.session_id,
            "started_at": self._current.started_at,
            "command_count": self._current.command_count,
            "threat_count": self._current.threat_count,
            "knowledge_queries": self._current.knowledge_queries,
            "duration_s": int(duration),
        }

    def _resolve_device_id(self) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), "deep_device_id", "unknown")
        except Exception:
            return "unknown"
