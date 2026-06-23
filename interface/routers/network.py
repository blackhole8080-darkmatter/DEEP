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
    """Connection geography: geolocate the machine's live established outbound connections."""
    import asyncio as _asyncio

    def _scan() -> dict:
        import ipaddress
        from collections import Counter, defaultdict
        try:
            import psutil
        except Exception as e:
            return {"error": f"psutil unavailable: {e}", "peers": []}
        remotes: Counter = Counter()
        procs: dict = defaultdict(set)          # ip -> {process names}
        _pid_name: dict = {}                     # pid -> name cache
        def _name(pid):
            if pid is None:
                return None
            if pid not in _pid_name:
                try:
                    _pid_name[pid] = psutil.Process(pid).name()
                except Exception:
                    _pid_name[pid] = None
            return _pid_name[pid]
        try:
            for c in psutil.net_connections(kind="inet"):
                if c.status == "ESTABLISHED" and c.raddr:
                    ip = c.raddr.ip
                    try:
                        if ipaddress.ip_address(ip).is_global:
                            remotes[ip] += 1
                            n = _name(c.pid)
                            if n:
                                procs[ip].add(n)
                    except ValueError:
                        continue
        except Exception as e:
            return {"error": f"connection enumeration failed: {e}", "peers": []}
        ips = [ip for ip, _ in remotes.most_common(50)]
        if not ips:
            return {"count": 0, "peers": [], "origin": None, "note": "no public connections"}
        try:
            import requests
            fields = "status,query,country,regionName,city,isp,as,lat,lon,proxy,hosting"
            r = requests.post("http://ip-api.com/batch",
                              params={"fields": fields}, json=ips, timeout=8)
            data = r.json()
            # Egress origin = geolocation of the IP this machine exits through.
            # This is the anchor for the connection arcs (origin → each peer);
            # it's part of the network scan, not a standalone self-locator.
            origin = None
            try:
                o = requests.get("http://ip-api.com/json/",
                                 params={"fields": "status,query,country,city,lat,lon,isp"}, timeout=5).json()
                if o.get("status") == "success":
                    origin = {"ip": o["query"], "lat": o["lat"], "lon": o["lon"],
                              "city": o.get("city"), "country": o.get("country"), "isp": o.get("isp")}
            except Exception:
                origin = None
        except Exception as e:
            return {"error": f"geo lookup failed: {e}", "peers": []}
        peers = []
        for d in data if isinstance(data, list) else []:
            if d.get("status") == "success":
                ip = d["query"]
                proxy, hosting = bool(d.get("proxy")), bool(d.get("hosting"))
                peers.append({
                    "ip": ip, "lat": d["lat"], "lon": d["lon"],
                    "city": d.get("city"), "region": d.get("regionName"),
                    "country": d.get("country"), "isp": d.get("isp"),
                    "asn": d.get("as"), "proxy": proxy, "hosting": hosting,
                    "risk": "elevated" if (proxy or hosting) else "normal",
                    "connections": remotes[ip],
                    "processes": sorted(procs.get(ip, [])),
                })
        peers.sort(key=lambda p: (p["risk"] != "elevated", -p["connections"]))
        elevated = sum(1 for p in peers if p["risk"] == "elevated")
        countries = sorted({p["country"] for p in peers if p["country"]})
        all_procs = sorted({n for p in peers for n in p["processes"]})
        return {"count": len(peers), "elevated": elevated, "countries": countries,
                "processes": all_procs, "origin": origin, "peers": peers}

    try:
        return await _asyncio.to_thread(_scan)
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
