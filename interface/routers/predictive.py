"""Predictive engine endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from interface.deps import require

router = APIRouter(prefix="/api/predictive", tags=["predictive"])


@router.get("/suggestions")
async def get_predictions():
    """Get current predictive suggestions."""
    return {"predictions": require("predictive_engine").get_predictions()}


@router.get("/stats")
async def predictive_stats():
    """Get predictive engine statistics."""
    return require("predictive_engine").get_stats()


@router.get("/patterns")
async def get_patterns():
    """Get detected user behavior patterns."""
    return require("predictive_engine").get_patterns()


@router.get("/history")
async def get_prediction_history(limit: int = Query(10, ge=1, le=200)):
    """Get recent predictions."""
    return {"predictions": require("predictive_engine").get_recent_predictions(limit)}


class Feedback(BaseModel):
    prediction_id: str = Field(..., min_length=1, max_length=128)
    accepted: bool


@router.post("/feedback")
async def prediction_feedback(body: Feedback):
    """Record user feedback on a prediction."""
    if not require("predictive_engine").record_feedback(
        body.prediction_id, body.accepted
    ):
        # record_feedback returns False for an id it has never seen. That was
        # reported as {"success": false} at 200, which the HUD rendered as a
        # successful call with a falsy field.
        raise HTTPException(
            status_code=404, detail=f"no such prediction: {body.prediction_id}"
        )
    return {"success": True}
