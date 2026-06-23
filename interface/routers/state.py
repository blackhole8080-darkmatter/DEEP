"""State and Redis endpoints."""
from fastapi import APIRouter
from interface.deps import services

router = APIRouter(prefix="/state", tags=["state"])

@router.get("/devices")
async def state_devices():
    """List currently active DEEP client devices."""
    try:
        devices = await services.device_registry.get_active_devices()
        return {"devices": [
            {
                "device_id": d.device_id,
                "name": d.name,
                "platform": d.platform,
                "tailscale_ip": d.tailscale_ip,
                "last_seen": d.last_seen,
                "active": d.active,
            }
            for d in devices
        ]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/conversation")
async def state_conversation():
    """Shared conversation history across all devices."""
    try:
        history = await services.redis_state.get_conversation_history()
        return {"history": history}
    except Exception as e:
        return {"error": str(e)}

@router.get("/status")
async def state_redis_status():
    """Redis shared-state layer status."""
    return services.redis_state.status()

@router.post("/handoff")
async def state_handoff(data: dict):
    """Transfer primary control to another device."""
    device_id = data.get("device_id")
    if not device_id:
        return {"error": "Missing device_id"}
    try:
        await services.device_registry.handoff_to(device_id)
        return {"success": True, "handoff_to": device_id}
    except Exception as e:
        return {"error": str(e)}
