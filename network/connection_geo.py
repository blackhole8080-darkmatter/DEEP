"""Connection geography — geolocate the machine's live established outbound
connections, attribute each to the owning local process, and resolve the egress
origin. Shared by the /api/network/geo route and the etis_connection_geo brain
tool so both stay in sync. Offline-degrading: private IPs are skipped, and a
failed geo lookup yields an error dict rather than raising.
"""
from __future__ import annotations

from typing import Any, Dict, List
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def scan_connections(max_peers: int = 50) -> Dict[str, Any]:
    """Return {count, elevated, countries, processes, origin, peers} describing
    current public outbound connections. `peers` is sorted elevated-first."""
    import ipaddress
    from collections import Counter, defaultdict
    try:
        import psutil
    except Exception as e:  # pragma: no cover
        return {"error": f"psutil unavailable: {e}", "peers": []}

    remotes: Counter = Counter()
    procs: dict = defaultdict(set)   # ip -> {process names}
    _pid_name: dict = {}             # pid -> name cache

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

    ips = [ip for ip, _ in remotes.most_common(max_peers)]
    if not ips:
        return {"count": 0, "peers": [], "origin": None, "note": "no public connections"}

    try:
        import requests
        fields = "status,query,country,regionName,city,isp,as,lat,lon,proxy,hosting"
        data = requests.post("http://ip-api.com/batch",
                             params={"fields": fields}, json=ips, timeout=8).json()
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


def check_geo_anomalies(data_dir: str = None) -> List[Dict[str, Any]]:
    """Stateful anomaly detector. Returns a list of 'anomaly' dicts for coarse novelties
    (new country or ASN) discovered via scan_connections(). Includes a learning phase
    to prevent day-one alert storms.
    """
    import os
    
    anomalies = []
    scan_res = scan_connections()
    if "error" in scan_res or not scan_res.get("peers"):
        return anomalies
        
    base_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data" / "security"
    base_dir.mkdir(parents=True, exist_ok=True)
    state_file = base_dir / "geo_baseline.json"
    
    # Load state
    state = {
        "first_run": datetime.now(timezone.utc).isoformat(),
        "baseline_established": False,
        "known_countries": [],
        "known_asns": []
    }
    
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state.update(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to load geo baseline: {e}")
            
    # Check warmup period (24 hours)
    first_run = datetime.fromisoformat(state["first_run"])
    hours_since_first = (datetime.now(timezone.utc) - first_run).total_seconds() / 3600.0
    
    if hours_since_first > 24 and not state["baseline_established"]:
        state["baseline_established"] = True
        logger.info("[Geo] Baseline warmup complete.")
        
    known_countries = set(state["known_countries"])
    known_asns = set(state["known_asns"])
    
    new_countries = set()
    new_asns = set()
    
    for p in scan_res.get("peers", []):
        c = p.get("country")
        asn = p.get("asn")
        procs = p.get("processes", [])
        
        if c and c not in known_countries:
            new_countries.add(c)
            known_countries.add(c)
            if state["baseline_established"]:
                anomalies.append({
                    "type": "new_country",
                    "title": f"First connection to {c}",
                    "description": f"Process(es) {', '.join(procs) or 'Unknown'} opened a connection to {c} ({p['ip']}).",
                    "severity": "medium",
                    "details": p
                })
                
        if asn and asn not in known_asns:
            new_asns.add(asn)
            known_asns.add(asn)
            if state["baseline_established"]:
                anomalies.append({
                    "type": "new_asn",
                    "title": f"Connection to new ASN",
                    "description": f"Process(es) {', '.join(procs) or 'Unknown'} talking to {asn} ({p['ip']}).",
                    "severity": "low",
                    "details": p
                })
                
    # Save state
    state["known_countries"] = sorted(list(known_countries))
    state["known_asns"] = sorted(list(known_asns))
    
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save geo baseline: {e}")
        
    return anomalies
