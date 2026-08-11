"""State and Redis endpoints.

Every handler here used to wrap its body in `except Exception: return {"error":
str(e)}`. That is a 200 — the frontend cannot tell it from a result, so a dead
subsystem rendered as an empty list and a genuine bug rendered as nothing at
all. The blanket catches are gone: real failures reach the app's 500 handler
(which logs them and returns a clean body rather than leaking the exception),
a subsystem that is not running is a 503, and bad input is a 422.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from interface.deps import require

router = APIRouter(prefix="/state", tags=["state"])


@router.get("/devices")
async def state_devices():
    """List currently active DEEP client devices."""
    devices = await require("device_registry").get_active_devices()
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


@router.get("/conversation")
async def state_conversation():
    """Shared conversation history across all devices."""
    return {"history": await require("redis_state").get_conversation_history()}


@router.get("/status")
async def state_redis_status():
    """Redis shared-state layer status."""
    return require("redis_state").status()


class Handoff(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)


@router.post("/handoff")
async def state_handoff(body: Handoff):
    """Transfer primary control to another device."""
    registry = require("device_registry")
    # handoff_to writes the target into shared state unconditionally, so a typo
    # used to "succeed" and hand control to a device that does not exist.
    active = {d.device_id for d in await registry.get_active_devices()}
    if body.device_id not in active:
        raise HTTPException(
            status_code=404,
            detail=f"no active device '{body.device_id}'; active: "
                   f"{', '.join(sorted(active)) or 'none'}",
        )
    await registry.handoff_to(body.device_id)
    return {"success": True, "handoff_to": body.device_id}
