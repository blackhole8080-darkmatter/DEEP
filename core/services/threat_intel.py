"""Compatibility shims for the original /api/threats/* and /api/servers/live routes.

The real implementation now lives in :mod:`core.intel.live_stats`. These
functions exist so the threat globe and matrix waterfall keep working while the
frontend migrates to ``/api/intel/map``.

What changed underneath, and why:

* **No more fabricated infrastructure.** ``get_live_public_servers`` used to
  resolve ~94 NTP-pool hostnames and then label each result "Mobile Tower",
  "IXP" or "Datacenter" by drawing ``random.random()``. Those labels were
  invented, and a security console that invents findings is worse than one
  that shows nothing. It now returns an empty set with an explicit note:
  DEEP has no keyless source of global infrastructure topology.
* **No more blocking I/O on the event loop.** The old code ran synchronous
  ``urllib.urlopen`` calls with no timeout, so a hung upstream wedged the
  request until the client gave up.
* **Failures are visible.** The old code returned a stale cache forever on
  error, so a permanently-broken feed looked healthy.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.intel.live_stats import shared_live_intel
from core.intel.osint_investigator import OSINTInvestigator

logger = logging.getLogger(__name__)

_investigator = OSINTInvestigator()


async def get_live_threats() -> List[Dict[str, Any]]:
    """Geolocated attacker/C2 nodes, in the flat shape the globe already reads."""
    result = await shared_live_intel().threat_map(limit=120)
    return [
        {
            "ip": n["ip"],
            "lat": n["lat"],
            "lon": n["lon"],
            "country": n["country"],
            "city": n["city"],
            "org": n["org"],
            "source": n["source"],
            "classification": n["classification"],
            "severity": n["severity"],
            "detail": n["detail"],
        }
        for n in result["nodes"]
    ]


async def get_osint_details(ip: str) -> Dict[str, Any]:
    """Full dossier for one address — registry, routing, exposure and reputation."""
    dossier = await _investigator.investigate(ip)
    return dossier.to_dict()


async def get_live_public_servers() -> Dict[str, Any]:
    """Retired. See the module docstring — the old implementation invented its data."""
    return {
        "servers": [],
        "note": (
            "Retired: the previous implementation assigned infrastructure types at "
            "random. DEEP has no keyless source of global infrastructure topology, so "
            "it reports none. Use /api/intel/map for real, attributed threat nodes."
        ),
    }
