"""
ai/retraining/data_extractor.py

Reads PatternMemory and builds a clean labelled dataset for intent classifier retraining.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TrainingSample:
    command: str
    intent: str
    confidence: float = 0.0
    quality_score: float = 0.0
    mood: str = ""
    timestamp: str = ""
    source: str = "microphone"


@dataclass
class TrainingDataset:
    samples: list[TrainingSample] = field(default_factory=list)
    by_intent: dict[str, list[str]] = field(default_factory=dict)
    total: int = 0
    real_samples: int = 0
    seed_supplements: int = 0
    date_range: tuple[str, str] = ("", "")


class TrainingDataExtractor:
    """Extracts and cleans training data from PatternMemory interactions."""

    def __init__(self, pattern_memory: Any) -> None:
        self.pattern_memory = pattern_memory
        self.settings = Settings()
        self._db_path = getattr(self.settings, "pattern_memory_db_path", "data/pattern_memory.db")

    async def extract(
        self,
        min_samples: int = 10,
        min_quality: float = 0.6,
        days_back: int = 90,
    ) -> TrainingDataset:
        """Build a clean labelled dataset from PatternMemory."""
        if not AIOSQLITE_AVAILABLE:
            logger.warning("aiosqlite not available — returning empty dataset")
            return TrainingDataset()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
        rows = await self._query_interactions(cutoff, min_quality)

        raw_samples: list[TrainingSample] = []
        for row in rows:
            cmd = row.get("command", "")
            intent = row.get("intent", "")
            if not cmd or not intent:
                continue
            raw_samples.append(
                TrainingSample(
                    command=cmd,
                    intent=intent,
                    confidence=row.get("quality_score", 0.0),
                    quality_score=row.get("quality_score", 0.0),
                    mood=row.get("mood", ""),
                    timestamp=row.get("timestamp", ""),
                    source=row.get("source", "microphone"),
                )
            )

        # Filter short commands (< 3 words)
        filtered = [s for s in raw_samples if len(s.command.split()) >= 3]

        # Filter unknown intents
        filtered = [s for s in filtered if s.intent not in ("unknown", "", None)]

        # Deduplicate by command text similarity
        deduplicated = self._deduplicate(filtered, ratio_threshold=0.95)

        real_count = len(deduplicated)

        # Group by intent
        by_intent: dict[str, list[str]] = {}
        for s in deduplicated:
            by_intent.setdefault(s.intent, []).append(s.command)

        # Supplement with seed data for under-represented intents
        seed_supplements = 0
        seed_data = self._get_seed_data()
        for intent, examples in by_intent.items():
            if len(examples) < min_samples and intent in seed_data:
                needed = min_samples - len(examples)
                seed_examples = seed_data[intent][:needed]
                for ex in seed_examples:
                    deduplicated.append(
                        TrainingSample(
                            command=ex,
                            intent=intent,
                            confidence=1.0,
                            quality_score=1.0,
                            mood="",
                            timestamp="",
                            source="seed",
                        )
                    )
                    seed_supplements += 1
                by_intent[intent].extend(seed_examples)
                logger.warning(
                    f"Intent '{intent}' has only {len(examples)} real samples — "
                    f"supplementing with {len(seed_examples)} seed examples"
                )

        # Date range
        timestamps = [s.timestamp for s in deduplicated if s.timestamp]
        date_range = (min(timestamps), max(timestamps)) if timestamps else ("", "")

        return TrainingDataset(
            samples=deduplicated,
            by_intent=by_intent,
            total=len(deduplicated),
            real_samples=real_count,
            seed_supplements=seed_supplements,
            date_range=date_range,
        )

    async def _query_interactions(
        self, cutoff: str, min_quality: float
    ) -> list[dict[str, Any]]:
        """Query pattern_memory.interactions table."""
        db_path = Path(self._db_path)
        if not db_path.exists():
            logger.warning(f"PatternMemory DB not found: {db_path}")
            return []

        async with aiosqlite.connect(str(db_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT command, intent, quality_score, mood, timestamp, source
                FROM interactions
                WHERE timestamp >= ?
                  AND quality_score >= ?
                  AND command IS NOT NULL
                  AND intent IS NOT NULL
                ORDER BY timestamp DESC
                """,
                (cutoff, min_quality),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    def _deduplicate(
        self, samples: list[TrainingSample], ratio_threshold: float = 0.95
    ) -> list[TrainingSample]:
        """Remove near-identical commands, keeping the most recent."""
        unique: list[TrainingSample] = []
        for s in sorted(samples, key=lambda x: x.timestamp or "", reverse=True):
            is_dup = False
            for u in unique:
                ratio = difflib.SequenceMatcher(None, s.command.lower(), u.command.lower()).ratio()
                if ratio >= ratio_threshold:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(s)
        return unique

    def _get_seed_data(self) -> dict[str, list[str]]:
        """Return SEED_DATA from ai.pipeline for supplementing."""
        try:
            from ai.pipeline import SEED_DATA
            return SEED_DATA
        except Exception:
            return {}

    async def get_dataset_stats(self) -> dict[str, Any]:
        """Return statistics about the raw data in PatternMemory."""
        if not AIOSQLITE_AVAILABLE:
            return {
                "total_commands_logged": 0,
                "usable_for_training": 0,
                "by_intent": {},
                "quality_distribution": {"excellent": 0, "good": 0, "poor": 0},
                "oldest_sample": None,
                "newest_sample": None,
            }

        db_path = Path(self._db_path)
        if not db_path.exists():
            return {
                "total_commands_logged": 0,
                "usable_for_training": 0,
                "by_intent": {},
                "quality_distribution": {"excellent": 0, "good": 0, "poor": 0},
                "oldest_sample": None,
                "newest_sample": None,
            }

        async with aiosqlite.connect(str(db_path)) as db:
            db.row_factory = aiosqlite.Row

            total_row = await db.execute("SELECT COUNT(*) FROM interactions")
            total = (await total_row.fetchone())[0]

            usable_row = await db.execute(
                "SELECT COUNT(*) FROM interactions WHERE command IS NOT NULL AND intent IS NOT NULL"
            )
            usable = (await usable_row.fetchone())[0]

            by_intent_rows = await db.execute(
                "SELECT intent, COUNT(*) FROM interactions GROUP BY intent"
            )
            by_intent = {r["intent"]: r[1] async for r in by_intent_rows}

            excellent_row = await db.execute(
                "SELECT COUNT(*) FROM interactions WHERE quality_score >= 0.8"
            )
            excellent = (await excellent_row.fetchone())[0]

            good_row = await db.execute(
                "SELECT COUNT(*) FROM interactions WHERE quality_score >= 0.6 AND quality_score < 0.8"
            )
            good = (await good_row.fetchone())[0]

            poor_row = await db.execute(
                "SELECT COUNT(*) FROM interactions WHERE quality_score < 0.6"
            )
            poor = (await poor_row.fetchone())[0]

            oldest_row = await db.execute(
                "SELECT MIN(timestamp) FROM interactions"
            )
            oldest = (await oldest_row.fetchone())[0]

            newest_row = await db.execute(
                "SELECT MAX(timestamp) FROM interactions"
            )
            newest = (await newest_row.fetchone())[0]

        return {
            "total_commands_logged": total,
            "usable_for_training": usable,
            "by_intent": by_intent,
            "quality_distribution": {
                "excellent": excellent,
                "good": good,
                "poor": poor,
            },
            "oldest_sample": oldest,
            "newest_sample": newest,
        }
