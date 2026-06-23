"""Connection geography — geolocate the machine's live established outbound
connections, attribute each to the owning local process, and resolve the egress
origin. Shared by the /api/network/geo route and the etis_connection_geo brain
tool so both stay in sync. Offline-degrading: private IPs are skipped, and a
failed geo lookup yields an error dict rather than raising.
"""
from __future__ import annotations

from typing import Any, Dict


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
