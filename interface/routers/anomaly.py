"""Anomaly endpoints."""
from fastapi import APIRouter
from typing import Optional
from interface.deps import services

router = APIRouter(tags=["anomaly"])


@router.get("/anomaly/status")
async def anomaly_status():
    """Return anomaly services.anomaly_detector operational status."""
    try:
        return anomaly_services.anomaly_detector.status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/anomaly/recent")
async def anomaly_recent(hours: int = 24):
    """Return recent anomalies detected."""
    try:
        anomalies = await anomaly_services.anomaly_detector.get_recent_anomalies(hours=hours)
        return {"anomalies": [a.__dict__ for a in anomalies]}
    except Exception as e:
        return {"error": str(e)}


@router.get("/anomaly/stats")
async def anomaly_stats():
    """Return anomaly statistics for today."""
    try:
        return await anomaly_services.anomaly_detector.get_anomaly_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/anomaly/baseline")
async def anomaly_baseline():
    """Return baseline collection status for system and network."""
    try:
        return {
            "system": system_baseline.status(),
            "network": network_baseline.status(),
        }
    except Exception as e:
        return {"error": str(e)}


