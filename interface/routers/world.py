"""Read-only Cybertech World projection endpoint.

This router composes existing DEEP services; it does not introduce scanning or
external side effects. Missing subsystems are represented as empty/degraded data
so the dashboard can explain what is unavailable.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from core.intel import public_apis
from core.intel.cybertech_world import build_world_snapshot
from core.intel.live_stats import shared_live_intel
from interface.deps import services

router = APIRouter(prefix="/api/world", tags=["world"])


@router.get("")
async def cybertech_world(limit: int = Query(120, ge=1, le=500)):
    """Return one bounded, evidence-attributed Cybertech World snapshot."""
    live = shared_live_intel()
    map_payload = await live.threat_map(limit=limit)

    timeline_service = getattr(services, "security_timeline", None)
    timeline_items = (
        timeline_service.get_timeline(limit=80)
        if timeline_service is not None
        else []
    )

    graph_service = getattr(services, "net_graph", None)
    graph_payload = (graph_service.export_graph() if graph_service is not None else {})

    return build_world_snapshot(
        map_payload=map_payload,
        timeline_items=timeline_items,
        graph_payload=graph_payload,
        source_summary=public_apis.summary(),
    )
