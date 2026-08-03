"""
deep/knowledge/breakthrough_detector.py

Monitors ingested papers and fires alerts for genuinely significant results.
Subscribes to "papers_ingested" events from the EventBus.

Scoring system (4 signals, each weighted):
    1. Title keywords (0.25)      — HIGH_SIGNAL_WORDS matches
    2. Quantified improvement (0.25) — regex patterns in abstract
    3. Source prestige (0.20)      — high-impact journal/conference
    4. Ollama impact rating (0.30)  — LLM rates abstract impact

Threshold: config.BREAKTHROUGH_THRESHOLD (default 0.72)
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

from .knowledge_store import Paper


# ═══════════════════════════════════════════════════════════════════════════════
# BreakthroughDetector
# ═══════════════════════════════════════════════════════════════════════════════

class BreakthroughDetector:
    """
    Scores papers for genuine scientific significance.
    Publishes "breakthrough_detected" and "tts_speak" events.
    """

    def __init__(
        self,
        event_bus: EventBus,
        knowledge_store,
    ) -> None:
        self.event_bus = event_bus
        self.knowledge_store = knowledge_store
        self.settings = Settings()
        self._started = False
        self._client: Optional[Any] = None
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(timeout=30.0)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to papers_ingested events."""
        self.event_bus.subscribe("papers_ingested", self._on_papers_ingested)
        self._started = True
        logger.info("[BreakthroughDetector] Started")

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._started = False
        logger.info("[BreakthroughDetector] Stopped")

    def status(self) -> Dict[str, Any]:
        return {"started": self._started}

    # ── Event handler ─────────────────────────────────────────────────────

    async def _on_papers_ingested(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Called after each ingestion run."""
        total_new = payload.get("total_new", 0)
        if total_new == 0:
            return

        # Get the most recent papers to score
        recent_papers = await self.knowledge_store.get_recent(days=1, n=total_new)
        if not recent_papers:
            return

        # Score concurrently with a semaphore to not hammer Ollama
        sem = asyncio.Semaphore(5)

        async def _score_with_sem(paper: Paper):
            async with sem:
                return await self._score_paper(paper)

        scores = await asyncio.gather(
            *[_score_with_sem(p) for p in recent_papers],
            return_exceptions=True,
        )

        threshold = getattr(self.settings, "breakthrough_threshold", 0.72)
        for paper, score_result in zip(recent_papers, scores):
            if isinstance(score_result, Exception):
                logger.warning(f"[BreakthroughDetector] Scoring error: {score_result}")
                continue

            score, signals = score_result
            if score >= threshold:
                summary = await self._summarise_breakthrough(paper)
                await self.event_bus.publish("breakthrough_detected", {
                    "paper_id": paper.id,
                    "title": paper.title,
                    "domain": paper.domain,
                    "score": round(score, 3),
                    "summary": summary,
                    "url": paper.url,
                    "signals": signals,
                })
                await self.event_bus.publish("tts_speak", {
                    "text": f"Breakthrough in {paper.domain}: {summary}",
                })
                logger.info(
                    f"[BreakthroughDetector] BREAKTHROUGH: '{paper.title[:60]}' "
                    f"score={score:.2f}"
                )

    # ── Scoring ───────────────────────────────────────────────────────────

    async def _score_paper(self, paper: Paper) -> tuple[float, Dict[str, float]]:
        """
        Score a paper across 4 signals. Returns (total_score, signals_dict).
        """
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower()

        # Signal 1 — Title keywords (weight 0.25)
        signal_words = getattr(self.settings, "high_signal_words", [
            "first demonstration", "surpasses human", "world record",
            "breakthrough", "novel approach", "outperforms",
            "state-of-the-art", "exceeds", "first ever", "previously impossible",
        ])
        matches = sum(1 for w in signal_words if w.lower() in title_lower)
        kw_score = min(matches * 0.08, 0.25)

        # Signal 2 — Quantified improvement (weight 0.25)
        quant_score = self._score_quantified_improvement(paper.abstract)
        quant_score = min(quant_score, 0.25)

        # Signal 3 — Source prestige (weight 0.20)
        prestige_score = self._score_prestige(paper)
        prestige_score = min(prestige_score, 0.20)

        # Signal 4 — Ollama impact rating (weight 0.30)
        llm_score = await self._score_llm_impact(paper.abstract)
        llm_score = min(llm_score, 0.30)

        total = kw_score + quant_score + prestige_score + llm_score
        return total, {
            "kw": round(kw_score, 3),
            "quant": round(quant_score, 3),
            "prestige": round(prestige_score, 3),
            "llm": round(llm_score, 3),
        }

    def _score_quantified_improvement(self, abstract: str) -> float:
        """Score based on quantified improvement patterns in abstract."""
        patterns = [
            r"(\d+\.?\d*)[x×]\s*(faster|better|improvement)",
            r"(\d+\.?\d*)%\s*(improvement|increase|reduction)",
            r"(\d+\.?\d*)\s*times\s*(more|faster|better)",
        ]

        max_mag = 0.0
        for pattern in patterns:
            for match in re.finditer(pattern, abstract, re.IGNORECASE):
                try:
                    val = float(match.group(1))
                    if "x" in match.group(0).lower() or "times" in match.group(0).lower():
                        max_mag = max(max_mag, val)
                    else:  # percentage
                        max_mag = max(max_mag, val / 100.0)
                except ValueError:
                    continue

        # Score proportional to magnitude, capped
        if max_mag >= 100:
            return 0.25
        elif max_mag >= 10:
            return 0.20
        elif max_mag >= 2:
            return 0.15
        elif max_mag >= 1.2:
            return 0.08
        return 0.0

    def _score_prestige(self, paper: Paper) -> float:
        """Score based on whether paper appears in a high-impact source."""
        high_impact = getattr(self.settings, "high_impact_sources", [
            "Nature", "Science", "Cell", "NeurIPS", "ICML", "ICLR",
            "CVPR", "ACL", "IEEE", "PNAS", "Physical Review Letters", "The Lancet",
        ])
        combined = f"{paper.url} {paper.source}".lower()
        for source in high_impact:
            if source.lower() in combined:
                return 0.20
        return 0.0

    async def _score_llm_impact(self, abstract: str) -> float:
        """Ask Ollama to rate the abstract's scientific impact."""
        if not HTTPX_AVAILABLE or not self._client:
            return 0.15  # neutral default

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = (
            f"Rate the potential scientific impact of this abstract from 0.0 to 1.0. "
            f"Consider: novelty, practical implications, and advancement of the field.\n\n"
            f"Abstract: {abstract[:600]}\n\n"
            f"Reply with ONLY a float between 0.0 and 1.0."
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "0.5")

            match = re.search(r"([0-9]*\.?[0-9]+)", raw.replace(",", "."))
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score)) * 0.30  # scaled to weight
        except Exception as e:
            logger.debug(f"[BreakthroughDetector] LLM scoring failed: {e}")

        return 0.15  # neutral default

    async def _summarise_breakthrough(self, paper: Paper) -> str:
        """Generate a 2-sentence summary of a breakthrough paper."""
        if not HTTPX_AVAILABLE or not self._client:
            # Fallback: truncate abstract
            sentences = paper.abstract.split(".")
            return ". ".join(s.strip() for s in sentences[:2] if s.strip()) + "."

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = (
            f"Summarise this paper in exactly 2 sentences for a scientifically literate "
            f"audience. Be specific about what was achieved and why it matters.\n\n"
            f"Abstract: {paper.abstract[:800]}"
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "(no summary generated)").strip()
        except Exception as e:
            logger.warning(f"[BreakthroughDetector] Summary failed: {e}")
            sentences = paper.abstract.split(".")
            return ". ".join(s.strip() for s in sentences[:2] if s.strip()) + "."
