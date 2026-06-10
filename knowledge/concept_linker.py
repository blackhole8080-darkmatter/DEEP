"""
deep/knowledge/concept_linker.py

Cross-domain synthesis engine. The most intellectually powerful component in DEEP.

Capabilities:
    - find_connections(concept_a, concept_b) → discovers links between fields
    - explain_concept(concept, depth) → adaptive-depth explanations
    - track_field(domain) → field summaries with themes, open problems, trends
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConnectionResult:
    concept_a: str = ""
    concept_b: str = ""
    connections: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FieldSummary:
    domain: str = ""
    themes: List[str] = field(default_factory=list)
    open_problems: List[str] = field(default_factory=list)
    trending_topics: List[str] = field(default_factory=list)
    notable_papers: List[Paper] = field(default_factory=list)
    paper_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# ConceptLinker
# ═══════════════════════════════════════════════════════════════════════════════

class ConceptLinker:
    """
    Cross-domain synthesis and concept explanation engine.
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
        self._started = True
        logger.info("[ConceptLinker] Started")

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._started = False
        logger.info("[ConceptLinker] Stopped")

    def status(self) -> Dict[str, Any]:
        return {"started": self._started}

    # ── find_connections ──────────────────────────────────────────────────

    async def find_connections(
        self,
        concept_a: str,
        concept_b: str,
    ) -> ConnectionResult:
        """
        Discover conceptual, mathematical, or mechanistic connections
        between two research areas.
        """
        if not self.knowledge_store._started:
            return ConnectionResult(
                concept_a=concept_a,
                concept_b=concept_b,
                connections=["(KnowledgeStore unavailable)"],
            )

        # Concurrent search for both concepts
        papers_a, papers_b = await asyncio.gather(
            self.knowledge_store.search(concept_a, n_results=6),
            self.knowledge_store.search(concept_b, n_results=6),
        )

        summaries_a = "\n".join(
            f"- {p.title}: {p.abstract[:200]}"
            for p in papers_a
        )
        summaries_b = "\n".join(
            f"- {p.title}: {p.abstract[:200]}"
            for p in papers_b
        )

        if not HTTPX_AVAILABLE or not self._client:
            return ConnectionResult(
                concept_a=concept_a,
                concept_b=concept_b,
                connections=["(LLM unavailable — no connections generated)"],
                evidence=[],
                confidence=0.0,
            )

        prompt = (
            f"You are a scientist with expertise across all fields. "
            f"Find genuine conceptual, mathematical, or mechanistic connections "
            f"between these two research areas. Be specific — cite paper titles. "
            f"Do not force connections that do not exist.\n\n"
            f"Papers about '{concept_a}':\n{summaries_a}\n\n"
            f"Papers about '{concept_b}':\n{summaries_b}\n\n"
            f"Format your response as:\n"
            f"CONNECTION: [specific connection description]\n"
            f"EVIDENCE: [paper title(s)]\n"
            f"(repeat for each connection found, max 4)\n"
            f"CONFIDENCE: [0.0-1.0]"
        )

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

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
            raw = data.get("response", "")
        except Exception as e:
            logger.warning(f"[ConceptLinker] find_connections LLM call failed: {e}")
            return ConnectionResult(
                concept_a=concept_a,
                concept_b=concept_b,
                connections=[f"(LLM error: {e})"],
                confidence=0.0,
            )

        # Parse CONNECTION/EVIDENCE/CONFIDENCE blocks
        connections: List[str] = []
        evidence: List[str] = []
        confidence = 0.0

        connection_matches = re.findall(
            r"CONNECTION:\s*(.+?)(?=EVIDENCE:|CONFIDENCE:|$)",
            raw,
            re.DOTALL,
        )
        evidence_matches = re.findall(
            r"EVIDENCE:\s*(.+?)(?=CONNECTION:|CONFIDENCE:|$)",
            raw,
            re.DOTALL,
        )

        for conn in connection_matches[:4]:
            connections.append(conn.strip())
        for ev in evidence_matches[:4]:
            evidence.append(ev.strip())

        conf_match = re.search(r"CONFIDENCE:\s*([0-9]*\.?[0-9]+)", raw)
        if conf_match:
            confidence = max(0.0, min(1.0, float(conf_match.group(1))))

        result = ConnectionResult(
            concept_a=concept_a,
            concept_b=concept_b,
            connections=connections,
            evidence=evidence,
            confidence=round(confidence, 3),
        )

        await self.event_bus.publish("connection_found", {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "connections": connections,
            "confidence": confidence,
        })

        return result

    # ── explain_concept ───────────────────────────────────────────────────

    async def explain_concept(
        self,
        concept: str,
        depth: str = "graduate",
    ) -> str:
        """
        Explain a concept at the requested depth level.
        """
        papers = await self.knowledge_store.search(concept, n_results=8)

        depth_prompts = getattr(self.settings, "explanation_depth_prompts", {
            "accessible": (
                "Explain clearly for a curious non-specialist. Use analogies."
            ),
            "undergraduate": (
                "Assume solid physics/math background. Define jargon."
            ),
            "graduate": (
                "Assume graduate-level knowledge. Use precise terminology. "
                "Mention current open questions."
            ),
            "research": (
                "Assume active researcher. Be rigorous. Cite specific results "
                "from the provided papers. Discuss what remains unsolved."
            ),
        })

        depth_instruction = depth_prompts.get(depth, depth_prompts.get("graduate", ""))

        context = ""
        if papers:
            context = "\n".join(
                f"[{p.domain}] {p.title}: {p.abstract[:300]}"
                for p in papers
            )

        if not HTTPX_AVAILABLE or not self._client:
            if papers:
                return f"Concept: {concept}\n\nRelevant research:\n{context}"
            return f"Concept: {concept}\n(No papers or LLM available for explanation.)"

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = f"Explain: {concept}"
        if context:
            prompt += f"\n\nRelevant research:\n{context}"
        if not papers:
            prompt += "\n\n(Note: No relevant papers found in local knowledge base. "
            prompt += "Provide explanation based on your training knowledge.)"

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "system": depth_instruction,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "(no explanation generated)").strip()
        except Exception as e:
            logger.warning(f"[ConceptLinker] explain_concept failed: {e}")
            if papers:
                return f"Concept: {concept}\n\nRelevant research:\n{context}"
            return f"Concept: {concept}\n(LLM error: {e})"

    # ── track_field ───────────────────────────────────────────────────────

    async def track_field(self, domain: str) -> FieldSummary:
        """
        Generate a summary of a research field from recent papers.
        """
        papers = await self.knowledge_store.get_recent(domain=domain, days=30, n=25)

        if len(papers) < 3:
            return FieldSummary(
                domain=domain,
                themes=["Insufficient data — fewer than 3 papers in the last 30 days"],
                paper_count=len(papers),
            )

        titles_abstracts = "\n".join(
            f"- {p.title}: {p.abstract[:150]}"
            for p in papers
        )

        if not HTTPX_AVAILABLE or not self._client:
            return FieldSummary(
                domain=domain,
                themes=["(LLM unavailable — raw paper list only)"],
                notable_papers=papers[:3],
                paper_count=len(papers),
            )

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = (
            f"Analyse these {domain} papers from the last 30 days. "
            f"Reply ONLY as JSON:\n"
            f"{{\n"
            f'  "themes": [top 5 active research themes],\n'
            f'  "open_problems": [top 3 unsolved questions evident from the papers],\n'
            f'  "trending_topics": [what is getting attention]\n'
            f"}}\n\n"
            f"Papers:\n{titles_abstracts}"
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
            raw = data.get("response", "")

            # Strip markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("\n", 1)[0]
            raw = raw.strip()

            parsed = json.loads(raw)
            summary = FieldSummary(
                domain=domain,
                themes=parsed.get("themes", [])[:5],
                open_problems=parsed.get("open_problems", [])[:3],
                trending_topics=parsed.get("trending_topics", [])[:5],
                notable_papers=sorted(papers, key=lambda p: p.ingested_at, reverse=True)[:3],
                paper_count=len(papers),
            )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[ConceptLinker] track_field JSON parse failed: {e}")
            summary = FieldSummary(
                domain=domain,
                themes=["(JSON parse error — see logs)"],
                paper_count=len(papers),
            )

        await self.event_bus.publish("field_summary_ready", {
            "domain": domain,
            "themes": summary.themes,
            "open_problems": summary.open_problems,
            "paper_count": summary.paper_count,
        })

        return summary
