"""Unified live security dashboard endpoint.

Merges the raw device-level `security_alert` stream with the enriched
`security_alert_correlated` stream (anomaly/threat + MITRE ATT&CK + CVE
context) into one severity-scored, time-ordered feed, instead of the HUD
having to poll security.py + threat.py + anomaly.py separately.
See core/security/security_timeline.py.
"""

from typing import Optional

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/api/security", tags=["security-timeline"])


@router.get("/timeline")
async def security_timeline(limit: int = 50, min_severity: Optional[str] = None):
    """Merged, severity-scored security event feed."""
    try:
        return {"timeline": services.security_timeline.get_timeline(limit=limit, min_severity=min_severity)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/timeline/stats")
async def security_timeline_stats():
    """Counts by severity and kind, for a dashboard summary widget."""
    try:
        return services.security_timeline.get_stats()
    except Exception as e:
        return {"error": str(e)}
