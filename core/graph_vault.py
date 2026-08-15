"""Optional enrichment layers over the knowledge graph.

The Memory Vault answers with entities and relationships. On top of that it can
add semantic-similarity edges, NetworkX analytics (PageRank, communities,
betweenness, link prediction) and GNN-predicted links — each of which needs a
heavy optional dependency that a default install does not have.

That optionality is the whole reason this module exists. It used to live inline
in the router as `try: … except Exception: pass`, which reads identically to the
blanket catches that were hiding real bugs everywhere else in the codebase. The
difference is real but invisible at the call site: enrichment failing means the
vault renders without an extra layer, not that the request failed.

So the distinction is made explicit here instead. Every function returns its
input unchanged when its dependency is missing, says so in ``degraded``, and
logs once — and the router keeps no exception handling at all, so a genuine bug
in it still reaches the app's 500 handler and gets logged like anything else.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


async def add_similarity_edges(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """Embedding-similarity edges. Returns (entities, extra_edges, degraded_reason).

    Explicit extracted relations alone are far too sparse to message-pass over,
    which is why the GNN path wants these too.
    """
    try:
        from core.graph_enrich import enrich
    except ImportError as exc:
        return entities, [], f"semantic enrichment unavailable: {exc}"

    # Only edges whose endpoints are both in the returned slice, or enrichment
    # scores against entities the caller never asked for.
    ids = {e.get("id") for e in entities}
    scoped = [
        r for r in relationships
        if r.get("source") in ids and r.get("target") in ids
    ]
    try:
        enriched, similarity = await asyncio.to_thread(enrich, entities, scoped)
    except Exception as exc:  # noqa: BLE001 - an optional layer, see module docstring
        logger.warning("[vault] semantic enrichment skipped: %s", exc)
        return entities, [], f"semantic enrichment failed: {exc}"
    return enriched, list(similarity or []), ""


async def add_analytics(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], str]:
    """PageRank, communities, betweenness and link prediction, annotated in place.

    Returns (entities, suggested_edges, metrics, degraded_reason).
    """
    try:
        from core.graph_analytics import analyze as graph_analyze
    except ImportError as exc:
        return entities, [], {}, f"graph analytics unavailable: {exc}"

    try:
        result = await asyncio.to_thread(graph_analyze, entities, relationships)
    except Exception as exc:  # noqa: BLE001 - an optional layer, see module docstring
        logger.warning("[vault] analytics skipped: %s", exc)
        return entities, [], {}, f"graph analytics failed: {exc}"

    if not result:
        return entities, [], {}, "graph analytics returned nothing (graph too small?)"

    pagerank = result.get("pagerank") or {}
    community = result.get("community") or {}
    betweenness = result.get("betweenness") or {}
    for entity in entities:
        entity_id = entity.get("id")
        entity["pagerank"] = round(pagerank.get(entity_id, 0.0), 5)
        entity["betweenness"] = round(betweenness.get(entity_id, 0.0), 4)
        if entity_id in community:
            entity["community"] = community[entity_id]

    suggestions = list(result.get("suggestions") or [])
    return entities, suggestions, result.get("metrics") or {}, ""


async def predict_links(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    epochs: int = 60,
) -> Tuple[Dict[str, Any], str]:
    """Train the GraphSAGE model and return its output. (result, degraded_reason)."""
    try:
        from core.graph_gnn import run_gnn
    except ImportError as exc:
        return {}, f"GNN unavailable: {exc}"

    try:
        result = await asyncio.to_thread(run_gnn, entities, relationships, epochs)
    except Exception as exc:  # noqa: BLE001 - an optional layer, see module docstring
        logger.warning("[vault] GNN skipped: %s", exc)
        return {}, f"GNN failed: {exc}"
    if not result:
        return {}, "GNN produced no result — torch missing, or the graph is too small"
    return result, ""


def name_predicted_links(
    result: Dict[str, Any], entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Resolve entity ids to names so predicted links are readable."""
    names = {e["id"]: e.get("name", "?") for e in entities if e.get("id")}
    for link in result.get("predicted_links") or []:
        link["source_name"] = names.get(link.get("source"), link.get("source"))
        link["target_name"] = names.get(link.get("target"), link.get("target"))
    return result


async def replay_conversations(graph: Any, texts: List[str]) -> Dict[str, int]:
    """Re-ingest stored conversations through the LLM extractor.

    One unparseable memory must not abort the other fifty-nine, so failures are
    tolerated — but counted and logged rather than passed over in silence,
    which is the difference between batch tolerance and a swallowed bug.
    """
    succeeded = failed = 0
    for text in texts:
        try:
            await graph.ingest_llm(text, source_id="reextract")
        except Exception as exc:  # noqa: BLE001 - see docstring
            failed += 1
            logger.warning("[reextract] one memory failed to re-ingest: %s", exc)
        else:
            succeeded += 1
    if failed:
        logger.warning("[reextract] finished with %d/%d failures", failed, len(texts))
    return {"succeeded": succeeded, "failed": failed}
