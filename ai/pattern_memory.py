"""
deep/ai/pattern_memory.py

Persistent interaction memory, mood tracking, behaviour pattern learning,
and daily summary generation for DEEP.

All data stored in a local SQLite database via aiosqlite — no cloud,
no external dependencies beyond what is in requirements.txt.

Role in DEEP:
    - Records every user interaction (intent, command, response, mood)
    - Learns temporal behaviour patterns (hour × day-of-week × intent)
    - Tracks mood history with acoustic features (energy, speech rate,
      pitch variance)
    - Provides recent context for LangGraph context injection
    - Generates nightly plain-text summaries
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    logger.warning("aiosqlite not installed — PatternMemory will use in-memory fallback")

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus


# ── Schema ───────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    intent TEXT,
    command TEXT,
    response TEXT,
    mood TEXT,
    quality_score REAL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS behaviour_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour INTEGER,
    day_of_week INTEGER,
    intent TEXT,
    frequency INTEGER DEFAULT 1,
    last_seen TEXT,
    UNIQUE(hour, day_of_week, intent)
);

CREATE TABLE IF NOT EXISTS mood_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    mood TEXT,
    energy REAL,
    speech_rate REAL,
    pitch_variance REAL
);

CREATE TABLE IF NOT EXISTS schedule_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour INTEGER,
    day_of_week INTEGER,
    activity TEXT,
    confidence REAL,
    sample_count INTEGER
);
"""


class PatternMemory:
    """
    SQLite-backed memory layer for interaction history, mood tracking,
    and behavioural pattern learning.

    Lifecycle: __init__ → start() → ... → stop() → status()
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_path: Optional[str] = None,
    ) -> None:
        self.event_bus = event_bus
        self._db_path = db_path or self._default_db_path()
        self._conn: Optional[Any] = None
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Open the database and ensure schema exists."""
        if not AIOSQLITE_AVAILABLE:
            logger.error("PatternMemory requires aiosqlite. Install: pip install aiosqlite")
            return

        # Ensure parent directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        self._started = True
        logger.info(f"[PatternMemory] DB ready at {self._db_path}")

    async def stop(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
        self._started = False
        logger.info("[PatternMemory] DB closed")

    def status(self) -> Dict[str, Any]:
        """Return operational status: total interactions, db size, oldest record."""
        if not self._started or not AIOSQLITE_AVAILABLE:
            return {"total_interactions": 0, "db_size_kb": 0.0, "oldest_record": None}

        total = 0
        size_kb = 0.0
        oldest = None
        try:
            import sqlite3
            with sqlite3.connect(self._db_path) as conn:
                cur = conn.execute("SELECT COUNT(*) FROM interactions")
                total = cur.fetchone()[0]
                cur = conn.execute("SELECT MIN(timestamp) FROM interactions")
                row = cur.fetchone()
                oldest = row[0] if row else None
            size_kb = round(os.path.getsize(self._db_path) / 1024, 2)
        except Exception as e:
            logger.warning(f"[PatternMemory] status() error: {e}")

        return {
            "total_interactions": total,
            "db_size_kb": size_kb,
            "oldest_record": oldest,
        }

    # ── Core API ──────────────────────────────────────────────────────────

    async def log_interaction(
        self,
        intent: str,
        command: str,
        response: str,
        mood: str,
        quality_score: float,
        source: str = "microphone",
    ) -> None:
        """
        Record a single interaction and update the behaviour pattern
        for the current hour + day-of-week.
        """
        if not self._conn:
            logger.warning("PatternMemory not started — skipping log_interaction")
            return

        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO interactions (timestamp, intent, command, response, mood, quality_score, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now, intent, command, response, mood, quality_score, source),
        )
        await self._conn.commit()

        now_dt = datetime.now(timezone.utc)
        await self._update_behaviour_pattern(now_dt.hour, now_dt.weekday(), intent)

        logger.debug(f"[PatternMemory] Logged interaction: intent={intent}, mood={mood}")

    async def get_recent_context(self, n: int = 10) -> str:
        """
        Return the last *n* interactions formatted as a context string
        suitable for LangGraph prompt injection.

        Format:
            [HH:MM] intent: command → response (mood: X)
        """
        if not self._conn:
            return "(no context — PatternMemory not started)"

        rows = await self._conn.execute_fetchall(
            """
            SELECT timestamp, intent, command, response, mood
            FROM interactions
            ORDER BY id DESC
            LIMIT ?
            """,
            (n,),
        )
        # aiosqlite returns rows in reverse chronological order; flip back
        lines: List[str] = []
        for row in reversed(rows):
            ts_raw, intent, command, response, mood = row
            try:
                ts = datetime.fromisoformat(ts_raw)
                time_str = ts.strftime("%H:%M")
            except Exception:
                time_str = "--:--"
            lines.append(
                f"[{time_str}] {intent}: {command} → {response} (mood: {mood})"
            )
        return "\n".join(lines)

    async def _update_behaviour_pattern(
        self, hour: int, day_of_week: int, intent: str
    ) -> None:
        """
        Upsert a behaviour-pattern row for the given hour + dow + intent.
        Increments frequency if the row already exists.
        """
        if not self._conn:
            return

        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO behaviour_patterns (hour, day_of_week, intent, frequency, last_seen)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(hour, day_of_week, intent) DO UPDATE SET
                frequency = frequency + 1,
                last_seen = excluded.last_seen
            """,
            (hour, day_of_week, intent, now),
        )
        await self._conn.commit()

    async def get_predicted_intent(
        self, hour: int, day_of_week: int
    ) -> Optional[str]:
        """
        Predict the most likely intent for the given hour and day-of-week.
        Returns None if fewer than 3 total samples exist for this slot.
        """
        if not self._conn:
            return None

        async with self._conn.execute(
            """
            SELECT intent, frequency FROM behaviour_patterns
            WHERE hour = ? AND day_of_week = ?
            ORDER BY frequency DESC
            LIMIT 1
            """,
            (hour, day_of_week),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        total_samples = await self._conn.execute_fetchall(
            "SELECT SUM(frequency) FROM behaviour_patterns WHERE hour = ? AND day_of_week = ?",
            (hour, day_of_week),
        )
        total = total_samples[0][0] if total_samples else 0
        if total < 3:
            return None

        return row[0]

    # ── Mood ──────────────────────────────────────────────────────────────

    async def log_mood(
        self,
        mood: str,
        energy: float,
        speech_rate: float,
        pitch_variance: float,
    ) -> None:
        """Record a mood snapshot with acoustic features."""
        if not self._conn:
            return

        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO mood_history (timestamp, mood, energy, speech_rate, pitch_variance)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now, mood, energy, speech_rate, pitch_variance),
        )
        await self._conn.commit()

    async def get_mood_trend(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyse mood over the last *hours* window.

        Returns:
            {
                "dominant": str,
                "distribution": {mood: count},
                "trend": "stable" | "improving" | "declining"
            }
        """
        if not self._conn:
            return {"dominant": "unknown", "distribution": {}, "trend": "stable"}

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = await self._conn.execute_fetchall(
            """
            SELECT mood, energy, speech_rate, pitch_variance
            FROM mood_history
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (cutoff,),
        )

        if not rows:
            return {"dominant": "unknown", "distribution": {}, "trend": "stable"}

        moods = [r[0] for r in rows]
        distribution = dict(Counter(moods))
        dominant = Counter(moods).most_common(1)[0][0]

        # Trend: compare first half vs second half average energy
        mid = len(rows) // 2
        first_half = [r[1] for r in rows[:mid]] if mid > 0 else [0.5]
        second_half = [r[1] for r in rows[mid:]] if mid > 0 else [0.5]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        delta = avg_second - avg_first

        if delta > 0.05:
            trend = "improving"
        elif delta < -0.05:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "dominant": dominant,
            "distribution": distribution,
            "trend": trend,
        }

    # ── Daily Summary ─────────────────────────────────────────────────────

    async def generate_daily_summary(self) -> str:
        """
        Generate a plain-text summary of the day.
        Called by scheduler at midnight.
        Writes to deep/logs/daily/YYYY-MM-DD.txt and returns the string.
        """
        if not self._conn:
            return "(PatternMemory not started — no summary available)"

        today = datetime.now(timezone.utc).date()
        start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        end = (datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)).isoformat()

        # Intent counts
        intent_rows = await self._conn.execute_fetchall(
            """
            SELECT intent, COUNT(*) FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY intent
            ORDER BY COUNT(*) DESC
            """,
            (start, end),
        )
        intent_counts = {intent: count for intent, count in intent_rows}

        # Mood counts
        mood_rows = await self._conn.execute_fetchall(
            """
            SELECT mood, COUNT(*) FROM mood_history
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY mood
            ORDER BY COUNT(*) DESC
            """,
            (start, end),
        )
        mood_counts = {mood: count for mood, count in mood_rows}
        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "unknown"

        # Most active hour
        hour_rows = await self._conn.execute_fetchall(
            """
            SELECT strftime('%H', timestamp) AS hour, COUNT(*) FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY hour
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """,
            (start, end),
        )
        most_active_hour = f"{hour_rows[0][0]}:00" if hour_rows else "N/A"

        total_interactions = sum(intent_counts.values()) if intent_counts else 0

        summary = f"""DEEP Daily Summary — {today.isoformat()}
═══════════════════════════════════════════════
Total interactions today: {total_interactions}
Dominant mood: {dominant_mood}
Most active hour: {most_active_hour}

Intent breakdown:
{chr(10).join(f"  • {intent}: {count}" for intent, count in intent_counts.items()) or "  (no interactions recorded)"}

Mood breakdown:
{chr(10).join(f"  • {mood}: {count}" for mood, count in mood_counts.items()) or "  (no mood entries recorded)"}

Generated at: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""

        # Write to daily log
        log_dir = Path("deep/logs/daily")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{today.isoformat()}.txt"
        log_path.write_text(summary, encoding="utf-8")

        logger.info(f"[PatternMemory] Daily summary written to {log_path}")
        return summary

    # ── Helpers ───────────────────────────────────────────────────────────

    def _default_db_path(self) -> str:
        """Resolve DB path from config, or fallback to a local default."""
        try:
            settings = Settings()
            # If the user hasn't set PATTERN_MEMORY_DB_PATH yet, fall back
            db_path = getattr(settings, "pattern_memory_db_path", None)
            if db_path:
                return str(db_path)
        except Exception:
            pass
        return str(Path(__file__).parent.parent.parent / "data" / "pattern_memory.db")
