"""Predictive engine endpoints."""

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/api/predictive", tags=["predictive"])


@router.get("/suggestions")
async def get_predictions():
    """Get current predictive suggestions."""
    try:
        predictions = services.predictive_engine.get_predictions()
        return {"predictions": predictions}
    except Exception as e:
        return {"error": str(e)}


@router.get("/stats")
async def predictive_stats():
    """Get predictive engine statistics."""
    try:
        return services.predictive_engine.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/patterns")
async def get_patterns():
    """Get detected user behavior patterns."""
    try:
        return services.predictive_engine.get_patterns()
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
async def get_prediction_history(limit: int = 10):
    """Get recent predictions."""
    try:
        return {"predictions": services.predictive_engine.get_recent_predictions(limit)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/feedback")
async def prediction_feedback(data: dict):
    """Record user feedback on a prediction."""
    prediction_id = data.get("prediction_id")
    accepted = data.get("accepted")
    if not prediction_id or accepted is None:
        return {"error": "Missing prediction_id or accepted"}
    success = services.predictive_engine.record_feedback(prediction_id, accepted)
    return {"success": success}
