"""
core/graph_inference.py — turn the memory graph into proactive INFERENCES.

The graph already stores facts and (via graph_gnn / graph_analytics) predicts
missing links. This module is the layer that was promised in knowledge_graph's
own docstring but never built: deriving human-readable, actionable inferences a
JARVIS-class assistant would volunteer —

  • HABIT      — "You usually use Python for coding."        (strong, fresh edges)
  • CONNECTION — "Python and FastAPI seem related."          (GNN/analytics link-pred)
  • STALE      — "You haven't touched Project X in a while." (decayed beliefs)
  • HUB        — "AI is central to a lot of what you do."     (high PageRank/degree)

Everything is fail-soft and read-only over the graph. `infer()` returns a ranked
list of {type, text, score, subjects}. The brain can fold these into context, and
the proactive layer can surface the top one as a toast.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Relation → natural verb phrase for readable habit lines.
_VERB = {
    "uses": "uses", "likes": "likes", "prefers": "prefers", "works_on": "is working on",
    "learns": "is learning", "builds": "is building", "studies": "is studying",
    "knows": "knows", "created": "created", "has": "has",
}


def _name(entities: Dict[str, dict], eid: str) -> Optional[str]:
    e = entities.get(eid)
    return e.get("name") if e else None


def infer(kg, max_items: int = 8) -> List[Dict[str, Any]]:
    """Derive proactive inferences from the live KnowledgeGraph instance `kg`.

    Pure read over kg's public surface + effective_confidence; never mutates.
    """
    out: List[Dict[str, Any]] = []
    try:
        ent_by_id = {e["id"]: e for e in kg.get_all_entities()}
        now = datetime.utcnow()

        # ── HABIT: strong, recency-weighted relationships ────────────────────
        scored = []
        for rel in kg.relationships.values():
            eff = kg.effective_confidence(rel, now)
            if eff < 0.25:
                continue
            s, t = _name(ent_by_id, rel.source), _name(ent_by_id, rel.target)
            if not s or not t:
                continue
            verb = _VERB.get(rel.relation.value, rel.relation.value.replace("_", " "))
            scored.append((eff, {
                "type": "habit",
                "text": f"{s} {verb} {t}.",
                "score": round(eff, 3),
                "subjects": [s, t],
            }))
        scored.sort(key=lambda x: x[0], reverse=True)
        out.extend(item for _, item in scored[:max_items])

        # ── HUB: most-connected entities (degree centrality, cheap) ──────────
        try:
            hubs = kg._get_most_connected(3)
            for h in hubs:
                if h.get("connections", 0) >= 3:
                    out.append({
                        "type": "hub",
                        "text": f"{h['name']} is central to a lot of what you do "
                                f"({h['connections']} connections).",
                        "score": round(min(1.0, h["connections"] / 10.0), 3),
                        "subjects": [h["name"]],
                    })
        except Exception:
            pass

        # ── STALE: meaningful but faded beliefs (gentle nudges) ──────────────
        stale = []
        for rel in kg.relationships.values():
            eff = kg.effective_confidence(rel, now)
            age_days = (now - rel.last_seen).total_seconds() / 86400.0
            if 0.05 < eff < 0.18 and age_days > 30:
                s, t = _name(ent_by_id, rel.source), _name(ent_by_id, rel.target)
                if s and t:
                    stale.append((age_days, {
                        "type": "stale",
                        "text": f"You haven't mentioned {t} (with {s}) in a while — "
                                f"still relevant?",
                        "score": round(eff, 3),
                        "subjects": [s, t],
                    }))
        stale.sort(key=lambda x: x[0], reverse=True)
        out.extend(item for _, item in stale[:2])

    except Exception as e:  # noqa: BLE001
        logger.warning(f"[graph_inference] infer failed: {e}")
    return out[: max_items + 5]


def infer_connections(kg, predicted_links: List[Dict[str, Any]],
                      limit: int = 4) -> List[Dict[str, Any]]:
    """Wrap GNN/analytics predicted links as readable CONNECTION inferences.

    `predicted_links` is what /gnn or graph_analytics returns (with source_name/
    target_name resolved, or raw ids we resolve here).
    """
    out: List[Dict[str, Any]] = []
    try:
        ent_by_id = {e["id"]: e for e in kg.get_all_entities()}
        for p in predicted_links[:limit]:
            s = p.get("source_name") or _name(ent_by_id, p.get("source", ""))
            t = p.get("target_name") or _name(ent_by_id, p.get("target", ""))
            if not s or not t:
                continue
            out.append({
                "type": "connection",
                "text": f"{s} and {t} seem related — want me to link them?",
                "score": round(float(p.get("score", 0.5)), 3),
                "subjects": [s, t],
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[graph_inference] infer_connections failed: {e}")
    return out
