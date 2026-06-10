"""Research engine endpoints."""

from typing import Optional

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/topics")
async def research_topics():
    """List all research topics."""
    try:
        return {"topics": services.research_engine.get_topics()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/topics")
async def add_research_topic(data: dict):
    """Add a new research topic."""
    name = data.get("name")
    keywords = data.get("keywords", [])
    sources = data.get("sources", [])
    if not name:
        return {"error": "Missing name"}
    topic = services.research_engine.add_topic(name, keywords=keywords, sources=sources)
    return {"success": True, "topic": topic.to_dict()}


@router.delete("/topics/{topic_id}")
async def remove_research_topic(topic_id: str):
    """Remove a research topic."""
    success = services.research_engine.remove_topic(topic_id)
    return {"success": success}


@router.get("/findings")
async def research_findings(topic_id: Optional[str] = None, limit: int = 20, unread_only: bool = False):
    """Get research findings."""
    try:
        findings = services.research_engine.get_findings(
            topic_id=topic_id,
            unread_only=unread_only,
            limit=limit,
        )
        return {"findings": findings}
    except Exception as e:
        return {"error": str(e)}


@router.post("/findings/{finding_id}/read")
async def mark_finding_read(finding_id: str):
    """Mark a finding as read."""
    success = services.research_engine.mark_read(finding_id)
    return {"success": success}


@router.get("/briefing")
async def get_briefing():
    """Get the latest briefing."""
    try:
        briefing = services.research_engine.get_latest_briefing()
        if briefing:
            return {"briefing": briefing}
        return {"briefing": None}
    except Exception as e:
        return {"error": str(e)}


@router.post("/briefing")
async def generate_briefing():
    """Force-generate a new briefing."""
    try:
        briefing = await services.research_engine.run_briefing()
        if briefing:
            return {"success": True, "briefing": briefing.to_dict()}
        return {"success": False, "message": "No new findings to brief"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/scan")
async def force_research_scan():
    """Force a scan of all topics."""
    try:
        results = await services.research_engine.force_scan_all()
        return {"success": True, "results": results}
    except Exception as e:
        return {"error": str(e)}


@router.get("/stats")
async def research_stats():
    """Get research engine statistics."""
    try:
        return services.research_engine.get_stats()
    except Exception as e:
        return {"error": str(e)}
