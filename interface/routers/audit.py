"""Audit endpoints."""
from fastapi import APIRouter
from interface.deps import services

router = APIRouter(tags=["audit"])


@router.get("/audit/log")
async def audit_log_query(
    entry_type: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    offset: int = 0,
    start: str | None = None,
    end: str | None = None,
):
    """Query the immutable audit log with filters and pagination."""
    try:
        entries = await services.audit_trail.query(
            entry_type=entry_type,
            actor=actor,
            start_time=start,
            end_time=end,
            limit=limit,
            offset=offset,
        )
        return {"entries": [e.__dict__ for e in entries], "count": len(entries)}
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/threats")
async def audit_threats(hours: int = 24):
    """Get security threat entries from the audit log."""
    try:
        entries = await services.audit_trail.get_threat_log(hours=hours)
        return {"entries": [e.__dict__ for e in entries]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/session")
async def audit_current_session():
    """Get current session info."""
    try:
        session_mgr = getattr(services, "session_manager", None)
        if session_mgr is None:
            return {"active": False, "error": "session manager unavailable"}
        session = session_mgr.get_current()
        return session.__dict__ if session else {"active": False}
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/session/{session_id}")
async def audit_session_by_id(session_id: str):
    """Get all audit entries for a specific session."""
    try:
        entries = await services.audit_trail.get_session_log(session_id)
        return {"entries": [e.__dict__ for e in entries]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/stats")
async def audit_stats():
    """Audit trail statistics and integrity status."""
    try:
        return await services.audit_trail.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/audit/verify")
async def audit_verify():
    """Run hash chain integrity verification."""
    try:
        report = await services.audit_trail.verify_integrity()
        return {
            "intact": report.intact,
            "total_entries": report.total_entries,
            "verified": report.verified,
            "failures": report.failures,
            "first_failure_id": report.first_failure_id,
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/export/{session_id}")
async def audit_export_session(session_id: str, format: str = "text"):
    """Export a session log to file (json or text)."""
    try:
        path = await services.audit_trail.export_session(session_id, format=format)
        return {"path": path, "format": format}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# RETRAINING ENDPOINTS (v3)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai/retraining/status")
async def retraining_status():
    """Return retraining scheduler status."""
    try:
        return services.retraining_scheduler.status()
    except Exception as e:
        return {"error": str(e)}


