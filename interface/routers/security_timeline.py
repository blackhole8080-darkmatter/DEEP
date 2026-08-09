"""Unified live security dashboard endpoint.

Merges the raw device-level `security_alert` stream with the enriched
`security_alert_correlated` stream (anomaly/threat + MITRE ATT&CK + CVE
context) into one severity-scored, time-ordered feed, instead of the HUD
having to poll security.py + threat.py + anomaly.py separately.
See core/security/security_timeline.py.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.alert_dispatcher import SEVERITY_RANK
from interface.deps import require

router = APIRouter(prefix="/api/security", tags=["security-timeline"])


@router.get("/timeline")
async def security_timeline(
    limit: int = Query(50, ge=1, le=500),
    min_severity: Optional[str] = None,
):
    """Merged, severity-scored security event feed."""
    if min_severity is not None and min_severity.lower() not in SEVERITY_RANK:
        # Previously an unknown level silently returned everything, so a typo
        # in a filter read as "nothing is being filtered out" — the opposite of
        # what an operator narrowing to `critical` would conclude.
        raise HTTPException(
            status_code=422,
            detail=f"min_severity must be one of: {', '.join(SEVERITY_RANK)}",
        )
    timeline = require("security_timeline").get_timeline(
        limit=limit, min_severity=min_severity
    )
    return {"timeline": timeline}


@router.get("/timeline/stats")
async def security_timeline_stats():
    """Counts by severity and kind, for a dashboard summary widget."""
    return require("security_timeline").get_stats()
