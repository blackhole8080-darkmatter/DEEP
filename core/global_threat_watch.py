"""
core/global_threat_watch.py

Bridges global cybersecurity signal (CISA KEV — actively-exploited CVEs) into
the same knowledge graph WorldModel already reads from, so DEEP can connect
"a CVE was disclosed today" to "you use that project/tool" — the
personal-memory + world-events correlation from the project's new direction.

How it works: periodically pull the KEV feed (core/intel_feeds.py), and for
each entry, keyword-match its vendor/product against the *existing* knowledge
graph entities (core/knowledge_graph.py — things DEEP already knows Aryan
works with, extracted from conversation). On a match, publish
`world_threat_match` on the bus and record a short note via
WorldModel.add_world_alert() so it surfaces in the next chat system prompt.

Deliberately keyword-level, not authoritative vulnerability scanning: a KG
entity named "Docker" matching a KEV entry for vendorProject "Docker" is a
plausible, worth-surfacing signal, not a confirmed "you are vulnerable"
claim — the alert text is phrased that way on purpose.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Generic words that shouldn't trigger a match on their own even though they
# might appear in both a KG entity name and a KEV vendor/product string.
_STOPWORDS = {
    "app", "apps", "system", "systems", "software", "server", "service",
    "web", "cloud", "the", "and", "for", "project", "tool", "platform",
}


class GlobalThreatWatch:
    def __init__(
        self,
        event_bus: Any,
        knowledge_graph: Any,
        world_model: Any,
        intel_feeds: Any,
        interval_s: int = 6 * 3600,
    ) -> None:
        self.event_bus = event_bus
        self.knowledge_graph = knowledge_graph
        self.world_model = world_model
        self.intel_feeds = intel_feeds
        self.interval_s = interval_s
        self._task: Optional[asyncio.Task] = None
        self._started = False
        self._last_matched_cve_ids: Set[str] = set()

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._task = asyncio.create_task(self._loop())
        logger.info("GlobalThreatWatch started")

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        await asyncio.sleep(60)  # let boot settle
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.warning(f"[global_threat_watch] cycle failed: {e}")
            await asyncio.sleep(self.interval_s)

    # ── core cycle (also callable directly, e.g. from tests / a manual trigger) ──

    async def run_once(self) -> List[Dict[str, Any]]:
        entities = self._get_kg_entities()
        if not entities:
            return []

        # (fetcher, source_label, alert_phrasing). OTX pulses are opt-in —
        # fetch_otx_pulses() itself no-ops to [] without OTX_API_KEY, so this
        # stays free to run even if the user hasn't configured it yet.
        sources = [
            (self.intel_feeds.fetch_kev, "CISA KEV",
             lambda entity: f"actively exploited — relates to '{entity}', which you've worked with. Worth checking exposure."),
            (self.intel_feeds.fetch_otx_pulses, "OTX pulse",
             lambda entity: f"a threat-intel pulse mentions '{entity}', which you've worked with. Worth a look."),
        ]

        matches: List[Dict[str, Any]] = []
        for fetcher, source_label, phrase in sources:
            items = await fetcher()
            matches.extend(await self._process_items(items, source_label, phrase, entities))

        # Keep the seen-set from growing unbounded across a long-running process.
        if len(self._last_matched_cve_ids) > 500:
            self._last_matched_cve_ids = set(list(self._last_matched_cve_ids)[-250:])

        return matches

    async def _process_items(self, items, source_label: str, phrase, entities: List[str]) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for item in items:
            hit_entity = self._match_entity(item, entities)
            if not hit_entity:
                continue
            key = f"{source_label}:{item.item_id}:{hit_entity}"
            if key in self._last_matched_cve_ids:
                continue
            self._last_matched_cve_ids.add(key)

            match = {
                "source": source_label,
                "cve_id": item.item_id,
                "title": item.title,
                "url": item.url,
                "matched_entity": hit_entity,
                "published": item.published,
            }
            matches.append(match)

            await self.event_bus.publish("world_threat_match", match)
            self.world_model.add_world_alert(f"{source_label}: {item.item_id} — {phrase(hit_entity)}")
            logger.info(f"[global_threat_watch] {source_label} {item.item_id} matched KG entity '{hit_entity}'")
        return matches

    # ── matching ────────────────────────────────────────────────────────────

    def _get_kg_entities(self) -> List[str]:
        try:
            ents = self.knowledge_graph.get_all_entities()
        except Exception as e:
            logger.debug(f"[global_threat_watch] KG read failed: {e}")
            return []
        names = []
        for e in ents:
            name = (e.get("name") or "").strip()
            if len(name) >= 3 and name.lower() not in _STOPWORDS:
                names.append(name)
        return names

    @staticmethod
    def _match_entity(item: Any, entities: List[str]) -> Optional[str]:
        haystack = f"{item.title} {item.summary}".lower()
        for name in entities:
            pattern = r"\b" + re.escape(name.lower()) + r"\b"
            if re.search(pattern, haystack):
                return name
        return None
