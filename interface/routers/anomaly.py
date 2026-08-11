"""Anomaly endpoints."""
from fastapi import APIRouter, Query

from interface.deps import require

router = APIRouter(tags=["anomaly"])


@router.get("/anomaly/status")
async def anomaly_status():
    """Return anomaly_detector operational status."""
    return require("anomaly_detector").status()


@router.get("/anomaly/recent")
async def anomaly_recent(hours: int = Query(24, ge=1, le=720)):
    """Return recent anomalies detected."""
    anomalies = await require("anomaly_detector").get_recent_anomalies(hours=hours)
    return {"anomalies": [a.__dict__ for a in anomalies]}


@router.get("/anomaly/stats")
async def anomaly_stats():
    """Return anomaly statistics for today."""
    return await require("anomaly_detector").get_anomaly_stats()


@router.get("/anomaly/baseline")
async def anomaly_baseline():
    """Return baseline collection status for system and network."""
    return {
        "system": require("system_baseline").status(),
        "network": require("network_baseline").status(),
    }
