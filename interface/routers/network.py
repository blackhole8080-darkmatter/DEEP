"""Network, Scanning, and Proximity endpoints.

The blanket `except Exception: return {"error": str(e)}` on every handler is
gone. It made a dead scanner and a bug in the graph exporter look identical to
the HUD — both arrived as a 200 the frontend rendered as "no devices". Real
failures now reach the app's 500 handler, which logs them; a subsystem that is
not running is a 503 that names it; and a thing that genuinely is not there is
a 404.
"""
import asyncio
import ipaddress
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from interface.deps import require

router = APIRouter(tags=["network"])


def _valid_ip(ip: str) -> str:
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"'{ip}' is not an IP address"
        ) from None


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK / SCANNING ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/network/devices")
async def network_devices():
    """List all discovered network devices."""
    devices = await require("scanner").get_devices()
    return {"devices": [d.__dict__ for d in devices]}


@router.get("/network/devices/{ip}")
async def network_device(ip: str):
    """Get details for a specific device by IP."""
    device = await require("scanner").get_device(_valid_ip(ip))
    if device is None:
        raise HTTPException(status_code=404, detail=f"no device discovered at {ip}")
    return device.__dict__


@router.post("/network/scan/{ip}")
async def network_scan_target(ip: str):
    """On-demand deep scan of a specific IP."""
    target = _valid_ip(ip)
    # The one endpoint here that emits packets. The ops terminal's `scan` already
    # refuses anything off your own subnet; the same boundary belongs on the API,
    # which is reachable from the LAN with a key.
    if not ipaddress.ip_address(target).is_private:
        raise HTTPException(
            status_code=403,
            detail=f"{target} is not a private address — "
                   "DEEP only scans your own subnet",
        )
    result = await require("scanner").scan_target(target)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail=f"scan of {target} produced no result "
                   "(host down, or nmap unavailable)",
        )
    return result.__dict__


@router.get("/network/threats")
async def network_threats(hours: int = Query(24, ge=1, le=8760)):
    """Get recent threat detections."""
    threats = await require("threat_monitor").get_threats(hours=hours)
    return {"threats": [t.__dict__ for t in threats]}


@router.get("/network/pihole")
async def network_pihole_summary():
    """Pi-hole DNS summary."""
    summary = await require("pihole").get_summary()
    return summary or {"reachable": False}


@router.get("/network/pihole/queries")
async def network_pihole_queries(count: int = Query(50, ge=1, le=1000)):
    """Recent Pi-hole DNS queries."""
    return {"queries": await require("pihole").get_recent_queries(count=count)}


@router.get("/network/wifi")
async def network_wifi_status():
    """Evil twin detector status."""
    return require("evil_twin").status()


@router.get("/api/network/geo")
async def api_network_geo():
    """Connection geography: geolocate the machine's live established outbound
    connections, attribute each to its owning process, and resolve the egress
    origin. Delegates to network.connection_geo (shared with the brain tool)."""
    from network.connection_geo import scan_connections

    return await asyncio.to_thread(scan_connections)


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK TOPOGRAPH / COMMAND CENTER ENDPOINTS (v3)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/api/network/graph")
async def network_graph_full(layer: Optional[str] = None):
    """Export full network graph (optionally filtered by layer)."""
    return require("net_graph").export_graph(layer=layer)


@router.get("/api/network/graph/{node_id}")
async def network_graph_subgraph(node_id: str, depth: int = Query(1, ge=1, le=6)):
    """Export subgraph centred on a node within N hops."""
    graph = require("net_graph")
    if graph.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"no such graph node: {node_id}")
    return graph.export_subgraph(centre_id=node_id, depth=depth)


@router.get("/api/network/stats")
async def network_graph_stats():
    """Graph statistics."""
    return require("net_graph").stats()


@router.get("/api/network/observations/{node_id}")
async def network_observations(
    node_id: str,
    metric: Optional[str] = None,
    hours: int = Query(24, ge=1, le=8760),
):
    """Time-series observations for a node."""
    graph = require("net_graph")
    if graph.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"no such graph node: {node_id}")
    return {"observations": graph.get_observations(node_id, metric=metric, hours=hours)}


@router.get("/api/network/inferences/{node_id}")
async def network_inferences(
    node_id: str,
    inference_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
):
    """AI-generated inferences for a node."""
    graph = require("net_graph")
    if graph.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"no such graph node: {node_id}")
    return {
        "inferences": graph.get_inferences(
            node_id, inference_type=inference_type, limit=limit
        )
    }


class AnalyseRequest(BaseModel):
    scope: str = Field("device", description="device | health | threats")
    node_id: str = Field("", max_length=128)


@router.post("/api/network/analyse")
async def network_analyse(body: AnalyseRequest):
    """On-demand AI analysis of a device or the whole network."""
    analyst = require("net_ai_analyst")
    scope = body.scope.strip().lower()
    if scope == "device":
        if not body.node_id:
            raise HTTPException(
                status_code=422, detail="scope=device requires a node_id"
            )
        result = await analyst.analyse_device(body.node_id)
    elif scope == "health":
        result = await analyst.generate_health_report()
    elif scope == "threats":
        result = await analyst.summarise_threats()
    else:
        raise HTTPException(
            status_code=422, detail="scope must be one of: device, health, threats"
        )
    return {"analysis": result}


class ExplainRequest(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=128)
    metric: str = Field(..., min_length=1, max_length=64)
    value: float
    expected: float


@router.post("/api/network/explain")
async def network_explain(body: ExplainRequest):
    """Explain an anomalous metric for a device."""
    # node_id/metric were `payload.get(..., "")` and value/expected were
    # float(...) on whatever arrived — a missing field asked the model to
    # explain metric "" moving from 0.0 to 0.0, and a non-numeric one raised
    # ValueError that came back as a 200.
    explanation = await require("net_ai_analyst").explain_anomaly(
        body.node_id, body.metric, body.value, body.expected
    )
    return {"explanation": explanation}


# ═══════════════════════════════════════════════════════════════════════════════
# PROXIMITY ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/network/proximity")
async def network_proximity_summary():
    """Passive proximity sensor summary (WiFi + Bluetooth)."""
    return await require("proximity").get_proximity_summary()


@router.get("/network/proximity/wifi")
async def network_proximity_wifi():
    """Nearby WiFi access points from passive scan."""
    aps = await require("proximity").get_nearby_aps()
    return {"aps": [ap.__dict__ for ap in aps]}


@router.get("/network/proximity/bt")
async def network_proximity_bt():
    """Nearby Bluetooth devices from passive advertisement scan."""
    devices = await require("proximity").get_nearby_bt()
    return {"devices": [d.__dict__ for d in devices]}


@router.get("/network/proximity/timeline")
async def network_proximity_timeline(limit: int = Query(24, ge=1, le=200)):
    """Per-device hour-of-day presence histograms (for the Presence Timeline)."""
    from network.proximity_store import get_store

    records = sorted(
        get_store().load_all().values(),
        key=lambda r: r.get("seen_count", 0),
        reverse=True,
    )
    devices = []
    for record in records[:limit]:
        hours = record.get("hours") or [0] * 24
        if len(hours) != 24:
            hours = (hours + [0] * 24)[:24]
        devices.append({
            "id": record.get("id"),
            "name": record.get("name") or record.get("vendor") or record.get("id"),
            "vendor": record.get("vendor"),
            "kind": record.get("kind"),
            "hours": hours,
            "seen_count": record.get("seen_count", 0),
            "first_seen": record.get("first_seen"),
            "last_seen": record.get("last_seen"),
        })
    return {"devices": devices, "current_hour": datetime.now(timezone.utc).hour}


@router.get("/network/proximity/known")
async def network_proximity_known():
    """Durable sensing memory — how many devices DEEP has ever observed."""
    from network.proximity_store import get_store

    return get_store().stats()


@router.get("/api/investigate")
async def api_investigate(target: str = Query(..., min_length=1, max_length=253)):
    """Build an intelligence dossier on an IP / MAC / hostname / domain.

    Local-network oriented (vendor, reverse DNS, ARP). For public indicators
    prefer /api/intel/investigate, which fans out across the public-API layer.
    """
    from network.investigator import investigate as _investigate

    return await asyncio.to_thread(_investigate, target)
