"""Security endpoints — network security status, devices, events, and trust/block
actions. Extracted from the server.py monolith; reads the network monitor lazily
from the shared service registry.
"""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from interface.deps import require

router = APIRouter(tags=["security"])

# A MAC that never matches a real device sits in the trust set forever, so the
# format is checked rather than taken on faith.
_MAC_RE = re.compile(r"^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$", re.IGNORECASE)


class MacAction(BaseModel):
    mac: str = Field(..., min_length=12, max_length=17)


class EventAck(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128)


def _normalise_mac(mac: str) -> str:
    if not _MAC_RE.match(mac.strip()):
        raise HTTPException(
            status_code=422,
            detail=f"'{mac}' is not a MAC address (expected aa:bb:cc:dd:ee:ff)",
        )
    return mac.strip().lower().replace("-", ":")


@router.get("/api/security/status")
async def security_status():
    """Current network security status summary."""
    netmon = require("netmon")
    snapshot = await netmon.get_snapshot()
    return {
        "status": "active",
        "summary": netmon.get_trust_summary(),
        "local_ip": snapshot.local_ip,
        "subnet": snapshot.subnet,
        "gateway": snapshot.gateway,
        "interface": snapshot.interface,
        "active_connections": snapshot.active_connections,
        "listening_ports": snapshot.listening_ports,
        "last_scan": snapshot.timestamp.isoformat(),
    }


@router.get("/api/security/devices")
async def security_devices():
    """List all discovered network devices."""
    return {"devices": [d.to_dict() for d in require("netmon").get_devices()]}


@router.get("/api/security/events")
async def security_events(
    limit: int = Query(50, ge=1, le=500),
    acknowledged: Optional[bool] = None,
):
    """Get security events."""
    events = require("netmon").get_events(limit=limit)
    if acknowledged is not None:
        events = [e for e in events if e.acknowledged == acknowledged]
    return {"events": [e.to_dict() for e in events]}


@router.post("/api/security/acknowledge")
async def acknowledge_security_event(body: EventAck):
    """Acknowledge a security event."""
    if not require("netmon").acknowledge_event(body.event_id):
        # Was {"success": false} at 200 — a successful call with a falsy field,
        # so acknowledging an id that had already aged out looked like it worked.
        raise HTTPException(
            status_code=404, detail=f"no such security event: {body.event_id}"
        )
    return {"success": True}


@router.post("/api/security/trust")
async def trust_device(body: MacAction):
    """Mark a device as trusted."""
    netmon = require("netmon")
    mac = _normalise_mac(body.mac)
    netmon.trust_device(mac)
    # Pre-trusting a device that hasn't appeared yet is legitimate, so this is
    # not a 404 — but the caller should be able to tell the difference between
    # that and a typo, which would otherwise sit in the trust set unnoticed.
    return {"success": True, "mac": mac,
            "known_device": netmon.get_device(mac) is not None}


@router.post("/api/security/block")
async def block_device(body: MacAction):
    """Mark a device as blocked/suspicious."""
    netmon = require("netmon")
    mac = _normalise_mac(body.mac)
    netmon.block_device(mac)
    return {"success": True, "mac": mac,
            "known_device": netmon.get_device(mac) is not None}
