"""Threat classifier endpoints (v3)."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from interface.deps import require

router = APIRouter(prefix="/threat", tags=["threat"])

_REPORT_DIR = Path("logs/threat")


@router.get("/status")
async def threat_status():
    """Return threat classifier operational status."""
    return require("threat_classifier").status()


@router.get("/predictions")
async def threat_predictions(limit: int = Query(20, ge=1, le=500)):
    """Return recent threat predictions."""
    predictions = await require("threat_classifier").get_recent_predictions(n=limit)
    return {"predictions": predictions}


@router.post("/train")
async def threat_train():
    """Manually trigger threat classifier training."""
    result = await require("threat_classifier").train_model()
    if isinstance(result, dict) and result.get("error"):
        # Training refuses on too little data, which is a legitimate answer
        # about the request rather than a server fault.
        raise HTTPException(status_code=409, detail=str(result["error"]))
    return {"success": True, "result": result}


@router.get("/report")
async def threat_report():
    """Return the latest training report."""
    reports = sorted(_REPORT_DIR.glob("train_*.json"), reverse=True) \
        if _REPORT_DIR.exists() else []
    if not reports:
        raise HTTPException(
            status_code=404,
            detail="no training reports yet — POST /threat/train to produce one",
        )
    try:
        latest = json.loads(reports[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # A corrupt report on disk is the server's problem, and saying so
        # beats handing back an empty object that reads as "no reports".
        raise HTTPException(
            status_code=500, detail=f"report {reports[0].name} is unreadable"
        ) from exc
    return {"latest": latest, "total_reports": len(reports)}
