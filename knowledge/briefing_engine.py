"""
deep/knowledge/briefing_engine.py

Generates daily spoken science briefings from the knowledge store.
Triggered on a schedule (config.BRIEFING_TIME) or on-demand via
"generate_briefing" EventBus events.

Architecture:
    generate_briefing(domains, days_back)
        ├── For each domain: get_recent() → _summarise_domain()
        └── Final stitch: one Ollama call for polished briefing text
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
# Briefing dataclass
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Briefing:
    domain_sections: Dict[str, str] = field(default_factory=dict)
    full_text: str = ""
    paper_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    top_papers: List[Paper] = field(default_factory=list)
    duration_estimate_seconds: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# BriefingEngine
# ═══════════════════════════════════════════════════════════════════════════════

class BriefingEngine:
    """
    Generates daily science briefings and publishes them on the EventBus.
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
            self._client = httpx.AsyncClient(timeout=60.0)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to on-demand generation events and start scheduler."""
        self.event_bus.subscribe("generate_briefing", self._on_generate_request)
        self._started = True
        # Start background scheduler
        asyncio.create_task(self._scheduler_loop())
        logger.info("[BriefingEngine] Started")

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._started = False
        logger.info("[BriefingEngine] Stopped")

    def status(self) -> Dict[str, Any]:
        return {"started": self._started}

    # ── Scheduler ─────────────────────────────────────────────────────────

    async def _scheduler_loop(self) -> None:
        """Run generate_briefing() at config.BRIEFING_TIME daily."""
        briefing_time = getattr(self.settings, "briefing_time", "06:00")

        while self._started:
            try:
                now = datetime.now(timezone.utc)
                target = datetime.strptime(briefing_time, "%H:%M").time()
                target_dt = datetime.combine(now.date(), target).replace(tzinfo=timezone.utc)
                if target_dt <= now:
                    target_dt += timedelta(days=1)

                wait_seconds = (target_dt - now).total_seconds()
                logger.info(f"[BriefingEngine] Next briefing at {target_dt.isoformat()} "
                            f"(in {wait_seconds/3600:.1f} hours)")
                await asyncio.sleep(wait_seconds)

                if self._started:
                    await self.generate_briefing()
            except Exception as e:
                logger.error(f"[BriefingEngine] Scheduler error: {e}")
                await asyncio.sleep(300)  # retry in 5 min

    # ── Event handler ─────────────────────────────────────────────────────

    async def _on_generate_request(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Handle on-demand briefing requests."""
        domains = payload.get("domains")
        days_back = payload.get("days_back", 1)
        await self.generate_briefing(domains=domains, days_back=days_back)

    # ── Main API ──────────────────────────────────────────────────────────

    async def generate_briefing(
        self,
        domains: Optional[List[str]] = None,
        days_back: int = 1,
    ) -> Briefing:
        """
        Generate a science briefing from recent papers.

        Args:
            domains: List of domains to include. Uses config.INGEST_DOMAINS if None.
            days_back: How many days back to look for papers.

        Returns:
            Briefing object with full_text, domain_sections, etc.
        """
        if not self.knowledge_store._started:
            logger.warning("[BriefingEngine] KnowledgeStore not started")
            return Briefing(full_text="(KnowledgeStore unavailable)")

        if domains is None:
            domains = getattr(self.settings, "ingest_domains", [
                "ai_ml", "physics", "cybersecurity", "space", "robotics", "quantum",
            ])

        # Concurrently fetch + summarise each domain
        sem = asyncio.Semaphore(4)

        async def _summarise_domain_with_sem(domain: str):
            async with sem:
                return domain, await self._summarise_domain(domain, days_back)

        domain_results = await asyncio.gather(
            *[_summarise_domain_with_sem(d) for d in domains],
            return_exceptions=True,
        )

        domain_sections: Dict[str, str] = {}
        all_top_papers: List[Paper] = []
        total_papers = 0

        for result in domain_results:
            if isinstance(result, Exception):
                logger.warning(f"[BriefingEngine] Domain summarisation error: {result}")
                continue
            domain, (section_text, papers) = result
            if section_text:
                domain_sections[domain] = section_text
                total_papers += len(papers)
                all_top_papers.extend(papers)

        if not domain_sections:
            logger.info("[BriefingEngine] No papers found — skipping briefing")
            return Briefing(
                full_text="No new papers found for briefing.",
                paper_count=0,
            )

        # Final stitch: one Ollama call for polished text
        sections_text = "\n\n".join(
            f"--- {dom.upper()} ---\n{text}"
            for dom, text in domain_sections.items()
        )

        full_text = await self._generate_final_briefing(sections_text)

        # Estimate duration: ~150 words per minute, ~2.5 words/sec
        word_count = len(full_text.split())
        duration_estimate = int(word_count / 2.5)

        briefing = Briefing(
            domain_sections=domain_sections,
            full_text=full_text,
            paper_count=total_papers,
            top_papers=all_top_papers[:10],
            duration_estimate_seconds=duration_estimate,
        )

        # Publish events
        await self.event_bus.publish("briefing_ready", {
            "full_text": briefing.full_text,
            "paper_count": briefing.paper_count,
            "domain_count": len(domain_sections),
            "duration_estimate_seconds": briefing.duration_estimate_seconds,
        })

        logger.info(
            f"[BriefingEngine] Briefing generated: {briefing.paper_count} papers, "
            f"{len(domain_sections)} domains, ~{duration_estimate}s spoken"
        )
        return briefing

    # ── Internal methods ────────────────────────────────────────────────

    async def _summarise_domain(self, domain: str, days_back: int) -> tuple[str, List[Paper]]:
        """
        Fetch recent papers for a domain and summarise them.
        Returns (section_text, papers_list).
        """
        papers = await self.knowledge_store.get_recent(
            domain=domain, days=days_back, n=4,
        )
        if not papers:
            return "", []

        if not HTTPX_AVAILABLE or not self._client:
            # Simple concatenation fallback
            titles = [f"- {p.title}" for p in papers]
            return f"Recent {domain} papers:\n" + "\n".join(titles), papers

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        titles_and_abstracts = "\n".join(
            f"Title: {p.title}\nAbstract: {p.abstract[:250]}"
            for p in papers
        )

        prompt = (
            f"Summarise these {domain} papers in 2-3 sentences, "
            f"focusing on the most significant finding.\n\n"
            f"{titles_and_abstracts}"
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
            return data.get("response", "").strip(), papers
        except Exception as e:
            logger.warning(f"[BriefingEngine] Domain summary failed for {domain}: {e}")
            titles = [f"- {p.title}" for p in papers]
            return f"Recent {domain} papers:\n" + "\n".join(titles), papers

    async def _generate_final_briefing(self, sections_text: str) -> str:
        """One Ollama call to stitch domain sections into a polished briefing."""
        if not HTTPX_AVAILABLE or not self._client:
            return sections_text

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        system_prompt = (
            "You are DEEP, an advanced intelligence system with deep scientific knowledge. "
            "Your tone is precise, direct, and genuinely engaged with the science — "
            "like a knowledgeable colleague sharing what they found exciting today, "
            "not a news anchor reading headlines."
        )

        prompt = (
            f"Create a spoken morning briefing from these research sections. "
            f"Highlight what is genuinely surprising or significant. "
            f"Target: 60-90 seconds when spoken aloud (~150-225 words).\n\n"
            f"{sections_text}"
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "system": system_prompt,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.4},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", sections_text).strip()
        except Exception as e:
            logger.warning(f"[BriefingEngine] Final briefing generation failed: {e}")
            return sections_text
