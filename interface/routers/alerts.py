"""Alert delivery: what went out, what was suppressed, and why.

The dispatcher's whole value is in what it *doesn't* send, so its decisions
have to be inspectable. `GET /api/alerts/status` shows the gates and the
per-channel health; `GET /api/alerts/recent` shows what actually left the
machine. Like `intel.py`, failures here are real status codes rather than a
200 carrying an error string.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.alert_dispatcher import SEVERITY_RANK, Alert
from interface.deps import services

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _dispatcher():
    dispatcher = getattr(services, "alert_dispatcher", None)
    if dispatcher is None:
        raise HTTPException(status_code=503, detail="alert dispatcher is not running")
    return dispatcher


@router.get("/status")
async def alert_status():
    """Severity floor, quiet hours, rate-limit budget and channel health."""
    return _dispatcher().status()


@router.get("/recent")
async def alert_recent(limit: int = Query(20, ge=1, le=50)):
    """Alerts that were actually delivered, newest first."""
    return {"alerts": _dispatcher().recent(limit=limit)}


class TestAlert(BaseModel):
    severity: str = Field("high", description="info | low | medium | high | critical")
    title: str = Field("Test alert", min_length=1, max_length=96)
    body: str = Field("Delivery test from DEEP.", min_length=1, max_length=512)


@router.post("/test")
async def alert_test(body: TestAlert):
    """Push one alert through the real channels.

    Notification setups fail quietly — a webhook typo or a missing notification
    daemon looks exactly like "nothing has happened yet". This bypasses the
    gates (dedupe, quiet hours, rate limit) so the answer is about the channels
    and nothing else, and reports which ones accepted it.
    """
    severity = body.severity.strip().lower()
    if severity not in SEVERITY_RANK:
        raise HTTPException(
            status_code=422,
            detail=f"severity must be one of: {', '.join(SEVERITY_RANK)}",
        )

    dispatcher = _dispatcher()
    alert = Alert(
        id="alert_test",
        kind="test",
        severity=severity,
        title=body.title,
        body=body.body,
        source="manual_test",
        dedupe_key="test",
    )
    results = {
        channel.name: await dispatcher._send_one(channel, alert)
        for channel in dispatcher.channels
    }
    return {"sent": alert.to_dict(), "channels": results}
