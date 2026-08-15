"""Knowledge graph endpoints (Memory Vault).

Every handler used to end in `except Exception: return {"error": str(e)}`, so a
bug in the vault and a graph with nothing in it reached the HUD identically —
as a 200. There is no exception handling left here at all: real failures reach
the app's 500 handler, which logs them.

The optional layers — semantic similarity, NetworkX analytics, the GNN — do
still degrade rather than fail, because a default install has none of their
dependencies. That behaviour moved to `core/graph_vault.py`, where it can say
*which* layer was skipped and why instead of being indistinguishable from a
swallowed bug. Callers get a `degraded` map, the same convention the OSINT
dossier already uses.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core import graph_vault
from interface.deps import require

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _graph():
    return require("knowledge_graph")


def _entity_or_404(name: str) -> Dict[str, Any]:
    entity = _graph().get_entity(name)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"no entity named '{name}'")
    return entity


# ── reads ────────────────────────────────────────────────────────────────────


@router.get("/stats")
async def knowledge_stats():
    """Get knowledge graph statistics."""
    return _graph().get_stats()


@router.get("/entities")
async def knowledge_entities():
    """Get all entities."""
    return {"entities": _graph().get_all_entities()}


@router.get("/entity/{name}")
async def knowledge_entity(name: str):
    """Get entity by name."""
    entity = _entity_or_404(name)
    return {"entity": entity, "neighbors": _graph().get_neighbors(name)}


@router.get("/neighbors/{name}")
async def knowledge_neighbors(name: str):
    """Get neighbors of an entity."""
    _entity_or_404(name)
    return {"neighbors": _graph().get_neighbors(name)}


@router.get("/paths")
async def knowledge_paths(
    source: str = Query(..., min_length=1, max_length=200),
    target: str = Query(..., min_length=1, max_length=200),
    max_depth: int = Query(3, ge=1, le=6),
):
    """Find paths between two entities."""
    graph = _graph()
    for name in (source, target):
        if graph.get_entity(name) is None:
            # "no path" and "you named something the graph has never heard of"
            # are different answers, and only one of them is about the graph.
            raise HTTPException(status_code=404, detail=f"no entity named '{name}'")
    return {"paths": graph.find_paths(source, target, max_depth)}


@router.get("/search")
async def knowledge_search(q: str = Query(..., min_length=1, max_length=200)):
    """Search entities."""
    return {"results": _graph().search(q)}


@router.get("/semantic_search")
async def knowledge_semantic_search(
    q: str = Query(..., min_length=1, max_length=200),
    k: int = Query(8, ge=1, le=100),
):
    """Embedding-based entity lookup — finds entities by meaning, not substring.

    This is what the brain should use to pull a relevant memory slice into
    context.
    """
    return {"results": _graph().semantic_search(q, k=k)}


@router.get("/recent")
async def knowledge_recent(limit: int = Query(10, ge=1, le=200)):
    """Get recently added entities."""
    return {"entities": _graph().get_recent_entities(limit)}


@router.get("/inferences")
async def knowledge_inferences(
    limit: int = Query(8, ge=1, le=50),
    connections: bool = True,
):
    """Proactive inferences derived from the graph: habits, hubs, stale facts, and
    (optionally) GNN-predicted connections — the JARVIS 'you usually…' layer."""
    from core.graph_inference import infer, infer_connections

    graph = _graph()
    items = infer(graph, max_items=limit)
    degraded: Dict[str, str] = {}

    if connections:
        entities = graph.get_all_entities()
        relationships = graph.get_all_relationships(limit=400)
        entities, similarity, reason = await graph_vault.add_similarity_edges(
            entities, relationships
        )
        if reason:
            degraded["semantic"] = reason
        result, reason = await graph_vault.predict_links(
            entities, relationships + similarity, epochs=40
        )
        if reason:
            degraded["gnn"] = reason
        if result.get("predicted_links"):
            items += infer_connections(graph, result["predicted_links"], limit=4)

    return {"inferences": items, "degraded": degraded}


@router.get("/vault")
async def knowledge_vault(
    q: str = "",
    limit: int = Query(200, ge=1, le=1000),
    semantic: bool = True,
    analyze: bool = True,
):
    """Full memory snapshot for the Memory Vault: stats + entities + relationships.

    Transparent, editable memory — everything the system has retained, in one
    call. `semantic` adds embedding-similarity edges; `analyze` runs NetworkX
    network science: per-node PageRank, modularity communities, betweenness,
    link-prediction edges and headline metrics. Either can be unavailable on a
    default install, in which case `degraded` names the layer and the reason.
    """
    graph = _graph()
    entities = graph.search(q) if q else graph.get_all_entities()
    entities = sorted(
        entities, key=lambda e: e.get("last_seen", ""), reverse=True
    )[:limit]

    relationships: List[Dict[str, Any]] = graph.get_all_relationships(limit=300)
    for relationship in relationships:
        relationship["kind"] = "relation"   # explicit, extracted relationship

    degraded: Dict[str, str] = {}
    if semantic:
        entities, similarity, reason = await graph_vault.add_similarity_edges(
            entities, relationships
        )
        relationships += similarity
        if reason:
            degraded["semantic"] = reason

    metrics: Dict[str, Any] = {}
    if analyze:
        entities, suggestions, metrics, reason = await graph_vault.add_analytics(
            entities, relationships
        )
        relationships += suggestions
        if reason:
            degraded["analytics"] = reason

    stats = graph.get_stats()
    if metrics:
        stats = {**stats, "graph": metrics}
    return {
        "stats": stats,
        "entities": entities,
        "relationships": relationships,
        "degraded": degraded,
    }


# ── writes ───────────────────────────────────────────────────────────────────


@router.post("/decay")
async def knowledge_decay(prune_below: float = Query(0.08, ge=0.0, le=1.0)):
    """Run a decay sweep: drop relationships whose time-decayed belief has faded
    below the threshold (the graph forgetting what it stopped hearing about)."""
    return {"success": True, **_graph().decay_sweep(prune_below)}


class Retraction(BaseModel):
    source: str = Field(..., min_length=1, max_length=200)
    target: str = Field(..., min_length=1, max_length=200)
    relation: str | None = None
    amount: float = Field(0.5, ge=0.0, le=1.0)


@router.post("/retract")
async def knowledge_retract(body: Retraction):
    """Weaken/remove a contradicted belief."""
    return {
        "success": True,
        **_graph().retract(
            body.source, body.target, relation=body.relation, amount=body.amount
        ),
    }


class Teaching(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)


@router.post("/teach")
async def knowledge_teach(body: Teaching):
    """Ingest free text into the knowledge graph via the LLM extractor.

    NOTE: path is /teach, not /ingest — the latter is taken by the app-level PDF
    upload endpoint (`@app.post('/api/knowledge/ingest')`), which would shadow
    this.
    """
    return {"success": True, "result": await _graph().ingest_llm(body.text)}


@router.post("/prune")
async def knowledge_prune():
    """Remove legacy junk entities (sentence-openers, fragments) the regex left."""
    return {"success": True, **_graph().prune_noise()}


@router.post("/reextract")
async def knowledge_reextract(
    limit: int = Query(60, ge=1, le=500),
    prune: bool = True,
):
    """Rebuild graph quality from stored conversations: prune legacy noise, then
    replay up to `limit` stored conversation memories through the LLM extractor
    in the background."""
    graph = _graph()
    if not getattr(graph, "extractor", None):
        raise HTTPException(
            status_code=503,
            detail="no LLM extractor is wired — re-extraction needs one",
        )

    pruned = graph.prune_noise() if prune else {"pruned": 0}
    collection = getattr(require("ltm"), "_collection", None)
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="conversation memory is unavailable, so there is nothing to replay",
        )

    stored = collection.get(where={"memory_type": "conversation"}, limit=limit)
    texts = [
        t for t in (stored.get("documents") or [])
        if t and len(t.strip()) > 24
    ][:limit]

    asyncio.create_task(graph_vault.replay_conversations(graph, texts))
    return {
        "success": True,
        "pruned": pruned.get("pruned", 0),
        "replaying": len(texts),
        "note": "re-extraction running in background",
    }


@router.post("/gnn")
async def knowledge_gnn(epochs: int = Query(60, ge=1, le=1000)):
    """Train a GraphSAGE GNN (CPU) on the memory graph and return predicted
    missing links plus learned-embedding clusters."""
    graph = _graph()
    entities = graph.get_all_entities()
    relationships = graph.get_all_relationships(limit=400)

    # Explicit relations alone are far too sparse to message-pass over.
    entities, similarity, _ = await graph_vault.add_similarity_edges(
        entities, relationships
    )
    result, reason = await graph_vault.predict_links(
        entities, relationships + similarity, epochs
    )
    if reason:
        # A missing dependency or a graph too small to train on is a fact about
        # this deployment, not a bug — and not a success either.
        raise HTTPException(status_code=503, detail=reason)
    return {"success": True, **graph_vault.name_predicted_links(result, entities)}


@router.delete("/entity/{name}")
async def knowledge_forget(name: str):
    """Forget (delete) an entity and its relationships — Memory Vault editing."""
    if not _graph().forget(name):
        # forget() returns False for a name it has never held, which came back
        # as {"success": false} at 200 — a successful call with a falsy field.
        raise HTTPException(status_code=404, detail=f"no entity named '{name}'")
    return {"success": True, "forgotten": name}
