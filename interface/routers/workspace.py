"""Workspace endpoints — Aryan's ingested documents (personal RAG) and DEEP's
persistent world model. Extracted from the server.py monolith; reads its services
lazily from the shared registry so the dependency arrow stays server → routers → deps.
"""

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(tags=["workspace"])


@router.get("/api/docs/search")
async def docs_search(q: str, k: int = 5):
    """Search Aryan's ingested documents — 'what did I write about X' with citations."""
    return services.personal_rag.search(q, k=k)


@router.post("/api/docs/scan")
async def docs_scan(force: bool = False):
    """Ingest new/changed files in the watch folder now."""
    return services.personal_rag.scan(force=force)


@router.get("/api/docs/stats")
async def docs_stats():
    """What documents DEEP has ingested + the watch-folder path."""
    return services.personal_rag.stats()


@router.get("/api/world")
async def get_world_model():
    """DEEP's persistent model of who Aryan is — projects, people, priorities, episodes."""
    return services.world_model.to_dict()


@router.post("/api/world/refresh")
async def refresh_world_model_now():
    """Force a re-synthesis of the world model from the graph + recent conversation."""
    await services.refresh_world_model()
    return {"success": True, **services.world_model.to_dict()}
