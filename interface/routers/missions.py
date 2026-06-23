"""Missions / Long-running Orchestrator endpoints."""
from fastapi import APIRouter
from core.long_running_orchestrator import LongRunningOrchestrator
from interface.deps import services

router = APIRouter(prefix="/api/missions", tags=["missions"])

def get_mission_api():
    if not hasattr(services, "_mission_api"):
        services._mission_api = LongRunningOrchestrator(event_bus=services.event_bus)
    return services._mission_api

@router.post("")
async def create_mission(data: dict):
    goal = (data or {}).get("goal", "")
    if not goal:
        return {"error": "goal required"}
    m = get_mission_api().create_mission(goal)
    return {"mission_id": m.id, "goal": m.goal, "status": m.status}

@router.get("")
async def list_missions(status: str = None, limit: int = 20):
    missions = get_mission_api().list_missions(status=status, limit=limit)
    return {"missions": [{
        "id": m.id, "goal": m.goal, "status": m.status,
        "progress_pct": m.progress_pct, "created_at": m.created_at,
        "updated_at": m.updated_at, "error": m.error,
    } for m in missions]}

@router.get("/{mission_id}")
async def get_mission(mission_id: str):
    try:
        return get_mission_api().get_mission_detail(mission_id)
    except ValueError as e:
        return {"error": str(e)}

@router.post("/{mission_id}/cancel")
async def cancel_mission(mission_id: str):
    get_mission_api().cancel_mission(mission_id)
    return {"mission_id": mission_id, "status": "cancelled"}
