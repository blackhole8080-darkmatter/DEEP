"""Live cybersecurity statistics and the geo intelligence map.

Two products, both assembled from the public-API catalog:

``cyber_stats()``
    The operations-center numbers: how fast CISA is adding actively-exploited
    CVEs, what the severity mix looks like, which upstream sources are healthy,
    and how the local estate is doing. This is what the HUD's stat tiles read.

``threat_map()``
    Geolocated nodes for the threat globe — real attacking IPs from real
    blocklists, each carrying the classification the source actually assigned
    it.

**On honesty.** Everything here is either measured or absent. The previous
implementation of this feed invented infrastructure types with
``random.random()``, tagged nodes as Tor exits on a coin flip, and synthesised
an "attack" every 2.5 seconds by picking two nodes and captioning them with a
randomly-chosen technique. A security console that fabricates findings is
worse than one that shows nothing, so none of that survives: a node's
classification comes from the feed that listed it, and a field DEEP cannot
determine is omitted rather than guessed.

**Privacy note.** Bulk geolocation goes through ip-api.com's batch endpoint,
which is HTTP-only on the free tier. Only addresses that are *already public*
— entries from published blocklists and attacker feeds — are ever sent there.
The user's own peers are geolocated over HTTPS one at a time by the
investigator instead.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.intel import public_apis
from core.intel.http import IntelHTTP, shared_http

logger = logging.getLogger(__name__)

# Public because ``core.intel.refresher`` pre-warms exactly these feeds; one
# definition means the refresher can never warm a URL the console doesn't read.
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
ISC_TOP_SOURCES = "https://isc.sans.edu/api/sources/attacks/{limit}?json"
FEODO_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
TOR_EXITS = "https://check.torproject.org/torbulkexitlist"
_GEO_BATCH = "http://ip-api.com/batch"  # see module docstring re: HTTP
_GEO_BATCH_MAX = 100
EPSS_TOP = "https://api.first.org/data/v1/epss?order=!epss&limit={limit}"


@dataclass(slots=True)
class MapNode:
    """One geolocated point on the intelligence map."""

    ip: str
    lat: float
    lon: float
    country: str = ""
    country_code: str = ""
    city: str = ""
    org: str = ""
    asn: str = ""
    # Where this node came from and what that source says it is. Never inferred.
    source: str = ""
    classification: str = ""
    severity: str = "medium"
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "lat": self.lat,
            "lon": self.lon,
            "country": self.country,
            "country_code": self.country_code,
            "city": self.city,
            "org": self.org,
            "asn": self.asn,
            "source": self.source,
            "classification": self.classification,
            "severity": self.severity,
            "detail": self.detail,
        }


class LiveIntel:
    """Aggregates the public feeds into stats and map data."""

    def __init__(self, http: Optional[IntelHTTP] = None) -> None:
        self._http = http or shared_http()

    # ═══════════════════════════════════════════════════════════════════════
    # Live statistics
    # ═══════════════════════════════════════════════════════════════════════

    async def cyber_stats(self) -> Dict[str, Any]:
        """Roll up the global threat picture plus source health."""
        kev_task = self._http.get_json(KEV_URL, ttl=3600)
        epss_task = self._http.get_json(EPSS_TOP.format(limit=20), ttl=3600)
        feodo_task = self._http.get_json(FEODO_URL, ttl=1800)
        tor_task = self._http.get_text(TOR_EXITS, ttl=3600)

        kev, epss, feodo, tor = await asyncio.gather(
            kev_task, epss_task, feodo_task, tor_task, return_exceptions=True
        )

        stats: Dict[str, Any] = {
            "generated_at": _now(),
            "sources": public_apis.summary(),
            "degraded": {},
        }

        stats["kev"] = self._kev_stats(kev, stats["degraded"])
        stats["epss"] = self._epss_stats(epss, stats["degraded"])
        stats["botnet"] = self._botnet_stats(feodo, stats["degraded"])
        stats["anonymity"] = self._tor_stats(tor, stats["degraded"])
        # A source that is down but has a recent cached answer is served from
        # disk rather than blanked. That is only honest if the age is shown.
        stats["stale"] = _stale_ages(
            cisa_kev=kev, epss=epss, feodo=feodo, tor_exits=tor,
        )
        stats["transport"] = self._http.stats()
        return stats

    def _kev_stats(self, payload: Any, degraded: Dict[str, str]) -> Dict[str, Any]:
        if _failed(payload) or not isinstance(getattr(payload, "data", None), dict):
            degraded["cisa_kev"] = _reason(payload)
            return {"available": False}

        data = payload.data
        vulns = [v for v in data.get("vulnerabilities", []) if isinstance(v, dict)]
        now = datetime.now(timezone.utc)

        def added_within(days: int) -> int:
            cutoff = now - timedelta(days=days)
            count = 0
            for v in vulns:
                added = _parse_date(v.get("dateAdded"))
                if added and added >= cutoff:
                    count += 1
            return count

        overdue = 0
        due_soon = 0
        for v in vulns:
            due = _parse_date(v.get("dueDate"))
            if not due:
                continue
            if due < now:
                overdue += 1
            elif due <= now + timedelta(days=14):
                due_soon += 1

        vendors: Dict[str, int] = {}
        for v in vulns:
            vendor = (v.get("vendorProject") or "unknown").strip()
            vendors[vendor] = vendors.get(vendor, 0) + 1
        top_vendors = sorted(vendors.items(), key=lambda kv: kv[1], reverse=True)[:10]

        ransomware = sum(
            1 for v in vulns
            if str(v.get("knownRansomwareCampaignUse", "")).lower() == "known"
        )

        return {
            "available": True,
            "catalog_version": data.get("catalogVersion", ""),
            "total": len(vulns),
            "added_7d": added_within(7),
            "added_30d": added_within(30),
            "added_90d": added_within(90),
            "remediation_overdue": overdue,
            "remediation_due_14d": due_soon,
            "ransomware_linked": ransomware,
            "top_vendors": [{"vendor": k, "count": v} for k, v in top_vendors],
            "latest": [
                {
                    "cve": v.get("cveID"),
                    "vendor": v.get("vendorProject"),
                    "product": v.get("product"),
                    "name": v.get("vulnerabilityName"),
                    "added": v.get("dateAdded"),
                    "due": v.get("dueDate"),
                    "ransomware": str(v.get("knownRansomwareCampaignUse", "")).lower() == "known",
                }
                for v in sorted(vulns, key=lambda x: x.get("dateAdded", ""), reverse=True)[:15]
            ],
        }

    def _epss_stats(self, payload: Any, degraded: Dict[str, str]) -> Dict[str, Any]:
        if _failed(payload) or not isinstance(getattr(payload, "data", None), dict):
            degraded["epss"] = _reason(payload)
            return {"available": False}

        rows = [r for r in (payload.data.get("data") or []) if isinstance(r, dict)]
        top = [
            {
                "cve": r.get("cve"),
                "probability": _to_float(r.get("epss")),
                "percentile": _to_float(r.get("percentile")),
            }
            for r in rows
        ]
        return {
            "available": True,
            "model_date": payload.data.get("status-code") and payload.data.get("data-date") or "",
            "highest_risk": top,
        }

    def _botnet_stats(self, payload: Any, degraded: Dict[str, str]) -> Dict[str, Any]:
        if _failed(payload) or not isinstance(getattr(payload, "data", None), list):
            degraded["feodo"] = _reason(payload)
            return {"available": False}

        entries = [e for e in payload.data if isinstance(e, dict)]
        families: Dict[str, int] = {}
        countries: Dict[str, int] = {}
        for e in entries:
            fam = (e.get("malware") or "unknown").strip()
            families[fam] = families.get(fam, 0) + 1
            cc = (e.get("country") or "??").strip()
            countries[cc] = countries.get(cc, 0) + 1

        return {
            "available": True,
            "active_c2_servers": len(entries),
            "families": [
                {"family": k, "count": v}
                for k, v in sorted(families.items(), key=lambda kv: kv[1], reverse=True)[:10]
            ],
            "top_countries": [
                {"country_code": k, "count": v}
                for k, v in sorted(countries.items(), key=lambda kv: kv[1], reverse=True)[:10]
            ],
        }

    def _tor_stats(self, payload: Any, degraded: Dict[str, str]) -> Dict[str, Any]:
        if _failed(payload) or not isinstance(getattr(payload, "data", None), str):
            degraded["tor_exits"] = _reason(payload)
            return {"available": False}
        exits = [line.strip() for line in payload.data.splitlines() if line.strip()]
        return {"available": True, "tor_exit_nodes": len(exits)}

    # ═══════════════════════════════════════════════════════════════════════
    # Intelligence map
    # ═══════════════════════════════════════════════════════════════════════

    async def threat_map(self, limit: int = 120) -> Dict[str, Any]:
        """Geolocated attacker/C2 nodes, each attributed to the feed that listed it."""
        isc_task = self._http.get_json(ISC_TOP_SOURCES.format(limit=100), ttl=1800)
        feodo_task = self._http.get_json(FEODO_URL, ttl=1800)
        isc, feodo = await asyncio.gather(isc_task, feodo_task, return_exceptions=True)

        degraded: Dict[str, str] = {}
        # ip -> the record we know about it before geolocation
        pending: Dict[str, Dict[str, Any]] = {}

        if _failed(isc) or not isinstance(getattr(isc, "data", None), list):
            degraded["sans_isc"] = _reason(isc)
        else:
            for entry in isc.data:
                if not isinstance(entry, dict):
                    continue
                ip = _normalise_isc_ip(entry.get("ip"))
                if not ip:
                    continue
                attacks = _to_int(entry.get("attacks"))
                pending[ip] = {
                    "source": "SANS ISC",
                    "classification": "scanner",
                    "severity": "high" if attacks > 5000 else "medium",
                    "detail": {
                        "attacks": attacks,
                        "targets": _to_int(entry.get("targets")),
                        "first_seen": entry.get("mindate"),
                        "last_seen": entry.get("maxdate"),
                    },
                }

        if _failed(feodo) or not isinstance(getattr(feodo, "data", None), list):
            degraded["feodo"] = _reason(feodo)
        else:
            for entry in feodo.data:
                if not isinstance(entry, dict):
                    continue
                ip = (entry.get("ip_address") or "").strip()
                if not ip:
                    continue
                # A C2 listing outranks a scanner listing for the same address.
                pending[ip] = {
                    "source": "abuse.ch Feodo Tracker",
                    "classification": "botnet_c2",
                    "severity": "critical",
                    "detail": {
                        "malware": entry.get("malware"),
                        "port": entry.get("port"),
                        "status": entry.get("status"),
                        "first_seen": entry.get("first_seen"),
                        "last_online": entry.get("last_online"),
                    },
                }

        # C2 first — those are the nodes worth showing when the cap bites.
        ordered = sorted(
            pending.items(),
            key=lambda kv: (kv[1]["classification"] != "botnet_c2",
                            -_to_int(kv[1]["detail"].get("attacks"))),
        )[:limit]

        nodes = await self._geolocate([ip for ip, _ in ordered], dict(ordered), degraded)

        by_country: Dict[str, int] = {}
        by_class: Dict[str, int] = {}
        for n in nodes:
            if n.country:
                by_country[n.country] = by_country.get(n.country, 0) + 1
            by_class[n.classification] = by_class.get(n.classification, 0) + 1

        return {
            "generated_at": _now(),
            "count": len(nodes),
            "nodes": [n.to_dict() for n in nodes],
            "by_country": [
                {"country": k, "count": v}
                for k, v in sorted(by_country.items(), key=lambda kv: kv[1], reverse=True)
            ],
            "by_classification": by_class,
            "degraded": degraded,
            "stale": _stale_ages(sans_isc=isc, feodo=feodo),
        }

    async def _geolocate(
        self,
        ips: List[str],
        records: Dict[str, Dict[str, Any]],
        degraded: Dict[str, str],
    ) -> List[MapNode]:
        """Batch-geolocate public blocklist IPs. Ungeolocatable entries are dropped."""
        nodes: List[MapNode] = []
        for chunk_start in range(0, len(ips), _GEO_BATCH_MAX):
            chunk = ips[chunk_start:chunk_start + _GEO_BATCH_MAX]
            fetch = await self._http.post_json(
                _GEO_BATCH,
                [{"query": ip, "fields": "status,query,lat,lon,country,countryCode,city,org,as"}
                 for ip in chunk],
                ttl=3600,
            )
            if not fetch.ok or not isinstance(fetch.data, list):
                degraded["geo"] = fetch.error or "unexpected batch response"
                continue

            for geo in fetch.data:
                if not isinstance(geo, dict) or geo.get("status") != "success":
                    continue
                ip = geo.get("query", "")
                record = records.get(ip)
                if not record:
                    continue
                lat, lon = geo.get("lat"), geo.get("lon")
                if lat is None or lon is None:
                    continue
                nodes.append(MapNode(
                    ip=ip,
                    lat=float(lat),
                    lon=float(lon),
                    country=geo.get("country", ""),
                    country_code=geo.get("countryCode", ""),
                    city=geo.get("city", ""),
                    org=geo.get("org", ""),
                    asn=geo.get("as", ""),
                    source=record["source"],
                    classification=record["classification"],
                    severity=record["severity"],
                    detail=record["detail"],
                ))
        return nodes


# ── helpers ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _failed(result: Any) -> bool:
    """True when a gathered task raised, or the fetch itself reported failure."""
    if isinstance(result, BaseException):
        return True
    return not getattr(result, "ok", False)


def _reason(result: Any) -> str:
    if isinstance(result, BaseException):
        return f"{type(result).__name__}: {result}"
    return getattr(result, "error", "") or "unavailable"


def _stale_ages(**fetches: Any) -> Dict[str, int]:
    """Age in seconds of every payload served past its TTL. Empty when all fresh."""
    out: Dict[str, int] = {}
    for source_id, fetch in fetches.items():
        if getattr(fetch, "stale", False):
            out[source_id] = int(getattr(fetch, "stale_age_s", 0) or 0)
    return out


def _parse_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value[:len(fmt) + 2].strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalise_isc_ip(raw: Any) -> str:
    """ISC returns zero-padded octets ('008.008.008.008'); strip them."""
    if not isinstance(raw, str) or not raw:
        return ""
    parts = raw.strip().split(".")
    if len(parts) != 4:
        return raw.strip()
    try:
        return ".".join(str(int(p)) for p in parts)
    except ValueError:
        return raw.strip()


_shared_live: Optional[LiveIntel] = None


def shared_live_intel() -> LiveIntel:
    global _shared_live
    if _shared_live is None:
        _shared_live = LiveIntel()
    return _shared_live
