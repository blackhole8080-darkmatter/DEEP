"""Network, Scanning, and Proximity endpoints."""
from typing import Optional
from fastapi import APIRouter
from interface.deps import services

router = APIRouter(tags=["network"])

# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK / SCANNING ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/network/devices")
async def network_devices():
    """List all discovered network devices."""
    try:
        devices = await services.scanner.get_devices()
        return {"devices": [d.__dict__ for d in devices]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/devices/{ip}")
async def network_device(ip: str):
    """Get details for a specific device by IP."""
    try:
        device = await services.scanner.get_device(ip)
        if device:
            return device.__dict__
        return {"error": "Device not found"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/network/scan/{ip}")
async def network_scan_target(ip: str):
    """On-demand deep scan of a specific IP."""
    try:
        result = await services.scanner.scan_target(ip)
        if result:
            return result.__dict__
        return {"error": "Scan failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/threats")
async def network_threats(hours: int = 24):
    """Get recent threat detections."""
    try:
        threats = await services.threat_monitor.get_threats(hours=hours)
        return {"threats": [t.__dict__ for t in threats]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/pihole")
async def network_pihole_summary():
    """Pi-hole DNS summary."""
    try:
        summary = await services.pihole.get_summary()
        return summary or {"reachable": False}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/pihole/queries")
async def network_pihole_queries(count: int = 50):
    """Recent Pi-hole DNS queries."""
    try:
        queries = await services.pihole.get_recent_queries(count=count)
        return {"queries": queries}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/wifi")
async def network_wifi_status():
    """Evil twin detector status."""
    return services.evil_twin.status()

@router.get("/api/network/geo")
async def api_network_geo():
    """Connection geography: geolocate the machine's live established outbound
    connections, attribute each to its owning process, and resolve the egress
    origin. Delegates to network.connection_geo (shared with the brain tool)."""
    import asyncio as _asyncio
    from network.connection_geo import scan_connections
    try:
        return await _asyncio.to_thread(scan_connections)
    except Exception as e:
        return {"error": str(e), "peers": []}


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK TOPOGRAPH / COMMAND CENTER ENDPOINTS (v3)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/network/graph")
async def network_graph_full(layer: Optional[str] = None):
    """Export full network graph (optionally filtered by layer)."""
    try:
        from network.graph import net_graph
        return net_graph.export_graph(layer=layer)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/network/graph/{node_id}")
async def network_graph_subgraph(node_id: str, depth: int = 1):
    """Export subgraph centred on a node within N hops."""
    try:
        from network.graph import net_graph
        return net_graph.export_subgraph(centre_id=node_id, depth=depth)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/network/stats")
async def network_graph_stats():
    """Graph statistics."""
    try:
        from network.graph import net_graph
        return net_graph.stats()
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/network/observations/{node_id}")
async def network_observations(node_id: str, metric: Optional[str] = None, hours: int = 24):
    """Time-series observations for a node."""
    try:
        from network.graph import net_graph
        return {"observations": net_graph.get_observations(node_id, metric=metric, hours=hours)}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/network/inferences/{node_id}")
async def network_inferences(node_id: str, inference_type: Optional[str] = None, limit: int = 20):
    """AI-generated inferences for a node."""
    try:
        from network.graph import net_graph
        return {"inferences": net_graph.get_inferences(node_id, inference_type=inference_type, limit=limit)}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/network/analyse")
async def network_analyse(payload: dict):
    """On-demand AI analysis of a device or the whole network."""
    try:
        from network.ai_analyst import net_ai_analyst
        scope = payload.get("scope", "device")
        node_id = payload.get("node_id", "")
        if scope == "device" and node_id:
            result = await net_ai_analyst.analyse_device(node_id)
        elif scope == "health":
            result = await net_ai_analyst.generate_health_report()
        elif scope == "threats":
            result = await net_ai_analyst.summarise_threats()
        else:
            return {"error": "Invalid scope."}
        return {"analysis": result}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/network/explain")
async def network_explain(payload: dict):
    """Explain an anomalous metric for a device."""
    try:
        from network.ai_analyst import net_ai_analyst
        node_id = payload.get("node_id", "")
        metric = payload.get("metric", "")
        value = float(payload.get("value", 0))
        expected = float(payload.get("expected", 0))
        result = await net_ai_analyst.explain_anomaly(node_id, metric, value, expected)
        return {"explanation": result}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════════════════════
# PROXIMITY ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/network/proximity")
async def network_proximity_summary():
    """Passive proximity sensor summary (WiFi + Bluetooth)."""
    try:
        summary = await services.proximity.get_proximity_summary()
        return summary
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/proximity/wifi")
async def network_proximity_wifi():
    """Nearby WiFi access points from passive scan."""
    try:
        aps = await services.proximity.get_nearby_aps()
        return {"aps": [ap.__dict__ for ap in aps]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/proximity/bt")
async def network_proximity_bt():
    """Nearby Bluetooth devices from passive advertisement scan."""
    try:
        devices = await services.proximity.get_nearby_bt()
        return {"devices": [d.__dict__ for d in devices]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/network/proximity/timeline")
async def network_proximity_timeline(limit: int = 24):
    """Per-device hour-of-day presence histograms (for the Presence Timeline)."""
    from datetime import datetime, timezone
    try:
        from network.proximity_store import get_store
        recs = list(get_store().load_all().values())
        recs.sort(key=lambda r: r.get("seen_count", 0), reverse=True)
        devices = []
        for r in recs[:max(1, limit)]:
            hours = r.get("hours") or [0] * 24
            if len(hours) != 24:
                hours = (hours + [0] * 24)[:24]
            devices.append({
                "id": r.get("id"), "name": r.get("name") or r.get("vendor") or r.get("id"),
                "vendor": r.get("vendor"), "kind": r.get("kind"),
                "hours": hours, "seen_count": r.get("seen_count", 0),
                "first_seen": r.get("first_seen"), "last_seen": r.get("last_seen"),
            })
        return {"devices": devices, "current_hour": datetime.now(timezone.utc).hour}
    except Exception as e:
        return {"error": str(e), "devices": []}

@router.get("/network/proximity/known")
async def network_proximity_known():
    """Durable sensing memory — how many devices DEEP has ever observed (survives restarts)."""
    try:
        from network.proximity_store import get_store
        return get_store().stats()
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/investigate")
async def api_investigate(target: str = ""):
    """Build an intelligence dossier on an IP / MAC / hostname / domain."""
    if not target:
        return {"error": "missing target"}
    import asyncio as _asyncio
    from network.investigator import investigate as _investigate
    try:
        return await _asyncio.to_thread(_investigate, target)
    except Exception as e:
        return {"error": str(e)}
