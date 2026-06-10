"""
core/entity_extractor.py — LLM-based knowledge extraction for the memory graph.

Replaces the legacy capitalized-word regex (which turned sentence-openers like
"Also"/"Right" and fragments like "Hey Ar" into "entities", with 93% dumped into
`concept`). Here DEEP's own LLM reads a passage and returns clean, typed,
canonically-named entities — each with a one-line fact — plus the relationships
between them. This is how modern memory systems (GraphRAG, mem0, Zep) build a
knowledge graph.

Decoupled by design: the caller injects an async `generate(system, user)` fn, so
this module never imports a provider. Fail-soft: on any error returns empty, and
the graph's regex path remains as the fallback.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)

GenerateFn = Callable[[str, str], Awaitable[str]]

VALID_TYPES = {
    "person", "technology", "topic", "project", "place",
    "organization", "preference", "action", "concept", "unknown",
}
VALID_RELATIONS = {
    "likes", "uses", "knows", "created", "works_on", "located_in",
    "related_to", "mentioned_in", "prefers", "learns", "builds",
    "studies", "has", "is_a",
}

# Obvious non-entities the model occasionally emits; dropped as a safety net.
_STOP = {
    "i", "me", "my", "you", "your", "it", "this", "that", "the", "a", "an",
    "also", "right", "well", "okay", "ok", "yes", "no", "hey", "hi", "hello",
    "thing", "things", "stuff", "something", "anything", "next", "steps", "step",
}

_SYSTEM = (
    "You are a precise knowledge-graph extractor. From the user's text, extract "
    "the real entities (people, technologies, topics, projects, places, "
    "organizations, preferences, concepts) and the relationships between them.\n"
    "Rules:\n"
    "- Use a canonical name for each entity (e.g. 'Aryan', not 'hey aryan'; "
    "'Python', not 'python3'). Merge first-person references (I/me/my) to 'Aryan'.\n"
    "- Skip pronouns, filler words, sentence-openers, and vague fragments.\n"
    f"- type MUST be one of: {', '.join(sorted(VALID_TYPES))}.\n"
    f"- relation MUST be one of: {', '.join(sorted(VALID_RELATIONS))}.\n"
    "- Give each entity a concise 'description' (one factual clause, <=120 chars).\n"
    "- Only assert relationships actually supported by the text.\n"
    "Respond with STRICT JSON only, no prose, in exactly this shape:\n"
    '{"entities":[{"name":"","type":"","aliases":[],"description":""}],'
    '"relationships":[{"source":"","target":"","relation":"","evidence":""}]}'
)


def _coerce_json(raw: str) -> Dict[str, Any]:
    """Pull a JSON object out of an LLM response (handles ```json fences / prose)."""
    if not raw:
        return {}
    s = raw.strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    # Fall back to the outermost {...} span.
    a, b = s.find("{"), s.rfind("}")
    if a != -1 and b != -1 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            return {}
    return {}


class LLMEntityExtractor:
    def __init__(self, generate: GenerateFn):
        self._generate = generate

    async def extract(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        text = (text or "").strip()
        if len(text) < 3:
            return {"entities": [], "relationships": []}
        try:
            raw = await self._generate(_SYSTEM, f"Text:\n{text}\n\nJSON:")
            data = _coerce_json(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[entity_extractor] generate/parse failed: {e}")
            return {"entities": [], "relationships": []}

        return {
            "entities": self._clean_entities(data.get("entities", [])),
            "relationships": self._clean_relationships(data.get("relationships", [])),
        }

    # ── normalisation ────────────────────────────────────────────────────────
    def _clean_entities(self, ents: Any) -> List[Dict[str, Any]]:
        out, seen = [], set()
        if not isinstance(ents, list):
            return out
        for e in ents:
            if not isinstance(e, dict):
                continue
            name = str(e.get("name", "")).strip()
            if not name or len(name) < 2:
                continue
            low = name.lower()
            if low in _STOP or low in seen:
                continue
            t = str(e.get("type", "concept")).strip().lower()
            if t not in VALID_TYPES:
                t = "concept"
            aliases = [str(a).strip() for a in (e.get("aliases") or []) if str(a).strip()]
            desc = str(e.get("description", "")).strip()[:160]
            seen.add(low)
            out.append({"name": name, "type": t, "aliases": aliases, "description": desc})
        return out

    def _clean_relationships(self, rels: Any) -> List[Dict[str, Any]]:
        out = []
        if not isinstance(rels, list):
            return out
        for r in rels:
            if not isinstance(r, dict):
                continue
            s = str(r.get("source", "")).strip()
            t = str(r.get("target", "")).strip()
            rel = str(r.get("relation", "related_to")).strip().lower().replace(" ", "_")
            if not s or not t or s.lower() == t.lower():
                continue
            if rel not in VALID_RELATIONS:
                rel = "related_to"
            out.append({
                "source_name": s, "target_name": t, "relation": rel,
                "evidence": str(r.get("evidence", "")).strip()[:160],
            })
        return out
