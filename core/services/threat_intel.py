import urllib.request
import json
import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)

# Cache to avoid spamming the free APIs
_cached_threats = []
_last_fetch = 0

def get_live_threats() -> List[Dict]:
    global _cached_threats, _last_fetch
    
    # Cache for 10 minutes (600 seconds)
    if time.time() - _last_fetch < 600 and _cached_threats:
        return _cached_threats

    try:
        import random
        ips_with_sources = []

        # 1. Get from SANS ISC (Top attackers)
        try:
            req = urllib.request.Request('https://isc.sans.edu/api/sources/attacks/100?json', headers={'User-Agent': 'DEEP-Threat-Map'})
            res = urllib.request.urlopen(req)
            data = json.loads(res.read())
            for d in data[:50]:
                if 'ip' in d: ips_with_sources.append({"ip": d['ip'], "source": "SANS ISC"})
        except Exception as e:
            logger.error(f"SANS fetch error: {e}")

        # 2. Get from Proofpoint Emerging Threats (Compromised Botnets)
        try:
            req = urllib.request.Request('https://rules.emergingthreats.net/blockrules/compromised-ips.txt', headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req)
            et_ips = [line.decode('utf-8').strip() for line in res.read().splitlines() if line.strip() and not line.startswith(b'#')]
            random.shuffle(et_ips)
            for ip in et_ips[:50]:
                ips_with_sources.append({"ip": ip, "source": "EmergingThreats.net"})
        except Exception as e:
            logger.error(f"ET fetch error: {e}")
            
        ips_to_resolve = [item["ip"] for item in ips_with_sources][:100]

        # 3. Get Geolocation using ip-api batch
        if ips_to_resolve:
            req2 = urllib.request.Request('http://ip-api.com/batch', data=json.dumps(ips_to_resolve).encode(), headers={'Content-Type': 'application/json'})
            res2 = urllib.request.urlopen(req2)
            geo_data = json.loads(res2.read())
            
            threats = []
            # ip-api batch returns array in same order
            for item, geo in zip(ips_with_sources, geo_data):
                if geo.get('status') == 'success':
                    threats.append({
                        "ip": geo.get('query'),
                        "lat": geo.get('lat'),
                        "lon": geo.get('lon'),
                        "country": geo.get('country'),
                        "city": geo.get('city'),
                        "org": geo.get('org'),
                        "source": item["source"]
                    })
                    
            _cached_threats = threats
            _last_fetch = time.time()
            return threats
        return []
        
    except Exception as e:
        logger.error(f"Failed to fetch live threats: {e}")
        return _cached_threats  # return old cache if error

def get_osint_details(ip: str) -> Dict:
    try:
        # Query ARIN's RDAP (which auto-redirects to other RIRs like RIPE, APNIC)
        req = urllib.request.Request(f'https://rdap.arin.net/registry/ip/{ip}', headers={'User-Agent': 'DEEP-OSINT'})
        res = urllib.request.urlopen(req)
        data = json.loads(res.read())
        
        details = {
            "name": data.get("name"),
            "country": data.get("country"),
            "entities": []
        }
        
        for entity in data.get("entities", []):
            ent = {"name": "", "address": "", "email": "", "phone": ""}
            for item in entity.get("vcardArray", [[]])[1]:
                if len(item) >= 4:
                    if item[0] == "fn": ent["name"] = item[3]
                    elif item[0] == "adr": 
                        if isinstance(item[1], dict) and "label" in item[1]:
                            ent["address"] = item[1]["label"].replace("\\n", " ")
                    elif item[0] == "email": ent["email"] = item[3]
                    elif item[0] == "tel": ent["phone"] = item[3]
            
            # only add if we found something useful
            if ent["name"] or ent["email"]:
                details["entities"].append(ent)
                
        return details
    except Exception as e:
        logger.error(f"Failed to fetch OSINT for {ip}: {e}")
        return {"error": str(e)}

_cached_servers = []
_last_servers_fetch = 0

def get_live_public_servers() -> List[Dict]:
    global _cached_servers, _last_servers_fetch
    if time.time() - _last_servers_fetch < 3600 and _cached_servers:
        return _cached_servers
    
    import socket
    ccs = ['us', 'gb', 'ca', 'au', 'de', 'fr', 'jp', 'cn', 'in', 'br', 'za', 'ru', 'it', 'es', 'nl', 'se', 'ch', 'kr', 'sg', 'ae', 'mx', 'ar', 'cl', 'co', 'nz', 'ie', 'no', 'dk', 'fi', 'pl', 'cz', 'at', 'be', 'pt', 'gr', 'tr', 'il', 'sa', 'eg', 'ng', 'ke', 'th', 'my', 'vn', 'ph', 'id', 'pk', 'bd', 'pe', 've', 'ua', 'ro', 'hu', 'bg', 'rs', 'hr', 'si', 'sk', 'lt', 'lv', 'ee', 'is', 'hk', 'tw']
    
    ips = []
    import random
    ccs = ['us', 'gb', 'ca', 'au', 'de', 'fr', 'jp', 'cn', 'in', 'br', 'za', 'ru', 'it', 'es', 'nl', 'se', 'ch', 'kr', 'sg', 'ae', 'mx', 'ar', 'cl', 'co', 'nz', 'ie', 'no', 'dk', 'fi', 'pl', 'cz', 'at', 'be', 'pt', 'gr', 'tr', 'il', 'sa', 'eg', 'ng', 'ke', 'th', 'my', 'vn', 'ph', 'id', 'pk', 'bd', 'pe', 've', 'ua', 'ro', 'hu', 'bg', 'rs', 'hr', 'si', 'sk', 'lt', 'lv', 'ee', 'is', 'hk', 'tw']
    
    ips = []
    selected_ccs = ccs + random.sample(ccs, 30) # get 94 domains
    for cc in selected_ccs:
        try:
            # Add some randomness to subdomain to hit different IPs in the pool
            prefix = random.randint(0, 3)
            ip = socket.gethostbyname(f"{prefix}.{cc}.pool.ntp.org")
            if ip not in ips:
                ips.append(ip)
        except Exception:
            pass
            
    if ips:
        # ip-api batch takes max 100
        ips = ips[:100]
        try:
            req = urllib.request.Request('http://ip-api.com/batch', data=json.dumps(ips).encode(), headers={'Content-Type': 'application/json'})
            res = urllib.request.urlopen(req)
            geo_data = json.loads(res.read())
            
            servers = []
            for geo in geo_data:
                if geo.get('status') == 'success':
                    # Determine infrastructure type randomly
                    rand = random.random()
                    node_type = "Public Server"
                    if rand < 0.25: node_type = "Mobile Tower"
                    elif rand < 0.40: node_type = "IXP"
                    elif rand < 0.70: node_type = "Datacenter"
                    
                    servers.append({
                        "ip": geo.get('query'),
                        "lat": geo.get('lat'),
                        "lon": geo.get('lon'),
                        "country": geo.get('country'),
                        "city": geo.get('city'),
                        "org": geo.get('org', 'Public NTP Pool'),
                        "type": node_type
                    })
            if servers:
                # Add a static central hub for visuals
                servers.append({"ip": "8.8.8.8", "lat": 37.386, "lon": -122.0838, "country": "United States", "city": "Mountain View", "org": "Google DNS", "type": "Hub"})
                servers.append({"ip": "1.1.1.1", "lat": -33.8688, "lon": 151.2093, "country": "Australia", "city": "Sydney", "org": "Cloudflare", "type": "Hub"})
                servers.append({"ip": "9.9.9.9", "lat": 48.8566, "lon": 2.3522, "country": "France", "city": "Paris", "org": "Quad9", "type": "Hub"})
                
                _cached_servers = servers
                _last_servers_fetch = time.time()
                return servers
        except Exception as e:
            logger.error(f"Failed to fetch public servers geo: {e}")
            
    return _cached_servers
