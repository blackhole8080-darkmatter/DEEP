"""
core/preference_learning.py

Preference Learning for Deep — "learns from you".

Captures durable user preferences from two signals:
  1. Explicit statements  ("I prefer concise answers", "call me Aryan", "I use metric")
  2. Corrections          ("no, I meant...", "don't do that", "use X instead")

Detected preferences are normalized to a concise statement, de-duplicated
against what's already known (using LTM's hybrid recall), and stored as
'preference' memories. They can then be injected into the prompt so Deep
actually adapts over time instead of repeating the same mistakes.

This is deliberately rule-based and dependency-light (no LLM call on the hot
path). An optional LLM refiner can be plugged in later via `refiner`.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Phrases that signal the user is stating a preference / standing instruction.
_PREFERENCE_CUES = [
    "i prefer", "i like", "i'd prefer", "i would prefer", "i love", "i hate",
    "i don't like", "i dont like", "please always", "please don't", "please dont",
    "from now on", "always", "never", "call me", "my name is", "i use", "i live in",
    "i work", "remember that", "remember to", "keep it", "make it", "in future",
    "going forward", "i want you to", "i'd like you to", "stop ", "don't ", "dont ",
]

# Cues that the user is correcting Deep (strong preference signal).
_CORRECTION_CUES = [
    "no,", "no.", "not ", "that's wrong", "thats wrong", "incorrect", "actually,",
    "actually ", "i meant", "i said", "wrong", "instead", "you should have",
    "that's not", "thats not", "don't ", "dont ",
]

# Leading filler to strip when normalizing.
_STRIP_PREFIXES = [
    "no, ", "no ", "actually, ", "actually ", "well, ", "well ", "um, ", "uh, ",
    "please ", "can you ", "could you ", "i'd like you to ", "i want you to ",
    "i would like you to ",
]


class PreferenceLearner:
    """Detects, normalizes, de-duplicates and stores user preferences in LTM."""

    def __init__(self, ltm, refiner: Optional[Callable[[str], str]] = None,
                 max_len: int = 200, dedup_overlap: float = 0.7):
        self.ltm = ltm
        self.refiner = refiner          # optional callable(raw_text) -> clean preference
        self.max_len = max_len
        self.dedup_overlap = dedup_overlap

    # ─── Detection ────────────────────────────────────────────────────────────

    def detect(self, user_text: str) -> bool:
        """Does this message look like it carries a preference or correction?"""
        if not user_text:
            return False
        lo = user_text.lower().strip()
        if len(lo) < 4:
            return False
        return (any(cue in lo for cue in _PREFERENCE_CUES)
                or any(lo.startswith(c) or c in lo for c in _CORRECTION_CUES))

    # ─── Normalization ──────────────────────────────────────────────────────────

    def normalize(self, user_text: str) -> str:
        """Turn a raw message into a concise preference statement."""
        text = (user_text or "").strip()
        if self.refiner:
            try:
                refined = self.refiner(text)
                if refined:
                    text = refined.strip()
            except Exception as e:
                logger.warning(f"[PrefLearn] refiner failed: {e}")
        # Take the most preference-bearing sentence if multiple.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chosen = text
        for s in sentences:
            sl = s.lower()
            if any(cue in sl for cue in _PREFERENCE_CUES + _CORRECTION_CUES):
                chosen = s.strip()
                break
        # Strip leading filler.
        cl = chosen
        lowered = cl.lower()
        for pre in _STRIP_PREFIXES:
            if lowered.startswith(pre):
                cl = cl[len(pre):]
                lowered = cl.lower()
        cl = cl.strip().rstrip(".")
        return cl[:self.max_len]

    # ─── Dedup ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _overlap(a: str, b: str) -> float:
        def words(s: str) -> set:
            return set(re.findall(r"[a-z0-9]+", s.lower()))
        wa, wb = words(a), words(b)
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _is_duplicate(self, preference: str) -> bool:
        try:
            existing = self.ltm.recall(preference, k=3, memory_type="preference")
        except Exception as e:
            logger.warning(f"[PrefLearn] dedup recall failed: {e}")
            return False
        for m in existing:
            content = getattr(m, "content", "")
            if self._overlap(preference, content) >= self.dedup_overlap:
                return True
        return False

    # ─── Public API ───────────────────────────────────────────────────────────

    def learn(self, user_text: str, importance: float = 1.5) -> Optional[str]:
        """Detect+normalize+dedup+store. Returns the stored preference, or None."""
        if not self.detect(user_text):
            return None
        preference = self.normalize(user_text)
        if not preference or len(preference) < 3:
            return None
        if self._is_duplicate(preference):
            logger.info(f"[PrefLearn] skipped duplicate: {preference}")
            return None
        try:
            self.ltm.store(
                "preference", preference,
                metadata={"source": "preference_learner"},
                importance=importance,
            )
            logger.info(f"[PrefLearn] learned: {preference}")
            return preference
        except Exception as e:
            logger.error(f"[PrefLearn] store failed: {e}")
            return None

    def get_preferences(self, query: str = "", k: int = 5) -> List[str]:
        """Fetch preferences relevant to a query (or recent if no query) for prompt injection."""
        try:
            results = self.ltm.recall(query or "user preference", k=k, memory_type="preference")
            return [getattr(m, "content", "") for m in results if getattr(m, "content", "")]
        except Exception as e:
            logger.warning(f"[PrefLearn] get_preferences failed: {e}")
            return []
