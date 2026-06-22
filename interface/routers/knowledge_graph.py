"""Knowledge graph endpoints (Memory Vault)."""

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats")
async def knowledge_stats():
    """Get knowledge graph statistics."""
    try:
        return services.knowledge_graph.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/entities")
async def knowledge_entities():
    """Get all entities."""
    try:
        return {"entities": services.knowledge_graph.get_all_entities()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/entity/{name}")
async def knowledge_entity(name: str):
    """Get entity by name."""
    try:
        entity = services.knowledge_graph.get_entity(name)
        if entity:
            return {"entity": entity, "neighbors": services.knowledge_graph.get_neighbors(name)}
        return {"error": "Entity not found"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/neighbors/{name}")
async def knowledge_neighbors(name: str):
    """Get neighbors of an entity."""
    try:
        return {"neighbors": services.knowledge_graph.get_neighbors(name)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/paths")
async def knowledge_paths(source: str, target: str, max_depth: int = 3):
    """Find paths between two entities."""
    try:
        paths = services.knowledge_graph.find_paths(source, target, max_depth)
        return {"paths": paths}
    except Exception as e:
        return {"error": str(e)}


@router.get("/search")
async def knowledge_search(q: str):
    """Search entities."""
    try:
        return {"results": services.knowledge_graph.search(q)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/semantic_search")
async def knowledge_semantic_search(q: str, k: int = 8):
    """Embedding-based entity lookup — finds entities by meaning, not substring.
    This is what the brain should use to pull a relevant memory slice into context."""
    try:
        return {"results": services.knowledge_graph.semantic_search(q, k=k)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/inferences")
async def knowledge_inferences(limit: int = 8, connections: bool = True):
    """Proactive inferences derived from the graph: habits, hubs, stale facts, and
    (optionally) GNN/analytics-predicted connections — the JARVIS 'you usually…' layer."""
    try:
        import asyncio
        from core.graph_inference import infer, infer_connections
        kg = services.knowledge_graph
        items = infer(kg, max_items=limit)
        if connections:
            try:
                entities = kg.get_all_entities()
                rels = kg.get_all_relationships(limit=400)
                from core.graph_enrich import enrich
                ids = {e.get("id") for e in entities}
                scoped = [r for r in rels if r.get("source") in ids and r.get("target") in ids]
                entities, sim = await asyncio.to_thread(enrich, entities, scoped)
                from core.graph_gnn import run_gnn
                res = await asyncio.to_thread(run_gnn, entities, rels + sim, 40)
                if res and res.get("predicted_links"):
                    items += infer_connections(kg, res["predicted_links"], limit=4)
            except Exception:
                pass
        return {"inferences": items}
    except Exception as e:
        return {"error": str(e)}


@router.post("/decay")
async def knowledge_decay(prune_below: float = 0.08):
    """Run a decay sweep: drop relationships whose time-decayed belief has faded
    below the threshold (the graph forgetting what it stopped hearing about)."""
    try:
        return {"success": True, **services.knowledge_graph.decay_sweep(prune_below)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/retract")
async def knowledge_retract(data: dict):
    """Weaken/remove a contradicted belief: {source, target, relation?, amount?}."""
    src, tgt = data.get("source", ""), data.get("target", "")
    if not src or not tgt:
        return {"error": "Need source and target"}
    try:
        return {"success": True, **services.knowledge_graph.retract(
            src, tgt, relation=data.get("relation"), amount=float(data.get("amount", 0.5)))}
    except Exception as e:
        return {"error": str(e)}


@router.post("/teach")
async def knowledge_teach(data: dict):
    """Ingest free text into the knowledge graph via the LLM extractor (clean, typed,
    canonical entities with a one-line fact each); falls back to regex if needed.

    NOTE: path is /teach, not /ingest — the latter is taken by the app-level PDF
    upload endpoint (`@app.post('/api/knowledge/ingest')`), which would shadow this."""
    text = data.get("text", "")
    if not text:
        return {"error": "Missing text"}
    try:
        result = await services.knowledge_graph.ingest_llm(text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/prune")
async def knowledge_prune():
    """Remove legacy junk entities (sentence-openers, fragments) the old regex left."""
    try:
        return {"success": True, **services.knowledge_graph.prune_noise()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/reextract")
async def knowledge_reextract(limit: int = 60, prune: bool = True):
    """Rebuild the graph quality from stored conversations: prune legacy noise, then
    replay up to `limit` stored conversation memories through the LLM extractor in
    the background. Cleans up the regex-era entities the live path can't reach."""
    import asyncio
    kg = services.knowledge_graph
    if not getattr(kg, "extractor", None):
        return {"error": "no LLM extractor wired"}
    pruned = kg.prune_noise() if prune else {"pruned": 0}

    texts = []
    try:
        col = getattr(getattr(services, "ltm", None), "_collection", None)
        if col is not None:
            res = col.get(where={"memory_type": "conversation"}, limit=limit)
            texts = [t for t in (res.get("documents") or []) if t and len(t.strip()) > 24][:limit]
    except Exception as e:
        return {"error": f"could not read conversation memory: {e}", "pruned": pruned.get("pruned", 0)}

    async def _replay():
        for t in texts:
            try:
                await kg.ingest_llm(t, source_id="reextract")
            except Exception:
                pass
    asyncio.create_task(_replay())
    return {"success": True, "pruned": pruned.get("pruned", 0),
            "replaying": len(texts), "note": "re-extraction running in background"}


@router.post("/gnn")
async def knowledge_gnn(epochs: int = 60):
    """Train a GraphSAGE GNN (CPU) on the memory graph and return GNN-predicted
    missing links + learned-embedding clusters. Real Graph ML, right-sized — no GPU."""
    import asyncio
    try:
        kg = services.knowledge_graph
        entities = kg.get_all_entities()
        rels = kg.get_all_relationships(limit=400)
        # Give the GNN real neighbourhood structure: add the semantic similarity
        # edges (explicit relations alone are far too sparse to message-pass over).
        try:
            from core.graph_enrich import enrich
            ids = {e.get("id") for e in entities}
            scoped = [r for r in rels if r.get("source") in ids and r.get("target") in ids]
            entities, sim = await asyncio.to_thread(enrich, entities, scoped)
            rels = rels + sim
        except Exception:
            pass
        from core.graph_gnn import run_gnn
        res = await asyncio.to_thread(run_gnn, entities, rels, epochs)
        if not res:
            return {"error": "GNN unavailable or graph too small"}
        # resolve ids → names for readability
        name = {e["id"]: e.get("name", "?") for e in entities if e.get("id")}
        for p in res.get("predicted_links", []):
            p["source_name"] = name.get(p["source"], p["source"])
            p["target_name"] = name.get(p["target"], p["target"])
        return {"success": True, **res}
    except Exception as e:
        return {"error": str(e)}


@router.get("/recent")
async def knowledge_recent(limit: int = 10):
    """Get recently added entities."""
    try:
        return {"entities": services.knowledge_graph.get_recent_entities(limit)}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/entity/{name}")
async def knowledge_forget(name: str):
    """Forget (delete) an entity and its relationships — Memory Vault editing."""
    try:
        ok = services.knowledge_graph.forget(name)
        return {"success": ok, "forgotten": name if ok else None}
    except Exception as e:
        return {"error": str(e)}


@router.get("/vault")
async def knowledge_vault(q: str = "", limit: int = 200, semantic: bool = True, analyze: bool = True):
    """Full memory snapshot for the Memory Vault: stats + entities (+ relationships).

    Transparent, editable memory — everything the system has retained, in one call.
    `semantic` adds embedding-similarity edges + context sentences. `analyze` runs
    NetworkX network science: per-node PageRank importance, real (modularity)
    communities, betweenness (bridges), link-prediction suggested edges, and
    headline graph metrics.
    """
    try:
        import asyncio
        kg = services.knowledge_graph
        entities = kg.search(q) if q else kg.get_all_entities()
        entities = sorted(entities, key=lambda e: e.get("last_seen", ""), reverse=True)[:limit]
        rels = kg.get_all_relationships(limit=300)
        for r in rels:
            r["kind"] = "relation"   # explicit, extracted relationship

        if semantic:
            try:
                from core.graph_enrich import enrich
                # Only consider edges whose endpoints are in the returned entity set.
                ids = {e.get("id") for e in entities}
                scoped = [r for r in rels if r.get("source") in ids and r.get("target") in ids]
                entities, sim_edges = await asyncio.to_thread(enrich, entities, scoped)
                rels = rels + sim_edges
            except Exception as ee:  # enrichment must never break the vault
                import logging
                logging.getLogger(__name__).warning(f"[vault] enrich skipped: {ee}")

        metrics = {}
        if analyze:
            try:
                from core.graph_analytics import analyze as gx_analyze
                a = await asyncio.to_thread(gx_analyze, entities, rels)
                if a:
                    pr, comm, btw = a.get("pagerank", {}), a.get("community", {}), a.get("betweenness", {})
                    for e in entities:
                        eid = e.get("id")
                        e["pagerank"] = round(pr.get(eid, 0.0), 5)
                        if eid in comm:
                            e["community"] = comm[eid]
                        e["betweenness"] = round(btw.get(eid, 0.0), 4)
                    rels = rels + (a.get("suggestions") or [])   # link-prediction edges
                    metrics = a.get("metrics", {})
            except Exception as ae:
                import logging
                logging.getLogger(__name__).warning(f"[vault] analyze skipped: {ae}")

        stats = kg.get_stats()
        if metrics:
            stats = {**stats, "graph": metrics}
        return {"stats": stats, "entities": entities, "relationships": rels}
    except Exception as e:
        return {"error": str(e)}
