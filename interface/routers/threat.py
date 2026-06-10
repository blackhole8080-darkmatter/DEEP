"""Threat classifier endpoints (v3)."""

import json
from pathlib import Path

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/threat", tags=["threat"])


@router.get("/status")
async def threat_status():
    """Return threat classifier operational status."""
    try:
        return services.threat_classifier.status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/predictions")
async def threat_predictions(limit: int = 20):
    """Return recent threat predictions."""
    try:
        predictions = await services.threat_classifier.get_recent_predictions(n=limit)
        return {"predictions": predictions}
    except Exception as e:
        return {"error": str(e)}


@router.post("/train")
async def threat_train():
    """Manually trigger threat classifier training."""
    try:
        result = await services.threat_classifier.train_model()
        return {"success": "error" not in result, "result": result}
    except Exception as e:
        return {"error": str(e)}


@router.get("/report")
async def threat_report():
    """Return the latest training report."""
    try:
        log_dir = Path("logs/threat")
        if not log_dir.exists():
            return {"reports": []}
        reports = sorted(log_dir.glob("train_*.json"), reverse=True)
        if not reports:
            return {"reports": []}
        latest = json.loads(reports[0].read_text(encoding="utf-8"))
        return {"latest": latest, "total_reports": len(reports)}
    except Exception as e:
        return {"error": str(e)}
