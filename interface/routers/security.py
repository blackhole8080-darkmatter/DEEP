"""Security endpoints — network security status, devices, events, and trust/block
actions. Extracted from the server.py monolith; reads the network monitor lazily
from the shared service registry.
"""

from typing import Optional

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(tags=["security"])


@router.get("/api/security/status")
async def security_status():
    """Current network security status summary."""
    try:
        netmon = services.netmon
        summary = netmon.get_trust_summary()
        snapshot = await netmon.get_snapshot()
        return {
            "status": "active",
            "summary": summary,
            "local_ip": snapshot.local_ip,
            "subnet": snapshot.subnet,
            "gateway": snapshot.gateway,
            "interface": snapshot.interface,
            "active_connections": snapshot.active_connections,
            "listening_ports": snapshot.listening_ports,
            "last_scan": snapshot.timestamp.isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/api/security/devices")
async def security_devices():
    """List all discovered network devices."""
    try:
        return {"devices": [d.to_dict() for d in services.netmon.get_devices()]}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/security/events")
async def security_events(limit: int = 50, acknowledged: Optional[str] = None):
    """Get security events."""
    try:
        events = services.netmon.get_events(limit=limit)
        if acknowledged is not None:
            ack = acknowledged.lower() == "true"
            events = [e for e in events if e.acknowledged == ack]
        return {"events": [e.to_dict() for e in events]}
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/security/acknowledge")
async def acknowledge_security_event(data: dict):
    """Acknowledge a security event."""
    event_id = data.get("event_id")
    if not event_id:
        return {"error": "Missing event_id"}
    return {"success": services.netmon.acknowledge_event(event_id)}


@router.post("/api/security/trust")
async def trust_device(data: dict):
    """Mark a device as trusted."""
    mac = data.get("mac")
    if not mac:
        return {"error": "Missing mac"}
    services.netmon.trust_device(mac)
    return {"success": True}


@router.post("/api/security/block")
async def block_device(data: dict):
    """Mark a device as blocked/suspicious."""
    mac = data.get("mac")
    if not mac:
        return {"error": "Missing mac"}
    services.netmon.block_device(mac)
    return {"success": True}
