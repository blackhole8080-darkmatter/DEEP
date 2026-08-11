"""Audit endpoints."""
from fastapi import APIRouter, HTTPException, Query

from interface.deps import require

router = APIRouter(tags=["audit"])

_EXPORT_FORMATS = ("json", "text")


@router.get("/audit/log")
async def audit_log_query(
    entry_type: str | None = None,
    actor: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start: str | None = None,
    end: str | None = None,
):
    """Query the immutable audit log with filters and pagination."""
    entries = await require("audit_trail").query(
        entry_type=entry_type,
        actor=actor,
        start_time=start,
        end_time=end,
        limit=limit,
        offset=offset,
    )
    return {"entries": [e.__dict__ for e in entries], "count": len(entries)}


@router.get("/audit/threats")
async def audit_threats(hours: int = Query(24, ge=1, le=8760)):
    """Get security threat entries from the audit log."""
    entries = await require("audit_trail").get_threat_log(hours=hours)
    return {"entries": [e.__dict__ for e in entries]}


@router.get("/audit/session")
async def audit_current_session():
    """Get current session info."""
    session = require("session_manager").get_current()
    return session.__dict__ if session else {"active": False}


@router.get("/audit/session/{session_id}")
async def audit_session_by_id(session_id: str):
    """Get all audit entries for a specific session."""
    entries = await require("audit_trail").get_session_log(session_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"no audit entries for session '{session_id}'",
        )
    return {"entries": [e.__dict__ for e in entries]}


@router.get("/audit/stats")
async def audit_stats():
    """Audit trail statistics and integrity status."""
    return await require("audit_trail").get_stats()


@router.post("/audit/verify")
async def audit_verify():
    """Run hash chain integrity verification."""
    report = await require("audit_trail").verify_integrity()
    return {
        "intact": report.intact,
        "total_entries": report.total_entries,
        "verified": report.verified,
        "failures": report.failures,
        "first_failure_id": report.first_failure_id,
    }


@router.get("/audit/export/{session_id}")
async def audit_export_session(session_id: str, format: str = "text"):
    """Export a session log to file (json or text)."""
    if format not in _EXPORT_FORMATS:
        # export_session treats anything that isn't "json" as text, so a typo
        # silently produced the wrong format and reported success.
        raise HTTPException(
            status_code=422,
            detail=f"format must be one of: {', '.join(_EXPORT_FORMATS)}",
        )
    trail = require("audit_trail")
    if not await trail.get_session_log(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"no audit entries for session '{session_id}' — nothing to export",
        )
    return {"path": await trail.export_session(session_id, format=format),
            "format": format}


# ═══════════════════════════════════════════════════════════════════════════════
# RETRAINING ENDPOINTS (v3)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/ai/retraining/status")
async def retraining_status():
    """Return retraining scheduler status."""
    return require("retraining_scheduler").status()
