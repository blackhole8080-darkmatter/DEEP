"""Knowledge and Science Briefing endpoints."""
from fastapi import APIRouter
from interface.deps import services

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.get("/status")
async def knowledge_status():
    """Return KnowledgeStore operational status."""
    return services.knowledge_store.status()

@router.get("/search")
async def knowledge_search(q: str, domain: str = None, n: int = 5):
    """Semantic search over the knowledge store."""
    papers = await services.knowledge_store.search(q, domain=domain, n_results=n)
    return {
        "query": q,
        "results": [p.to_dict() for p in papers],
        "count": len(papers),
    }

@router.get("/recent")
async def knowledge_recent(domain: str = None, days: int = 7):
    """Get recently ingested papers."""
    papers = await services.knowledge_store.get_recent(domain=domain, days=days, n=20)
    return {
        "papers": [p.to_dict() for p in papers],
        "count": len(papers),
    }

@router.post("/briefing")
async def knowledge_briefing(domains: list = None, days_back: int = 1):
    """Generate an on-demand science briefing."""
    briefing = await services.briefing_engine.generate_briefing(
        domains=domains, days_back=days_back,
    )
    return {
        "full_text": briefing.full_text,
        "paper_count": briefing.paper_count,
        "domain_count": len(briefing.domain_sections),
        "duration_estimate_seconds": briefing.duration_estimate_seconds,
    }

@router.get("/domains")
async def knowledge_domains():
    """List available domains in the knowledge store."""
    status = services.knowledge_store.status()
    return {
        "domains": list(status.get("papers_by_domain", {}).keys()),
        "papers_by_domain": status.get("papers_by_domain", {}),
    }

@router.post("/explain")
async def knowledge_explain(body: dict):
    """Explain a concept at requested depth."""
    concept = body.get("concept", "")
    depth = body.get("depth", "graduate")
    explanation = await services.concept_linker.explain_concept(concept, depth=depth)
    return {"concept": concept, "depth": depth, "explanation": explanation}

@router.post("/connect")
async def knowledge_connect(body: dict):
    """Find connections between two concepts."""
    concept_a = body.get("concept_a", "")
    concept_b = body.get("concept_b", "")
    result = await services.concept_linker.find_connections(concept_a, concept_b)
    return {
        "concept_a": result.concept_a,
        "concept_b": result.concept_b,
        "connections": result.connections,
        "evidence": result.evidence,
        "confidence": result.confidence,
    }
